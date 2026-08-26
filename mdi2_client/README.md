# macOS MDI2 client

Native, Windows-free client for the GM/Bosch **MDI2** device-facing protocol, implementing the RE
in `../research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` (see that doc's §0 summary). **Live-validated
end-to-end** over USB: discover → derive key → control handshake → session_open → get-logs →
Blowfish-ECB decrypt → SID container → Varlog → session_close, repeatable back-to-back.

## Status
| piece | module | state |
|---|---|---|
| Discovery (`225.1.1.1:8194` beacon; serial at LE u32 offset 9) | `discovery.py` | done |
| Key derivation (`base_key[MDI_2] + serial`, byte-verified) | `crypto.py` | done |
| Blowfish-ECB (big-endian, stock pycryptodome) | `crypto.py` | done |
| Wire frame + 8-byte control frame (construct) | `framing.py` | done |
| 900x session, control handshake, patient recv | `transport.py` | done |
| JSON app messages + body length-suffix framing + get-logs + session-close | `messages.py` | done |
| SID log container decode (`0x8a9` meta / `0x8a8` data) | `container.py` | done |
| Log pull, back-to-back | `logs.py` | **done, live-validated** |
| Non-log 900x services (device info, network settings) | — | not yet mapped (needs a WiFi capture) |

## Install / run
```
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m mdi2.cli key 88985275   # serial -> 56-byte Blowfish key
./.venv/bin/python -m mdi2.cli scan           # listen for the device beacon
```
Pull logs (requires the MDI2 on this machine's `192.168.171.0/24` link):
```python
from mdi2 import crypto
from mdi2.transport import Session
from mdi2.logs import pull_logs
key = crypto.derive_key(88985275)                     # or read serial from discovery.discover()
s = Session(key, "192.168.171.2").connect(ports=[9052])
print([(n, len(d)) for n, d in pull_logs(s)])         # [('messages', ~56900)]  = Varlog
s.close()
```
Offline: `mdi2_key.py <serial>` (→ key) and `mdi2_9052_decrypt.py <pcap> <key_hex>` (→ plaintext logs).

## Operational notes
- The MDI2 must be on this machine's network (direct USB gadget, or a tunnel). macOS gives the
  gadget iface (`en17`) a `/32` and a VPN can steal the route — fix per re-plug:
  `sudo ifconfig en17 inet 192.168.171.30 netmask 255.255.255.0`.
- **No Bosch/Windows activation is needed** — macOS generic RNDIS is sufficient.
- The device holds **one session**; `pull_logs` sends the session-close so back-to-back pulls work.
  If it stops responding (dangling sessions from crashed/aborted runs), USB power-cycle it.
- The 900x channels are `common_service::generic_client<PORT>` JSON services (9001=speaker,
  9052=logs, …); only the log path is implemented so far.
