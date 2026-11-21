# MDI2 Protocol Reference

Scope: what an operator needs to know about the wire behaviour of the Bosch GM MDI2 as spoken by
`tools/mdi2_client/mdi2/`. Derivation, evidence and the investigation trail live in the research docs and
are linked, not repeated:

- Management/log-pull stack and key derivation: `research/mdi2-bench-sessions/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md`
  (§0 current state, §4.19 key, §4.20 app layer, §4.22/§4.26 live client)
- D-PDU tunnel (TCP/10123): `research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md` (§1 framing, §4 bring-up, §11 re-arm)
- Port roles and troubleshooting: `MDI2_ACCESS_AND_TOOL_GUIDE.txt` §7-§8 (operator guide, outside this repo)

Constants are in `mdi2/const.py`. Serials, keys and VINs are never recorded in docs; use placeholders.

## Bench topology (confirmed 2026-11-14)

MDI2 on a direct USB RNDIS link to the Mac; it reaches radio ECU 0x80 through the D-PDU CAN tunnel.
It is **not** connected to a vehicle OBD2 port. The link enumerates as `en17` (name may differ) with a
`/32` mask; after every replug set it to `/24` (`sudo ifconfig <USB_IF> inet <MAC_USB_IP> netmask
255.255.255.0`). Discovery keys off the subnet, not the interface name. Device default IP
`192.168.171.2`, host `192.168.171.30`.

## Verified end to end (2026-11-14)

discovery -> key -> 9052 handshake -> `session_open` returns a session id -> `pull_logs` returns the
`messages` stream. The beacon offset-9 serial yields the correct key.

## 1. Discovery beacon

Device announces ~1 Hz to multicast `225.1.1.1`, UDP/8194 (`discovery.py`). Beacon payload is 98 bytes
(a 41-byte variant also occurs). Serial = little-endian u32 at byte offset 9
(`decode_beacon`); the UDP source address is the device's current link IP. Passive: join the group and
listen; there is no listener on the device. Blocked multicast or the wrong interface shows as
"no MDI2 announce beacon seen".

## 2. Blowfish-ECB key

Standard Blowfish-ECB (big-endian), per-device key, 56 bytes, computed from the serial with no
extraction (`crypto.py`):

    key[i] = base_key[MDI_2][i] + device_serial   (14 little-endian dwords, 32-bit add)

Static `base_key` for module type `0x1c` and the proof: research doc §4.19.

## 3. Management bank (900x) and control-frame handshake

Each connect opens a 14-socket TCP bank: 9001, 9003, 9006-9014, 9050-9052. Log pull and session use
**9052**; 9050 carries PDU START (re-arms 10123); 9011 is the session's data port.

Wire message (big-endian): `[u32 0][u32 len][u32 counter][Blowfish-ECB body]`. Counter is cleartext
and must have bit31 set. Inside the body: `content + zero-pad + u32be(content_len)`, padded to 8.

Each channel first exchanges an 8-byte plaintext control frame `00 53 50 00 00 <code> 00 00`:

| Port | Who speaks first | Device code | Client code |
|---|---|---|---|
| 9001, 9050, 9051 | device sends its own frame on connect | `0x31` | `0x30` |
| 9011 | device sends on connect | `0x20` | `0x21` |
| 9052 | **silent on connect**; replies only after the client's frame (`0053500000310000`) | `0x31` | `0x30` |

The client must send its frame regardless (`Channel.handshake`); a device that never answers on 9052
means no session slot is available (see Recovery).

## 4. session_open / session_close (9052, encrypted JSON)

    {"data":{"date":"DDMMYYHHMMSS<frac>","dialer":"<host ip>","interface":2,"keep_alive":false,
             "listener":"<device ip>","master":true,"name":"<client>"},"has_data":true,"id":1,"target":"session"}

Success reply: `{"data":{"port":9011,"session":<id>},"error":0,"has_data":true,"id":1}`. `session_open`
must be the first app message on the channel. Release with

    {"data":<session_id>,"has_data":true,"id":2,"target":"session"}

The device has a small session table. **Always send session_close** (`logs.pull_logs` does in a
`finally`). A `poll` is `{"has_data":false,"id":N,"target":"session"}`.

## 5. Log container

After `session_open` + poll, send the binary get-logs trigger (`messages.GET_LOGS_CMD`); the device
streams a decrypted container of little-endian SID-tagged records (`container.py`):

| SID | Record | Layout (u32le fields) |
|---|---|---|
| `0x8a9` | metadata | sid, _r, id, kind, namelen, name |
| `0x8a8` | data | sid, _r, id, namelen, name, datalen, data |

`pull_logs` returns `[(name, bytes)]`; `messages` is the Varlog text. Parsing stops at an unknown SID.

## 6. D-PDU tunnel (TCP/10123)

Separate stack from 900x: little-endian `[u32 total_len][u32 mid][payload]` (`dpdu.py`), two sockets per
session (command + event), hello `0x884` / `<u32 1><u32 channel><u32 0x1388>`. Port 10123 is closed
until re-armed (PDU START on 9050 using a fresh session id; `live_calibration.rearm_dpdu_tunnel`). It
survives closing the management session. It is fragile: one malformed frame closes it and it does not
self-rearm. ECU 0x80 (radio) uses resource `0x2A`, request `0x14DA80F1`, response `0x145AF180`.
Full opcode table and bring-up: DPDU research doc. Do not send arbitrary probe payloads to it.

## Recovery: unresponsive 9052 / "no session id"

Normally **session-table exhaustion** from sessions opened without `session_close` (repeated connect
loops make it worse), not a hardware fault. In order:

1. Stop all connect loops and close diagnostic apps/sockets.
2. Let the table drain; release any session id you still hold with `session_close`.
3. Re-test 9052 once in isolation (discovery, then a single pull).
4. Only if it still does not answer: USB power-cycle the MDI2 (last resort), then re-set the `/24` mask,
   re-run discovery, and re-arm 10123 if needed.

Do not reset the radio to fix the adapter's management service.
