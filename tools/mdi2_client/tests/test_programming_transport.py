import struct
import unittest

from mdi2.programming_transport import (
    CorrelationUnproven,
    OfflineFrameDecoder,
    OfflineResponseGuard,
    OfflineSerializedSession,
    OfflineTeardown,
    ProgrammingUnavailable,
    _required_positive_prefix,
    build_one_shot,
    open_live_programming_transport,
)


class RequiredPositivePrefixTests(unittest.TestCase):
    """The guard rejects any request whose service is not registered here, so
    every service program() sends MUST round-trip. 85 02 / 28 03 were added to
    the SPS sequence; without registration the live guard refused them with
    'request cannot be safely sent' (observed 2026-11-10)."""

    def test_dtc_and_comm_control_registered(self):
        # 85 ControlDTCSetting -> C5; 28 CommunicationControl -> 68. Subfunction echoed.
        self.assertEqual(_required_positive_prefix(b"\x85\x02"), b"\xc5\x02")
        self.assertEqual(_required_positive_prefix(b"\x28\x03\x01"), b"\x68\x03")

    def test_guard_round_trips_85_and_28(self):
        for req, resp in ((b"\x85\x02", b"\xc5\x02"), (b"\x28\x03\x01", b"\x68\x03")):
            state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
            state.begin(req, _required_positive_prefix(req))
            self.assertEqual(state.accept(resp), "positive")


