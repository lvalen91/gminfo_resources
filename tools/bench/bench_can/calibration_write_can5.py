#!/usr/bin/env python3
"""Calibration write over CAN5/CANable (not T1) -- the documented-successful transport.

platform/can_bench_experiments.md "Full genuine LTZ/HC rewrite through CANable" is explicit:
T1 stock-transfer attempts failed pre-transfer (NRC70); programming/finalization used
CAN5/CANable. This script is therefore a minimal, mechanical adaptation of
tools/bench/bench_can/boot_radio_elk.py's already-reviewed CanDiagnostics class (same
CAN613/614 XCP route, same CAN-ISO-TP UDS transport, same keepalive-replay architecture)
-- NOT new protocol logic. The only changes from boot_radio_elk.py:
  1. select_word/read_word/write_word take an explicit address (boot_radio_elk.py hardcodes
     the ELK gate address; can0_dev.py already made this exact generalization for the
     calibration verifier words, independently reviewed correct).
  2. A write_calibration() method chains the already-validated UDS byte sequence from
     pi_dashboard/backend/app.py's _uds_cal_transfer (10 03 / 27 01 / 27 02+DEGENERATE_KEY /
     31 01 FF01 / 31 01 021E / 10 02 / 34 / 36.. / 37 / 22 F0F1), sent via self.uds() (CAN
     ISO-TP) instead of the T1 UDSClient, and the CAN613/614 save/override/restore sequence
     from can0_dev.py's VERIFIER_WORDS/MARKER_VALUES -- both already-reviewed, not new.
boot_radio_elk.py's own uds() already raises on any non-matching positive-response byte, so a
rejected step stops the sequence immediately (no separate "ok" bookkeeping needed, no risk of
the dashboard's earlier false-success bug recurring here).
"""

import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import queue
import signal
import struct
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boot_radio_elk import CanDiagnostics, KEEPALIVE_ID, StopReplay, validate_keepalive  # noqa: E402


