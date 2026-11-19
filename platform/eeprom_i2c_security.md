# EEPROM / I2C Security

EEPROM memory map and security-flag analysis, the merged I2C-bus permission
table (Android `/dev/i2c-N` view, security.md + hardware.md reconciled), and
the DAC-level local hardware attack surface (I2C/GPIO/serial) for gminfo37.

**Evidence legend:** `[C]` confirmed live, `[V]` verified, `[U]` unverified/unverifiable-from-live, `[X]` external/retracted.

**Related:** [security.md](security.md) (Android security posture, ProtoKey/ADB auth, kernel mitigations, SELinux denials — owns the MEC/ADB-unlock *consequence* of the SBI flag), [hardware_specs.md](hardware_specs.md) (physical I2C adapter/controller enumeration, VIP MCU part number, UART/serial hardware), [ota_update_stack.md](ota_update_stack.md) (OTA signing). External: `../eeprom/` (EEPROM programming workflow/tooling — this doc does not duplicate or edit that directory, only the security-relevant memory map) and `../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` (primary EEPROM research, authoritative for anything not reproduced here).

---

## EEPROM Security

**Device:** ST M24C64, 8KB, I2C address `0x50` (on `i2c-0`; see I2C Bus Table below).

- Security flags located at offsets `0x0440`, `0x0A80`, `0x0B40`
- CRC is present but **NOT enforced** at boot (write-and-reboot bypass possible)
- CalGroup markers are runtime-generated, not static EEPROM values
- I2C buses 0, 1, 2, and 3 are world-writable at the DAC layer (`crw-rw-rw-`, 0666) — see I2C Bus Table for the live-confirmed owners/labels. This is a privilege-escalation vector in principle (any process with filesystem access to the node can read/write EEPROM), but see "Local Hardware Attack Surface" below: SELinux enforcing on all builds gates which *domains* may actually open these nodes.

