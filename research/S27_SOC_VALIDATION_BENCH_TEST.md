# Bench Test — Does the SoC `diagnosticsd` Honor the VIP's Bypassed (all-0xFF) `$27` Seed?

**Target:** GM Info 3.7 (gminfo37), Y181. Radio/CSM/IHU.
**Owner setup:** SBI flipped in EEPROM (`0x0440`/`0x0A80` data byte = `0xFF`), MDI2 available, `udsoncan` installed, host on the vehicle Ethernet reaching the radio at `eth0:49156`.
**Goal:** Send `$27 01` at programming level over the Ethernet diagnostic channel, capture the seed, and decide empirically whether the SoC's `diagnosticsd` returns the VIP's bypassed all-`0xFF` seed (and accepts any key) — the condition under which `SCREEN_RESOLUTION` can be written **without** knowing GM's seed/key algorithm.

---

## 0. The crux, stated precisely

There are **two independent diagnostic paths** into this radio, and the whole point of this test is that they may not agree:

| Path | Transport | Reaches | SecurityAccess handler | Bypass status in the repo evidence |
|------|-----------|---------|------------------------|-------------------------------------|
| **CAN / DPS** | 29-bit CAN, ECU `0x80`, req `0x14DA80F2` / rsp `0x145AF280` | VIP (RH850) gateway → radio domain | **VIP** validates seed/key | **CONFIRMED bypassed.** `diagnostics/dps/A11_CSM_x80.Txt` line 177-180: `27 01` → `67 01 FF FF FF FF FF …` (all-`0xFF` seed) |
| **Ethernet** | Custom GM Ethernet-Diag over TCP `:49156`, ECU addr `0x0084` | `diagnosticsd` (root, PID 599) → bridges to RTOS `172.16.4.107:49156` | **SoC `diagnosticsd`** at the app layer | **UNKNOWN — this is what we are testing.** An *untrusted Android shell* to `:49156` got `7F 27 10` (generalReject) for `27 01` (see `diagnostics/ethernet_uds_diagnosticsd.md`). Whether a proper tester at programming level gets the all-`0xFF` seed is the open question. |

The VIP already hands out an all-`0xFF` seed on CAN. **This test determines whether the SoC's own Ethernet SecurityAccess handler mirrors that bypass, generates its own real seed, or refuses the connection outright.** If it mirrors the bypass, any key unlocks it and `SCREEN_RESOLUTION` calibration writes (`$34/$36/$37`) become possible without the real algorithm.

> **Important transport correction.** `diagnosticsd` on `:49156` is **NOT DoIP** and **NOT ISO-TP**. Do not use `doipclient`/`DoIPClient(...,13400,...)` here — that will not speak to `:49156`. It uses a fixed **8-byte binary header** (below). The `udsoncan`+DoIP snippet in `research/MDI2_RAW_UDS_BYPASS_GUIDE.md` is correct only for a real DoIP endpoint; for the SoC bridge on `:49156` use the raw-socket framing in this document.

---

## 1. Wire format — GM Ethernet Diagnostics (custom, confirmed live)

Every message (request and response) on TCP `:49156` is:

```
[ SRC_ADDR : 2 bytes BE ][ TGT_ADDR : 2 bytes BE ][ PAYLOAD_LEN : 4 bytes BE ][ UDS payload : PAYLOAD_LEN bytes ]
```

- **Tester (our) source address:** `0x0FA0` (Techline/MDI).
- **Radio/CSM ECU diagnostic address:** `0x0084`. (Target address is not strictly validated by the daemon, but use the canonical value.)
- **UDS payload:** raw ISO 14229-1 service bytes, no ISO-TP length/PCI byte, no addressing inside the payload.

Confirmed live exchange (from `diagnostics/ethernet_uds_diagnosticsd.md`):

```
Request:  0F A0  00 84  00 00 00 02  10 03
Response: 00 84  0F A0  00 00 00 03  7F 10 10     <- from an UNTRUSTED shell connection
```

Response header echoes the addresses swapped (`ECU`→`tester`) and gives the reply length.

**Read discipline (matters — the daemon has quirks):**
- Send exactly `PAYLOAD_LEN` bytes. Do **not** send `PAYLOAD_LEN = 0` and half-close — that just closes the socket.
- Do **not** over-declare the length: if you declare more bytes than you send and hold the socket open, `diagnosticsd` blocks with no reply and no RST (documented no-read-timeout behavior). Always declare the exact payload size.
- After sending, read the 8-byte reply header, parse `PAYLOAD_LEN`, then read exactly that many bytes.
- Keep one TCP connection open for the whole session (session/security state is per-connection).

