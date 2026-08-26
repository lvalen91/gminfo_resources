# Provenance / QA Audit — gminfo_resources

Date: 2026-08-17. Method: each claim checked against on-disk ground-truth artifacts
(EEPROM .bin, enumeration/Y181/apr2026 raw dumps, scratchpad/diagx firmware extract,
CalSets.db, external GM_research VIP binary + delivery_manifest). Default = disbelief.

> **Why this exists.** The owner flagged that prior AI research sessions may have written
> inferred or hallucinated findings into this repo as if they were fact. This ledger is the
> skeptical cross-check: it classifies the decision-driving claims by how well the *actual
> artifacts* back them, so a reader knows what is measured vs guessed. See the
> "Resolutions applied" section at the bottom for what was corrected as a result.

Verdict key: VERIFIED (artifact shows it) / INFERRED (plausible, backed by derived or
partial evidence, stated harder than warranted) / UNSUPPORTED (asserted as fact, no
artifact) / CONTRADICTED (an artifact refutes it).

---

## CLUSTER 1 — EEPROM offset→function mappings

| # | claim (short) | doc:location | verdict | ground-truth evidence | note |
|---|---|---|---|---|---|
|1| EEPROM = ST M24C64, 8192 B | EEPROM_Analysis_Report.md:4-5 | VERIFIED | `eeprom/bins/*.bin` are exactly 8192 bytes | chip id is a hw claim, size confirmed |
|2| 0x0440 Primary SBI = `5A FF 5A FF`, data byte 0xFF = ADB bypass | Report:131 / UNDOC:29 | VERIFIED | `xxd -s0x440` both bins → `5aff 5aff` | data byte FF in both variants |
|3| 0x0A80 Backup SBI = `5A FF 5A FF` | Report:136 | VERIFIED (LTZ) / variant-specific | LTZ bin `5aff5aff`; **HC bin `69ff 69ff`** | marker differs by variant, data byte FF same |
|4| Bypass is marker-agnostic (only data byte matters; markers CalGroup-assigned at runtime) | UNDOC:§13, T1:137 | VERIFIED | HC vs LTZ differ in frame byte at 0x0A80 (0x69 vs 0x5A) but share data 0xFF; VIP binary has `[CAL] EEPROM Write Failure for CalGroup-%d`, `read eeprom error !, Reinstating the default value` | two-variant diff is real cross-check |
|5| "Firmware refs" counts (0x04A0=17, 0x04C0=11, 0x0A40=28, 0x0BE0=24, 0x0A00=871, 0x0B00=311) | UNDOC:§2,§5 | UNSUPPORTED (self-admitted) | not reproducible from shipped artifacts; doc's own note: two passes disagree (0x0A00 871 vs 854; 0x0B00 311 vs 305) | doc honestly flags this at lines 14-20 |
|6| Debug-string context anchors `[IPC_S]`,`[SS_SWC]`,`[GYROACCL]`,`[CAL]`,`PROTOKEY`,`ICUSB` in VIP binary | UNDOC:§10.2 | VERIFIED | `strings 86331656` returns all of them | string anchoring legit even if ref COUNTS aren't |
|7| "Zero literal marker patterns (`69 00 69`,`C3 00 C3`,`5A FF 5A`) in binary" | UNDOC:§13.4 line 565 | **CONTRADICTED** | hex scan of 86331656: `690069`×3, `c300c3`×4 (only `5aff5a`=0) | literal "zero" is false; broader runtime-marker thesis still separately supported by #4 |
|8| VIP validation fn @ 0xb67d0 (Y177 4-byte stub vs Y181 906-byte), chain 0xecd84/0xb6652/0xaee28, flag @ RAM 0x3e06 | UNDOC:§8,§10.1 | **RESOLVED 2026-08-25: the "Y177 stub" is REFUTED** | Three-way VIP_APP diff (Y175/Y177/Y181) shows a full ~906-byte fn in ALL builds (Y177 @0xb67d4, Y175 @0xb6708); "stub" was a fixed-address misread. Confirmed at byte level. See VIP_FIRMWARE_Y177_Y181_COMPARISON.md §2 | asm-quote non-reproducibility now explained: the stub never existed |
|9| VIP PN 86331656 hash = `c381ed1c507d6ac6381c315fe94d9114` | UNDOC:§13.1 line 536 | UNSUPPORTED/CONTRADICTED | md5 of shipped `.../Y181/86331656` = `e47928d9f409834083abc9a068ce65e0` (≠) | may be a packaging diff; hash not reproducible from this artifact |
|10| EEPROM 0x0E13=900 "display width" / 0x0E17=600 etc. (Store A) | Report:336, T1:§5 Store A | INFERRED (self-marked) | no dump-decode proof; T1 correctly marks `[I]` "bit mapping GUESSED" | honest |