**History:** security.md previously carried a now-superseded EEPROM "security" section naming offsets `0x04A0/0x04C0/0x0A40/0x0BE0/0x1A00` as security flags, with "disasm-confirmed" status on `0x0440/0x0A80`. **CORRECTED 2026-08-26** (`research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0): those five offsets are NOT security flags, the ref-counts and "IPC Security Config" naming were fabricated, and the disasm-confirmed claim on `0x0440/0x0A80` is wrong. The real SBI pair is `0x0441` (data byte of `0x0440`) + `0x0A80`, established empirically (flips ADB). The memory map and offsets below are the corrected set. The ADB-unlock consequence of flipping the SBI (EEPROM SBI → VIP transmits MEC=0xFF on DID `0xF1A0` → `gm_adb_auth_init` sets `is_secure_mode=1` → adb allowed with no cloud cert) is owned by [security.md's ProtoKey / ADB Authentication section](security.md#protokey--adb-authentication); not duplicated here.

- Empirically, the ADB-enabled dump shows **both** `0x0440` and `0x0A80` flipped to `5A FF 5A FF`. The claim that both cells *must* match for the bypass to hold is an **unverified mechanism** — there are zero code references to the literal address `0x0A80` in either VIP binary, and the security check reads only the DATA byte (marker-agnostic). The empirical bypass-works observation stands; only the hardcoded second-address mechanism is disputed.
- A post-Y181 reflash re-initializes the backup cell to `F0 00 F0` (initialized+locked). The earlier claim that a specific calibration file (85783460) targets and resets these flags is **REFUTED** (2026-08) — those bytes live inside a gzip-compressed CalOvride XML stream, not an EEPROM address:value table. SBI values change only via the VIP's bulk restore-to-ROM-defaults routine (`FUN_ram_000c6564`, reached on an AUTOSAR NvM CRC/validity failure), not a targeted cal payload.
- `[U]` EEPROM-SBI→VIP MEC=0xFF→`is_secure_mode`→DID `0xF1A0` chain and the `$27`/`$22 F1A0` traces are **UNVERIFIABLE-FROM-LIVE** (EEPROM/VIP/DoIP, not reachable from a locked user shell). Posture note (`[C]` live-Y175 2026-10-05): this unit is in **secured** operation, not the bypass path — `ro.secure=1`, `ro.adb.secure=1`, `ro.debuggable=0`, and the live adb shell is the normal uid 2000 (`u:r:shell:s0`), i.e. adb via the standard path, not an `is_secure_mode=1` no-cert unlock.

`[C]` live-Y175 2026-10-05 (`dev_listing.txt`): `i2c-0 crw-rw-rw- root:root u:object_r:saturnhd_device:s0`, `i2c-1 crw-rw-rw- root:root i2c_device`, `i2c-2 crw-rw-rw- system:system i2c_device`, `i2c-3 crw-rw-rw- audioserver:audioserver dirana3_device`. All four are mode `0666`. (`i2c-4/5/6/8/9/10` are `crw-------` root; `i2c-7 crw-rw---- system` display_panel.) The EEPROM-at-0x50 contents, CRC-not-enforced, and SBI-flag claims above remain **UNVERIFIABLE-FROM-LIVE** — this DISK-ONLY audit did not (and must not) i2c-probe the live device.

### EEPROM Memory Map

| Offset Range | Function | Details |
|--------------|----------|---------|
| `0x0000`-`0x005F` | Header & Boot Flags | `0x0001` boot state: `0x00`=virgin, `0x01`=normal, `0xFF`=corrupted |
| `0x0400`-`0x045F` | Security Configuration | **OUTSIDE CRC protection** — modifications not detected |
| `0x0440` | Primary SBI Flag | Data byte at `0x0441`: `0x00`=secured, `0xFF`=bypass |
| `0x05C0`-`0x05D1` | VIN (Vehicle ID Number) | 17-byte VIN storage |
| `0x0A80` | Backup SBI Flag | Stock = uninitialized (`FF FF FF`); ADB-bypass = `5A FF 5A FF`; post-Y181 reflash = `F0 00 F0` (initialized+locked). Data byte `0xFF` = bypass; marker (`5A`/`69`/…) is variant/CalGroup-specific |
| `0x0B40` | Candidate security/debug-related record | A `0x0B41` change was not required for the documented minimal ADB recipe; no root/developer effect established |
| `0x16E0` | CRC Location 1 | NOT enforced at boot |
| `0x19E0` | CRC Location 2 | NOT enforced at boot |
| `0x1A80` | CRC Location 3 | NOT enforced at boot |
| `0x1B40` | CRC Location 4 | NOT enforced at boot |

**CRC bypass confirmed:** Tested with corrupted VIN at `0x05C0` — system boots normally, CRC mismatch ignored.

### EEPROM Framing Markers

| Marker Byte | Type |
|-------------|------|
| `0x5A` | Security |
| `0x69` | Configuration |
| `0xF0` | Data |
| `0xC3` | Calibration |

### EEPROM Attack Surface

The combination of unenforced CRC and world-writable I2C buses means that EEPROM contents (including security flags and calibration data) can be modified by any user-space process without requiring elevated privileges at the DAC layer. Changes persist across reboots since CRC validation is not enforced during boot. The security configuration region (`0x0400`-`0x045F`) is deliberately outside CRC protection, meaning even if CRC were enforced, SBI flag modifications would not be detected. See "Local Hardware Attack Surface" below for the SELinux-domain caveat that narrows "any process" to "any process in an allowed domain."

**MEC (Manufacturer Enable Counter):** the authentication chain, range checks, signed-byte conversion, historical readings, Boolean inversion, root/registration limits, and distinction from failed-boot counters are maintained in [the consolidated MEC source](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration) — pointer only, not reproduced here. EEPROM layout and VIP code remain owned by [the EEPROM audit](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md); the parent repo's `../eeprom/` directory (programming workflow/tooling) is likewise out of scope for this doc — flagged as overlap, not edited.

---

## I2C Bus Table (merged)

Merges the Android-guest `/dev/i2c-N` security table (security.md, two prior
copies) with the fuller permission/owner/use table in hardware.md. This is
the `/dev/i2c-N` numbering as seen by the Android guest; the native/physical
DesignWare adapter enumeration (eight DesignWare + three i915 GMBUS + I801
SMBus, differently numbered) is owned by
[hardware_specs.md](hardware_specs.md) — coordinate there for raw controller
topology, this table is the security-relevant guest-side view.

| Bus | Permissions | Owner/Label | Use |
|-----|-------------|-------|-----|
| i2c-0 | `crw-rw-rw-` (0666) — **world-writable** | `root:root`, SELinux `saturnhd_device` | General purpose; EEPROM (M24C64 at `0x50`) |
| i2c-1 | `crw-rw-rw-` (0666) — **world-writable** | `root:root`, SELinux `i2c_device` | General purpose; ELMOS antenna controller |
| i2c-2 | `crw-rw-rw-` (0666) — **world-writable** | `system:system`, SELinux `i2c_device` | System bus |
| i2c-3 | `crw-rw-rw-` (0666) — **world-writable** | `audioserver:audioserver`, SELinux `dirana3_device` | Audioserver bus; TDF8532 codec control |
| i2c-4 to i2c-6 | `crw-------` (root-only) | root | Reserved |
| i2c-7 | `crw-rw----` | system, SELinux `display_panel` | Atmel maXTouch (`0x4B`) touchscreen |
| i2c-8 to i2c-10 | `crw-------` (root-only) | root | Reserved |

`[C]` live-Y175 2026-10-05 (`dev_listing.txt`): CONFIRMED — i2c-0/1/2/3 all `crw-rw-rw-` (0666); owners/labels as above. i2c-4/5/6/8/9/10 confirmed `crw-------` root; i2c-7 confirmed `crw-rw---- system` `display_panel` (not `i2c_device` as some prior copies implied).

**Additional devices (hardware.md):** Faceplate controller at `0x12` (on i2c-7, same bus as the touchscreen). GYRO/ACCEL sensors not present.

**Security note:** i2c-0, i2c-1, i2c-2, and i2c-3 are world-writable at the DAC layer — EEPROM, the ELMOS antenna controller, the general system bus, and the audioserver/TDF8532 codec bus are all accessible by any process that can open the node. See "Local Hardware Attack Surface" for the SELinux-enforcing caveat that applies on every build.

### IPC / Serial

| Interface | Config | Permissions | Notes |
|-----------|--------|-------------|-------|
| `/dev/ttyS1` | 1 Mbps, HDLC v16, 20 IPC channels to VIP MCU | `root:root` (as documented) | IPC link to the VIP MCU |
| `/dev/ttyACM1` | SXM serial | `crw-rw-rw-` | **World-writable** at DAC layer |

`[C]` live-Y175 2026-10-05 (`dev_listing.txt`):
- `/dev/ttyS1`: owner `root:root`, SELinux `ipc_serial_device` CONFIRMED, but mode is **`crw-------` (0600, root-only)** — NOT world-accessible; the IPC link to the VIP is DAC-closed. (1 Mbps/HDLC-v16/20-channel detail itself is UNVERIFIABLE-FROM-LIVE.)
- `/dev/ttyACM1`: `crw-rw-rw-` (0666, world-rw) CONFIRMED, owner root — but SELinux label is **`sxm_device`** (SiriusXM), not a debug UART. The earlier "Debug UART" description is **REFUTED** → it is the SXM tuner serial. No `/dev/ttyACM0` present on this unit.

Dual-processor IPC architecture, VIP MCU part number, and the physical UART wiring are owned by [hardware_specs.md](hardware_specs.md); this table covers only the security-relevant permission/label facts.

---

## GPIO

| GPIO | Function | Risk (as originally claimed) |
|------|----------|------|
| gpio458 | MCU control | MCU reset/boot mode manipulation |
| gpio460 | MCU control | MCU reset/boot mode manipulation |
| gpio464 | MCU control | MCU reset/boot mode manipulation |
| gpio466 | MCU control | MCU reset/boot mode manipulation |

These GPIOs were originally claimed to control MCU reset and boot mode pins, with world-writable access meaning any user-space process could force the VIP MCU into reset or bootloader mode.

**"World-Writable" REFUTED on captured evidence** (`[C]` live-Y175 2026-10-05): the GPIO char devices `/dev/gpiochip0-3` are **`crw-------` root (0600)** — root-only, not world-writable. `gpio458/459/460/463/464/466` exist only as entries under `/sys/class/gpio/` and appear as **symlinks** (`lrwxrwxrwx` → `…/INT3452:00/gpiochip0/gpio/gpioNNN`); symlink mode bits are always 0777 and carry no access meaning. The underlying `value`/`direction` node permissions were initially not captured (`export`/`unexport` read back as `?`). Independently, `world_writable.txt` enumerates exactly **two** world-writable nodes on the live unit — both stock memcg `cgroup.event_control` — and **no** gpio path. The missing datum was then captured directly (2026-10-05): `ls /sys/class/gpio/gpio{458,460,464,466}/` returns **`Permission denied`** to shell (uid 2000), and `export`/`unexport` read back as `?` (root-only) — the value/direction nodes are not even stat-able by a non-root process, let alone writable. Claim **REFUTED**: a non-root process cannot toggle these pins. Second-agent concurrence obtained 2026-10-05 (14-flip ledger).

---

## Local Hardware Attack Surface (all builds)

**History/CORRECTED 2026-08-26.** This section was formerly titled "Y177 Attack Vectors (SELinux Permissive)" and premised on Y177 running permissive. That premise is FALSE — Y175/Y177/Y181 all run SELinux **enforcing**. The DAC-level exposures below (world-writable I2C/GPIO/debug-UART nodes) exist on **all** builds regardless of SELinux mode; SELinux enforcing constrains which *domains* may reach them, but does not change the underlying file-mode permissions themselves.

### Direct Hardware Access

- **I2C EEPROM manipulation:** a process in an allowed SELinux domain can read/write EEPROM security flags (`0x0440`, `0x0A80`) via `i2cset`/`i2cget` on the world-writable buses (see I2C Bus Table). SELinux enforcing (all builds) gates this by domain; the DAC world-writable bit does not.
- **GPIO MCU control:** earlier claimed as world-writable GPIOs (458/460/464/466) toggleable to force the VIP MCU into reset/bootloader mode. **REFUTED (concurred), `[C]` live-Y175 2026-10-05** — see GPIO section above; `/dev/gpiochip0-3` are root-only and the value/direction nodes return `Permission denied` to shell. Not a non-root DAC exposure.
- **Debug serial access:** `/dev/ttyACM1` (`crw-rw-rw-`) is world-writable at the DAC layer; SELinux enforcing restricts which domains may open it. `[C]` live-Y175 2026-10-05: world-writable CONFIRMED, but the node is the **SXM serial** (`sxm_device`), not a debug UART — see IPC/Serial section above.

### Kernel Exploitation

- **Kernel CVEs (CVE-2024-53104, -36971, -53150, -53197):** unpatched-kernel exposure tracks the build's kernel version/patch level, not SELinux mode. SELinux is enforcing on all builds, so MAC containment (neverallow rules) applies equally to Y177 and Y181. Patch-level/CVE detail is owned by [security.md](security.md) (Key CVEs section) — not reproduced here.
- **BPF verifier bypass (CVE-2023-2163):** CAP_BPF plus SELinux enforcing domain restrictions apply on all builds.
- **ptrace:** `CONFIG_SECURITY_YAMA` is not set, so ptrace scope is unrestricted at the YAMA layer on all builds; SELinux domain rules still apply.

### Persistence

- **EEPROM SBI state:** `0x0441=0xFF` is the confirmed primary-state input that produces a non-zero MEC and permits ADB without the GM client; `0x0A81` is empirically associated with the same configuration. Persistence is conditional: the VIP bulk restore-to-ROM-defaults path can re-lock the cells after re-validation.
- **`0x0B41` is not a debug-mode control:** it is read as part of CalGroup `0xA3`, but tests at `0x00`, `0x01`, and `0xFF` produced no ADB, SELinux, UI, or logged behavior change. Do not represent it as an enable path.

---

## Open conflicts

None found specific to EEPROM/I2C/GPIO content in scope for this doc. All prior contradictions in this area (world-writable GPIO claim, "Debug UART" label on `ttyACM1`, Y177-permissive premise) have a dated live-capture resolution (2026-08-26 / 2026-10-05) and are reflected inline above, not left as open conflicts.
