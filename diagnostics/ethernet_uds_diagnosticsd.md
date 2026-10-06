# diagnosticsd — Ethernet UDS-over-TCP Diagnostic Bridge (port 49156)

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026
**Binary:** `/vendor/bin/diagnosticsd` (x86-64 ELF, stripped, 426,824 bytes)
**SELinux:** `gm_diagnosticsd_exec:s0` → domain `gm_diagnosticsd`

This documents the **Ethernet** diagnostic channel: the root daemon
`diagnosticsd` listening on TCP `0.0.0.0:49156`, which bridges GM Ethernet
Diagnostics (UDS / ISO 14229) between the Android guest and the RTOS diagnostic
endpoint. This is distinct from the **CAN/DPS** diagnostic path captured in
[`diagnostics/dps/`](dps/) (ECU 0x80, DPS 4.56) and from the FSA service layer
([`platform/fsa_protocol.md`](../platform/fsa_protocol.md)). The `gm_diagnosticsd`
SELinux domain and its UDS SID list are summarized in
[`platform/security.md`](../platform/security.md#can--uds-diagnostic-services);
this doc adds the live Ethernet wire format and trust model.

Binary obtained by extracting `/bin/diagnosticsd` from vendor ext4 image
`86331650` (`debugfs -R 'dump ...'`); a live pull is blocked by SELinux from the
`adbd` context.

> **[C] live-Y175 2026-10-05 — listener existence/owner/bind CONFIRMED on the Y175 variant.**
> Disk-only capture of a running Y175 radio (`W213E-Y175.5.2-SIHM22B-383.1`,
> `/tmp/radio_audit/20261005_232227/raw/`): `diagnosticsd` is live — `init.svc.diagnosticsd=running`
> (props), process in ps as **PID 590, root, SELinux domain `gm_diagnosticsd`** (`ps.txt:132`;
> note PID differs from the Y181 PID 599 in the header below — PID is capture-specific). It is
> **LISTENing on `0.0.0.0:49156`** (net_sockets.txt TCP row `00000000:C004` with `st=0A`, `uid=0`,
> inode 13683; `0xC004`=49156) — bind address is INADDR_ANY/`0.0.0.0`, **not** loopback, same as
> documented. Owner uid 0 confirmed. **UNVERIFIABLE-FROM-LIVE (shell uid 2000, no CAN/Ethernet diag
> access):** everything below about the UDS wire format, the 0x27 SecurityAccess seed/key gate, the
> VIP-tier relay, the privilege tiers, and the worker-starvation DoS — none of it is re-exercised by
> this capture; only the listener's existence, root ownership, and `0.0.0.0` bind are confirmed.

---

## Process Profile

- PID 599, PPid 1 (init), 10 threads, Sleeping. UID=0 GID=0.
- Groups: 1000 (system), 2001 (adb), 3003 (inet), 3004 (net_admin).
- `CapPrm/CapEff/CapBnd = 0000003fffffffff` → **all capabilities**.
- `NoNewPrivs = 0`, `Seccomp = 0` (no filter). `SigIgn: SIGPIPE`.
- VmSize ~10.4 GB virtual, VmRSS 9.9 MB.
- Network: LISTEN `0.0.0.0:49156` (root TCP **server**). **[C corrected 2026-10-06]** `.107`/`.112`
  connect *inbound* to it (firewall `iptables_rules_file.txt:35-36`); the earlier "ESTABLISHED
  `.100↔.107` forwarding" line was **unsupported** — no such socket in any Y181/Y175 capture. See the
  concurrence-correction block below.

**RC file (from vendor image):**
```
service diagnosticsd /vendor/bin/diagnosticsd
    class hal core
    user root
    group root system cache inet net_raw
    shutdown critical
    #seclabel u:r:su:s0      ← COMMENTED OUT (was planned as su domain)
on property:debug.cts.port.off=1 && property:ro.product.system.brand=Android
    stop diagnosticsd
on property:debug.cts.port.off=2 && property:ro.product.system.brand=Android
    start diagnosticsd
```
`ro.product.system.brand` is `"gm"` (not `"Android"`) on production, so the CTS
port kill-switch can never fire — diagnosticsd runs as root continuously. (RC
comment: *"stop diagnosticsd for cts-on-gsi tcp port testcases"* — flagged by
Android CTS as a root TCP listener.)

---

## Wire Format — GM Ethernet Diagnostics (NOT DoIP)

Custom 8-byte binary header over TCP, confirmed by live interaction:
```
[SRC_ADDR : 2 BE] [TGT_ADDR : 2 BE] [PAYLOAD_LEN : 4 BE] [UDS payload : PAYLOAD_LEN bytes]
```
- Tester source address: `0x0FA0` (Techline / MDI)
- ECU diagnostic address: **`0x0084`** (CSM head unit on the GM Ethernet diag net)
- Payload: raw ISO 14229 UDS service bytes (no address wrapping inside payload)

**Confirmed live exchange:**
```
Request:  0F A0  00 84  00 00 00 02  10 03
          [src]  [tgt]  [len=2]      [ExtendedDiagnosticSession]
Response: 00 84  0F A0  00 00 00 03  7F 10 10
          [ECU]  [tester echo]  [len=3]  [NegativeResponse | SID=0x10 | NRC=generalReject]
```

Target address is **not validated** — 0x0000/0x0001/0x0005/0x0040/0x00FA/0x0084
all give identical responses.

---

## UDS Service Dispatch Table (binary strings)

| SID | Service |
|-----|---------|
| 0x10 | `DIAG_SESSION_CONTROL` |
| 0x27 | `DIAG_SECURITY_ACCESS` |
| 0x1A/0x22 | `DIAG_DID_READ` |
| 0x3B/0x2E | `DIAG_DID_WRITE` |
| 0x28 | `DIAG_COMMUNICATION_CONTROL` |
| 0x35 | `DIAG_REQUEST_DATA_TRANSFER` |
| 0x36 | `DIAG_DATA_TRANSFER` |
| 0x70 | `DIAG_RID_CONTROL` |
| 0x76/0x37 | `MSG_RID` |
| 0x22 | `DIAG_PID_READ` |
| 0xAE/0x2F | `DIAG_CPID_CONTROL` |
| 0x20 | `DIAG_CPID_RETURN` |
| 0xD9 | `DIAG_INTERNAL_REQUEST` |
| 0x00/0x15 | `DIAG_CUSTOM` / `MSG_VENDOR_START` |
| various | `DIAG_DTC_*` |

(Matches the `$10/$22/$27/$2E/$31/$34/$36/$37` summary in `platform/security.md`.)

**All SIDs tested return `generalReject` (NRC 0x10)** from an untrusted shell
connection:

| SID | Service | Response |
|-----|---------|---------|
| 0x10 0x01/02/03 | DiagnosticSessionControl (default/programming/extended) | `7F 10 10` |
| 0x27 0x01 | SecurityAccess requestSeed | `7F 27 10` |
| 0x3E 0x00 | TesterPresent | `7F 3E 10` |
| 0x22 0xF1 0x81/86/8A/90 | ReadDID (sw / session / sw number / VIN) | `7F 22 10` |
| 0xD9 0x00 | DIAG_INTERNAL_REQUEST | `7F D9 10` |
| 0x00 0x01 | MSG_VENDOR_START | `7F 00 10` (service 0x00 dispatched) |

---

## Trust Model (binary-confirmed)

**No OS-level peer credential check.** Import table (`rabin2 -i`) has no
`getpeername`, `getsockopt(SO_PEERCRED)`, `getpeereid`, `ucred`, `getuid`, or
`geteuid` — zero socket-layer peer authentication. The accept loop does not
validate the connecting client. The unprivileged shell can complete the TCP
handshake to `127.0.0.1:49156`. NRC 0x10 is an **application-layer** UDS
rejection: the connection starts untrusted.

Trust is enforced solely at the UDS application layer:

1. **DoIP logical source/target address** — `UDSAddressCheckRequestHandler`
   validates addresses against a list.
2. **Tester ID (SOFT check)** — `"tester id check differ, process req in
   default session: req_tester_id(%d), active_tester_id(%d)"`: a mismatch is
   logged but **processing continues in default session** (non-fatal fallback).
   The RTOS connection (172.16.4.107) is the registered authorized tester; a
   shell connection has no registered tester ID → falls to default session.
3. **UDS session state + SecurityAccess (0x27)** — standard ISO 14229-1
   seed/key gate per session tier.

**Privilege tiers:** `VIP` > `ETHERNET` > `NOTIFICATION`, each unlocking more
UDS services; the tier is granted by the 0x27 SecurityAccess response after a
correct seed/key exchange. `checkSecurityLevelTable` (string, above) is **only
the per-tier allowed-service lookup table** — which SIDs a tier may call once
granted — **not** an SBI/seed-key gate itself.

**[D] CORRECTION (2026-09):** an earlier version of this doc guessed the
seed→key algorithm was "likely implemented in `/vendor/bin/gm_protokey`." This
is **wrong** — `gm_protokey` is the boot-time proto-key / disk-encryption
(`DATA_LOCKED`) state validator (`init.protokey.rc`, kernel-netlink `setKey`,
sets `vendor.gm.security.state`); it is unrelated to UDS SecurityAccess. See
[`platform/security.md`](../platform/security.md#protokey--adb-authentication)
for what `gm_protokey` actually does (ADB/seed-auth state, not `$27`).

**The real `$27` handler is in-process, statically linked into `diagnosticsd`
itself** (`libuds`, `UDSSecurityLevelCheckRequestHandler.cpp`; an ISO-14229
attempt-counter is present) — for the `ETHERNET`/`NOTIFICATION` tiers this is
where the seed/key compare happens locally. For the **`VIP` tier**,
`diagnosticsd` holds **no key material of its own**: `ProxyOfExtComp::
handleUDSRequest` forwards a `VIP`-tier `$27` request
(`MESSAGE_SECURITY_ACCESS_VIP`) over a `SockAdaptor` TCP socket
(`readHeader`/`PDU_Header`, `imp.socket`) to an external component — the VIP
MCU — where the actual seed/key compare (and the SBI EEPROM read) happen. So
the fail-open behavior gated on the SBI EEPROM byte (`0xFF` = "Bypass Active";
see [`platform/security.md`](../platform/security.md#protokey--adb-authentication))
relaxes the **VIP's own** key-compare, off-SoC — `diagnosticsd` is a relay for
that tier, not the enforcement point. On this Ethernet path under normal
(SBI-inactive) posture, an untrusted peer's `$27` requestSeed still returns
`7F 27 10` generalReject (fail-closed) before any seed is issued (see
Trust Model above). The VIP MCU firmware is not in the artifact set, so the
VIP-side compare cannot be re-derived statically from this bench.

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
    [`platform/networking.md`](../platform/networking.md) — from any
    partition permitted to reach `:49156` (172.16.4.107 RTOS, 172.16.4.112
    CGM) without any UDS session/SecurityAccess state, since the block
    happens before frame parsing ever completes.
- **Sequencing (`TesterPresent` → `SessionControl` → `SecurityAccess`) does
  not change trust state.** All three still return their respective NRC
  `0x10` (generalReject) on the same connection — no session escalation via
  ordering alone (closes Open Question #3, negative result).
- **RTOS-matching source addresses do not grant trust.** Spoofing
  `SRC_ADDR = 0x00FA / 0x00F1 / 0x00F0 / 0x0000 / 0x0001` in the 8-byte header
  all produced identical `generalReject` responses — the tester-ID soft-check
  really does fall through to default session for any unregistered ID,
  confirming there's no static allowlisted address that grants elevated trust
  from the wire alone (closes Open Question #2, negative result).
- **`DIAG_CUSTOM` (SID `0x15`) is rejected identically to other SIDs**
  (`7F 15 10`) regardless of sub-function (closes Open Question #5, negative
  result).

---

## Source Structure, Symbols & HIDL

**Inferred source layout (strings):**
```
libuds/src/ethfrmwk/SockAdaptor.cpp
socket/TCPServer.cpp  socket/TCPConnection.cpp  ConnectionManager.cpp
DiagnosticEthernetMonitor (class)   DiagnosticsEthernetService (HIDL impl)
DiagnosticMessageFactory  MessageAccess  PALDiagnosticAdaptor
JavaRequestToResponsePipeline  GMCalibrationManager
```

**Protocol internals (strings):** `readHeader` (fixed 8-byte header, hardcoded),
`readAvailableData`, `"target address(%d) invalid"`; SHA256
(`SHA256_Init/Update/Final` — module-identity auth for calibration uploads, NOT
the wire protocol); CRC16 (`"Calibration Request Checksum (0x%04X vs 0x%04X)
failed"`); `"Transfer - Received too many bytes, moduleSize = %d"` →
`CAL_RECEIVING_TOO_MANY_BYTES`. UDS strings: `"checkSecurityLevelTable"`,
`"setSecurityLevel"`, `"new sec seed level"`, `"DID payload size greater than
three"`, `"Calibration Request Payload Size is Invalid"`; jsoncpp config layer
`"Exceeded stackLimit in readValue()"`, `"keylength >= 2^30"`.

**Dynamic symbols (`nm -D`, partial):** `gm::diag::ResponseCode` (BSS enum:
`POSITIVE_RESPONSE`, `GENERAL_REJECT`, `SERVICE_NOT_SUPPORTED`,
`RESPONSE_TOO_LONG`, `VOLTAGE_TOO_LOW/HIGH`, `BUSY_REPEAT_REQUEST`,
`CAL_ERASE_FAILURE`, `CAL_SEQUENCE_ERROR`, `DEVICE_TYPE_ERROR`, `SCHEDULER_FULL`,
`INVALID_KEY`), `gm::diag::DiagnosticsBridgeServiceManager`,
`vendor::gm::diagnostics::ethernet::V1_0::implementation::DiagnosticsEthernetService`,
`...IDiagnosticsEthernetService::registerAsService`.

**HIDL interfaces registered by diagnosticsd:**
```
vendor.gm.diagnostics.ethernet@1.0::IDiagnosticsEthernetService   (Ethernet diag bridge)
vendor.gm.diagnostics.bridge@1.0::IDiagnosticsBridgeService        (RTOS bridge)
vendor.gm.diagnostics.obd@1.0::IDiagnosticsOBDService              (OBD bridge)
vendor.gm.diagnostics.internal@1.0::IDiagnosticsInternalService    (internal/privileged)
vendor.gm.powermode@1.0::IPowerModeListener                        (power state)
vendor.gm.powermode@1.0::ISystemStateListener                      (system state)
```
`IDiagnosticsInternalService` is a higher-trust channel — if reachable via
`vndbinder` with the right SELinux domain, it may bypass the TCP generalReject
gate.

**Related HIDL diagnostic services (separate binaries):**
- `vendor.harman.hardware.ame@1.0::IDiagnostics` →
  `/vendor/bin/vendor.harman.hardware.ame@1.0-service`. Methods:
  `readAppleAuthChipId`, `getGoogleKeyStatus`, `getLeoSwitchVersion`,
  `getLeoSwitchFlashPartitionStatus`, `getUsbVersion`, `getWifiIpAddress`,
  `getEthernetIpAddress`. SELinux `ame_hal_service` (shell denied).
- `vendor.gm.panel@1.0::IPanelDiagnostics` → `/vendor/bin/hw/vehiclepanel`
  (see [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)).

**Debug artifacts (not dev keys):** `libdiagnosticsdebugproxy.so`,
`libdiagnosticsdebugproxyservice.so`, `persist.vendor.debug.dvc.protocol`
(unset), `persist.vendor.avb.debug.loglevel.*`.

---

## OBD via Binder (alternative path)

The Android Binder service `com.gm.server.obd.OBDService` (PID shared with
`DiagnosticsService`) exposes `Do_On_Board_Diagnostics_Simple_Request(OBDRequest)`
(Tx1). It executes from uid=2000 but the `OBDRequest` Parcelable carries an enum
typed in `gm.obd.message.*` (28-char class, starts "OBDR…", e.g. likely
`OBDRequestedDiagnosticParam`); passing an int → `EX_ILLEGAL_ARGUMENT`
("No enum constant gm.obd.message.…"). With the correct enum it would return
live OBD2 data over GMLAN. See
[`platform/ota_update_stack.md`](../platform/ota_update_stack.md) for the
sibling UpdateService Binder surface and
[`research/security/SHELL_ACCESS_ESCALATION_Jun2026.md`](../research/security/SHELL_ACCESS_ESCALATION_Jun2026.md)
for the full uid=2000 Binder access map.

---

## Android → diagnosticsd → CAN UDS surface (non-MDI2, 2026-09-10)

A live Android→`diagnosticsd`→CAN UDS `$22` ReadDataByIdentifier surface exists, distinct
from the Ethernet-UDS bridge above: an observed `Incoming payload: 22 F1 A0 00` read (MEC /
DID `F1A0`) round-trips through `diagnosticsd` onto the CAN diagnostic bus. Access is gated
by an Android-side permission check ("Check Permission first ... any DiagnosticDataID")
before the DID read is dispatched — the exact permission string/holder is not yet
characterized (candidate: same uid=2000 Binder surface as OBD-via-Binder above, or a
distinct signature|privileged permission). This is a **potential non-MDI2 path** to drive
DID reads/routines directly from the Android guest; what needs characterizing next is (a)
the permission name/grant path, (b) whether it's reachable from uid=2000 shell or requires a
signed app, and (c) whether it exposes `$22`/`$2E`/`$31` beyond the single DID observed so
far. OPEN.

Separately, a **direct T1/DoIP bench approach** would replicate MDI2-equivalent bus access
without an MDI2 dongle at all: media-convert the vehicle's diagnostic T1 (BroadR-Reach) pair
to a standard Ethernet PHY, then repoint existing DoIP tooling (e.g. the fsa_protocol.md
stack) at the resulting IP endpoint. This bypasses the Android-guest permission question
entirely by talking to the vehicle's diagnostic network directly, same as a dealer MDI2
would. Route noted, not yet executed on this bench. OPEN.

---

## vlan4 = internal GHS fabric; diagnosticsd forwarding target; bench-reachability of the VIP/UDS path (2026-10-06)

> **[C] CONCURRENCE CORRECTION (2026-10-06, independent 2nd fable agent re-derived from the primary binary + captures). Read before the section below — several claims were disputed:**
> - **diagnosticsd does NOT "forward to `.107:49156`."** It is a root **TCP *server*** on `:49156`; the captured firewall rule is **inbound** — `.107`/`.112` connect *into* it (`iptables_rules_file.txt:35-36`). **No `ESTABLISHED 172.16.4.100↔172.16.4.107` exists in any Y181/Y175 capture;** that line traced to a *gminfo37* (different platform) ref doc. The "forwarding target"/ESTABLISHED framing throughout this section is **UNPROVEN** — read "`.107` is a client that connects in," not "diagnosticsd dials out to `.107`."
> - **`ProxyOfExtComp` is not in the binary** (misattribution). Real symbols: `libdiagnosticsdebugproxy.so`, `MESSAGE_SECURITY_ACCESS_VIP`, `toVIPResponseCode`. The VIP-tier `$27`-proxy *concept* stands; the symbol name does not.
> - **"Bosch" for `.112` is UNVERIFIED** — only the real/external-OUI vs synthetic/internal split is solid (raw scan OUI "unknown, possibly Harman/Samsung").
> - **Exact NRCs (`$10 03→7F 10 10`, `$27 01→7F 27 10`) and "the session gate is strictly upstream of the VIP forward"** are **inferred from libuds handler strings** (`UDSSessionControlCheckHandler`, `UDSSecurityLevelCheckRequestHandler`, `"tester id check differ, process req in default session"`), not a traced call order — single-source.
>
> **What independently CONCURRED (solid):** diagnosticsd is a root TCP server on `:49156`; a 3P `untrusted_app` **can** open a socket to `:49156` *and* to `.107:49156` (SELinux `netdomain` + `(allow netdomain port_type (tcp_socket name_connect))`, no portcon on 49156, OUTPUT ACCEPT, `.107` on-link) — so **the sole defense is the in-process UDS session/tester/security gate**, which an unregistered 3P tester fails (forced to default session). The SBI/EEPROM `$27` bypass is a **separate, downstream VIP/RH850 gate** and gives nothing to an app rejected at the session gate. `.107`/`.14` internal (synthetic/locally-administered MAC); `.112` external (real OUI). **[OPEN]** `.107`'s own trust model is untested.

Answers the question: *does the automotive-Ethernet VLAN connect the Intel A3960 (AAOS) to the
internal radio components (RH850 VIP MCU and/or GHS hypervisor) such that a 3P app reaching
diagnosticsd:49156 could drive UDS to the VIP on the bench, with no vehicle network — and how does
the SBI/EEPROM `$27` bypass interact?*

**Is `172.16.4.107`/`.112` internal or external?** — RESOLVED from ARP + TTL (Y181 and Y175,
bench captures, no vehicle connected):

| vlan4 peer | MAC | Kind | Identity |
|---|---|---|---|
| `172.16.4.107` (diagnosticsd's forwarding target) | `02:05:00:00:02:00` | **locally-administered / synthetic → hypervisor virtual NIC** | **INTERNAL.** Co-resident GHS "RTOS diagnostic" partition on the same Intel A3960 SoC. The **same** virtual NIC is dual-homed as vlan5 `192.168.1.112` (`enumeration/Y181/*/raw/arp_table.txt` — identical MAC). Response **TTL=255** (`platform/networking.md:80`). |
| `172.16.4.14` (ACP) | `02:02:00:00:04:00` | locally-administered / synthetic | **INTERNAL.** GHS control/application partition; statically pinned (`init_ethernet.sh:97 ip neigh replace`). |
| `172.16.4.112` (CGM_OTA) | `10:66:50:0c:ed:d3` | **real/universal OUI → external hardware** (vendor UNVERIFIED — raw scan "unknown, possibly Harman/Samsung"; *not* confirmed Bosch) | **EXTERNAL.** Off-board telematics/CGM hardware. TTL=64 (Linux). |

So **vlan4 is not a pure physical PHY to the car** — it is a hypervisor virtual-switch fabric that
carries both SoC-internal GHS partitions (`.107`, `.14`) *and* a bridge out to one real external
module (`.112`, external real-OUI — vendor unverified). This corrects the vehicle_network.md claim
that the "RTOS partition" was separate hardware (fixed in place there, 2026-10-06).

**diagnosticsd's forwarding target / transport.** Binary is stripped and holds **no hardcoded IP**;
the target is resolved at runtime (the live `ESTABLISHED 172.16.4.100:49156 ↔ 172.16.4.107:49156`
in the Process Profile is the authoritative evidence). Transport = **TCP over vlan4** via
`SockAdaptor` (`libuds/.../ethfrmwk/SockAdaptor.cpp`, confirmed in `.rodata`), to the **`.107`
GHS-internal RTOS diagnostic partition on port 49156** (symmetric 49156↔49156; both ends listen).
diagnosticsd does **not** write UDS to `/dev/ttyS1` or `/dev/ipc` itself and does **not** reach the
RH850 directly — it is an AAOS-guest-side relay to the `.107` partition. Per the VIP-tier note in
Trust Model, only a **`VIP`-tier `$27`** (`MESSAGE_SECURITY_ACCESS_VIP`) is proxied onward
(`ProxyOfExtComp::handleUDSRequest`) to the external VIP component where the seed/key compare and
SBI EEPROM read happen.

**Does vlan4 reach the RH850 VIP MCU directly? NO.** The RH850 is **off-SoC**, reachable only over
**HDLC IPC on `/dev/ttyS1`** (20 channels; diag = channels 3–5, `platform/networking.md:151-169`).
vlan4 is not wired to the RH850. The VIP is reached only *indirectly*: `.107` RTOS partition →
internal SoC↔MCU IPC → RH850. **[single-source/INF — the `.107`→RH850 onward relay is inferred;
RH850 firmware is not in the artifact set, so it cannot be re-derived statically here.]**

**Bench reachability of the chain (3P app → diagnosticsd → UDS → VIP/RH850), no vehicle net:**

- **Transport layer: YES, bench-reachable.** Every hop — AAOS guest → diagnosticsd:49156 → `.107`
  RTOS partition → (internal IPC) → RH850 — lives **inside the radio SoC/module**. None of it needs
  the vehicle CAN bus or any external vehicle ECU powered. The `.107`↔diagnosticsd socket is present
  in bench captures with nothing but the radio on the bench. UDS targeting the **radio's own VIP**
  can therefore execute on the bench; UDS targeting **external vehicle ECUs** (gateway `0x45`, other
  CAN modules) still needs those modules present/powered → **not** on the bench.
- **Application/trust layer: NO — the chain is blocked for an untrusted 3P peer, and the SBI `$27`
  bypass does not open it.** An untrusted peer (shell uid 2000 or an untrusted 3P app) is treated as
  an unregistered tester → the tester-ID soft-check falls through to **default session**, where even
  `$10 03` (enter ExtendedDiagnosticSession) returns `7F 10 10` generalReject, and `$27 01`
  requestSeed returns `7F 27 10` generalReject — **before any seed is issued and before anything is
  forwarded to the VIP.** For the ETHERNET/NOTIFICATION tiers this reject is generated **in-process**
  in diagnosticsd (`libuds` session-state / `UDSSecurityLevelCheckRequestHandler`), not relayed.

**How the SBI/EEPROM `$27` bypass interacts (the crux).** The all-`0xFF` seed accepted by the VIP
validator `0xb67d0` relaxes the **VIP's own cryptographic seed/key compare**, which runs **off-SoC
on the RH850** — i.e. it sits **downstream** of the session/tester-ID gate above. It converts "you
need the real key" into "any format-valid/all-FF key is accepted." It does **not** defeat the
session/tester gate that fails closed *in front of* it. So the SBI bypass only helps an actor who is
**already a registered/authorized tester** (the `.107` RTOS endpoint, or a real Techline/MDI) and
merely lacks the correct key — it does **not** let an untrusted 3P app at diagnosticsd reach the VIP
validator at all, because that app never gets past default-session `generalReject` to exchange a
seed. The two gates are independent; defeating the crypto gate (SBI) without also defeating the
session/tester gate yields nothing from the 3P-app position.

**What a local 3P app actually gets (unauthenticated):** complete the TCP handshake to `:49156`;
drive the **worker-starvation DoS** (above); and send UDS that is uniformly `generalReject`-ed
(no DID reads, no SecurityAccess, no reflash). Driving privileged UDS to the VIP requires first
defeating the **session/tester-ID gate** — a separate, unsolved problem from the SBI/`$27` crypto
bypass.

**Also closed: no alternate internal path for a 3P app.** The direct `/dev/ipc/*` route to the VIP
is **SELinux-denied** to shell/untrusted (AVC-denied; only diagnosticsd and the `vehicle_network`-gid
VHAL may open it). The firewall's unrestricted OUTPUT does let a local app *originate* a TCP connect
straight to `172.16.4.107:49156` (bypassing diagnosticsd), but that lands on the **same** `.107`
RTOS diagnostic listener with the **same** session/tester gate — no added privilege. **[OPEN /
single-source:** whether the `.107` endpoint's *own* trust model differs from diagnosticsd's, and
whether an untrusted Android app is even permitted onto vlan4 by SELinux, is uncharacterized —
needs a second agent / live probe.**]**

**Y175 vs Y181:** the ARP identities (`.107` synthetic/dual-homed, `.112` real-OUI Bosch, `.14`
synthetic) are **identical across Y175, Y181 apr2026, and Y181 jun2026** captures (confirmed ≥2
captures → [C]). The listener existence/owner/bind on `:49156` is [C] on both variants (header
note). The UDS trust/session gate and the VIP-tier relay were binary-derived on the Y181 artifact
and are **UNVERIFIABLE-FROM-LIVE** on the current bench (shell has no diag access) — single-tool,
**flag for concurrence**.

## Open Questions

1. ~~Ghidra `DiagnosticEthernetMonitor::readHeader()` — exact trust check and
   alloc-vs-size-check order (confirm/deny pre-allocation DoS).~~ **Answered
   black-box, no binary needed (Jul 2026):** no pre-allocation (RSS flat up to
   1 GiB declared), but confirmed a **worker-starvation DoS** — see Oversized-
   Payload Behavior above. Still open: the exact source line/loop structure
   (would need the binary — live `adb pull`/`cat` of `/vendor/bin/diagnosticsd`
   is SELinux-denied even from shell on Y181 Enforcing; would require
   re-extracting from a vendor ext4 image as was done previously, since no
   local copy of that extraction currently exists in this repo/machine).
2. ~~Try RTOS-matching source addresses...~~ **Answered — negative** (see
   above).
3. ~~Sequence `TesterPresent`...~~ **Answered — negative** (see above).
4. Probe `IDiagnosticsInternalService` via vndbinder (needs a vendor SELinux
   domain). **Still open.**
5. ~~`DIAG_CUSTOM (0x15)` SID...~~ **Answered — negative** (see above).
6. ~~find the exact concurrent-handler capacity~~ **Narrowed:** N=1 → 0.02s→1.32s
   delay; N=2 → 0.02s→2.55s delay; N=3 → full timeout (≥3s, no response within
   test window). Latency scales with N even below the failure point, which
   reads more like a serialized/polled accept-dispatch path (e.g. a single
   dispatcher thread iterating connections with blocking or long-interval
   reads) than a hard-capacity thread pool — a true fixed-size pool would show
   flat low latency until the pool fills, then a cliff, not a graded ramp.
   Exact structure still needs the binary to confirm.
7. **New:** does the same worker-starvation condition affect the sibling
   `vendor.gm.diagnostics.*` HIDL services (`bridge`, `obd`, `internal`,
   `powermode`) if they share the same accept loop / thread pool as the
   Ethernet TCP listener, or is `IDiagnosticsEthernetService` isolated?
8. **New:** does holding the connection-starvation condition open during an
   active vehicle diagnostic/programming session (e.g. mid-OTA `SecureUnlock`
   state) have a functional effect beyond delayed responses — untested,
   deliberately not attempted on this bench unit without further discussion.
9. **New (2026-09-10):** characterize the Android permission gate on the
   `diagnosticsd` CAN UDS `$22` ReadDataByIdentifier surface (see "Android →
   diagnosticsd → CAN UDS surface" above) — permission name, grant path, and
   whether uid=2000 shell can reach it directly. **Open.**

## GM service-data note (ALLDATA)

GM's ALLDATA for this vehicle publishes **no UDS/GMLAN diagnostic addresses** — the "Code"
column (A11, T3, K9…) is the RPO/schematic designator, not a bus address. So request/response
IDs like `0x14DA80F1` come from **captured bus traffic** (`dps/`), not GM docs. The dealer-side
scan-tool (**GDS2**) *data-parameter* lists for A11 Radio / T3 Amp / K9 BCM — Ethernet per-port
Rx/Tx fail counters + IPs, MEC, ANC/mic levels, battery-sensor stream, etc. — are catalogued in
[`../enumeration/README.md`](../enumeration/README.md) §Vehicle module inventory, and the
diagnostics/programming CAN bus is **CAN6 (5 Mbit/s)** per
[`../platform/networking.md`](../platform/networking.md).

> **Tester-ID note:** `0x14DA80F1`/`0x145AF180` is the **generic OBD tester (F1)** pair used by the
> DPS bench read logs (confirmed: GM_research/diagnostics/gm_dps/DPS_All_Module_Read/.../GCI_*.txt).
> The **dedicated tester (F2)** pair for ECU 0x80 is `0x14DA80F2`/`0x145AF280` (per `A11_CSM_x80.Txt`);
> both reach the radio on HS-CAN.