---

## 2. Network / host setup (do this first)

The radio (CSM/IHU) is `192.168.1.100` on the vehicle LAN (VLAN 5 / `eth0`). Your test host must be on `192.168.1.0/24` but **not** `.100`.

```bash
# Pick an unused address on the vehicle LAN, e.g. .200
sudo ip addr add 192.168.1.200/24 dev <your_iface>   # Linux
# macOS: sudo ifconfig <iface> alias 192.168.1.200 255.255.255.0

# Reachability + port open
ping -c2 192.168.1.100
nc -vz 192.168.1.100 49156      # expect "succeeded"/"open"
```

If you are instead bridged in on the vlan4/RTOS side, the equivalent endpoint is `172.16.4.107:49156`; the framing is identical. Prefer the radio face (`192.168.1.100`) unless you know you are on vlan4.

> Note on "MDI2 + udsoncan": the MDI2 is your CAN/DoIP tool for the **control test** in §7 (the CAN path to ECU `0x80`). The Ethernet `:49156` test does not go through the MDI2 — it is a direct TCP socket from your host to the radio. Both are run from the same laptop.

---

## 3. Exact UDS sequence

Run these on one open TCP connection, in order. `→` = payload we send; expected replies listed.

| # | Step | UDS payload (`→`) | Full frame on the wire (`→`) | Positive reply | Common negatives |
|---|------|-------------------|------------------------------|----------------|------------------|
| 1 | TesterPresent (liveness) | `3E 00` | `0F A0 00 84 00 00 00 02 3E 00` | `7E 00` | `7F 3E 10` (generalReject → untrusted channel) |
| 2 | **Enter programming session** | `10 02` | `0F A0 00 84 00 00 00 02 10 02` | `50 02 …` | `7F 10 22/12/7E`; `7F 10 10` (generalReject) |
| 2b | (fallback) extended session — this is what the CAN capture used before its all-FF seed | `10 03` | `0F A0 00 84 00 00 00 02 10 03` | `50 03 …` | `7F 10 10` |
| 3 | **Request seed, level 1** | `27 01` | `0F A0 00 84 00 00 00 02 27 01` | `67 01 <seed…>` | `7F 27 {10,12,22,24,33,37,36}` |
| 4 | Send dummy key (only if seed looked bypassed) | `27 02 <key…>` (`key` = all-`0x00`, length = seed length) | `0F A0 00 84 00 00 00 <2+n> 27 02 00…00` | `67 02` | `7F 27 {35,36,24,10}` |

Sub-function convention: `$27` odd = requestSeed (`01`), even = sendKey (`02`). The response SID for a positive `$27` is `0x67`; for any positive service it is `SID + 0x40`. A negative reply is always `7F <echoed SID> <NRC>`.

---

## 4. Python script template (stdlib only, ready to run)

No external packages required — this speaks the confirmed 8-byte framing directly. Save as `s27_bench.py`, edit the CONFIG block, run `python3 s27_bench.py`.

