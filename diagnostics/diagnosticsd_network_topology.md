# diagnosticsd — Network Topology (vlan4, Android→CAN UDS surface)

> Part of the [`diagnosticsd` Ethernet UDS bridge](ethernet_uds_diagnosticsd.md) doc set (port 49156).

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
would. The original proposal was untested at that checkpoint. The later direct-T1
tests below established custom diagnosticsd TCP access, not DoIP or full
MDI2-equivalent programming access (scope corrected 2026-11-15).

**[Updated 2026-11-11 per Y175_2026-11-02 Bus 2 tap bench finding:]** This has now been
**executed** on the Y175 bench, specifically against `172.16.4.100:49156` (diagnosticsd,
vlan4, reached by posing as CGM `.112` or RTOS `.107` on a direct T1 tap — BUELEC media
converter, no switch in path, since a switch was found to silently strip the 802.1Q VLAN
tags needed to reach vlan4/vlan5 at all). Result: diagnosticsd **is** externally reachable
over this plane — it is a root TCP server bound `0.0.0.0:49156`, gated only by a source-IP
allow-list of exactly `{172.16.4.107, 172.16.4.112}` (an exhaustive sweep of all 253 vlan4
source addresses and the full TCP 1–65535 range found no other allow-listed identity or
listening port). **Corrected 2026-11-14:** the historical `$10/$27/$31`
NRC `0x10` results did not prove a source-independent application lock; the
corrected tester/session sequence now returns a level-1 `67 02` grant. The original
routine request was not rerun at that checkpoint. Later direct-T1 routine
results, including the calibration clear, are recorded in the
[owning routine/recovery reference](diagnosticsd_routines_and_recovery.md);
blanket claims that no routine effect was demonstrated are superseded.
No DoIP service was confirmed by the later probes; a silent UDP result is not
proof of absence. See
`Y175_LIVE_RADIO_T1_SECURITY_ASSESSMENT_2026-11-02.md` and
`source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.

---

## vlan4 = internal GHS fabric; diagnosticsd forwarding target; bench-reachability of the VIP/UDS path (2026-10-06)

> **[C] CONCURRENCE CORRECTION (2026-10-06, independent 2nd fable agent re-derived from the primary binary + captures). Read before the section below — several claims were disputed:**
> - **diagnosticsd does NOT "forward to `.107:49156`."** It is a root **TCP *server*** on `:49156`; the captured firewall rule is **inbound** — `.107`/`.112` connect *into* it (`iptables_rules_file.txt:35-36`). **No `ESTABLISHED 172.16.4.100↔172.16.4.107` exists in any Y181/Y175 capture;** that line traced to a *gminfo37* (different platform) ref doc. The "forwarding target"/ESTABLISHED framing throughout this section is **UNPROVEN** — read "`.107` is a client that connects in," not "diagnosticsd dials out to `.107`."
> - **`ProxyOfExtComp` is not in the binary** (misattribution). Real symbols: `libdiagnosticsdebugproxy.so`, `MESSAGE_SECURITY_ACCESS_VIP`, `toVIPResponseCode`. The VIP-tier `$27`-proxy *concept* stands; the symbol name does not.
> - **"Bosch" for `.112` is UNVERIFIED** — only the real/external-OUI vs synthetic/internal split is solid (raw scan OUI "unknown, possibly Harman/Samsung").
> - **Exact NRCs (`$10 03→7F 10 10`, `$27 01→7F 27 10`) and "the session gate is strictly upstream of the VIP forward"** are **inferred from libuds handler strings** (`UDSSessionControlCheckHandler`, `UDSSecurityLevelCheckRequestHandler`, `"tester id check differ, process req in default session"`), not a traced call order — single-source.
>
> **Corrected 2026-11-14:** diagnosticsd is a root TCP server; the direct
> external client completed the F4/extended-session/31-FF/12-zero exchange.
> Historical SELinux `name_connect` and OUTPUT rules describe permission to
> attempt a connection, not proof that a GHS endpoint is present or reachable.
> The later external T1 checks did not reach those candidates. Their own
> trust models remain untested; synthetic MACs alone do not prove a specific
> partition's identity. The successful Android endpoint does not establish
> arbitrary service/key acceptance or GHS access.

Answers the question: *does the automotive-Ethernet VLAN connect the Intel A3960 (AAOS) to the
internal radio components (RH850 VIP MCU and/or GHS hypervisor) such that a 3P app reaching
diagnosticsd:49156 could drive UDS to the VIP on the bench, with no vehicle network — and how does
the SBI/EEPROM `$27` bypass interact?*

**Partition identity and onward transport — corrected 2026-11-15:** the
previous table labeled historical peers as conclusively identified internal
GHS partitions and inferred the VIP relay from address/MAC/TTL patterns.
Those observations do not prove current partition identity or reachability.
A configured permanent neighbor establishes configuration intent; a locally
administered MAC does not establish hypervisor ownership. Later external T1
probes did not reach the candidate GHS endpoints. No symmetric RTOS socket
or complete Android→GHS→VIP forwarding chain was demonstrated.

RH850 is a separate MCU with a documented VIP↔SoC HDLC UART link. The
UART-derived diagnostic channel is **6**, not the earlier unsupported range
3–5; see the [owning IPC channel map](../hardware/teardown.md#ipc-channel-map-from-vip-uart-log).
This does not establish which internal component/transport implements every
Ethernet diagnostic request. Direct-T1 reads, routine outcomes and SID/enum
conversion gaps must be evaluated individually.

**Bench results and internal-route limits (corrected 2026-11-14):**

- The external client reached Android `diagnosticsd`, read software identification,
  entered extended session and obtained a level-1 `67 02` grant with the documented
  31-FF/12-zero exchange. The old claim that an unregistered shell/app can never
  pass the default session is withdrawn; no app-registration step was needed
  for the successful direct T1 test.
- The original negative address sweep omitted F4/F5. Its all-rejected result
  does not show that a correct tester/session sequence fails or that SBI has
  no effect on Ethernet. Only the exact 12-zero-byte response was accepted;
  arbitrary format-valid, all-FF or differently sized keys were not tested.
- At the initial SecurityAccess checkpoint no write/routine/reset was demonstrated.
  **Later results supersede that blanket limit:** selected direct-T1 routines
  completed, including calibration clear; RequestDownload remained rejected,
  and the tested ECUReset did not reboot Android. Stock LTZ programming later
  succeeded using MDI2, which is a separate transport result. See the
  [routine/recovery record](diagnosticsd_routines_and_recovery.md).
  No Android root or GHS shell was obtained; diagnostic SecurityAccess does
  not itself change the Android UID or SELinux domain.
- The static reference contains diagnostic framework code, but no complete
  live path through GHS/RTOS to the VIP was established. Prior claims of an
  observed internal RTOS socket are explicitly disputed above. The external
  GHS candidates did not answer the later T1 reachability checks. Do not
  substitute historical addresses, permitted socket policy, or synthetic MACs
  for proof of a currently reachable partition or of its authorization rules.
- Direct IPC and HIDL paths are separate interfaces. Live shell queries to
  the diagnostic-internal and root file-service HALs returned
  `does not exist, or no permission to connect`; the updater returned
  `No shell command implementation.` No alternate UID-0 shell was obtained.

**Build scope:** the corrected UDS responses are live Y175 results, informed
by Y181B static address/session handlers. These binaries are not claimed
identical. Historical Y181/Y175 ARP observations do not replace current
reachability testing or prove the key-compare backend's location.


## Working T1 ADB follow-up (2026-11-15)

**Working radio listener: TCP 9040.** USB-authorized ADB was used to select
an unused port already allowed by the shipped firewall for the chosen
VLAN-5 source identity. A source-bound host relay on loopback TCP 19040
then provided a working ADB transport. A fresh shell returned UID 2000;
the radio boot identity matched the USB connection in memory. No private
addresses or identifiers are reproduced here.

The firewall is default-deny and matches interface, source/destination
address and destination port. Standard TCP 5555 remains unavailable through
that tested T1 policy. Historical `Connection refused` on 9040 described an
absent listener at that checkpoint, not a permanent prohibition. No firewall
rule change, root shell, diagnostic unlock or privileged app conversion was
needed for the successful ADB connection.

Use the [networking reference](../platform/networking.md#listening-ports) and
the established `BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §9.2 procedure
in the Y175 analysis/source_notes tree. Preserve the allowed source binding;
selecting port 9040 alone is insufficient. This adds an Android shell
transport, not a new UDS service or proof of direct GHS access.

The radio clock was compared to the Mac and synchronized before subsequent
live tests; timezone matched the Mac. RH850 calendar timestamps are a
separate clock and must not be assumed corrected by an Android time update.
