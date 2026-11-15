# diagnosticsd — SecurityAccess & Trust Model

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

---

## Live T1 SecurityAccess correction (2026-11-14)

**Live target:** Y175 `W213E-Y175.5.2-SIHM22B-383.1`, owner's isolated bench,
with SBI modification reported by the owner. **Static reference:** Y181B
`W231E-Y181.3.2-SIHM22B-499.3`, processed `os/vendor/bin/diagnosticsd`.
The builds differ; the Y181B binary has not been byte-matched to the live Y175
executable. Its address checks predicted the successful live correction.

The direct T1 client used a firewall-allowed VLAN 4 source identity and tester
`0x00F4`, target `0x0084`, on one TCP connection. No controlling Android app,
root shell, MDI2, or separately registered tester was needed for this exchange:

| Step | UDS request | Final response / observation |
|---|---|---|
| Software-identification read | `22 F1 81` | `62 F1 81 <software data>` |
| TesterPresent | `3E 00` | `7E 00` |
| Enter extended session | `10 03` | `50 03 00 64 01 F2` |
| Request level-1 seed | `27 01` | `67 01` + **31 bytes of `FF`** |
| Submit documented bypass response | `27 02` + **12 zero bytes** | **`67 02`** |
| Restore default session | `10 01` | `50 01 00 64 01 F2` |

Two successful extended-session/seed exchanges were performed; the second also
included the 12-zero-byte response. Both restored the default session. Basic
requests with tester `0x00F5` also returned positive software/TesterPresent
responses; its default-session `27 01` returned `7F 27 7F`
(`serviceNotSupportedInActiveSession`). `22 F1 86` returned `7F 22 31`, which
is a DID-specific rejection, not a blanket denial of diagnostic access.

**Why the earlier probes failed:** tester `0x0FA0` returned `7F <SID> 10`
for DID reads, TesterPresent and requestSeed. In the Y181B binary,
`UDSAddressCheckRequestHandler::handleUDSRequest` at `0x49350` accepts tester
low bytes `F4`/`F5`; its invalid-tester branch constructs NRC `0x10`. The
big-endian decoding is in `SockAdaptor::readHeader` at `0x46260`. Thus the old
all-rejected tests did not establish a missing app, SBI-inactive state, or a
universal SecurityAccess barrier. Changing TCP source IP alone did not fix the
incorrect logical tester address. Extended-session entry was also necessary
for the tested seed request.

**Scope:** `67 02` proves acceptance of this exact level-1 response. It does
not prove arbitrary-key acceptance, programming-session entry, calibration or
partition writes, relaxed signature verification, Android UID 0, or a GHS
shell. No download/transfer/routine/reset request was sent during that
SecurityAccess validation; the separate ECUReset follow-up is documented below. The Android
UpdateService dump reported `SBI=false`, `MEC=-1` despite the accepted
exchange; those application values are not an authoritative VIP-state reading.

The MDI2/CAN reference also uses a 31-byte all-FF seed and a 12-zero-byte
response. This supports shared UDS behavior; the custom TCP framing is not
MDI2 transport, CAN ISO-TP, or DoIP. Neither identical payloads nor overlapping
service names prove the complete OBD connector → gateway → A11 internal route
or the component performing the key comparison.

Separate reachability checks on both external T1 adapters received replies
from the Android guest on both tagged networks, but no ARP reply from the
historically documented GHS candidates. Targeted candidate connections did
not complete. This bounds external reachability under the tested switch
configuration; it does not show that GHS is absent or stopped. Temporary host
VLAN interfaces were removed; no packet-capture file was created.

---

## Live T1 ECUReset validation (2026-11-14)

A separate follow-up tested whether the direct T1 path can perform the radio
hard reset used by the MDI2 workflow. The same live Y175 bench target,
firewall-allowed VLAN 4 identity, logical tester F4 and ECU target 0x0084 were
used. Extended-session entry and the documented SecurityAccess exchange both
succeeded before sending `11 01`.

| Stage | Observed response |
|---|---|
| Extended session `10 03` | `50 03 00 64 01 F2` |
| Seed `27 01` | `67 01` plus 31 all-FF bytes |
| `27 02` plus 12 zero bytes | `67 02` |
| Hard reset `11 01`, while processing | Repeated `7F 11 78`, approximately every 5 seconds |
| Final hard-reset result | **`7F 11 25` at approximately 30 seconds** |
| Restore default session `10 01` | `50 01 00 64 01 F2` |