```python
#!/usr/bin/env python3
"""
s27_bench.py — Determine whether the SoC diagnosticsd on :49156 honors the
VIP's bypassed all-0xFF $27 seed at programming level.

Transport: GM Ethernet Diagnostics custom 8-byte header over TCP (NOT DoIP).
  [SRC 2 BE][TGT 2 BE][LEN 4 BE][UDS payload LEN bytes]
"""

import socket
import struct
import sys
import time

# ----------------------------- CONFIG -----------------------------
ECU_IP        = "192.168.1.100"   # radio/CSM on eth0/vlan5 (or 172.16.4.107 on vlan4)
ECU_PORT      = 49156
SRC_ADDR      = 0x0FA0            # tester (Techline/MDI)
TGT_ADDR      = 0x0084            # radio/CSM diagnostic address
RECV_TIMEOUT  = 5.0              # seconds; diagnosticsd has no read timeout, so WE must
SESSION       = 0x02             # 0x02 = programming (goal); 0x03 = extended (CAN-capture used this)
TRY_DUMMY_KEY = True            # send $27 02 with all-0x00 key if seed looks bypassed
# ------------------------------------------------------------------

def frame(payload: bytes) -> bytes:
    return struct.pack(">HHI", SRC_ADDR, TGT_ADDR, len(payload)) + payload

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed while reading %d bytes (got %d)" % (n, len(buf)))
        buf += chunk
    return buf

def send_recv(sock, payload: bytes, label=""):
    print(f"\n[>] {label}  UDS={payload.hex(' ').upper()}")
    print(f"    frame={frame(payload).hex(' ').upper()}")
    sock.sendall(frame(payload))
    hdr = recv_exact(sock, 8)                       # SRC TGT LEN
    r_src, r_tgt, r_len = struct.unpack(">HHI", hdr)
    body = recv_exact(sock, r_len) if r_len else b""
    print(f"[<] hdr src={r_src:#06x} tgt={r_tgt:#06x} len={r_len}  UDS={body.hex(' ').upper()}")
    return body

def decode(body: bytes) -> str:
    if not body:
        return "empty response"
    if body[0] == 0x7F:
        sid = body[1] if len(body) > 1 else 0
        nrc = body[2] if len(body) > 2 else 0
        names = {0x10:"generalReject", 0x11:"serviceNotSupported", 0x12:"subFunctionNotSupported",
                 0x22:"conditionsNotCorrect", 0x24:"requestSequenceError", 0x31:"requestOutOfRange",
                 0x33:"securityAccessDenied", 0x35:"invalidKey", 0x36:"exceededNumberOfAttempts",
                 0x37:"requiredTimeDelayNotExpired", 0x78:"responsePending",
                 0x7E:"subFunctionNotSupportedInActiveSession", 0x7F:"serviceNotSupportedInActiveSession"}
        return f"NEGATIVE  service={sid:#04x}  NRC={nrc:#04x} ({names.get(nrc,'?')})"
    return f"POSITIVE  respSID={body[0]:#04x}"

def classify_seed(seed: bytes) -> str:
    if len(seed) == 0:
        return "ZERO-LENGTH seed (unusual)"
    if all(b == 0xFF for b in seed):
        return "ALL-0xFF"
    if all(b == 0x00 for b in seed):
        return "ALL-0x00"
    return "REAL/RANDOM"

def main():
    print(f"[*] Connecting to {ECU_IP}:{ECU_PORT} ...")
    s = socket.create_connection((ECU_IP, ECU_PORT), timeout=RECV_TIMEOUT)
    s.settimeout(RECV_TIMEOUT)
    try:
        # 1) liveness
        try:
            body = send_recv(s, bytes([0x3E, 0x00]), "TesterPresent $3E 00")
            print("    ->", decode(body))
        except Exception as e:
            print("    (TesterPresent failed:", e, ")")

        # 2) programming session (goal). Falls back to extended if it wants comparison.
        body = send_recv(s, bytes([0x10, SESSION]), f"SessionControl $10 {SESSION:02X}")
        print("    ->", decode(body))
        session_ok = bool(body) and body[0] == 0x50

        # 3) request seed
        body = send_recv(s, bytes([0x27, 0x01]), "SecurityAccess requestSeed $27 01")
        print("    ->", decode(body))

        if body and body[0] == 0x67 and len(body) >= 2 and body[1] == 0x01:
            seed = body[2:]
            verdict = classify_seed(seed)
            print(f"\n[SEED] len={len(seed)}  value={seed.hex(' ').upper()}  ==> {verdict}")

            if verdict == "ALL-0xFF":
                print("[=] Seed matches the VIP bypass pattern seen on CAN. Proceeding to key test.")
            elif verdict == "ALL-0x00":
                print("[=] All-0x00 seed => ECU reports security ALREADY granted this session.")
            else:
                print("[=] REAL seed => SoC generated its own challenge; bypass NOT mirrored here.")

            # 4) dummy key
            if TRY_DUMMY_KEY and verdict in ("ALL-0xFF", "ALL-0x00", "REAL/RANDOM"):
                key = b"\x00" * len(seed)   # match seed length; dummy zero key
                body = send_recv(s, bytes([0x27, 0x02]) + key, f"SecurityAccess sendKey $27 02 ({len(key)}B dummy)")
                print("    ->", decode(body))
                if body and body[0] == 0x67 and body[1] == 0x02:
                    print("\n[RESULT] KEY ACCEPTED. Security unlocked with a dummy key.")
                    print("         => BYPASS IS HONORED end-to-end. SCREEN_RESOLUTION writable without the real algo.")
                elif body and body[0] == 0x7F and len(body) > 2 and body[2] == 0x35:
                    print("\n[RESULT] invalidKey (0x35). Dummy key REJECTED => real key validation is active.")
                    print("         => Bypass NOT honored for the key; you need the seed/key algorithm.")
                else:
                    print("\n[RESULT] Inconclusive key response:", decode(body))
        elif body and body[0] == 0x7F:
            print("\n[RESULT] $27 01 rejected:", decode(body))
            print("         See failure-diagnosis table (esp. 0x10 generalReject = channel-level refusal).")
        else:
            print("\n[RESULT] Unexpected $27 01 response:", body.hex(' ').upper())

    finally:
        s.close()
        print("\n[*] Connection closed.")

if __name__ == "__main__":
    main()
```