## CLUSTER 2 — Security / lockdown verdicts

| # | claim | doc:location | verdict | evidence | note |
|---|---|---|---|---|---|
|11| Bootloader locked | T1:57, QUICK_REF:243 | VERIFIED | `all_properties.txt`: `ro.boot.flash.locked=1` | |
|12| AVB locked + green | T1:57, QUICK_REF:242-244 | VERIFIED | `ro.boot.vbmeta.device_state=locked`, `ro.boot.verifiedbootstate=green`, avb_version 1.2 | |
|13| oem_unlock disabled | T1:57 | VERIFIED | `sys.oem_unlock_allowed=0` | |
|14| ro.debuggable=0 / ro.adb.secure=1 (adb not root-able) | T1:57 | VERIFIED | `debug_props.txt` + `all_properties.txt` both show 0 / 1; adbd running but secured | |
|15| SELinux Enforcing (Y181) | QUICK_REF:61 | VERIFIED | `selinux_status.txt` = `Enforcing` | |
|16| **IOMMU/VT-d is OFF (`intel_iommu=off`)** `[C]` | T1:71-73 | **UNSUPPORTED** | `cmdline.txt` = permission-denied (never captured); only IOMMU artifact is `kernel_config.txt: INTEL_IOMMU=y` (compiled IN). No artifact shows runtime off | `[C]` marker unjustified — this underpins the "wire→host DMA" vector |
|17| No virtio-net in guest | T1:65 | VERIFIED | `kernel_modules.txt`: only `trusty_virtio`, no `virtio_net` | |
|18| **Guest drives eth0 with `e1000e`** `[C]` | T1:65 | **CONTRADICTED** | `network_interfaces.txt`: `eth0 Driver igb_avb`; `kernel_modules.txt` loads `igb_avb`, no e1000e. Also contradicts T1's own §1 | |
|19| Y181→Y177 downgrade blocked by GHS rollback counter (misc/vda9, "tested FAILED") | QUICK_REF:64-65,278; T1:106 | INFERRED / UNSUPPORTED as measured **→ NOW OWNER-VERIFIED, see Resolutions** | rb_ua.conf + A/B fstab + TSS/AVB manifest support a rollback mechanism; empirical result now corroborated by owner bench re-test (2026-08-17) | mechanism plausible; behavior now field-confirmed |
|20| DSU/GSI present but dead (sepolicy-blocked) | QUICK_REF:185-193 | Split: present VERIFIED / dead INFERRED | `service_list.txt`: `dynamic_system` service present; sepolicy-block claim not confirmable (cil not in provided set) | |
|21| No adb→root path | security corpus | VERIFIED (as configured) | ro.debuggable=0 + ro.adb.secure=1 (preconditions) | |

## CLUSTER 3 — Network topology + listeners