class ProgrammingTransportTests(unittest.TestCase):
    def test_fragmented_and_coalesced_frames(self):
        frames = (struct.pack("<II", 12, 0x452) + bytes(4) +
                  struct.pack("<II", 16, 0x462) + bytes(8))
        for split in range(len(frames) + 1):
            decoder = OfflineFrameDecoder()
            result = decoder.feed(frames[:split]) + decoder.feed(frames[split:])
            decoder.finish()
            self.assertEqual(result, [(0x452, bytes(4)), (0x462, bytes(8))])

    def test_decoder_rejects_invalid_and_truncated_frames(self):
        for frame in (struct.pack("<II", 7, 1), struct.pack("<II", 65, 1)):
            decoder = OfflineFrameDecoder(max_frame=64, max_buffer=128)
            with self.assertRaises(ValueError):
                decoder.feed(frame)
            with self.assertRaises(CorrelationUnproven):
                decoder.feed(b"")
        for size in (3, 9):
            decoder = OfflineFrameDecoder()
            decoder.feed((struct.pack("<II", 12, 0x452) + bytes(4))[:size])
            with self.assertRaisesRegex(ValueError, "truncated"):
                decoder.finish()

    def test_decoder_caps_coalesced_input(self):
        decoder = OfflineFrameDecoder(max_frame=16, max_buffer=32)
        with self.assertRaisesRegex(ValueError, "buffered"):
            decoder.feed(bytes(33))
        with self.assertRaises(CorrelationUnproven):
            decoder.finish()

    def test_captured_teardown_sequence(self):
        radio, keepalive = 0x25000006, 0x25000007
        teardown = OfflineTeardown(radio, keepalive)
        self.assertEqual(teardown.next_frame(), struct.pack("<III", 12, 0x451, keepalive))
        with self.assertRaises(CorrelationUnproven):
            teardown.next_frame()
        teardown.acknowledge(0x452, bytes(4))
        self.assertEqual(teardown.next_frame(), struct.pack("<III", 12, 0x461, radio))
        teardown.acknowledge(0x462, bytes(8))
        self.assertEqual(teardown.next_frame(), struct.pack("<III", 12, 0x451, radio))
        teardown.acknowledge(0x452, bytes(4))
        self.assertTrue(teardown.complete)
        with self.assertRaises(CorrelationUnproven):
            teardown.next_frame()

    def test_teardown_fails_closed_on_bad_ack_or_timeout(self):
        for mid, payload in ((0x462, bytes(4)), (0x452, b"\x01\x00\x00\x00"),
                             (0x452, bytes(3))):
            with self.subTest(mid=mid, payload=payload):
                teardown = OfflineTeardown(1, 2)
                teardown.next_frame()
                with self.assertRaises(CorrelationUnproven):
                    teardown.acknowledge(mid, payload)
                self.assertTrue(teardown.poisoned)
                with self.assertRaises(CorrelationUnproven):
                    teardown.next_frame()
        teardown = OfflineTeardown(1, 2)
        teardown.next_frame()
        teardown.fail()
        with self.assertRaises(CorrelationUnproven):
            teardown.acknowledge(0x452, bytes(4))

    def test_serialized_model_requires_explicit_ordering_assumption(self):
        for flag in (False, 1, "true"):
            with self.subTest(flag=flag), self.assertRaises(CorrelationUnproven):
                OfflineSerializedSession(assume_fresh_ordered_no_late_events=flag)

    def test_serialized_model_allows_14_downloads_under_assumption(self):
        state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
        for _ in range(14):
            state.begin(b"\x34\x00\x44", b"\x74")
            with self.assertRaises(CorrelationUnproven):
                state.begin(b"\x34\x00\x44", b"\x74")
            self.assertEqual(state.accept(b"\x7f\x34\x78"), "pending")
            self.assertEqual(state.accept(b"\x74\x20\x0f\xff"), "positive")
            state.begin(b"\x36\x01\x00", b"\x76\x01")
            self.assertEqual(state.accept(b"\x76\x01"), "positive")
            state.begin(b"\x37", b"\x77")
            self.assertEqual(state.accept(b"\x77"), "positive")

    def test_serialized_model_never_retries_after_ambiguous_outcome(self):
        # sid-mismatched NRC, short/long malformed NRC, unexpected positive.
        # (A correlated `7F 34 xx` is terminal, not ambiguous; see below.)
        for response in (b"\x7f\x22\x78", b"\x7f\x34", b"\x7f\x34\x31\x00", b"\x76\x01"):
            state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
            state.begin(b"\x34\x00\x44", b"\x74")
            with self.assertRaises(CorrelationUnproven):
                state.accept(response)
            with self.assertRaises(CorrelationUnproven):
                state.begin(b"\x34\x00\x44", b"\x74")
        state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
        state.begin(b"\x37", b"\x77")
        state.fail()
        with self.assertRaises(CorrelationUnproven):
            state.accept(b"\x77")

    def test_serialized_model_rejects_malformed_transfer_ack(self):
        for request, prefix, malformed in (
            (b"\x34\x00\x44", b"\x74", b"\x74"),
            (b"\x34\x00\x44", b"\x74", b"\x74\x20\x0f"),
            (b"\x34\x00\x44", b"\x74", b"\x74\x20\x00\x02"),
            (b"\x36\x01\x00", b"\x76\x01", b"\x76\x01\x00"),
            (b"\x37", b"\x77", b"\x77\x00"),
        ):
            state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
            state.begin(request, prefix)
            with self.subTest(malformed=malformed), self.assertRaises(CorrelationUnproven):
                state.accept(malformed)
            self.assertTrue(state.poisoned)

    def test_serialized_model_terminal_nrc_completes_without_poison(self):
        # Live 2026-11-10: F18C answered 7F 22 31 (requestOutOfRange). That is
        # the correlated terminal answer; the same session must carry on.
        state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
        state.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertEqual(state.accept(b"\x7f\x22\x31"), "negative")
        self.assertFalse(state.poisoned)
        self.assertIsNone(state.pending)
        state.begin(b"\x22\xf1\x90", b"\x62\xf1\x90")
        self.assertEqual(state.accept(b"\x62\xf1\x90" + b"1" * 17), "positive")
        self.assertFalse(state.poisoned)
        # Terminal means terminal: anything after completion is unsolicited.
        with self.assertRaises(CorrelationUnproven):
            state.accept(b"\x62\xf1\x8c\x00")
        self.assertTrue(state.poisoned)

    def test_serialized_model_pending_keeps_request_in_flight(self):
        state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
        state.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertEqual(state.accept(b"\x7f\x22\x78"), "pending")
        self.assertEqual(state.pending, (0x22, b"\x62\xf1\x8c"))
        self.assertFalse(state.poisoned)
        with self.assertRaises(CorrelationUnproven):  # still in flight
            state.begin(b"\x22\xf1\x90", b"\x62\xf1\x90")
        self.assertFalse(state.poisoned)
        self.assertEqual(state.accept(b"\x7f\x22\x31"), "negative")
        self.assertIsNone(state.pending)

    def test_serialized_model_malformed_or_foreign_nrc_still_poisons(self):
        for response in (b"\x7f\x22", b"\x7f\x22\x31\x00", b"\x7f\x34\x31", b"\x7f\x34\x78"):
            with self.subTest(response=response):
                state = OfflineSerializedSession(assume_fresh_ordered_no_late_events=True)
                state.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
                with self.assertRaisesRegex(CorrelationUnproven, "negative response"):
                    state.accept(response)
                self.assertTrue(state.poisoned)
                with self.assertRaises(CorrelationUnproven):
                    state.begin(b"\x22\xf1\x90", b"\x62\xf1\x90")

    def test_single_shot_layout_and_4095_byte_limit(self):
        # Vehicle-tested channel 0x25: marker is 0x2510, byte-identical to the
        # pre-fix hardcoded constant. The handle high byte is the D-PDU channel.
        uds = b"\x36\x01" + bytes(4093)
        frame = build_one_shot(0x25000006, 7, 0x14DA80F1, uds)
        length, mid = struct.unpack_from("<II", frame)
        self.assertEqual(length, len(frame))
        self.assertEqual(mid, 0x463)
        handle, cop, marker, kind, zero, data_len = struct.unpack_from("<IHHHHI", frame, 8)
        self.assertEqual((handle, cop, marker, kind, zero), (0x25000006, 7, 0x2510, 0x8004, 0))
        self.assertEqual(data_len, len(uds) + 4)
        self.assertEqual(frame[24:28], bytes.fromhex("14da80f1"))
        self.assertEqual(frame[28:28 + len(uds)], uds)
        with self.assertRaisesRegex(ValueError, "4095"):
            build_one_shot(1, 2, 3, bytes(4096))

    def test_single_shot_marker_derives_from_channel(self):
        # The 0x463 marker is (channel << 8) | 0x10, not a fixed 0x2510.
        # Byte-identity on 0x25 is proven against the fully hand-built frame;
        # a non-0x25 channel (0x2C) must move the marker to 0x2C10.
        uds = b"\x22\xf1\x82"
        data = (0x14DA80F1).to_bytes(4, "big") + uds
        for channel, want_marker in ((0x25, 0x2510), (0x2C, 0x2C10), (0x1E, 0x1E10)):
            handle = (channel << 24) | 0x06
            frame = build_one_shot(handle, 7, 0x14DA80F1, uds)
            marker = struct.unpack_from("<H", frame, 14)[0]
            with self.subTest(channel=channel):
                self.assertEqual(marker, want_marker)
                self.assertEqual(marker, (channel << 8) | 0x10)
                if channel == 0x25:
                    payload = (struct.pack("<IHHHHI", handle, 7, 0x2510, 0x8004, 0, len(data))
                               + data + b"\x01"
                               + struct.pack("<IiiIIII", 0, 1, 0, 0, 4, 0x40010020, 0))
                    expected = struct.pack("<II", len(payload) + 8, 0x463) + payload
                    self.assertEqual(frame, expected)

    def test_live_programming_is_unconditionally_unavailable(self):
        with self.assertRaises(ProgrammingUnavailable):
            open_live_programming_transport()

    def test_pending_then_positive_and_repeated_74_rejected(self):
        guard = OfflineResponseGuard()
        guard.begin(b"\x34\x00\x44", b"\x74")
        self.assertEqual(guard.accept(b"\x7f\x34\x78"), "pending")
        self.assertEqual(guard.accept(b"\x74\x20\x0f\xff"), "positive")
        with self.assertRaisesRegex(CorrelationUnproven, "indistinguishable"):
            guard.begin(b"\x34\x00\x44", b"\x74")
        self.assertTrue(guard.poisoned)

    def test_overlapping_positive_prefixes_rejected(self):
        guard = OfflineResponseGuard()
        guard.begin(b"\x34\x00\x44", b"\x74\x20")
        self.assertEqual(guard.accept(b"\x74\x20\x00\xff"), "positive")
        with self.assertRaises(CorrelationUnproven):
            guard.begin(b"\x34\x00\x44", b"\x74")

    def test_wrong_sid_or_malformed_negative_poisons_session(self):
        # In-flight sid is 36: 7F 22 / 7F 34 are foreign; 7F 36 (2 bytes) and
        # 7F 36 31 00 (4 bytes) are malformed; 74 20 is a wrong positive.
        for response in (b"\x7f\x22\x78", b"\x7f\x34\x31", b"\x7f\x36",
                         b"\x7f\x36\x31\x00", b"\x74\x20"):
            with self.subTest(response=response):
                guard = OfflineResponseGuard()
                guard.begin(b"\x36\x01\x00", b"\x76\x01")
                with self.assertRaises(CorrelationUnproven):
                    guard.accept(response)
                with self.assertRaises(CorrelationUnproven):
                    guard.begin(b"\x36\x02\x00", b"\x76\x02")

    def test_required_echo_must_match_before_request_is_recorded(self):
        invalid = (
            (b"\x22\xf1\x90", b"\x62"),
            (b"\x22\xf1\x90", b"\x62\xf1\x98"),
            (b"\x27\x01", b"\x67"),
            (b"\x27\x01", b"\x67\x02"),
            (b"\x36\x01\x00", b"\x76"),
            (b"\x36\x01\x00", b"\x76\x02"),
            (b"\x31\x01\x02\x49", b"\x71\x01"),
            (b"\x10\x03", b"\x50\x02"),
            (b"\x11\x01", b"\x51"),
            (b"\x2e\xf1\x90\x41", b"\x6e\xf1"),
            (b"\x3e\x80", b"\x7e\x80"),
            (b"\x22\xf1\x90\xf1\x98", b"\x62\xf1\x90"),
        )
        for request, prefix in invalid:
            with self.subTest(request=request, prefix=prefix):
                guard = OfflineResponseGuard()
                with self.assertRaises(ValueError):
                    guard.begin(request, prefix)
                self.assertIsNone(guard.pending)
                self.assertFalse(guard.used)

    def test_wrong_did_seed_and_block_response_poison(self):
        for request, prefix, wrong in (
            (b"\x22\xf1\x90", b"\x62\xf1\x90", b"\x62\xf1\x98\x00"),
            (b"\x27\x01", b"\x67\x01", b"\x67\x02"),
            (b"\x36\x01\x00", b"\x76\x01", b"\x76\x02"),
        ):
            with self.subTest(request=request):
                guard = OfflineResponseGuard()
                guard.begin(request, prefix)
                with self.assertRaises(CorrelationUnproven):
                    guard.accept(wrong)
                self.assertTrue(guard.poisoned)

    def test_timeout_requires_new_session(self):
        guard = OfflineResponseGuard()
        guard.begin(b"\x22\xf1\x82", b"\x62\xf1\x82")
        guard.fail()
        with self.assertRaises(CorrelationUnproven):
            guard.accept(b"\x62\xf1\x82\x00")

    def test_unsolicited_response_permanently_poisons_guard(self):
        for after_success in (False, True):
            guard = OfflineResponseGuard()
            if after_success:
                guard.begin(b"\x22\xf1\x82", b"\x62\xf1\x82")
                self.assertEqual(guard.accept(b"\x62\xf1\x82\x00"), "positive")
            with self.subTest(after_success=after_success), self.assertRaises(CorrelationUnproven):
                guard.accept(b"\x62\xf1\x82\x00")
            self.assertTrue(guard.poisoned)
            with self.assertRaises(CorrelationUnproven):
                guard.begin(b"\x22\xf1\xa0", b"\x62\xf1\xa0")

    def test_guard_terminal_nrc_completes_without_poison(self):
        guard = OfflineResponseGuard()
        guard.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertEqual(guard.accept(b"\x7f\x22\x78"), "pending")
        self.assertEqual(guard.pending, (0x22, b"\x62\xf1\x8c"))
        self.assertEqual(guard.accept(b"\x7f\x22\x31"), "negative")
        self.assertFalse(guard.poisoned)
        self.assertIsNone(guard.pending)
        # Same instance proceeds to the next DID.
        guard.begin(b"\x22\xf1\x90", b"\x62\xf1\x90")
        self.assertEqual(guard.accept(b"\x62\xf1\x90" + b"1" * 17), "positive")
        self.assertFalse(guard.poisoned)
        # The negative does not release the prefix: re-asking F18C on this
        # guard is still refused as indistinguishable (unchanged conservatism).
        with self.assertRaisesRegex(CorrelationUnproven, "indistinguishable"):
            guard.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")

    def test_guard_malformed_or_foreign_nrc_still_poisons(self):
        for response in (b"\x7f\x22", b"\x7f\x22\x31\x00", b"\x7f\x34\x31", b"\x7f\x34\x78"):
            with self.subTest(response=response):
                guard = OfflineResponseGuard()
                guard.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
                with self.assertRaisesRegex(CorrelationUnproven, "negative response"):
                    guard.accept(response)
                self.assertTrue(guard.poisoned)

    def test_guard_accept_event_reports_terminal_nrc(self):
        handle, cop, can_id = 0x2A000002, 1, 0x145AF180

        def event(uds):
            payload = bytearray(82)
            struct.pack_into("<II", payload, 0, handle, 1)
            struct.pack_into("<H", payload, 20, cop)
            payload[70:74] = can_id.to_bytes(4, "big")
            struct.pack_into("<I", payload, 74, len(uds) + 4)
            payload[78:82] = payload[70:74]
            return bytes(payload + uds)

        guard = OfflineResponseGuard()
        guard.begin(b"\x22\xf1\x8c", b"\x62\xf1\x8c")
        self.assertEqual(guard.accept_event(event(b"\x7f\x22\x31"), handle=handle, cop=cop, can_id=can_id),
                         "negative")
        self.assertFalse(guard.poisoned)
        self.assertIsNone(guard.pending)


if __name__ == "__main__":
    unittest.main()