### Optional: same test through `udsoncan` (custom connection)

If you want `udsoncan`'s service objects/decoding, wrap the framing in a `BaseConnection`. Use this instead of any DoIP connector.

```python
from udsoncan.connections import BaseConnection
import socket, struct, queue, threading

class GMEthDiagConnection(BaseConnection):
    def __init__(self, ip, port=49156, src=0x0FA0, tgt=0x0084, name="gmeth"):
        super().__init__(name)
        self.ip, self.port, self.src, self.tgt = ip, port, src, tgt
        self.sock = None
        self.rxqueue = queue.Queue()
        self._stop = threading.Event()

    def open(self):
        self.sock = socket.create_connection((self.ip, self.port), timeout=5)
        self.sock.settimeout(1.0)
        self._stop.clear()
        self.rxthread = threading.Thread(target=self._rx, daemon=True); self.rxthread.start()
        return self

    def _rx(self):
        buf = b""
        while not self._stop.is_set():
            try:
                data = self.sock.recv(4096)
                if not data: break
                buf += data
                while len(buf) >= 8:
                    _src, _tgt, ln = struct.unpack(">HHI", buf[:8])
                    if len(buf) < 8 + ln: break
                    self.rxqueue.put(buf[8:8+ln]); buf = buf[8+ln:]
            except socket.timeout:
                continue
            except OSError:
                break

    def close(self):
        self._stop.set()
        if self.sock:
            try: self.sock.close()
            finally: self.sock = None
    def is_open(self): return self.sock is not None
    def empty_rxqueue(self):
        while not self.rxqueue.empty(): self.rxqueue.get()
    def specific_send(self, payload):
        self.sock.sendall(struct.pack(">HHI", self.src, self.tgt, len(payload)) + payload)
    def specific_wait_frame(self, timeout=2):
        return self.rxqueue.get(timeout=timeout)

# usage:
# from udsoncan.client import Client
# from udsoncan import services
# with Client(GMEthDiagConnection("192.168.1.100")) as client:
#     client.change_session(0x02)                     # programming
#     resp = client.request_seed(0x01)                # $27 01
#     seed = resp.service_data.seed
#     client.send_key(0x02, b"\x00"*len(seed))        # dummy key
```

---

## 5. Interpretation guide — what each response means

### `$27 01` (requestSeed) responses

| Reply | Meaning | Implication for the bypass |
|-------|---------|----------------------------|
| `67 01 FF FF … FF` (all-`0xFF`) | SoC returned the **same bypassed seed the VIP returns on CAN** | **Bypass mirrored.** Almost certainly any key is accepted — go to step 4 to confirm. |
| `67 01 00 00 … 00` (all-`0x00`) | ECU says security is **already unlocked** for this session | Effectively no gate; proceed to write. Confirm with a benign privileged read. |
| `67 01 <random/non-trivial>` | SoC generated its **own real challenge**, independent of the VIP/EEPROM bypass | **Bypass NOT honored on Ethernet.** You need the real seed→key algorithm (`gm_protokey`). SBI flip did not reach this handler. |
| `7F 27 10` generalReject | Channel-level refusal — connection is **untrusted** at the app layer (no registered tester ID); daemon rejects `$27` before security logic | Bypass is **irrelevant on this path** for this client. This is exactly what the untrusted shell saw. See failure diagnosis. |
| `7F 27 22` conditionsNotCorrect | Preconditions unmet (wrong session, voltage, vehicle state) | Ensure `$10 02` succeeded first; retry. |
| `7F 27 24` requestSequenceError | Seed requested out of order / no valid session | Send `$10 02` on the *same* connection first. |
| `7F 27 12` subFunctionNotSupported | Level `01` not a valid seed level here | Try other odd levels (`03`,`05`) or confirm this ECU/session exposes `$27`. |
| `7F 27 33` securityAccessDenied | Security explicitly denied in this session/tier | The tier you reached does not allow this level. |
| `7F 27 37` requiredTimeDelayNotExpired | Anti-brute-force delay active (often ~10 s, or since boot) | Wait, keep `$3E 00` alive, retry once. |
| `7F 27 36` exceededNumberOfAttempts | Too many failed keys; locked out | Power-cycle the radio, wait the delay, retry with fewer attempts. |

