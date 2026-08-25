# `diagnosticsd` UDS-over-TCP Worker-Starvation DoS (port 49156)

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Component:** `/vendor/bin/diagnosticsd` (root daemon, HIDL service host)
**Status:** CONFIRMED — live black-box testing, Jul 2026 session (see
`diagnostics/ethernet_uds_diagnosticsd.md`, "Oversized-Payload Behavior" +
"Open Questions" #1/#6). This document exists to package that finding as a
standalone, disclosure-ready report; it introduces no new testing.

---

## Summary

`diagnosticsd` — a root process (UID 0, all capabilities, no seccomp filter,
`NoNewPrivs=0`) that bridges GM Ethernet Diagnostics (UDS/ISO 14229) between
the Android guest and the RTOS diagnostic endpoint — accepts connections on
TCP `0.0.0.0:49156` and blocks synchronously on each connection's declared
payload length with **no read timeout**. As few as **3 concurrent
connections**, each sending only the 8-byte frame header and then withholding
the declared payload, are sufficient to make the daemon stop servicing
**every** client — including the legitimate RTOS diagnostic bridge on VLAN 4
— for as long as the attacker holds the connections open. No authentication,
UDS session state, or SecurityAccess (`$27`) is required: the block occurs
before frame parsing completes, so it is reachable by anything that can open
a TCP connection to the port.

## Affected Component

- Binary: `/vendor/bin/diagnosticsd` (x86-64 ELF, stripped, 426,824 bytes),
  SELinux domain `gm_diagnosticsd`.
- Class/symbols implicated (from binary strings/HIDL registration, not yet
  confirmed against disassembly — binary not currently available for further
  static analysis; see Confidence section):
  `DiagnosticEthernetMonitor` / `SockAdaptor::readHeader` /
  `readAvailableData`, part of `vendor.gm.diagnostics.ethernet@1.0`.
- Confirmed present: Y181 `W231E-Y181.3.2-SIHM22B-499.3`. Not yet tested
  against other GM Info 3.7 builds/model years — the wire protocol and
  process profile (root, all caps, no seccomp) are documented as fixed
  platform characteristics, not build-specific, so the same behavior is
  likely present elsewhere but this has not been verified.

## Wire Protocol (context)

8-byte header, no anti-replay/session token:
```
[SRC_ADDR : 2 BE] [TGT_ADDR : 2 BE] [PAYLOAD_LEN : 4 BE] [UDS payload : PAYLOAD_LEN bytes]
```
Target address is not validated (any value produces an identical response
path). No UDS session/SecurityAccess state is required to reach the
vulnerable code path — the connection blocks while still reading the raw
frame, before any UDS-layer logic runs.

## Technical Details

- **No pre-allocation on declared length.** Testing up to a 1 GiB declared
  `PAYLOAD_LEN` with zero payload bytes sent produced no measurable `VmRSS`
  growth (flat at 9524 kB across 3 simultaneous such connections,
  `/proc/<pid>/status`). The receive path reads incrementally into a bounded
  buffer rather than allocating the declared size up front — this rules out
  a heap-exhaustion primitive via oversized length fields.
- **No read timeout.** A connection that sends the 8-byte header and then
  neither sends the declared payload nor half-closes (`FIN`/
  `shutdown(SHUT_WR)`) is held open indefinitely (confirmed ≥8 s with no
  server-side abort).
- **Small concurrent-handler capacity, serialized rather than pooled.**
  Latency to a well-formed 4th request scales with the number of stalled
  connections rather than showing a flat-then-cliff pattern:
  - N=1 stalled connection: legitimate request latency 0.02 s → 1.32 s
  - N=2: 0.02 s → 2.55 s
  - N=3: full timeout, ≥3 s, no response within the test window
  This graded ramp (rather than a hard capacity cliff) is more consistent
  with a single dispatcher iterating connections with blocking/long-interval
  reads than with a fixed-size worker-thread pool. The daemon's OS thread
  count (10 threads) does not grow with the number of stalled connections,
  supporting that the limiting resource is a logical handler/queue depth,
  not OS threads. Exact structure (single dispatcher vs. small fixed pool)
  is inferred from black-box timing, not confirmed against disassembly.
- **Fully recoverable, no crash.** Closing the stalled connections restores
  normal ~20 ms response latency immediately. Daemon PID, `VmRSS`, and thread
  count are unchanged after testing — this is an availability/DoS condition,
  not a memory-corruption or crash primitive.

## Reproduction

1. Open ≥3 TCP connections to `<device-ip>:49156`.
2. On each, send a well-formed 8-byte header only (e.g.
   `SRC=0x0FA0 TGT=0x0084 PAYLOAD_LEN=0x00000010`) — do not send the declared
   payload bytes, and do not close or half-close the socket.
3. From a 4th connection, send a complete, well-formed diagnostic request
   (e.g. `10 03` / `ExtendedDiagnosticSession`) with a correct header and
   full payload.
4. Observe: the 4th request receives no response within the test window
   (≥3 s), versus ~20 ms baseline with no stalled connections present.
5. Close the 3 stalled connections; observe the 4th connection's request
   class now responds at baseline latency again.

No authentication, VIN, or vehicle state is required. Steps 1–4 were
performed from the unprivileged Android guest shell (uid=2000) over loopback;
per `platform/networking.md`, the same port is reachable without any UDS
session state from any network partition permitted to reach `:49156`
(documented as including the RTOS bridge address `172.16.4.107` and
`172.16.4.112`), so on-vehicle-network reachability beyond loopback is
plausible but has not itself been independently re-verified from an external
network position for this report.

## Impact

- **Availability of a root-owned diagnostic bridge**, including for the
  legitimate RTOS diagnostic endpoint, is denied by an unauthenticated,
  unprivileged actor with 3 sockets and no special access.
- No UDS SecurityAccess, VIN knowledge, or prior compromise is needed — the
  precondition is strictly "can open a TCP connection to the port."
- No corruption, crash, or persistence: recovery is immediate on connection
  closure. This is a pure availability issue, not an RCE or privilege
  escalation primitive by itself.
- Downstream risk is context-dependent: if legitimate diagnostic/programming
  traffic (e.g. dealer/Techline sessions) is blocked during a
  time-sensitive operation, the practical impact could exceed "delayed
  response," but this has not been tested (see Open Questions below) and
  should not be assumed without further, more careful testing given
  potential effects on an active programming session.

## Confidence / What Is Not Yet Confirmed

- The exact source-level cause (single dispatcher loop vs. small fixed pool;
  precise read-loop structure) is inferred from black-box timing behavior,
  not confirmed against the binary. The binary (`/vendor/bin/diagnosticsd`,
  426,824 bytes) is not currently available on this machine for further
  static confirmation — SELinux denies `adb pull`/`cat` even from shell on
  Y181 Enforcing; a prior extraction was done from a vendor ext4 image
  (`86331650`) but no local copy of that extraction currently exists in this
  corpus. Re-confirming the exact mechanism would require re-extracting the
  binary (hardware/bench access) or locating the prior extraction.
- Whether the same starvation affects the sibling HIDL services
  (`vendor.gm.diagnostics.{bridge,obd,internal}@1.0`,
  `vendor.gm.powermode@1.0`) if they share an accept/dispatch path with the
  Ethernet TCP listener is untested.
- Effect (if any) beyond delayed responses when held during an active
  `SecureUnlock`/programming session is untested and was deliberately not
  attempted on the bench unit pending further discussion, given the
  possibility of interfering with in-progress vehicle state.
- Reachability from outside the vehicle's internal network segments (i.e.,
  whether an external attacker could ever reach `:49156` at all, as opposed
  to a device already on VLAN 4/vlan5) is out of scope for this finding and
  governed by the vehicle's broader network exposure, not by this bug.

## Suggested Remediation (for GM)

- Add a read/idle timeout on in-progress `diagnosticsd` connections that
  have sent a header but not the full declared payload.
- Bound the number of connections held in the pre-dispatch/receive state
  per-source or globally, independent of full worker-pool capacity.
- Consider whether the accept/dispatch path can be made non-blocking or
  moved off a single dispatcher thread so one slow/malicious peer cannot
  delay unrelated connections.

## Evidence / Related Documents

- `diagnostics/ethernet_uds_diagnosticsd.md` — primary source; full wire
  protocol, process profile, and all black-box test results this report
  summarizes.
- `platform/networking.md` — VLAN/firewall reachability context for
  `:49156`.
- `platform/security.md#can--uds-diagnostic-services` — SELinux domain
  (`gm_diagnosticsd`) and UDS SID reference.
- `research/UNTRIED_ATTACK_VECTORS.md` #9/#10 — earlier (2026-06-29)
  hypotheses (malloc-before-check heap exhaustion; source-address
  trust-tier spoofing) that this and the underlying doc's testing
  superseded with a negative result for both, and surfaced this DoS in their
  place.