def _load_mdi2_readback():
    """Load mdi2's own validated F182 parser/comparator (calibration_payloads.Calibration,
    calibration_readback.parse_f182/calibration_record) directly by file, bypassing
    mdi2/__init__.py -- that package eagerly imports crypto.py (pycryptodome, for talking
    to a real MDI2 dongle), a dependency this bench venv doesn't have and doesn't need for
    two pure, offline, dependency-free modules. Same importlib.util pattern this script
    already uses below for can_bench_emulator.py."""
    import types
    mdi2_dir = Path(__file__).resolve().parents[2] / 'mdi2_client' / 'mdi2'
    stub = types.ModuleType('mdi2')
    stub.__path__ = [str(mdi2_dir)]
    sys.modules['mdi2'] = stub

    def load(name):
        spec = importlib.util.spec_from_file_location(f'mdi2.{name}', mdi2_dir / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    payloads = load('calibration_payloads')
    readback = load('calibration_readback')
    return payloads.Calibration, readback.parse_f182, readback.calibration_record


Calibration, parse_f182, calibration_record = _load_mdi2_readback()

VERIFIER_WORDS = (0xFEBF0BF8, 0xFEBF0BFC)
MARKER_VALUES = {0xFEBF0BF8: bytes.fromhex("A5163829"), 0xFEBF0BFC: bytes.fromhex("5AE9C7D6")}
DEGENERATE_KEY = bytes(12)  # pi_dashboard/backend/diagdata.py DEGENERATE_KEY

# Programming-session precondition, verified byte-for-byte against a real accepted
# 021E/10 02 exchange in ~/.codex/sessions/2026/11/16/...fc2c.../ (lines 442, 789):
# 0x284 = all-zero (authenticated system power-mode Off), NOT raw=2/Run.
# 0x20D = the pinned native harness byte string (af176db58210) with byte5 bit7 set
# (0x10 | 0x80 = 0x90), per platform/can_network.md:64-65,256,499.
PRECONDITION_284 = bytes.fromhex("000000000000")
PRECONDITION_20D = bytes.fromhex("af176db58290")
# ~0.7-2s pacing between UDS steps, matching the verified working session (not fired
# back-to-back).
STEP_DELAY = 0.8


class CalDiagnostics(CanDiagnostics):
    """select/read/write generalized to an explicit address -- same change can0_dev.py
    already made over this class's hardcoded single-address original."""

    def select_word(self, address):
        self.xcp(bytes.fromhex('f6000000') + struct.pack('<I', address))

    def read_word(self, address):
        self.select_word(address)
        response = self.xcp(bytes.fromhex('f504'))
        if len(response) < 5:
            raise RuntimeError('Short XCP memory read')
        return response[1:5]

    def write_word(self, address, value):
        self.select_word(address)
        self.xcp(bytes.fromhex('f004') + value)

    def connect_613_614(self):
        reply = self.xcp(bytes.fromhex('ff00'))
        print(f'613/614 connected (reply {reply.hex()})', flush=True)

    def disconnect_613_614(self):
        try:
            self.xcp(bytes.fromhex('fe'))
            print('613/614 disconnected', flush=True)
        except Exception as error:
            print(f'613/614 disconnect failed: {error}', flush=True)

    def test_613_614(self):
        """Non-destructive: connect, read+verify both verifier words, disconnect."""
        self.connect_613_614()
        try:
            for addr in VERIFIER_WORDS:
                value = self.read_word(addr)
                print(f'verifier word {addr:08X} = {value.hex()} (read, not modified)', flush=True)
        finally:
            self.disconnect_613_614()

    def enter_programming_session(self, log, *, genuine=True):
        """Open the programming session ONCE for the whole package -- matching
        tools/mdi2_client/mdi2/calibration_transaction.py's program(), which does this
        exactly once and then loops ALL 14 slot transfers inside the same open
        session. Doing this per-slot (the earlier bug) tears down to default session
        (10 01) after every single slot, which the VIP reads as "programming event
        over" and starts winding down -- racing the next slot's re-entry. That is
        what produced the alternating success/fail pattern, not a vehicle-side quirk.
        Returns the saved verifier-word dict (empty if genuine) for later restore."""
        def rec(name, result):
            entry = {name: result.hex() if isinstance(result, (bytes, bytearray)) else result}
            log.append(entry)
            print(f'{name} -> {entry[name]}', flush=True)

        def step(name, payload):
            time.sleep(STEP_DELAY)
            rec(name, self.uds(payload))

        saved = {}
        if not genuine:
            self.connect_613_614()
            for addr in VERIFIER_WORDS:
                saved[addr] = self.read_word(addr)
                rec(f'save {addr:08X}', saved[addr])
            for addr in VERIFIER_WORDS:
                self.write_word(addr, MARKER_VALUES[addr])
                readback = self.read_word(addr)
                if readback != MARKER_VALUES[addr]:
                    raise RuntimeError(f'verifier word {addr:08X} override readback mismatch')
                rec(f'override+verify {addr:08X}', readback)

        step('10 01 (pre-clear)', bytes.fromhex('1001'))
        # Verified order (~/.codex/sessions/2026/11/16/...fc2c.../ lines 442, 789):
        # 10 03 / SecurityAccess / FF01 / 021E / 85 02 / 28 03 01 / 10 02.
        step('10 03', bytes.fromhex('1003'))
        step('27 01', bytes.fromhex('2701'))
        step('27 02 (key)', bytes.fromhex('2702') + DEGENERATE_KEY)
        step('31 01 FF01', bytes.fromhex('3101ff01'))
        step('31 01 021E', bytes.fromhex('3101021e'))
        step('85 02', bytes.fromhex('8502'))
        step('28 03 01', bytes.fromhex('280301'))
        step('10 02', bytes.fromhex('1002'))
        if not genuine:
            # The 2026-11-16 successful custom write applied the override AFTER this
            # exact session-open sequence (profile-01 grant/FF01/021E/programming-session
            # first, THEN the verifier-word write) -- this driver does it BEFORE, matching
            # the documented order for session mechanics but not for override placement.
            # Re-read (not re-write) both words now to check whether anything in 021E/85
            # 02/28 03 01/10 02 reset them before any TransferData/signature check runs.
            for addr in VERIFIER_WORDS:
                readback = self.read_word(addr)
                rec(f'post-session-open check {addr:08X}', readback)
                if readback != MARKER_VALUES[addr]:
                    print(f'!!! verifier word {addr:08X} no longer holds the marker after '
                          f'session-open (expected {MARKER_VALUES[addr].hex()}, got '
                          f'{readback.hex()}) -- session-open cleared it', flush=True)
        return saved

    def transfer_one(self, slot_hex, container_bytes, log):
        """34/36/37/F0F1 for ONE slot. Caller must already have an open programming
        session (enter_programming_session) -- this does not touch session state."""
        def rec(name, result):
            entry = {name: result.hex() if isinstance(result, (bytes, bytearray)) else result}
            log.append(entry)
            print(f'{name} -> {entry[name]}', flush=True)

        length = len(container_bytes)
        time.sleep(STEP_DELAY)
        rd = self.uds(b'\x34\x00\x44' + b'\x00\x00\x00\x00' + length.to_bytes(4, 'big'))
        rec('34 RequestDownload', rd)
        # Root cause of the 04/06/07 timeouts (NOT a settle-time issue -- a settle delay
        # here was tried and made no difference, same identical failure): every slot
        # whose decompressed container is >= 4095 bytes needs a block at the full 0x0FFF
        # size, and 0x0FFF ("maxNumberOfBlockLength" from the ECU's own 74 response)
        # INCLUDES the 0x36 service byte and the block-sequence-counter byte -- verified
        # byte-for-byte against tools/mdi2_client/mdi2/calibration_payloads.py
        # transfer_requests()'s own "max_request_length includes the service byte and
        # transfer block counter" / "block_size = max_request_length - 2". The old code
        # here sliced a 0x0FFF-byte DATA chunk and then prepended the 2 header bytes,
        # sending 4097 bytes total for a full block -- 2 bytes over the ECU's own stated
        # limit, which it silently drops (no response at all) rather than NRC'ing.
        # Every slot that happened to fit in one block under 4093 data bytes (02, 03, 05,
        # 08, 09, 0A, 0B, 0C, 0D, 0E, 0F) never hit this ceiling and transferred fine.
        time.sleep(STEP_DELAY)
        block, idx = 0x0FFF - 2, 1
        for off in range(0, length, block):
            chunk = container_bytes[off:off + block]
            resp = self.uds(bytes([0x36, idx & 0xFF]) + chunk)
            rec(f'36 block {idx}', resp)
            idx += 1
            time.sleep(STEP_DELAY)
        rec('37 TransferExit', self.uds(bytes.fromhex('37')))
        pec = self.uds(bytes.fromhex('22f0f1'))
        rec('22 F0F1 (PEC)', pec)
        ok = pec[:3] == bytes.fromhex('62f0f1') and pec.endswith(b'\x00\x00')
        return {'ok': ok, 'slot': slot_hex, 'log': list(log)}

    def exit_programming_session(self, saved, log):
        """Restore verifier words (if any were overridden) and disconnect 0x613/0x614.
        Call once, after all slots are transferred -- not between slots."""
        def rec(name, result):
            entry = {name: result.hex() if isinstance(result, (bytes, bytearray)) else result}
            log.append(entry)
            print(f'{name} -> {entry[name]}', flush=True)

        restore_error = None
        if saved:
            for addr in VERIFIER_WORDS:
                try:
                    self.write_word(addr, saved[addr])
                    readback = self.read_word(addr)
                    if readback != saved[addr]:
                        raise RuntimeError(f'verifier word {addr:08X} restore readback mismatch')
                    rec(f'restore+verify {addr:08X}', readback)
                except Exception as error:
                    restore_error = error
                    print(f'!!! RESTORE FAILED for {addr:08X}: {error}', flush=True)
            self.disconnect_613_614()
        if restore_error is not None:
            raise RuntimeError(f'verifier-word restore failed: {restore_error}')

    def write_calibration(self, slot_hex, container_bytes, *, genuine=True):
        """Single-slot convenience wrapper (own session, open+transfer+close) -- kept
        for the 'write' CLI mode / the earlier single-slot test. write_package()
        below does NOT use this; it keeps one session open across all slots."""
        log = []
        saved = {}
        try:
            saved = self.enter_programming_session(log, genuine=genuine)
            return self.transfer_one(slot_hex, container_bytes, log)
        except Exception as error:
            return {'ok': False, 'slot': slot_hex, 'log': log, 'error': f'{type(error).__name__}: {error}'}
        finally:
            self.exit_programming_session(saved, log)


def load_container(path):
    """These files are gzip-wrapped CSM containers on disk (confirmed: the raw bytes
    decompress to a smaller payload starting with a slot byte at offset 3 and a
    "CSM\\x00" tag at offset 6-10 -- matching tools/mdi2_client/mdi2/calibration_payloads
    .load_stock_package's own validation). The UDS 34/36/37 transfer uses the
    DECOMPRESSED CSM bytes, not the raw on-disk gzip blob."""
    raw = path.read_bytes()
    data = gzip.decompress(raw)
    if len(data) < 10 or data[6:10] != b'CSM\x00':
        raise ValueError(f'{path}: decompressed data is not a CSM container (len={len(data)})')
    return data


# slot(hex) -> part number, from pi_dashboard/backend/ltz_ref.py LTZ_REFERENCE
# (already-verified against tools/mdi2_client/mdi2/ltz_reference_manifest.py).
SLOT_PARTS = {
    "02": "87863250", "03": "84517309", "04": "85045371", "05": "87846416",
    "06": "87846371", "07": "85783460", "08": "87846432", "09": "87846376",
    "0A": "87846368", "0B": "86292118", "0C": "85102312", "0D": "87846384",
    "0E": "84517418", "0F": "87846380",
}


SLOT_SETTLE = 0.3     # minimal pause between slots -- the whole package must finish
                      # inside the module's own post-wake active window (owner-stated
                      # ~10 min); the prior run's per-slot retries + 2s settles burned
                      # most of that window, which is what let an idle/session timeout
                      # fire mid-package. Total wall-clock time is now the priority.
SLOT_RETRIES = 1      # one shot per slot, no retry loop -- move on fast so every slot
                      # gets attempted inside the window rather than spending it on
                      # retries for one slot.


def write_package(transport, package_dir, *, genuine=True, only=None):
    """Open the programming session ONCE for the whole package, then transfer every
    slot inside that one open session (tools/mdi2_client/mdi2/calibration_transaction
    .py's program() does exactly this). The earlier version re-ran the full
    10 01/10 03/SecurityAccess/FF01/021E/85 02/28 03 01/10 02 sequence for every
    slot, which the VIP read as "programming event ended" after each slot and raced
    the next slot's re-entry -- that is the documented cause of the alternating
    success/fail/timeout pattern, not a per-slot vehicle condition. A per-slot retry
    here only redoes that slot's own 34/36/37 transfer -- it never re-enters the
    session, since re-entry mid-package is the bug being fixed."""
    items = SLOT_PARTS.items() if only is None else [(s, SLOT_PARTS[s]) for s in only]
    items = list(items)

    loaded = []
    results = []
    for slot_hex, part in items:
        path = package_dir / part
        if not path.is_file():
            results.append({'ok': False, 'slot': slot_hex, 'part': part, 'error': 'file not found'})
            continue
        loaded.append((slot_hex, part, load_container(path)))

    session_log = []
    saved = {}
    try:
        print(f'\n=== opening programming session (once for all {len(loaded)} slots) ===', flush=True)
        saved = transport.enter_programming_session(session_log, genuine=genuine)
    except Exception as error:
        results.append({'ok': False, 'slot': None, 'error': f'session open failed: {type(error).__name__}: {error}',
                         'log': session_log})
        return {'ok': False, 'results': results}

    try:
        for slot_hex, part, data in loaded:
            r = None
            for attempt in range(1, SLOT_RETRIES + 1):
                print(f'\n=== slot {slot_hex} ({part}) attempt {attempt}/{SLOT_RETRIES} (shared session) ===',
                      flush=True)
                try:
                    r = transport.transfer_one(slot_hex, data, [])
                except Exception as error:
                    r = {'ok': False, 'slot': slot_hex, 'error': f'{type(error).__name__}: {error}'}
                if r.get('ok'):
                    break
                print(f'!!! slot {slot_hex} attempt {attempt} FAILED: {r.get("error")}', flush=True)
                # Capture PEC immediately, at the moment of failure -- it was found to not
                # persist usefully once later diagnostic reads (verify mode, etc.) happen
                # after the fact.
                try:
                    time.sleep(STEP_DELAY)
                    r['pec_at_failure'] = transport.uds(bytes.fromhex('22f0f1')).hex()
                    print(f'    PEC at failure -> {r["pec_at_failure"]}', flush=True)
                except Exception as pec_error:
                    print(f'    PEC read after failure also failed: {pec_error}', flush=True)
                if attempt < SLOT_RETRIES:
                    time.sleep(SLOT_SETTLE)
            r['part'] = part
            r['attempts'] = attempt
            results.append(r)
            time.sleep(SLOT_SETTLE)
    finally:
        print('\n=== closing programming session (once, after all slots) ===', flush=True)
        transport.exit_programming_session(saved, session_log)

    return {'ok': all(r.get('ok') for r in results), 'results': results, 'session_log': session_log}


def verify_package(transport, package_dir, only=None):
    """Post-write acceptance check: read live DID F182 (calibration identity block) and
    compare every slot against its on-disk container, using mdi2's own validated
    parse_f182()/calibration_record() (tools/mdi2_client/mdi2/calibration_readback.py) --
    not a reimplementation. F182 is an identity-only read (pi_dashboard/backend/app.py's
    uds_calibration(): `c.session(0x03); c.read_did(0xF182)`, no SecurityAccess/RoutineControl
    needed), so this only needs 10 03 then 22 F1 82 -- no programming session."""
    items = list(SLOT_PARTS.items()) if only is None else [(s, SLOT_PARTS[s]) for s in only]
    calibrations = []
    for slot_hex, part in items:
        path = package_dir / part
        if not path.is_file():
            raise FileNotFoundError(f'{path}')
        calibrations.append(Calibration(int(slot_hex, 16), part, load_container(path)))

    log = []

    def rec(name, result):
        entry = {name: result.hex() if isinstance(result, (bytes, bytearray)) else result}
        log.append(entry)
        print(f'{name} -> {entry[name]}', flush=True)

    time.sleep(STEP_DELAY)
    rec('10 03', transport.uds(bytes.fromhex('1003')))
    time.sleep(STEP_DELAY)
    f182 = transport.uds(bytes.fromhex('22f182'))
    rec('22 F182', f182)

    observed = parse_f182(f182)
    slots = []
    for cal in calibrations:
        expected = calibration_record(cal)
        actual = observed.get(cal.slot)
        slots.append({
            'slot': f'{cal.slot:02X}', 'part': cal.part,
            'ok': actual == expected,
            'expected': expected.hex() if expected is not None else None,
            'observed': actual.hex() if actual is not None else None,
        })
    return {'ok': all(s['ok'] for s in slots), 'slots': slots, 'log': log}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('test613', 'write', 'package', 'verify', 'pec'))
    parser.add_argument('--package-dir', type=Path, help='directory of part-number-named containers')
    parser.add_argument('--only', help='comma-separated hex slots to (re)attempt, e.g. 03,04,05')
    parser.add_argument('--tools', type=Path, default=Path.home() /
                        'Downloads/github/gminfo_resources/tools/bench')
    parser.add_argument('--profile', type=Path, default=Path.home() /
                        '.local/share/gminfo-bench/harness-profile.json')
    parser.add_argument('--slot', help='hex slot id, e.g. 02')
    parser.add_argument('--container', type=Path, help='path to the container file to write')
    parser.add_argument('--modified', action='store_true',
                        help='container is a modified/custom one -- use the VIP 0x613/0x614 '
                             'development interface to set the header-verifier words first. '
                             'Default (genuine/stock) skips it entirely -- verified unneeded.')
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()

    import usb.core
    import usb.util
    import usb.backend.libusb1
    import libusb_package

    spec = importlib.util.spec_from_file_location('can_bench_emulator', args.tools / 'can_bench_emulator.py')
    bench = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bench
    spec.loader.exec_module(bench)
    profile = bench.load_profile(args.profile)
    validate_keepalive(profile)
    if args.mode in ('write', 'package', 'verify', 'pec'):
        # verify (22 F182) needs no SecurityAccess/RoutineControl, but it still needs the
        # module AWAKE and responsive -- the just-run 'verify' attempt without this got
        # 10 03 accepted (module was still winding up) and then timed out on the very next
        # request 6s later. Only the precondition injector (modified 0x20D + 0x284=0, same
        # as write/package) has been verified live to hold the module in that state; a bare
        # native-profile replay has not.
        # Documented precondition environment (can_bench_experiments.md: "Full genuine
        # LTZ/HC rewrite"): "all captured profile IDs replayed EXCEPT 20D; separate
        # ~100 ms stream supplied original 20D with b5-bit7 set". Sending both the
        # native 20D (via the normal replay) and the modified 20D (via the injector)
        # at once contradicts that -- drop native 20D from the replay so only the
        # injector's modified version is ever on the bus.
        kept = [(f, o) for f, o in zip(profile.frames, profile.offsets) if f.can_id != 0x20D]
        profile = bench.Profile(tuple(f for f, _ in kept), tuple(o for _, o in kept),
                                profile.period, profile.cycles)
        print('Excluded native 0x20D from the replay (precondition injector supplies '
              'the modified version instead)', flush=True)

    stop_requested = threading.Event()
    finished = threading.Event()
    transport = CalDiagnostics(usb, stop_requested, finished, profile.period)
    result_holder = {}
    original_find = usb.core.find

    def stop(signum, stack):
        stop_requested.set()

    precondition_stop = threading.Event()

    def precondition_injector():
        # Separate ~100 ms stream alongside the keepalive replay, matching
        # can_bench_experiments.md's documented successful environment. Same shared
        # device/send() as the replay loop and the 613/614 channel -- one USB owner.
        transport.ready.wait(30)
        while not precondition_stop.is_set():
            try:
                transport.send(0x284, PRECONDITION_284)
                transport.send(0x20D, PRECONDITION_20D)
            except Exception as error:
                print(f'precondition injector send failed: {error}', flush=True)
            time.sleep(0.1)

    def worker():
        try:
            if not transport.ready.wait(30):
                raise TimeoutError('No admitted 0x529 keepalive replay within 30 seconds')
            time.sleep(1)
            if args.mode == 'test613':
                transport.test_613_614()
                result_holder['result'] = {'ok': True, 'mode': 'test613'}
            elif args.mode == 'package':
                only = [s.strip().upper() for s in args.only.split(',')] if args.only else None
                result_holder['result'] = write_package(transport, args.package_dir,
                                                        genuine=not args.modified, only=only)
            elif args.mode == 'verify':
                only = [s.strip().upper() for s in args.only.split(',')] if args.only else None
                result_holder['result'] = verify_package(transport, args.package_dir, only=only)
            elif args.mode == 'pec':
                time.sleep(STEP_DELAY)
                s10 = transport.uds(bytes.fromhex('1003'))
                time.sleep(STEP_DELAY)
                pec = transport.uds(bytes.fromhex('22f0f1'))
                result_holder['result'] = {'ok': True, '10 03': s10.hex(), '22 F0F1': pec.hex()}
            else:
                data = load_container(args.container)
                result_holder['result'] = transport.write_calibration(args.slot, data, genuine=not args.modified)
        except Exception as error:
            result_holder['result'] = {'ok': False, 'error': f'{type(error).__name__}: {error}'}
        finally:
            print('Keepalive continues until Ctrl-C', flush=True)
            finished.set()
            stop_requested.set()
            precondition_stop.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    def observed_read(device, endpoint, size, *a, **kw):
        if device.idVendor == 0x1D50 and device.idProduct == 0x606F:
            return transport.observe(device, endpoint, size, *a, **kw)
        return transport.original_read(device, endpoint, size, *a, **kw)

    def observed_find(*a, **kw):
        if kw.get('idVendor') == 0x1D50 and stop_requested.is_set() and finished.is_set():
            raise StopReplay()
        return original_find(*a, **kw)

    usb.core.Device.read = observed_read
    usb.core.find = observed_find
    pt = threading.Thread(target=precondition_injector)
    t = threading.Thread(target=worker)
    pt.start()
    t.start()
    try:
        bench.replay(profile, status_interval=60)
    except StopReplay:
        pass
    finally:
        stop_requested.set()
        precondition_stop.set()
        t.join()
        pt.join()
        usb.core.Device.read = transport.original_read
        usb.core.find = original_find

    result = result_holder.get('result', {'ok': False, 'error': 'worker produced no result'})
    print(json.dumps(result, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
