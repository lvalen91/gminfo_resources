# macOS MDI2 client

Native, Windows-free Python client for the GM/Bosch **MDI2** adapter, used on an owner's **bench
radio**. The MDI2 sits on a direct USB RNDIS link to the Mac and reaches the radio ECU (`0x80`)
through its D-PDU CAN tunnel (TCP/10123). It is not connected to a vehicle OBD2 port. No
Bosch/Windows activation is needed; macOS generic RNDIS is sufficient.

## Scope

- Adapter discovery (multicast beacon), key derivation, encrypted 900x management session.
- Adapter log pull (TCP/9052, the MDI2's own logs, not Android/radio logs).
- D-PDU tunnel re-arm, radio identify (VIN, MEC, calibration metadata), recovery diagnosis.
- Gated stock-LTZ calibration write. Live-validated on the bench (multiple High Country -> LTZ
  writes); still gated and requires explicit authorization every time. Stock GM-signed packages
  only. See [docs/CALIBRATION_WRITE.md](docs/CALIBRATION_WRITE.md).
  Cleared-A11 recovery was also validated on 2026-11-14 using a one-time
  in-memory source-profile exception and restoration of an erased VIN;
  [recovery details](docs/CALIBRATION_WRITE.md#cleared-a11-recovery-2026-11-14).
  The normal CLI still rejects the cleared source profile.
- Out of scope: arbitrary or modified packages (rejected with `7F 36 72`, cause not isolated),
  real-seed AES-CMAC SecurityAccess (math proven offline, never run on hardware; the writes used
  the SBI-flipped module's all-FF seed path), custom-package signing (no key recovered).
- `read-all` (SocketCAN/ISO-TP), `security` and `key` are offline/bench helpers, not MDI2 access.
  `read-all` has never run against a live bus.

Protocol detail: `../research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md`,
`../research/MDI2_DPDU_API_PROTOCOL_AUG2026.md`,
`../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`.

## Quickstart

Run from this directory with the project venv, one client at a time. Placeholders in angle
brackets are never to be replaced in committed text.

```
python3 -m venv .venv        # only if missing
./.venv/bin/python -m pip install -r requirements.txt    # pycryptodome, typer, construct; no sudo
./.venv/bin/python -B -m mdi2.cli --help                 # no hardware contact
```

1. Discover (adapter IP changes across reconnects; serial is derived from the beacon):
   `./.venv/bin/python -B -m mdi2.cli scan`
   If it fails: check the `/24` netmask fix in [docs/ACCESS.md](docs/ACCESS.md#4-usb-netmask-and-routing).
2. 9052 health check (isolated; accepted TCP is not health):
   ```
   ./.venv/bin/python -B - <<'PYCODE'
   from mdi2.discovery import resolve_device
   from mdi2.crypto import derive_key
   from mdi2.transport import Session
   d = resolve_device()
   with Session(derive_key(d.serial), d.ip).connect(ports=[9052]) as s:
       reply = s.channels[9052]._ctrl_reply
       print("9052 control reply:", reply.hex() if reply else "NONE")
   PYCODE
   ```
   `NONE` means stop probing and go to [docs/ACCESS.md](docs/ACCESS.md#6-9052-unresponsive-session-table-exhaustion).
3. Identify the radio (read-only; auto-rearms the tunnel):
   `./.venv/bin/python -B -m mdi2.cli identify`
4. Pull adapter logs (keep content in memory; logs hold addresses/serials):
   the snippet in [docs/ACCESS.md](docs/ACCESS.md#7-adapter-log-pull). Zero streams is a failure.

## CLI summary

| command | what it does |
|---|---|
| `scan` | multicast beacon discovery (not a port scan) |
| `connect` | opens/closes the management channel bank; not proof of a usable session |
| `rearm` | starts the D-PDU tunnel on 10123; not a reset or write |
| `identify` | read-only radio VIN/MEC/calibration metadata |
| `recover` | diagnoses a radio left in programming mode; omit `--force-default-session` first |
| `write` | dry-run plan; `--confirm` programs |
| `key`, `security` | print key material / offline CMAC; not needed for access, never copy output |
| `read-all` | SocketCAN fallback, offline-verified only |

Serial is a positional integer (`identify <MDI2_SERIAL> --host <MDI2_IP>`), only useful when both
values are known.

## Layout

| module | role |
|---|---|
| `discovery.py`, `crypto.py`, `framing.py`, `transport.py`, `messages.py` | beacon, key (`base_key + serial`), wire format, 900x session |
| `logs.py`, `container.py` | 9052 log pull and SID container decode |
| `live_calibration.py` | rearm, identify, recover, plan/write |
| `live_programming_transport.py`, `dpdu.py` | D-PDU tunnel and live radio link |
| `ltz_preflight.py`, `ltz_reference_manifest.py` | source-profile gate and 14 pinned hashes |
| `security_cmac.py`, `uds_generic.py`, `ecu_catalog.py`, `module_reader.py`, `can_transport.py` | offline/bench helpers |

Offline tools (in `scripts/`): `scripts/mdi2_key.py <serial>` (key), `scripts/mdi2_9052_decrypt.py <pcap> <key_hex>` (decrypt).

## Keys

SecurityAccess key maps (`{ecuid_hex: aes128_key_hex}`) are never committed. Only
`keys.example.json` (placeholders) is tracked; real maps go in a git-ignored path such as
`~/.config/mdi2/keys.json` and are passed with `--key-map`. Nothing is auto-loaded.

## Docs

- [docs/ACCESS.md](docs/ACCESS.md): access, health check, session hygiene, netmask fix, troubleshooting.
- [docs/CALIBRATION_WRITE.md](docs/CALIBRATION_WRITE.md): gates, plan vs confirm, write sequence.
