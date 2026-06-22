# gminfo37 — uid=2000 Shell Access, Binder Surface & Escalation Assessment

**Device:** GM Info 3.7 (gminfo37), Y181 `W231E-Y181.3.2-SIHM22B-499.3`
**Research Date:** June 2026
**Access:** ADB shell `uid=2000(shell)`, `u:r:shell:s0`, SELinux **Enforcing**

Companion to [`research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt`](GM_AAOS_Y181_SECURITY_ANALYSIS.txt)
(overall posture/CVEs), [`research/security/KERNEL_CVE_ANALYSIS.txt`](KERNEL_CVE_ANALYSIS.txt),
and [`platform/security.md`](../../platform/security.md). This doc records what
an **unprivileged** ADB shell can actually reach on a live Y181 unit (ADB enabled
via SBI EEPROM, not root), the Android Binder service surface, the kernel
extraction + KASLR measurement, the GM Secure ADB architecture, and a
consolidated escalation-gate inventory.

Current shell context: groups include `readtracefs(3012)`, `readproc(3009)`,
`inet(3003)`, `log(1007)`. `NoNewPrivs=0`, no seccomp on the shell process.
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
  `1-6.3`. See USB H2H bridge in [`platform/networking.md`](../../platform/networking.md#usb-identifiers).

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
`0x0A81=0xFF`; see [`platform/security.md`](../../platform/security.md#eeprom-security)
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

`restart_root_service` ("restarting adbd as root") is reachable only if GM
Secure ADB auth succeeds **and** the policy permits root restart; with SBI=0xFF,
the shell stays uid=2000. Root needs either `ro.debuggable=1` (root to set) or a
GM-signed root-permitting policy.

---

## 4. Consolidated Escalation Gate Inventory

| Priority | Vector | Status | Blocker / next step |
|----------|--------|--------|---------------------|
| HIGH | Kernel exploit (4.19.305, KASLR ~0x0D000000) | In progress | Symbols known; need exact slide + exploit. SELinux Enforcing contains documented CVEs by policy. `perf_event_open`/`ptrace`/no-seccomp available |
| HIGH | diagnosticsd UDS SecurityAccess (0x27) | New path | No OS-level peer gate (binary-confirmed); need seed→key algo (`gm_protokey`). See [`diagnostics/ethernet_uds_diagnosticsd.md`](../../diagnostics/ethernet_uds_diagnosticsd.md) |
| HIGH | diagnosticsd oversized-payload alloc | Potential | Confirm `malloc(PAYLOAD_LEN)`-before-check via Ghidra |
| MEDIUM | diagnosticsd IP source spoof (vlan4) | Speculative | If any trust check is IP-based, a 172.16.4.x source bypasses |
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
- Source: live `enumeration/Y181/jun2026/` capture; Y181 firmware extraction
