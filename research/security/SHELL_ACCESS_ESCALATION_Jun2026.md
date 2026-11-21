# Shell Access Escalation

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026
**Access:** ADB shell `uid=2000(shell)`, `u:r:shell:s0`, SELinux **Enforcing**

> **[C] live-Y175 2026-10-05 — this doc is Y181; a LIVE Y175 radio cross-checks the shell posture but
> NOT the kernel.** Read-only capture of `W213E-Y175.5.2-SIHM22B-383.1`
> (`/tmp/radio_audit/20261005_232227/raw/`) confirms the *unprivileged-shell* baseline on Y175:
> shell is `uid=2000(shell) ... context=u:r:shell:s0`, SELinux **Enforcing**, groups include
> `log(1007),inet(3003),readproc(3009),uhid(3011),readtracefs(3012)` (`00_whoami.txt`), **no `su` in
> ps (0 hits)**, `ro.secure=1 / ro.adb.secure=1 / ro.debuggable=0`, bootloader locked — i.e. the
> "shell stays uid 2000, no root" model holds on Y175. **But the kernel is `4.19.283`, NOT the 4.19.305
> this doc analyzes** (§2) — the KASLR slide, BuildID, symbol offsets, and extraction chain are all
> Y181-specific and do NOT transfer to Y175 unchanged. Per-method Binder `service call` results (§1
> OPEN/Blocked/Partial) were produced by live-calling Y181; this capture is DISK-ONLY (device owned by
> another agent, no `service call` run), so those results are Y181-scope here — only *service presence*
> and *gate permission levels* are re-confirmed on Y175 (see §1 note).

Companion to [`research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt`](GM_AAOS_Y181_SECURITY_ANALYSIS.txt)
(overall posture/CVEs), [`research/security/KERNEL_CVE_ANALYSIS.txt`](KERNEL_CVE_ANALYSIS.txt),
and [`platform/security.md`](../../platform/security.md). This doc records what
an **unprivileged** ADB shell can actually reach on a live Y181 unit (ADB enabled
via SBI EEPROM, not root), the Android Binder service surface, the kernel
extraction + KASLR measurement, the GM Secure ADB architecture, and a
consolidated escalation-gate inventory.

Current shell context: groups include `readtracefs(3012)`, `readproc(3009)`,
`inet(3003)`, `log(1007)`.

> **[C] live-Y181.3.2 2026-11-12 (read-only `adb shell id`):** `uid=2000(shell) gid=2000`, context `u:r:shell:s0`,
> full group set `shell(2000), input(1004), log(1007), adb(1011), sdcard_rw(1015), sdcard_r(1028), ext_data_rw(1078),
> ext_obb_rw(1079), net_bt_admin(3001), net_bt(3002), inet(3003), net_bw_stats(3006), readproc(3009), uhid(3011),
> readtracefs(3012)`; `getenforce`=Enforcing; `ro.secure=1`, `ro.debuggable=0`, `ro.adb.secure=1`; no `su` binary
> at `/system/bin/su` and no `su` process in `ps -A`; build tags `release-keys`. Any "shell can do X" claim in this doc
> must fit this set: still no `system(1000)` group. Not re-run today: the Binder `service call` results and tracefs/
> `perf_event_open` statements (carried from the Jun2026 capture, not re-probed).
 `NoNewPrivs=0`, no seccomp on the shell process.
SELinux Enforcing blocks `tracefs` writes (`current_tracer`, `kprobe_events`)
but **not** `perf_event_open`.

---

## 1. Android Binder Service Access Map

Probed via `adb shell service call`.

| Service | Descriptor | Permission | uid=2000 |
|---------|-----------|------------|----------|
| UpdateService | `com.gm.server.update.UpdateService` | none (read methods) | **OPEN — 30 methods** (see [`platform/ota_update_stack.md`](../../platform/ota_update_stack.md)) |
| GALService | `GALService` | none (most) | **OPEN — methods 1-6, 8-11, 16-20** |
| clusterService | `gm.cluster.IClusterHmi` | `ACCESS_IPC_HUD` | Blocked (all methods) |
| OnStarRemoteReflashManager | `gm.onstar.OnStarRemoteReflashManager` | `gm.permission.ACCESS_ONSTAR` | Blocked |
| DiagnosticsService | `com.gm.server.diagnostics_service.DiagnosticsService` | vehicle-internal | Partial (Tx4/Tx5 open) |
| OBDService | `com.gm.server.obd.OBDService` | VIN/internal | Partial (enum gate) |
| deviceInformationService | `deviceInformationService` | none | Partial (method 3) |
| RDMSADBHandler | `com.gm.server.screenprojection.RDMSADBHandler` | none | **OPEN (2 tx)** |

