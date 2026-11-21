# diagnosticsd — UDS-over-TCP Bridge

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026 - November 15, 2026
**Binary:** `/vendor/bin/diagnosticsd` (x86-64 ELF, stripped, 426,824 bytes)
**SELinux:** `gm_diagnosticsd_exec:s0` → domain `gm_diagnosticsd`

This documents the **Ethernet** diagnostic channel: the root daemon
`diagnosticsd` listening on TCP `0.0.0.0:49156`, which bridges GM Ethernet
Diagnostics (UDS / ISO 14229) into Android diagnostic handlers. A complete
live forwarding path to a separate RTOS diagnostic endpoint remains unproven
(corrected scope, 2026-11-15). This is distinct from the **CAN/DPS** diagnostic path captured in
[`diagnostics/dps/`](dps/) (ECU 0x80, DPS 4.56) and from the FSA service layer
([`platform/fsa_protocol.md`](../platform/fsa_protocol.md)). The `gm_diagnosticsd`
SELinux domain and its UDS SID list are summarized in
[`platform/security.md`](../platform/security.md#can--uds-diagnostic-services--pointer-only);
this doc adds the live Ethernet wire format and trust model.

**2026-10-30, Y175:** A shell running as UID 1000 in `system_app` connected to
the UID 0 listener on port 49156 without sending protocol data. This confirms
TCP reachability from that domain, not service identity on that connection,
request authorization, or calibration-write access.

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

## Contents

This document was split 2026-11-15 by subject matter; each file is self-contained with
its original section headings/anchors preserved in the destination files.
Links must target those files; fragments on this index do not automatically redirect.

| File | Covers |
|---|---|
| [`diagnosticsd_protocol.md`](diagnosticsd_protocol.md) | Process profile, 8-byte wire header, SID/DID/RID service tables, native Java handler inventory, the native wire-SID↔enum bimap (root cause of the `11`/`23` NRC-25 failures), legacy service labels, HIDL interfaces, source structure/symbols, OBD-via-Binder |
| [`diagnosticsd_security_access.md`](diagnosticsd_security_access.md) | The live T1 SecurityAccess bypass (31-FF seed / 12-zero response → `67 02`), the live ECUReset validation, and the binary-confirmed trust model (tester/session checks, privilege tiers) |
| [`diagnosticsd_dos.md`](diagnosticsd_dos.md) | Oversized-payload behavior and the confirmed unauthenticated worker-starvation DoS |
| [`diagnosticsd_dids_and_dtc.md`](diagnosticsd_dids_and_dtc.md) | RH850/UART DID correlation, the bounded read-only sweep (DTC/memory/file probes), the exhaustive 0x0000–0xFFFF DID sweep, cross-state verification, and the calibration-identity archive comparison |
| [`diagnosticsd_routines_and_recovery.md`](diagnosticsd_routines_and_recovery.md) | RoutineControl outcomes (0249/0475/0260/0248/FF01/etc.), the full calibration-clear → NoCalibration fault → MDI2 LTZ recovery incident, the BCM-replacement/factory-wipe investigation, and the AVTP pcap/audio side-findings |
| [`diagnosticsd_network_topology.md`](diagnosticsd_network_topology.md) | The Android→diagnosticsd→CAN UDS surface, the direct-T1/DoIP bench approach, and the vlan4 internal-GHS-fabric topology finding |

### Follow-up findings, 2026-11-15

- [Working T1 ADB](diagnosticsd_network_topology.md#working-t1-adb-follow-up-2026-11-15):
  radio TCP 9040, source-bound host relay 19040; historical 5555 failures are
  not evidence that all network ADB is unavailable.
- [UART checksum scope](diagnosticsd_routines_and_recovery.md#uart-checksum-scope-2026-11-15):
  logged seed-buffer checksums match Adler-32; this does not recover UDS seed/key math.
- [Audio follow-up](diagnosticsd_routines_and_recovery.md#audio-usage-follow-up-2026-11-15):
  all 16 public usages mapped to live PCM positions; five system usages refused focus.
  The complete wire reference stays in [avb_audio_transport.md](../platform/avb_audio_transport.md#4-vlan-stream-inventory-and-packet-layout).

---

## Open Questions

1. ~~Ghidra `DiagnosticEthernetMonitor::readHeader()` — exact trust check and
   alloc-vs-size-check order (confirm/deny pre-allocation DoS).~~ **Answered
   black-box, no binary needed (Jul 2026):** no pre-allocation (RSS flat up to
   1 GiB declared), but confirmed a **worker-starvation DoS** — see
   [Oversized-Payload Behavior](diagnosticsd_dos.md#oversized-payload-behavior).
   Still open: the exact source line/loop structure
   (would need the binary — live `adb pull`/`cat` of `/vendor/bin/diagnosticsd`
   is SELinux-denied even from shell on Y181 Enforcing; would require
   inspecting the processed Y181B reference. That reference is now available;
   `readHeader` at `0x46260` was inspected for the 2026-11-14 framing correction.
   Worker-starvation call flow was not re-tested or fully traced in that work).
2. **Corrected 2026-11-14:** the old address sweep omitted accepted testers
   F4/F5. F4 is live-validated through a level-1 SecurityAccess grant.
3. **Corrected 2026-11-14:** F4 plus extended-session entry, requestSeed and
   a 12-zero-byte response succeeded; the old negative sequencing conclusion
   is superseded by the
   [validated sequence](diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
4. Probe `IDiagnosticsInternalService` via vndbinder (needs a vendor SELinux
   domain). **Still open.**
5. ~~`DIAG_CUSTOM (0x15)` SID...~~ **Answered — negative** (see
   [Oversized-Payload Behavior](diagnosticsd_dos.md#oversized-payload-behavior)).
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
   `diagnosticsd` CAN UDS `$22` ReadDataByIdentifier surface (see
   [Android → diagnosticsd → CAN UDS surface](diagnosticsd_network_topology.md#android--diagnosticsd--can-uds-surface-non-mdi2-2026-09-10))
   — permission name, grant path, and whether uid=2000 shell can reach it
   directly. **Open.**

10. **ELK control path, updated 2026-11-15:** VIP selector `8180` is now
    traced statically. GWM FDF0 writes and candidate GM IOCID 8180 were rejected
    by missing Android handlers on the tested Ethernet route; CAN acceptance,
    outer gates and actual ELK entry remain open. See the
    [live test](diagnosticsd_routines_and_recovery.md#gwm-boot-target-and-gm-8180-follow-up-2026-11-15)
    and [firmware trace](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#vip-elk-control-selector-and-gwm-comparison-2026-11-15).

## GM service-data note (ALLDATA)

GM's ALLDATA for this vehicle publishes **no UDS/GMLAN diagnostic addresses** — the "Code"
column (A11, T3, K9…) is the RPO/schematic designator, not a bus address. So request/response
IDs like `0x14DA80F1` come from **captured bus traffic** (`dps/`), not GM docs. The dealer-side
scan-tool (**GDS2**) *data-parameter* lists for A11 Radio / T3 Amp / K9 BCM — Ethernet per-port
Rx/Tx fail counters + IPs, MEC, ANC/mic levels, battery-sensor stream, etc. — are catalogued in
[`../enumeration/README.md`](../enumeration/README.md) §Vehicle module inventory, and the
diagnostics/programming CAN bus is **CAN6 (5 Mbit/s)** per
[`../platform/ethernet_networking.md`](../platform/ethernet_networking.md#can-bus).

> **Tester-ID note:** `0x14DA80F1`/`0x145AF180` is the **generic OBD tester (F1)** pair used by the
> DPS bench read logs (confirmed: GM_research/diagnostics/gm_dps/DPS_All_Module_Read/.../GCI_*.txt).
> The **dedicated tester (F2)** pair for ECU 0x80 is `0x14DA80F2`/`0x145AF280` (per `A11_CSM_x80.Txt`);
> both reach the radio on HS-CAN.

**UART RX follow-up, 2026-11-14:** a bounded owner-requested CR/LF/Ctrl-C
burst test on reported MCU RX pin 170 at 115200/8N1 produced no recognizable
prompt or demonstrated shell. Pin-52 logs remained readable and included
NoCalibration. This did not verify MCU reception or the RX mux. See the
[owning UART findings](../hardware/teardown.md#rh850f1k-package--uart-pinout).
