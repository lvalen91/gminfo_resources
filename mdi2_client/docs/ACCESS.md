# MDI2 access and troubleshooting

Operator flow for the native macOS client in this checkout. Source: the owner's MDI2 access guide
(2026-11-14), corrected by bench findings. Placeholders: `<MDI2_SERIAL>`, `<MDI2_IP>`,
`<USB_IF>`, `<MAC_USB_IP>`, `<EXPECTED_VIN>`. Never put real values, keys, or raw logs in
durable text.

Do not use the older client under `research/GM_research/mdi2/mdi2_macos/client`; it lacks the
current live-write code. The `run_cal_write.py` bench wrapper imports this package and uses
`--go --log` rather than `--confirm`; prefer the main CLI.

## 1. Bench topology and requirements

- MDI2 powered, on a **direct USB RNDIS link to the Mac**. It reaches the radio ECU `0x80` over
  its D-PDU CAN tunnel. It is not on a vehicle OBD2 port.
- Radio connected and powered for `identify`/`write`.
- Use `./.venv/bin/python` from the checkout root, never global Python or `sudo python3`.
  Install deps without sudo. `-B` avoids bytecode-cache writes.
- One diagnostic client at a time. Close Bosch/other tools first.

## 2. Discovery and 9052 health check

```
./.venv/bin/python -B -m mdi2.cli scan
```

Discovery listens for the multicast beacon (UDP/8194) and derives the adapter IP and serial; the
IP changes across reconnects. No manual key is needed.

Then check TCP/9052 for a real protocol answer (not just an accepted connection):

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

`_ctrl_reply` is an internal detail, not a public API. `NONE` means stop application-level
probing and see section 6. Use this check instead of repeated `connect` loops; `connect` only
proves sockets opened (its generic path opens 9011 before `session_open`, whereas `rearm` opens
9011 after; do not blame the ordering alone for a failure).

Then, with a healthy 9052 and a radio attached:

```
./.venv/bin/python -B -m mdi2.cli rearm
./.venv/bin/python -B -m mdi2.cli identify
./.venv/bin/python -B -m mdi2.cli identify <MDI2_SERIAL> --host <MDI2_IP>   # bypass multicast, both values required
```

`identify` auto-rearms if needed and prints a masked VIN plus summary fields. It uses diagnostic
reads and cyclic TesterPresent; no programming.

## 3. Session hygiene

The MDI2's session table is finite. Every `session_open` that is not followed by `session_close`
leaks an entry.

- Always use the `with Session(...)` context manager; `pull_logs` sends `session_close` when it
  has a session id.
- Serialize requests; no parallel clients, no retry or `connect` loops.
- Do not use `connect` as a health check; use the isolated 9052 check.
- Crashed or aborted runs are the usual source of leaked sessions.
- After any failure, stop and let the table drain before retrying (section 6).

## 4. USB netmask and routing

macOS can configure the RNDIS interface as `/32`, and a VPN can capture the route
(`OSError(65, 'No route to host')`). Identify the current interface (do not assume `en17`):

```
ifconfig -a
route -n get <MDI2_IP>     # must resolve via <USB_IF>, not a utun interface
```

Fix, keeping the Mac's existing local address and changing only the mask:

```
sudo ifconfig <USB_IF> inet <MAC_USB_IP> netmask 255.255.255.0
```

`<MAC_USB_IP>` is the Mac's address on that link, not the adapter's. **This recurs after every
replug**; re-check after each reconnect. Do not delete VPN/default routes blindly.

## 5. Privileged vs unprivileged

If discovery or sockets fail, compare the same command under `sudo -n ./.venv/bin/python -B -m
mdi2.cli scan`. If sudo says a password is required, authenticate in your own terminal with
`sudo -v`; never put a password in a command, script, or log. Use the same execution identity
for every later command.

Bench result 2026-11-14: the failures seen (unresponsive 9052, "no session id") were **not**
privilege-related; privileged and unprivileged runs behaved identically. Keep the comparison as
a diagnostic step, but compare cwd, interpreter, interface, and route first, and do not assume
sudo fixes anything.

## 6. 9052 unresponsive (session-table exhaustion)

Symptoms: TCP/9052 opens but gives no control reply; "no session id"; log streams = 0;
`re-arm FAILED (session service wedged - USB power-cycle the MDI2)`.