- **`gm.permission.ACCESS_ONSTAR`** and **`ACCESS_IPC_HUD`** are signature-level;
  `pm grant` fails ("not a changeable permission type") — cannot be granted to
  uid=2000.

> **[C] live-Y175 2026-10-05: service presence + gate levels CONFIRMED on Y175; per-method results
> Y181-scope.** All eight services in this table are live-registered on Y175 (`services.txt`):
> UpdateService (#67), GALService (`gm.gal.IGALService` #56), clusterService (`gm.cluster.IClusterHmi`
> #52), OnStarRemoteReflashManager (#105), DiagnosticsService (#60), OBDService (#63),
> deviceInformationService (#80), RDMSADBHandler (`gm.connection.IRDMSADBHandler` #65). The two gate
> permissions are CONFIRMED signature-family on Y175 (not uid-2000 grantable):
> `com.gm.cluster.permission.ACCESS_IPC_HUD` = `signature`, `gm.permission.ACCESS_ONSTAR` =
> `signature|privileged` (`permissions_full.txt`). The OPEN/Blocked/Partial per-method verdicts were
> obtained by live `service call` on Y181 and were **not** re-run on Y175 (DISK-ONLY capture) →
> UNVERIFIABLE-FROM-LIVE for Y175.
>
> **[C] Y181.3.2-ref 2026-10-06 — service presence + SELinux labels re-confirmed on a LIVE Y181.3.2 root
> reference (same variant as this doc: `W231E-Y181.3.2-SIHM22B-499.3`); READ-ONLY, no state-changing
> `service call` issued.** All eight services are live-registered in `service list` on the reference:
> `clusterService: [gm.cluster.IClusterHmi]`, `com.gm.gal.service.BINDER: [gm.gal.IGALService]`,
> `com.gm.server.diagnostics_service.DiagnosticsService: [gm.diagnostics_service.IDiagnosticsService]`,
> `com.gm.server.obd.OBDService: [gm.obd.IOBDService]`,
> `com.gm.server.screenprojection.RDMSADBHandler: [gm.connection.IRDMSADBHandler]`,
> `com.gm.server.update.UpdateService: [gm.update.IUpdateService]`,
> `deviceInformationService: [gm.deviceinfo.IDeviceInfoService]`,
> `gm.onstar.OnStarRemoteReflashManager: [gm.onstar.IRemoteReflashService]`. SELinux labels
> (`/product/etc/selinux/product_service_contexts`): `DiagnosticsService`, `OBDService`,
> `OnStarRemoteReflashManager`, `com.gm.server.wlanservice`, `UpdateService`, `RDMSADBHandler` all →
> `u:object_r:gm_domain_service:s0`; `clusterService` → `gm_cluster_service`; `deviceInformationService`
> → `gm_deviceinformation_service`. The per-method OPEN/Blocked/Partial verdicts in the table were produced by
> the original June-2026 live `service call` run and were deliberately **not** re-executed here (read-only
> mandate: no state-changing transactions on the shared reference) — they stand as originally measured, not
> re-confirmed on this session.
- **DiagnosticsService:** Tx1–3 permission-gated ("To Read Vehicle Internal
  Inf…"); **Tx4** returns `00000000`; **Tx5** returns a live 4-int struct
  (`00000000 73622a85 00000113 0…0 00000001`) with no gate. Reads `/proc/stat`
  and `thermal_zone0/temp` every 60 s for Connected Diagnostics.
- **OBDService Tx1** `Do_On_Board_Diagnostics_Simple_Request`: executes from
  shell but its Parcelable enum (`gm.obd.message.*`, 28-char class, "OBDR…")
  rejects an int → `EX_ILLEGAL_ARGUMENT`. Correct enum name needed from APK.
- **RDMSADBHandler** (Binder #66): `ADB_Disable` (Tx1) attempts USB
  peripheral→host role reversal via `/sys/bus/usb/drivers/dabridge/bridgeport` —
  **blocked by the GM V10 E2 PD hub**, ADB recovers; `ADB_Enable` (Tx2) writes
  `1-6.3`. See USB H2H bridge in [`platform/ethernet_networking.md`](../../platform/ethernet_networking.md#usb-identifiers-and-gadget).

### Filesystem (uid=2000)

| Path | Access |
|------|--------|
| `/sdcard/Download/` | **WRITE** (staging for filename-arg paths) |
| `/update_cache/`, `/mnt/media_rw/…`, `/data/data/` | Permission denied |
| `/dev/ipc/ipc2`–`ipc21` | Visible, SELinux-denied (GHS IPC sockets) |
| `/dev/ghs/*` | SELinux + root-only |

---

## 2. Kernel Extraction & KASLR Measurement

The repo's [`platform/security.md`](../../platform/security.md#kernel-security-mitigations)
records KASLR as *enabled*; this is the concrete extraction + runtime-slide work
on a live unit. Kernel: **Linux 4.19.305** (matches Y181), BuildID
`e102f392ca20c0e504b686e96bca8d9c06fc1fdb` (firmware == running, via
`/proc/version`).

### Extraction chain

```
Y181/86331652 (SOC_BOOT, Android bootimg, 64 MB)
  → kernel bzImage (15,364,688 bytes; setup_sects=31, payload_offset=0x2EA, payload_size=0xE6FC57)
  → payload @ 0x42EA: LZ4 legacy magic 02 21 4C 18
  → lz4.block.decompress (uncompressed_size=42,662,124)   # lz4.frame rejects legacy format
  → vmlinux_raw: ELF64 x86-64, statically linked, stripped
  → vmlinux-to-elf → 117,828 symbols recovered
    kallsyms_names @ 0x01d79868; token_table @ 0x01efe990; token_index @ 0x01efed10
```

### Static symbols (pre-KASLR, base `0xffffffff81000000`)

```
0xffffffff81000000  _text / _stext / startup_64
0xffffffff810d71e0  commit_creds            (+0x0D71E0)
0xffffffff810d7690  prepare_kernel_cred     (+0x0D7690)
0xffffffff811579b0  kallsyms_lookup_name    (+0x1579B0)
```

### KASLR slide (simpleperf, unprivileged)

`perf_event_paranoid = -1` permits unprivileged kernel IP sampling
(`/proc/kallsyms` itself is denied by kptr_restrict):
```
simpleperf record -e cpu-clock:k --duration 2 -o perf.data -- sleep 2
```
46 kernel-mode samples; observed kernel-text IPs `0xffffffff8e002000 –
0xffffffff8f20008f`. Lowest ≈ `0xffffffff8e002494`; raw delta vs `_text` =
`0xD002494`; 2 MB-aligned → **estimated slide ≈ `0x0D000000`** (208 MB).

**Estimated runtime addresses (slide 0x0D000000):**
```
_text                → 0xffffffff8e000000
commit_creds         → 0xffffffff8e0d71e0
prepare_kernel_cred  → 0xffffffff8e0d7690
kallsyms_lookup_name → 0xffffffff8e1579b0
```

> ESTIMATE — exact slide needs a sampled IP mapped to a known static symbol; the
> aligned value could be `0x0C000000`/`0x0E000000`. The slide re-randomizes each
> boot, so sampling must occur in the same boot session as any use. Re-run
> `--duration 10` and parse MMAP2 events to pin it.

This pairs with the kernel CVEs in
[`research/security/KERNEL_CVE_ANALYSIS.txt`](KERNEL_CVE_ANALYSIS.txt): on Y181
SELinux Enforcing blocks the documented chains by policy, but `perf_event_open`,
`ptrace` (no YAMA), and `process_vm_readv` are available to the shell and KASLR
is measurable.

---

## 3. GM Secure ADB Architecture

Current unit has standard ADB via the SBI EEPROM bypass (`0x0441=0xFF`,
`0x0A81=0xFF`; see [`platform/security.md`](../../platform/security.md#eeprom-security--pointer-only)
and [`eeprom/README.md`](../../eeprom/README.md)). This section documents what
`adbd` does when SBI is **locked** (`0x00`).

`adbd`: `/apex/com.android.adbd/bin/adbd`, x86-64 ELF, **not stripped**. Custom
symbols:
```
GM_ADB_DIR              → "/data/gm_adb/"
gm_adb_auth_init        gm_adb_auth_verify(atransport*)
gm_adb_is_secure_mode   gm_adb_check_authentication
restart_root_service    → "restarting adbd as root"
```

**`gm_adb_auth_init` logic (disassembled):**
```
1. GetProperty("persist.gm.adb.secure") == "1" → ENABLED (test-build bypass) else →
2. query_auth_manager("key", buf)  → Unix socket gmauthmanagerservice.socket.adb
   (retries 49× × 1 s; failure → DISABLED)
3. buf must start with "MEC" (4D 45 43) else DISABLED
4. mec = atoi(buf+3); if mec==0 or mec>=256 → DISABLED; else 1..255 → secure_mode=1 → ENABLED
ENABLED  → client must auth with /data/gm_adb/{policy,password}
DISABLED → standard ADB if SBI=0xFF, else ADB locked
```

**`gmauthmanagerservice.socket.adb` is absent on production** (not in
`/dev/socket/`, not started by any `.rc`) — a factory/dealer-only service.
`query_auth_manager` therefore always times out → GM Secure ADB is effectively
disabled, and standard ADB is gated purely by the SBI flag. The `MEC=174` seen
in `adbd` disabled-path logs is a `%rcx` register artifact, **not** a live EEPROM
read (0xAE is not at any meaningful EEPROM offset — distinct from the boot-failure
MEC counter in security.md). `/data/gm_adb/{password,policy}` (GM-signed
credential + VIN/CSMID-locked policy) are Permission Denied from uid=2000.

**Corrected 2026-11-15:** the inspected normal Y175 `restart_root_service`
first handles an already-root daemon, then calls `__android_log_is_debuggable()`.
A false result returns the production-build refusal **before** checking
`gm_adb_is_secure_mode()`. Only the debug-capable branch reaches the GM
secure-mode/authentication condition and `service.adb.root=1`. The former
claim that a GM root-permitting policy independently substitutes for debug
capability is withdrawn for this entry point. SBI-dependent ADB access,
UDS SecurityAccess and adbd UID are separate gates.

| Y175 binary | SHA-256 | Root-service ELF RVA |
|---|---|---:|
| Normal APEX adbd | `6bfa2ba86ab2fe2a0ca0e2eb588139bc6402f687822b72b9c6d2efecda0de713` | `0xC2270` |
| Boot-ramdisk recovery adbd | `32fc5f29f8d7aeed4c81eaedc95d870127f32c85bed8645f6c69f39ce421602d` | `0xBBFA0` |

The normal cleanroom APEX aliases are byte-identical. Recovery also checks
`__android_log_is_debuggable()` before a root restart, but lacks the normal
handler's GM secure-mode branch. These are package-binary observations,
not a new live root attempt or proof about every GM authentication command.
Both contain the standard production refusal; normal contains
`gm_adb_auth_init`, while the inspected recovery binary does not.

### Community root reports and target applicability (2026-11-15)

A bounded GitHub, GitLab, Reddit, XDA and forum search found no independently
reproduced Intel GM A11/Y175–Y181 UID0-shell method. This is a search result,
not proof of universal absence. Original Harman GWM forum posts describe
`service.adb.root.hkey` followed by an OEM root restart; both inspected Y175
adbd binaries lack that property, the OEM root messages and generic hkey
fingerprints. The original pages returned 403 to direct retrieval, so the
report is based on indexed excerpts rather than a fully fetched recipe:
[original GWM thread](https://4pda.to/forum/index.php?showtopic=1047354&st=2340),
[earlier discussion](https://4pda.to/forum/index.php?showtopic=1047354&st=2120),
[later reports](https://4pda.to/forum/index.php?showtopic=1047354&st=3080).
No device serial was used to derive a key, and no such property was set.

[GWM-Harman-VCE](https://github.com/DymOK93/GWM-Harman-VCE) requires existing
rooted ADB to edit its vehicle configuration; it is not an initial-root
method or a GM CalOverride writer. The
[GWM boot-target source](https://github.com/DymOK93/GWM-CAN-Tools/blob/master/uds.py#L351)
is a cross-platform diagnostic lead, not proof of GM shell privilege.
The reported ADB routine in [The ABCs of Global B](https://surrealdev.com/the-abcs-of-global-b/)
does not supply a reproduced A11 build/transport/response combination;
the target's negative trials remain the stronger evidence for that layout.
An [older GM logo discussion](https://www.reddit.com/r/CarHacking/comments/1g7phbs/change_20_gm_infotainment_logosbadges/)
reports HMI2.5 experience, not HMI3+/Info3.7 rooting.

Kernel LPE is a separate research track. The existing
[CVE inventory](CVE_ATTACK_SURFACE_ANALYSIS.md) distinguishes Y175 and Y181
kernel baselines and candidate prerequisites. No new kernel exploit was
validated by this search; public PoC availability or version similarity is
not a reproduction from this radio's shell. A root diagnostic server running
selected handlers likewise does not confer an arbitrary command shell.

---

## 4. Consolidated Escalation Gate Inventory

| Priority | Vector | Status | Blocker / next step |
|----------|--------|--------|---------------------|
| HIGH | Kernel exploit (4.19.305, KASLR ~0x0D000000) | In progress | Symbols known; need exact slide + exploit. SELinux Enforcing contains documented CVEs by policy. `perf_event_open`/`ptrace`/no-seccomp available |
| HIGH | diagnosticsd UDS SecurityAccess (0x27) | New path | No OS-level peer gate (binary-confirmed). **CORRECTED 2026-09:** `ETHERNET`/`NOTIFICATION` tiers are checked in-process (`libuds`), not by `gm_protokey`; `VIP` tier is forwarded off-SoC to the VIP MCU (`ProxyOfExtComp`/`SockAdaptor`), gated by the SBI EEPROM byte. See [`diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md) and [`platform/security.md`](../../platform/security.md#ethernet-uds-27-securityaccess--vip-side-forwarding-off-soc-2026-09) |
| ~~HIGH~~ | diagnosticsd oversized-payload alloc | **[C] Resolved 2026-11-21 — Confirmed-clean** | diagnosticsd's body-read bound (`length ≤ 0x3fffff`) exactly matches its fixed 4 MB buffer; no malloc-before-bounds-check overflow. `readHeader` is attested in [`diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md) (as `DiagnosticEthernetMonitor::readHeader`) and [`diagnostics/diagnosticsd_protocol.md`](../../diagnostics/diagnosticsd_protocol.md) (as `SockAdaptor::readHeader`). See [`AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md) NATIVE-1 (confirmed-clean negative result) |
| MEDIUM | diagnosticsd source-IP admission / logical tester | Corrected 2026-11-14: firewall admission and UDS tester/session checks are separate. Old all-rejected probes used invalid tester `0x0FA0`; direct T1 F4 + extended session + 31-FF seed + 12-zero response yielded `67 02`. | See [validated T1 sequence](../../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14); no root shell, partition write or calibration write established. |
| MEDIUM | `IDiagnosticsInternalService` HIDL | Untested | Needs vendor SELinux domain (vndbinder) |
| MEDIUM | GM Secure ADB fake `gmauthmanagerservice` socket | Theoretical | Feed MEC 1–255; still needs GM-signed policy to complete auth |
| MEDIUM | `gm_protokey` extraction | Blocked | Permission Denied from uid=2000 |
| LOW | UpdateService `AllowDevSignedVIP` / `changeDebugMode` | Blocked | `isDebugBuild()=false`; app-layer only ([`ota_update_stack.md`](../../platform/ota_update_stack.md)) |
| LOW | `gm_usb_auto_install` + package | Blocked | Package needs GPD Production CA signing |
| LOW | EEPROM `0x0B41=0x01` debug flag | No effect | VIP MCU layer only (Android-side confirmed inert) |
| INFO | `ro.oem_unlock_supported=1` | Available | fastboot unlock wipes /data; destructive |

**Boot-cmdline divergence:** the DEV_REL package (`86331652`) boots
`enforcing=0 androidboot.selinux=permissive`; the production unit boots SELinux
**Enforcing**. Flashing DEV_REL firmware (→ permissive) would trivialize the
above, but is itself gated by the GPD Production CA signing barrier — consistent
with the repo's standing Research Status (signing/rollback is the root gate; see
[`README.md`](../../README.md) and [`hardware/teardown.md`](../../hardware/teardown.md)).

> **[C] live-Y175 2026-10-05: the "cmdline permissive ≠ runtime permissive" point is CONFIRMED on a
> production Y175.** The live production unit carries `ro.boot.selinux=permissive` on its cmdline
> (`props.txt:259`) yet runs SELinux **Enforcing** (`00_whoami.txt:3`; 179/179 avc lines `permissive=0`).
> So a permissive cmdline token is present and inert even on a locked production Y175 — init forces
> Enforcing regardless. This both confirms the divergence note and refutes any reading that
> `ro.boot.selinux=permissive` in props implies a permissive runtime.

---

## Cross-References

- [`platform/security.md`](../../platform/security.md) — SELinux, ProtoKey,
  EEPROM/SBI, kernel mitigations, CVEs
- [`platform/ota_update_stack.md`](../../platform/ota_update_stack.md) —
  UpdateService Binder surface, signing gate
- [`platform/fsa_protocol.md`](../../platform/fsa_protocol.md) — FSA service
  surface reachable from the shell
- [`diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md)
  — UDS-over-TCP trust model
- Source: live `evidence/enumeration/Y181/jun2026/` capture; Y181 firmware extraction