NRC `0x78` is responsePending, not an acceptance acknowledgment. NRC `0x25`
is noResponseFromSubnetComponent. No `51 01` positive reset reply was received.
The Android guest's boot ID remained unchanged and its uptime increased from
about 4806 to 5072 seconds across the setup and observations; diagnosticsd
remained running with the same PID. No Android reboot or completed radio hard
reset was demonstrated. VIP/GHS partition state was not independently observed,
so these checks do not exclude an unobserved partial-component effect.

The first attempt stopped waiting after 15 seconds of pending replies; an
immediate default-session request received `7F 10 21` (busyRepeatRequest).
After the channel again answered TesterPresent/default-session requests, one
repeat allowed up to 90 seconds and obtained the final `7F 11 25` at 30 seconds.
Thus the reported result is the final wire response, not the shorter client's
timeout. Default session was then positively restored and the temporary host
VLAN interface removed. No reset was substituted through ADB; ADB was used
only to observe boot identity, uptime, daemon state and existing logs. A later
UART-instrumented repeat is recorded in the
[bounded read-sweep section](diagnosticsd_dids_and_dtc.md#bounded-read-only-sweep-and-uart-reset-follow-up-2026-11-14).

**MDI2 comparison:** successful session/SecurityAccess traffic proves that
some UDS services work through the custom T1 transport. This reset result
neither proves that `0x11` is unsupported nor demonstrates a working reset or
a drop-in MDI2 replacement. At this stage the cause was unresolved; the later
[concurrent UART/logcat test](diagnosticsd_protocol.md#concurrent-uart-and-usb-logcat-correlation-2026-11-14)
identifies an unmapped AAOS converter service for both reset and memory read. The NRC alone did not prove downstream receipt. No programming transfer,
partition write, firmware replacement or UID-0 shell was attempted by this reset
test.

---

## Trust Model (binary-confirmed)

**Live socket access and UDS authorization are separate.** An unprivileged
client can connect to the daemon and, with the corrected logical tester ID
and session sequence above, obtain positive UDS responses and `67 02`. Root
ownership of the daemon does not give the client a root shell. Import-table
absence of credential functions alone is not proof that every authorization
check is absent.

The inspected application checks include:

1. **Logical source/target validation:** tester low byte `F4`/`F5` is accepted
   by `UDSAddressCheckRequestHandler`; the old `0x0FA0` fails here.
2. **Active tester/session checks:** `UDSSessionControlCheckHandler` at
   `0x4a7c0` compares tester IDs and evaluates a mismatched tester in the
   default session. This is not proof that only an RTOS client can establish
   a session. The live external client entered extended session successfully.
3. **Session and security level:** the successful order is `10 03`, `27 01`,
   `27 02` plus 12 zero bytes. Keep the exchange serialized on one connection
   and explicitly restore `10 01`; connection closure alone was not tested as
   a session-reset mechanism. The static service uses shared active-tester/
   session state, so do not describe it as proven purely per-connection state.

**Privilege tiers:** `VIP` > `ETHERNET` > `NOTIFICATION`, each unlocking more
UDS services; the tier is granted by the 0x27 SecurityAccess response after a
correct seed/key exchange. `checkSecurityLevelTable` (string, see the
[memory-access security table](diagnosticsd_dids_and_dtc.md#memory-access-and-additional-security-levels))
is **only the per-tier allowed-service lookup table** — which SIDs a tier may
call once granted — **not** an SBI/seed-key gate itself.

**[D] CORRECTION (2026-09):** an earlier version of this doc guessed the
seed→key algorithm was "likely implemented in `/vendor/bin/gm_protokey`." This
is **wrong** — `gm_protokey` is the boot-time proto-key / disk-encryption
(`DATA_LOCKED`) state validator (`init.protokey.rc`, kernel-netlink `setKey`,
sets `vendor.gm.security.state`); it is unrelated to UDS SecurityAccess. See
[`platform/security.md`](../platform/security.md#protokey--adb-authentication)
for what `gm_protokey` actually does (ADB/seed-auth state, not `$27`).

**Backend-location limit:** the binary contains in-process `libuds` address,
session and allowed-security-level handlers. A handler/table name does not by
itself identify the component performing the seed/key comparison. Historical
`ProxyOfExtComp` symbol and direct RTOS-forwarding claims are disputed in the
[concurrence correction](diagnosticsd_network_topology.md#vlan4--internal-ghs-fabric-diagnosticsd-forwarding-target-bench-reachability-of-the-vipuds-path-2026-10-06).
The live level-1 all-FF/12-zero/`67 02` exchange
establishes the observable Ethernet behavior, not the exact VIP/SoC/GHS call
chain or a normal non-bypass seed-to-key algorithm.

---