| # | claim | doc:location | verdict | evidence | note |
|---|---|---|---|---|---|
|22| eth0=192.168.1.100, MAC 02:04:00:00:01:00, driver igb_avb | T1:§1 | VERIFIED | `ip_addr.txt`, `network_interfaces.txt` | |
|23| vlan5=192.168.1.100 (service), vlan4=172.16.4.100 (internal) | T1:§1 | VERIFIED | `ip_addr.txt`, `ip_route.txt` | |
|24| br0 DOWN no IP; brctl_add/setip stopped | T1:19-21 | VERIFIED | `ip_addr.txt` br0 state DOWN no inet; `init_services.txt` brctl_add=stopped, setip=stopped | |
|25| Listeners 6363 + 49156 on 0.0.0.0 | T1:§2, QUICK_REF:103-105 | VERIFIED | `open_ports.txt` both LISTEN 0.0.0.0 | |
|26| 90xx (9002/9005/9010/9012/9016/9018) bind ::ffff:192.168.1.1 = VM↔host IPC | T1:45,§6 | VERIFIED | `open_ports.txt` all six present on ::ffff:192.168.1.1 | |
|27| OLD "192.168.1.1 = GHS hypervisor bridge (networked service)" is wrong/superseded | T1:§6 | VERIFIED correction (old claim CONTRADICTED) | old framing literally present in `network_scan.txt` ("GHS Hypervisor Bridge… Virtual IP 192.168.1.1"); T1 retires it correctly | |
|28| 90xx "unreachable even from local guest — No route to host" `[C]` | T1:45,§6 | INFERRED / partly CONTRADICTED | `open_ports.txt` shows ESTABLISHED sessions from 192.168.1.x → .1:9005/9010/9012/9018 — the guest IS connected. "No route to host" quote has no artifact | reachability of the *client* direction is demonstrated |
|29| Gateway .102 runs dnsmasq-2.78 + SOME/IP-SD UDP 30490 | T1:32-34 | VERIFIED (derived) | `network_scan.txt`: .102 TCP53 dnsmasq-2.78, UDP30490 SOME/IP-SD | from derived scan file, not raw pcap |
|30| ".102 (= 172.16.4.1)" gateway equivalence | T1:33 | INFERRED | raw `arp_table.txt` has 192.168.1.102 (02:04:00:00:02:00) but **no 172.16.4.1 row**; equivalence asserted only in derived `network_scan.txt` via shared MAC | |
|31| DoIP 13400 not present on IVI | T1:47 | VERIFIED | absent from `open_ports.txt` | |
|32| No perimeter firewall in vendor init | T1:49-51 | INFERRED | referenced rc absence-of-DROP not confirmed from provided set | |
|33| diagnosticsd = the 49156 UDS-over-TCP server | T1:42,§6 | INFERRED (well-supported) | `open_ports.txt` PID col = `-` (not captured); binary has `TCPServer`,`UDSTransferData`,`CalibrationProgrammer`; rc has "stop diagnosticsd for cts-on-gsi tcp port testcases" | doc honestly flags attribution caveat + gives live command to settle |

## CLUSTER 4 — Calibration / $27

| # | claim | doc:location | verdict | evidence | note |
|---|---|---|---|---|---|
|34| Cal blob unsigned: 16-bit checksum + SHA-256 only, **no RSA/X.509/SecOC** | T1:88-89 | VERIFIED | diagnosticsd strings `CAL_CHECKSUM_FAILURE`, `CAL_MESSAGE_DIGEST_FAILURE`, `generateSHA256`; no RSA/X509/SecOC in cal-path binaries | negative confirmed within provided binaries |
|35| Single gate = UDS `$27` SecurityAccess (checkSecurityLevelTable, SecurityRequestToResponsePipeline) | T1:90 | VERIFIED | both symbols present in `bin__diagnosticsd` | |
|36| Self-write path overrides dir → inotify → processZippedModFile → CalSets.db | T1:82-86 | VERIFIED | calserviced strings: `/mnt/vendor/calibration/overrides/`, `inotify_add_watch`, `processZippedModFile`, `apply_overrides`; `calserviced.rc` creates the dirs | |
|37| `*.calovride` OVERRIDE_BACKDOOR with "!!!DISABLE BEFORE RELEASE!!!" at main | T1:98-102 | VERIFIED (verbatim) | `bin__calserviced`: `main: !!!WARNING!!! !!!OVERRIDE_BACKDOOR (*.calovride) HAS BEEN ENABLED!!!  !!!DISABLE BEFORE RELEASE!!!` and `.calovride` | whether *compiled active* still open, correctly `[O]` |
|38| Backdoor needs vendor_cald ctx, overrides dir mode 770 | T1:102 | VERIFIED | `calserviced.rc`: `mkdir /mnt/vendor/calibration/overrides 770 vendor_cald system`; service `user vendor_cald` | |
|39| SCREEN_RESOLUTION: CalType 4, value 2=1280×768, enum 0:800×480/1:1280×720/2:1280×768/3:1920×1080/4:2400×960, file GIS738_RVCVIDEOROBUSTNESSREQUIREMENT v7 | T1:96-97,§5 | VERIFIED (exact) | `CalSets.db`: AllCalSets row CalType 4 CalValue 2; EnumSets 5 rows match exactly; CalDefFileName + v7 match | strongest single verification in the corpus |
|40| Source-address trust tiers 0x00FA/0x00F1/0xF0 + generalReject 0x10 framing | T1:54-55 | INFERRED (exact values) | mechanism VERIFIED (getSourceAddress, "tester id check", DIAG_SESSION_CONTROL 0x10); exact tier hex not found as strings | |
|41| diagnosticsd uid=0 (all caps, no seccomp) | T1:109 | uid=0 VERIFIED / caps+seccomp INFERRED | `vendor.gm.diagnostics.rc`: `user root`; no seccomp directive present (absence ≠ proof) | |

