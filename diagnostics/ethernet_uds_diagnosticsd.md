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

---

## Process Profile

- PID 599, PPid 1 (init), 10 threads, Sleeping. UID=0 GID=0.
- Groups: 1000 (system), 2001 (adb), 3003 (inet), 3004 (net_admin).
- `CapPrm/CapEff/CapBnd = 0000003fffffffff` → **all capabilities**.
- `NoNewPrivs = 0`, `Seccomp = 0` (no filter). `SigIgn: SIGPIPE`.
- VmSize ~10.4 GB virtual, VmRSS 9.9 MB.
- Network: LISTEN `0.0.0.0:49156`; ESTABLISHED `172.16.4.100:49156 ↔
  172.16.4.107:49156` (bridge to the RTOS diagnostic endpoint on VLAN 4).

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
correct seed/key exchange. Any client that reaches port 49156 and completes 0x27
gains the corresponding tier — the only barrier is the seed→key algorithm,
likely implemented in `/vendor/bin/gm_protokey` (Permission Denied from
uid=2000; see [`platform/security.md`](../platform/security.md#protokey-authentication)).

---

## Oversized-Payload Behavior

| PAYLOAD_LEN | Behavior |
|------------|---------|
| `0x00000000` | Connection closed immediately, no response (zero-length invalid) |
| `0x7FFFFFFF` | **No response — nc times out (2–3 s)**; server blocks waiting for ~2 GB |
| `0xFFFFFFFF` | Same — no response, connection held open |

`SockAdaptor::sendResponse` allocates a **128 KB stack buffer**
(`sub rsp, 0x20008`) with a stack canary; the size check
(`"Payload size too large: %d"` when `payload_size + 9 ≥ 0x20001`) is unsigned
and relies on `getPayloadSize()` being pre-bounded by `EthernetConverter`
(`"Reported Payload Size is incorrect (Payload Size %d vs Data Payload Size %d)"`)
before `sendResponse`. The receive path appears to recv/allocate **before**
fully bounding the size — oversized frames stall the connection rather than
returning an immediate NRC. Whether a `malloc(PAYLOAD_LEN)` precedes the check
(a potential pre-allocation DoS / memory-exhaustion in the root process) needs
Ghidra confirmation of `DiagnosticEthernetMonitor::readHeader()`.

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

## Open Questions

1. Ghidra `DiagnosticEthernetMonitor::readHeader()` — exact trust check and
   alloc-vs-size-check order (confirm/deny pre-allocation DoS).
2. Try RTOS-matching source addresses (`0x00FA`, `0x00F1`, `0xF0`) in the 8-byte
   header to see whether a specific logical address gains a pre-authorized
   tester registration without IP spoofing.
3. Sequence `TesterPresent (0x3E 00)` first, then `0x10 03`, then `0x27 01`.
4. Probe `IDiagnosticsInternalService` via vndbinder (needs a vendor SELinux
   domain).
5. `DIAG_CUSTOM (0x15)` SID for GM-specific initialization.