### `$27 02` (sendKey, dummy `0x00…`) responses

| Reply | Meaning | Implication |
|-------|---------|-------------|
| `67 02` | **Key accepted** — security unlocked | **Bypass fully honored.** With a *dummy* key accepted, you do not need GM's algorithm. Proceed to `$34/$36/$37` for `SCREEN_RESOLUTION`. |
| `7F 27 35` invalidKey | Wrong key | The seed was a **real challenge** (even if it *looked* like `0xFF`, the key is still validated) → **not** honored. Need the real algorithm. |
| `7F 27 36` exceededNumberOfAttempts | Lockout after wrong key(s) | Confirms real validation. Power-cycle, wait delay. |
| `7F 27 24` requestSequenceError | No matching prior seed request in this session/connection | Your `$27 01` and `$27 02` must be on the **same** open connection; re-run without reconnecting. |
| `7F 27 10` generalReject | Channel refusal (as above) | Bypass path is closed for this client on Ethernet. |

### Session responses (`$10`)

- `50 02` = programming session entered (good — this is "programming level").
- `50 03` = extended session (the level the CAN capture used before it got the all-`0xFF` seed; useful as a comparison).
- `7F 10 22` = conditionsNotCorrect (vehicle state/voltage; try ignition on, engine off, stable 12–13.5 V).
- `7F 10 10` = generalReject → the whole channel is treating you as untrusted; `$27` will also be rejected. Go to failure diagnosis.

---

## 6. Success criteria (bypass IS honored at the programming level)

All of the following, on one connection, in order:

1. `$10 02` → `50 02` (programming session entered). *(Or accept `$10 03`→`50 03` as the CAN-parallel case.)*
2. `$27 01` → `67 01` followed by a seed that is **all-`0xFF`** (or all-`0x00`).
3. `$27 02 00…00` (dummy zero key, length = seed length) → **`67 02`** (key accepted).

If you see all three, the SoC `diagnosticsd` honors the VIP bypass end-to-end. **You can write `SCREEN_RESOLUTION` without GM's seed/key algorithm** — proceed to the calibration transfer (`$34` RequestDownload → `$36` TransferData → `$37` RequestTransferExit) with a cal blob carrying a correct CRC16 + SHA-256 (no RSA signature is checked on this platform, per the firmware analysis; recompute both after editing the enum).

A weaker but still-usable success: `$27 01` → `67 01 00…00` (all-zero seed) means security is already granted for the session — no key step needed; verify by performing a benign privileged operation before trusting it for a write.

---

## 7. Failure diagnosis — deciding *why* the bypass is not honored

Work down this tree based on the `$27 01` reply.

**A. `$27 01` → `67 01 <real/random seed>` (not FF, not 00), and `$27 02` dummy → `7F 27 35`.**
> The SoC's `diagnosticsd` runs its **own** SecurityAccess with a real challenge that is independent of the EEPROM SBI flip / VIP bypass. The bypass simply does not reach this handler.
> - Confirm it is genuinely random: request the seed twice (reconnect between) — a changing seed proves a live RNG, a fixed non-FF seed proves a static (still real) key.
> - Path forward is NOT the SBI flip: you need the real seed→key routine. On this platform that lives in `/vendor/bin/gm_protokey` (see `platform/security.md`) — reversing/invoking it is a separate effort.

**B. `$27 01` → `7F 27 10` (generalReject), and `$10 02` also → `7F 10 10`.**
> This is the **untrusted-channel** signature — identical to what the unprivileged Android shell saw in `diagnostics/ethernet_uds_diagnosticsd.md`. `diagnosticsd` has *no* OS-level peer check, but the UDS app layer soft-checks a **registered tester ID**; an unregistered client falls to default session and every service is `generalReject`. The bypass never gets evaluated because the service is refused first.
> Distinguish sub-cases:
> - **Every SID → `7F .. 10`** regardless of order/session/source address → you are simply not a recognized tester on this channel. Spoofing `SRC_ADDR` (`0x00FA/0x00F1/0x00F0/0x0000/0x0001`) does **not** help (already tested, negative). The authorized tester is the RTOS bridge at `172.16.4.107`.
> - Try connecting **from the vlan4/RTOS side** (`172.16.4.107:49156` endpoint) or as the registered tester if you can position there — the trust decision may differ by origin.
> - If the goal is only the *calibration write*, note the CAN path (below) is already proven bypassed and is the more reliable route for `SCREEN_RESOLUTION`.