## CLUSTER 5 — Module ID / signing table

| # | claim | doc:location | verdict | evidence | note |
|---|---|---|---|---|---|
|42| Full module table (ID/name/sign-type: 1 VIP_APP TSS, 21 HostOS TSS/GHS, 22 System TSS, 23 Boot NONE, 24 Utils NONE, 26 Vendor TSS, 28 SXM, 29 GPS, 51 Tuner, 52 EthSwitch, 55 ACPIO, 56 VBMETA, 57 Product, 71 VIP_BOOT, 72 SOC_ABL) | QUICK_REFERENCE:37-56 | VERIFIED | `delivery_manifest.csv`: every module ID, name, and Sign Type matches (86331656 VIP_APP id1 TSS; 85098662 SOC_HOSTOS id21 TSS "GHS INTEGRITY OS and Hypervisor"; 85738845 SOC_ABL id72 NONE "Intel Automotive Bootloader"; etc.) | all hex conversions correct too |
|43| EEPROM ADB flip 0x0440 `C3 00 C3→5A FF 5A`, 0x0A80 `FF FF FF→5A FF 5A` | QUICK_REFERENCE:18-19 | VERIFIED (consistent) | matches UNDOC stock markers (0x0440 stock C3, 0x0A80 stock FF) and final LTZ bin `5A FF 5A` | |

## CLUSTER 6 — Stale-spec / misc self-corrections

| # | claim | doc:location | verdict | evidence | note |
|---|---|---|---|---|---|
|44| ORIGINAL Dec-2025 spec block: GPU Intel HD 500 / 6GB RAM / Android 10-12 | EEPROM_Analysis_Report.md:29-35 | CONTRADICTED (self-corrected) | doc's own review block (37-41) retires it → HD 505 / 8GB / A12; cites teardown.md + VERIFICATION.md (not re-verified here) | corrected values not independently checked against teardown artifact in this pass |

---

## Summary counts

