# macOS MDI2 Manager (Python foundation)

Native reimplementation of the GM/Bosch MDI2 Manager's device-facing protocol, from the RE in
`gminfo_resources/research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md`.

## Status
| piece | module | state |
|---|---|---|
| Device discovery (225.1.1.1:8194 beacon) | `discovery.py` | works; beacon *field* decode = TODO |
| Key derivation (`base + serial`) | `crypto.py` | **done, byte-verified** |
| Blowfish-ECB (big-endian) | `crypto.py` | done |
| Frame + control frame (construct) | `framing.py` | done |
| 14-socket 900x session | `transport.py` | done; partial-frame rebuffering = TODO |
| Log pull (9052) | `logs.py`+`messages.py` | **request decoded (JSON+binary); active** |
| App protocol (JSON `generic_client<PORT>`) | `messages.py` | **decoded (session_open/poll)**; per-service schemas TODO |
| Network settings read/change | — | needs a WiFi-connected capture |

## Install / run
```
pip install -r requirements.txt
python -m mdi2.cli key 88985275        # -> fde7ccb2...  (serial -> Blowfish key)
python -m mdi2.cli scan                # listen for the device beacon
python -m mdi2.cli connect 88985275    # open the 900x bank (needs MDI2 on this machine's net)
```
Pair with `../mdi2_9052_decrypt.py` (pcap + key -> plaintext logs) and `../mdi2_key.py`.

## Notes
- The MDI2 must be reachable from this machine (direct link, or the WireGuard tunnel used on the
  bench). The Mac cannot reach `192.168.171.2` through the Surface by default.
- The 900x channels carry **JSON** (`json_format::base_request/response`) under the Blowfish layer;
  each port is a `common_service::generic_client<PORT,...>` service (9001 = speaker, 9052 = logs).
- Next RE step to make log-pull *active*: decrypt the captured 28-byte 9052 request body with the
  session key to recover the "get logs" command, then send it via `Channel.send`.
