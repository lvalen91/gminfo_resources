"""Wire-format and failure-path tests; no CAN interface is opened."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
from mdi2.vip_dev_memory import (DevMemoryError, VipDevMemory, DEV_REQUEST_ID,
                                 DOWNLOAD, SET_MTA, UPLOAD)


class Message:
    def __init__(self, arbitration_id, data, is_extended_id=False):
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_extended_id = is_extended_id


class Bus:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []

    def send(self, message, timeout=None):
        self.sent.append(message)

    def recv(self, timeout=None):
        return next(self.replies, None)


def fake_frame(payload):
    return Message(DEV_REQUEST_ID, payload)


def test_read_uses_little_endian_mta_and_exact_response_length():
    bus = Bus([Message(0x614, b"\xff"), Message(0x614, b"\xffabcd")])
    client = VipDevMemory(bus)
    with patch.object(VipDevMemory, "_frame", side_effect=fake_frame):
        assert client.read(0xFEBF0BF8, 4) == b"abcd"
    assert [bytes(frame.data) for frame in bus.sent] == [
        bytes([SET_MTA, 0, 0, 0, 0xF8, 0x0B, 0xBF, 0xFE]), bytes([UPLOAD, 4])]


def test_write_is_bounded_and_sends_download_after_mta():
    bus = Bus([Message(0x614, b"\xff"), Message(0x614, b"\xff")])
    client = VipDevMemory(bus)
    with patch.object(VipDevMemory, "_frame", side_effect=fake_frame):
        client.write(0x12345678, b"\x01\x02\x03\x04")
    assert [bytes(frame.data) for frame in bus.sent] == [
        bytes([SET_MTA, 0, 0, 0, 0x78, 0x56, 0x34, 0x12]), bytes([DOWNLOAD, 4, 1, 2, 3, 4])]


def test_negative_reply_and_invalid_lengths_fail_closed():
    bus = Bus([Message(0x614, b"\xfe\x22")])
    client = VipDevMemory(bus)
    with patch.object(VipDevMemory, "_frame", side_effect=fake_frame):
        try:
            client.connect()
        except DevMemoryError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("negative reply was accepted")
    for length in (0, 7):
        try:
            client.write(0, bytes(length))
        except ValueError:
            pass
        else:
            raise AssertionError("invalid write size was accepted")