- VERIFIED: 24  (incl. 1 "verified correction" #27, and split rows counted on the verified side)
- INFERRED: 11
- UNSUPPORTED: 3  (#5 ref-counts, #9 VIP hash, #16 intel_iommu=off)
- CONTRADICTED: 3  (#7 zero-marker-patterns, #18 e1000e, #44 stale spec [self-flagged])
- Split/partial: #3, #20, #28, #41 (verified core + inferred tail)

## Top claims the owner should NOT rely on
1. **`intel_iommu=off` `[C]` (T1 §3a).** Not captured — `/proc/cmdline` was permission-denied; the only IOMMU artifact (`kernel_config`) shows it compiled IN. The entire "crafted-frame/DMA → hypervisor" wire→host vector rests on this and is UNSUPPORTED.
2. **"Guest drives eth0 with `e1000e`" `[C]` (T1 §3a).** CONTRADICTED — driver is `igb_avb` (network_interfaces + kernel_modules), and it even contradicts T1's own §1.
3. **"Zero literal marker patterns in the VIP binary" (UNDOC §13.4).** CONTRADICTED — `69 00 69`×3, `C3 00 C3`×4 are present. The marker-runtime-generation conclusion survives on other evidence, but this specific supporting statement is false.
4. **EEPROM "firmware refs" counts (§2/§5) and the 0xb67d0 asm quotes (§8/§10).** UNSUPPORTED / non-reproducible — the doc itself admits this. **Update 2026-08-25:** the `0xb67d0` "Y177 stub" asm quote is now RESOLVED as **refuted** by the three-way VIP_APP diff (full ~906-byte fn in all builds; see VIP_FIRMWARE_Y177_Y181_COMPARISON.md §2). The EEPROM ref counts remain un-reproduced; don't build a flag-testing plan on the exact counts.
5. **VIP PN 86331656 hash `c381ed1c…` (§13.1).** Does not match the shipped file's md5 (`e47928d9…`).
6. **90xx "No route to host even locally" (T1 §6).** open_ports shows the guest holding ESTABLISHED connections to .1:9005/9010/9012/9018 — reachable in the client direction.
7. **Y181→Y177 "tested FAILED" downgrade block.** Mechanism plausible; the empirical result was asserted without a capture artifact — **now corroborated by owner bench re-test (2026-08-17), see Resolutions.**

## Core claims that ARE solidly ground-truth-verified
- **SCREEN_RESOLUTION** CalType/value/enum/CalDef file — exact match in CalSets.db (#39).
- **Calibration is not signature-protected** — checksum + SHA-256 only, no RSA/X509/SecOC (#34); gate is UDS `$27` (#35).
- **`*.calovride` OVERRIDE_BACKDOOR** string + "DISABLE BEFORE RELEASE" — present verbatim in bin__calserviced (#37); override→inotify→CalSets.db path real (#36); vendor_cald/770 gating real (#38).
- **Security lockdown posture** — flash.locked=1, vbmeta locked, verifiedbootstate green, oem_unlock=0, debuggable=0, adb.secure=1, SELinux Enforcing (#11-15) all straight from getprop/status dumps.
- **Network fabric** — eth0/vlan5/vlan4 IPs+MAC+driver, br0 down, 6363/49156 listeners, 90xx on 192.168.1.1, no 13400 (#22-26,31).
- **Module ID / signing table** — every row matches delivery_manifest.csv (#42).
- **EEPROM ADB SBI bytes + marker-agnostic bypass** — confirmed across two variant bins (#2-4,43).
- **diagnosticsd = root, cts-on-gsi stop hook, TCPServer/UDS symbols** — from rc + binary (#33,41).

---

## Resolutions applied (2026-08-17)

Actions taken in response to this audit:

- **#16 `intel_iommu=off`, #18 `e1000e`, #28 `.1` reachability** — corrected in
  `T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` with inline `⚠CORRECTED` markers + a
  provenance banner. IOMMU-off downgraded to an unverified research question; driver fixed to
  `igb_avb`; `.1` reframed as guest-client-reachable-but-not-on-wire.
- **#7 zero-marker-patterns, #9 VIP PN hash** — `⚠CORRECTED` annotations added in
  `EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md` (§13.4, §13.1). Claims retained with the refuting
  evidence noted, not deleted (preserves the trail).
- **#19 downgrade block** — upgraded from UNSUPPORTED-as-measured to **OWNER-VERIFIED** via a
  detailed owner bench re-test recorded in `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt` §2.4
  (2026-08-17). The observed pattern (same-build reapply succeeds; older build does nothing on
  normal boot and fails "update not supported/invalid" in recovery) is the signature of a
  version/rollback-index rejection, corroborating the inferred GHS/AVB anti-rollback mechanism.
- **#5 ref-counts, #8 asm quotes** — already self-flagged by the source doc's own provenance
  note; left as-is with that caveat standing.