**C. `$27 01` → `67 01 FF…FF` but `$27 02` dummy → `7F 27 35`/`7F 27 36`.**
> Contradictory-looking but meaningful: the seed is a **fixed** `0xFF` constant, yet the key is still validated by a real function. The FF seed is cosmetic; the bypass is **partial** and does **not** cover the key. Treat as case A (need the real algorithm). Do not keep hammering keys — `0x36` means you are one lockout/power-cycle cycle deep.

**D. `$27 01` → `7F 27 22/24`.**
> Not a bypass failure — a **sequencing/precondition** issue. Re-run ensuring: same TCP connection for session+seed, `$10 02` returned `50 02` first, ignition on / stable voltage, and a `$3E 00` keep-alive if you paused. Then re-evaluate the seed.

**E. `$27 01` → `7F 27 37` then repeated `7F 27 36`.**
> Anti-brute-force timing, not a verdict. Power-cycle the radio, wait the delay (≈10 s or longer), and take **one** clean shot at `$27 01` → inspect the seed. Do not script rapid retries.

### Control test — prove your rig and isolate the path (run via MDI2 on CAN)

Because the all-`0xFF` seed is **already documented on CAN** (`diagnostics/dps/A11_CSM_x80.Txt`: `27 01` → `67 01 FF FF …`), run the CAN path as a control to separate "bypass broken" from "Ethernet channel refuses me":

- MDI2 as J2534/DoIP-CAN, ECU `0x80`, request CAN ID `0x14DA80F2`, response `0x145AF280`, 29-bit, ISO-TP.
- Sequence: `10 03` (or `10 02`) → `27 01`.
- **Expected:** `67 01 FF FF FF FF …` (all-`0xFF`), reproducing the capture.

Interpretation of the two paths together:

| Ethernet `$27 01` result | CAN `$27 01` result | Conclusion |
|--------------------------|---------------------|------------|
| `67 01 FF…FF` | `67 01 FF…FF` | Bypass honored on **both** paths. Use Ethernet or CAN to write. |
| `7F 27 10` (refused) | `67 01 FF…FF` | Bypass works, but the **Ethernet channel won't accept you as a tester**. Write via the **CAN/VIP path** (proven), or get onto the RTOS-side origin for `:49156`. |
| `67 01 <real>` | `67 01 FF…FF` | The **VIP** bypasses, but the **SoC `diagnosticsd` enforces its own** security. Ethernet writes need the real algorithm; CAN writes to ECU `0x80` do not. |
| `67 01 <real>` | `67 01 <real>` | The SBI flip did not take effect — re-verify EEPROM `0x0440`/`0x0A80` data byte is `0xFF` on the live part and the module re-read it (power-cycle after the EEPROM write). |

---

## 8. Operational safety notes

- **One shot per attempt at the key.** `$27 02` failures accumulate toward `exceededNumberOfAttempts` (`0x36`) and can impose delays; do not loop keys.
- **Keep the session alive** with `$3E 00` every ~2 s if you pause between steps; losing the session resets security and can trip `requestSequenceError`.
- **Do not over-declare `PAYLOAD_LEN`** — the daemon blocks with no reply (documented). Always send exactly what you declare.
- **This is read/seed reconnaissance.** No `$34/$36/$37` is issued here. Only proceed to a calibration write after a clean `67 02`, with a cal blob whose CRC16 + SHA-256 you have recomputed. A malformed cal write can leave the display mis-calibrated until re-flashed.
- **EEPROM state note:** the captured DPS session listed `SBI $0000 Bypass Inactive` yet still received an all-`0xFF` seed on CAN, and logged `Access to the security validation facility failed` three times — read the live seed yourself rather than trusting the DPS "Bypass Inactive" string; the wire response is the ground truth.

---

## 9. One-line summary

Open one TCP connection to `192.168.1.100:49156`, frame `[0F A0][00 84][len][UDS]`, send `10 02` then `27 01`. **All-`0xFF` seed + `67 02` on a dummy key = bypass honored, write freely. A real/random seed or `invalidKey` = the SoC enforces its own security (need the algorithm). `7F 27 10` = the Ethernet channel refuses you as a tester (use the proven CAN/VIP path to ECU `0x80` instead).**