Common cause: **session-table exhaustion** from sessions opened without `session_close`. The CLI
message names a wedged service and a power-cycle; that overstates the cause and the first fix.
Order of recovery:

1. Stop all connect/retry loops and close diagnostic apps and sockets.
2. Let the session table drain (release sessions); run the isolated 9052 check at intervals,
   not in a loop.
3. Retry `rearm` once only after 9052 returns a control reply.
4. **Last resort:** USB power-cycle the MDI2 (it works, but is not the first fix). Do it with no
   programming active. If the adapter has another power source, USB removal may not restart it.
   Then rediscover and re-run the 9052 check.

Do not reset the radio to fix the adapter's management service. Zero logs does not prove an empty
device log.

## 7. Adapter log pull

Reads the MDI2's own logs over 9052. Pass the real local socket address as `dialer_ip`.

```
./.venv/bin/python -B - <<'PYCODE'
from mdi2.discovery import resolve_device
from mdi2.crypto import derive_key
from mdi2.transport import Session
from mdi2.logs import pull_logs
d = resolve_device()
with Session(derive_key(d.serial), d.ip).connect(ports=[9052]) as s:
    ch = s.channels[9052]
    if not ch._ctrl_reply:
        raise SystemExit("9052 did not answer its control handshake")
    streams = pull_logs(s, dialer_ip=ch.sock.getsockname()[0])
    print("Log streams:", len(streams))
    for _, content in streams:
        print("Stream bytes:", len(content))
PYCODE
```

Keep raw content in memory; logs contain addresses, serials, hostnames. Zero streams is not
success.

## 8. Symptom -> check -> fix

| symptom | check / fix |
|---|---|
| `ModuleNotFoundError` (Crypto/typer/construct/mdi2) | canonical cwd + `./.venv/bin/python`; install into the venv; keep the explicit interpreter under sudo |
| `no device seen` / `no MDI2 announce beacon seen` | power, cable, RNDIS interface, netmask (section 4), multicast on the right interface; compare privileged path; known serial + IP bypasses multicast only |
| `OSError(65)` / VPN route | section 4 |
| `TimeoutError` | identify the layer: TCP connect (route/device), discovery (multicast), or service reply after connect (section 6) |
| 9052 opens, no reply | section 6 |
| `ConnectionRefusedError` on 10123 | tunnel not started: with 9052 healthy run `rearm` then `identify`; if 9052 is dead, section 6. Closed tunnel does not prove absent CAN |
| malformed D-PDU frame / ambiguous radio response | stop and close the link; a malformed frame closes the tunnel and it does not self-rearm; rearm only after 9052 is healthy; send no arbitrary probe payloads; mid-write, use `recover` and inspect the failure phase, never blind retry |
| `BCM F085 is not the documented OFF value` | put bench in OFF state, verify F085 reads `00`; screen state and service mode `02` do not substitute |
| `battery voltage outside programming window` | fix power and re-measure; never lower limits or treat 30 V as safe |
| VIN mismatch, source-profile rejection, missing slots, hash failure | confirm radio and unchanged pinned package; do not bypass gates; do not substitute a serial for the VIN |
| real non-degenerate seed, missing key, NRC 35, `7F 36 72` | stop; NRC 35 may advance lockout; `7F 36 72` is a general failure, not a root cause; never fabricate keys |

## 9. Ports

| port | role |
|---|---|
| UDP/8194 | discovery announcement destination |
| TCP/9001, 9003, 9006-9014, 9050-9052 | management channel bank (9050 PDU START, 9052 encrypted session + logs) |
| TCP/10123 | D-PDU diagnostic tunnel, opened by `rearm` |
| TCP/21 | FTP with explicit TLS; separate from the log path |
| TCP/80 | HTTP, root may be empty |
| TCP/13400 | DoIP reference port; not this client's live path |

Scanner service labels are number-based guesses. For an authorized inventory scan only the
discovered adapter, no output files, and avoid `-sV/-A`/NSE on management or diagnostic ports
(payloads can disrupt the tunnel); `open|filtered` is not confirmed open.

## 10. Notes for terminal agents

Use the same directory, venv interpreter, interface, and privileges as a working terminal. Do not
substitute adb, SocketCAN, a Windows VM, or a guessed DoIP client. Report the actual exception and
layer; do not claim success from TCP connect alone. If adb is also used against the radio, sync
the radio clock from the Mac when drift exceeds about 90 s.
