# diagnosticsd — Worker-Starvation DoS

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

---

## Oversized-Payload Behavior

| PAYLOAD_LEN | Behavior |
|------------|---------|
| `0x00000000` | **Only closes immediately if the client also half-closes (FIN/`shutdown(SHUT_WR)`)** after the header. A `nc`/`printf` pipe does this implicitly on EOF, which is what earlier testing observed. Holding the socket open past the 8-byte header with **no** half-close hangs indefinitely (confirmed ≥8 s) even for a declared length of 0. |
| `0x1000`–`0x40000000` (tested up to 1 GiB) | Connection is held open, blocking, waiting for the declared byte count or EOF. **No response, no rejection, no RST.** |
| `0x7FFFFFFF` / `0xFFFFFFFF` | Same blocking behavior — no response, connection held open. |
| Unsigned-wrap boundary values (`0xFFFFFFF0`–`0xFFFFFFFF`, targeting the `payload_size + 9` arithmetic in `sendResponse`) | Behave identically to any other nonzero declared length — connection blocks, no distinguishing response. The wraparound in `sendResponse`'s check could not be triggered from the wire; that check is not reached until a *response* is being built, which never happens because `readAvailableData()` never gets enough bytes. |

**`SockAdaptor::sendResponse`** allocates a **128 KB stack buffer**
(`sub rsp, 0x20008`) with a stack canary; the size check
(`"Payload size too large: %d"` when `payload_size + 9 ≥ 0x20001`) is unsigned
and relies on `getPayloadSize()` being pre-bounded by `EthernetConverter`
(`"Reported Payload Size is incorrect (Payload Size %d vs Data Payload Size %d)"`)
before `sendResponse`.

**Confirmed live (Jul 2026 session), black-box, no binary access required:**

- **No pre-allocation.** Declaring PAYLOAD_LEN up to 1 GiB and sending zero
  payload bytes produces **no measurable `VmRSS` growth** (`9524 kB` flat,
  `/proc/598/status`, before/during/after) across 3 simultaneous such
  connections. This **rules out** a `malloc(PAYLOAD_LEN)`-before-check
  memory-exhaustion primitive — `readAvailableData()` reads into a bounded
  buffer incrementally rather than allocating the declared size up front.
- **Confirmed: trivial unauthenticated worker-starvation DoS.** The receive
  path blocks synchronously per-connection until either (a) the declared byte
  count arrives, or (b) the peer half-closes. There is **no read timeout** on
  this path. With as few as **3 concurrent connections** that send a valid
  8-byte header and then withhold the declared payload (never closing), a
  **4th, fully well-formed diagnostic request from a separate connection times
  out completely** (≥3 s, no response). A single stalled connection alone
  measurably serializes/delays (but does not fully block) a concurrent
  request (0.02 s → 1.32 s), consistent with a very small (~2–4 slot)
  concurrent-handler capacity despite the process having 10 OS threads total
  (thread count does not grow with stalled connections — the limit is a
  logical handler/queue depth, not the OS thread count).
  - **Open Conflict (2026-11-21):** [`ethernet_uds_diagnosticsd.md`'s Open
    Question #6](ethernet_uds_diagnosticsd.md#open-questions) re-reads this
    same N=1 latency point plus an additional N=2 data point (0.02 s → 2.55 s)
    as a graded ramp, and argues that pattern "reads more like a
    serialized/polled accept-dispatch path... than a hard-capacity thread
    pool" — i.e. a single dispatcher iterating connections, not a fixed-size
    concurrent-handler slot pool as concluded here. Not resolved; carried
    forward as an open conflict between the two docs rather than picked one
    way or the other.
  - **Effect:** the root `diagnosticsd` (UID 0, all capabilities, bridges to
    the RTOS diagnostic endpoint on vlan4/172.16.4.107) stops servicing
    **any** client — including the legitimate RTOS bridge and any real
    Techline/MDI tester — for as long as the attacker holds ≥3 incomplete
    connections open.
  - **Recovery:** fully recoverable. Closing the stalled connections restores
    normal ~20 ms response times immediately; the daemon PID, `VmRSS`, and
    thread count are unchanged after the test (no crash observed).
  - **Reachability:** exploitable from the unprivileged Android shell
    (uid=2000) over loopback, and — per the firewall rules in
    [`platform/vehicle_network.md`](../platform/vehicle_network.md#reachable-services-and-host-firewall-topology-summary-findings-securitymd) — from any
    partition permitted to reach `:49156` (172.16.4.107 RTOS, 172.16.4.112
    CGM) without any UDS session/SecurityAccess state, since the block
    happens before frame parsing ever completes.
- **Corrected 2026-11-14 — sequencing and tester identity both matter.**
  Earlier all-rejected sequences used invalid tester IDs. Tester `0x00F4`
  successfully entered extended session and completed level-1 SecurityAccess;
  see the [validated T1 sequence](diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
- **Corrected 2026-11-14 — old address sweep omitted the accepted testers.**
  `0x00FA`, `0x00F1`, `0x00F0`, `0x0000` and `0x0001` negative results do not
  establish that every wire-supplied tester ID is invalid. Basic live requests
  succeeded with `0x00F4` and `0x00F5`; the complete grant was tested with F4.
- **`DIAG_CUSTOM` (SID `0x15`) is rejected identically to other SIDs**
  (`7F 15 10`) regardless of sub-function (closes Open Question #5, negative
  result).

---
