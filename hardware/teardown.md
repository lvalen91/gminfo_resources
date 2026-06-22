# GM Info 3.7 (gminfo37) — A11 Radio / CSM Module: Complete Hardware Teardown

## Module Identity

| Field | Value |
|-------|-------|
| Platform | gminfo37 (GM Info 3.7) |
| ECU Address | 0x80 (A11 Radio) |
| Manufacturer | Harman/Samsung |
| VIN (test unit) | XXXXXXXXXXXXXXXXX (2024 Silverado 1500, ICE) |
| RPO | IOK |
| Device ID | <DEVSERIAL_REDACTED> |
| GM Service P/N | 3765210 |
| Harman Assembly P/N | 91.UMAF2HG.GS6FAAG |
| HWID | ZQ68GEC80317, EC-Index 20 |
| Production Serial | U1J3N05D2F01C01 |
| Mfg Trace | F2G6MHBW0114601N01PSXXX |
| CAN Architecture | GM VIP/SDV1 (GB) — CAN 2.0, 29-bit extended |
| CAN IDs | Req: 0x14DA80F1, Rsp: 0x145AF180 (HS-CAN) |

---

## Hardware Architecture

Three-processor design on a single PCB:

```
+-------------------------------------------------------------+
|  GM Info 3.7 Main PCB                                       |
|  AT&S MX3 SH 94V-0, fab A922114                            |
|  Drawing: G071-4010-03MN, Board: 4050897 REVA              |
|                                                             |
|  +----------------------------+                             |
|  |  Intel SOM (soldered)      |                             |
|  |  +----------------------+  |                             |
|  |  | Atom x7-A3960        |  |                             |
|  |  | Apollo Lake, 14nm    |  |                             |
|  |  | Goldmont, quad-core  |  |                             |
|  |  | SREKE step (e1)      |  |                             |
|  |  | J238G327             |  |                             |
|  |  | AEC-Q100 auto-grade  |  |                             |
|  |  |                      |  |                             |
|  |  | +------------------+ |  |                             |
|  |  | | CSE              | |  |  <-- AES-CMAC master key    |
|  |  | | (own uC+SRAM)    | |  |      lives HERE             |
|  |  | | HW root of trust | |  |      (fuse-protected)       |
|  |  | +------------------+ |  |                             |
|  |  | GPU: HD 505          |  |                             |
|  |  | VPU: HW decode       |  |                             |
|  |  +----------------------+  |                             |
|  |  4x Micron LPDDR4 (8GB)   |                             |
|  |  MT53E512M32D2DS-053       |                             |
|  |  2400 MT/s, dual-die       |                             |
|  |  IFWI Flash: IS25WP064A    |                             |
|  |  8MB SPI NOR (BGA, CS0)    |                             |
|  +----------------------------+                             |
|                                                             |
|  +------------+    +----------+    +-----------+            |
|  | RH850      |<-->| M24C64   |    | Samsung   |            |
|  | VIP MCU    |I2C | EEPROM   |    | eMMC 64GB |            |
|  | TM52176    |    | 8KB      |    | KLMCG4JEUD|            |
|  | QFP-144+   |    | TSSOP-8  |    | BGA-153   |            |
|  +------+-----+    +----------+    +-----------+            |
|         | IPC (HDLC)                                        |
|  +------+-----+    +-----------+    +-----------+           |
|  | BCM89551   |    | Intel I210|    | NXP       |           |
|  | Eth Switch |    | GbE MAC   |    | SAF7751   |           |
|  | Broadcom   |    | AVB Audio |    | Tuner+DSP |           |
|  +------------+    +-----------+    +-----------+           |
|                         | AVB Ethernet                      |
|                    +-----------+                            |
|                    | NXP       |                            |
|                    | TDF8532   |--> External DSP/Amp        |
|                    +-----------+                            |
+-------------------------------------------------------------+
```

---

## Complete Bill of Materials (Photo-Verified)

### Compute & Storage

| Component | Part Number | Package | Notes |
|-----------|-------------|---------|-------|
| CPU | Intel Atom x7-A3960 (J238G327 e1, SREKE, 72MS459202251) | BGA on SOM | 14nm Goldmont, quad-core @ 1.88GHz |
| RAM | 4x Micron MT53E512M32D2DS-053 (2TE77) | BGA on SOM | 8GB LPDDR4 2400 MT/s, dual-die 3733 Mbps |
| eMMC | Samsung KLMCG4JEUD (SEC 228, B04P, NT24G0046) | BGA-153 | 64GB eMMC 5.1 |
| BCM89551 FW Flash | ISSI IS25LP016D-JNLE | SOIC-8 | 2MB NOR — **Broadcom Ethernet switch firmware** (confirmed via partial dump; IC damaged during extraction) |
| IFWI/TXE Boot Flash | ISSI IS25WP064A-JHLA3 (P3B37364) | BGA (ball array) | 8MB NOR — **confirmed** Apollo Lake IFWI/TXE boot flash (Intel docs mandate 8MB external SPI NOR on CS0). Contains Flash Descriptor, TXE 3.0 FW, UEFI, PMC FW, microcode, SMIP, Boot Guard v2. NOT dumped. |
| VIP MCU | Renesas RH850 (TM52176, 3TC 2251, lot 15873) | QFP-144+ | V850 core, system/power/security controller |
| VIP EEPROM | ST M24C64 (464RQ, K228) | TSSOP-8 | 8KB I2C — SBI security flags |

### Networking & Connectivity

| Component | Part Number | Package | Notes |
|-----------|-------------|---------|-------|
| Ethernet Switch | Broadcom BCM89551B1BFBG (TN2224 P21, 395-34 P3 W) | BGA | Automotive BroadR-Reach Ethernet |
| Ethernet FW Flash | ISSI IS25LP016D-JNLE | SOIC-8 | 2MB NOR — BCM89551 firmware (confirmed via partial dump; IC damaged during extraction) |
| IFWI/TXE Boot Flash | ISSI IS25WP064A-JHLA3 (P3B37364) | BGA (ball array) | 8MB NOR — confirmed IFWI/TXE boot flash per Intel Apollo Lake platform requirements. NOT dumped. |
| Ethernet MAC | Intel WGI210CL (I210) rev A3 (2214ASP) | QFN-48 | GbE for AVB audio, 25MHz xtal |
| WiFi/BT | Shielded module (PN 4D+0847, EC-02 7A85H.G05) | Module | ~21.3 x 12.9 x 7.9mm |
| USB-UART | Microchip MCP2200 | QFN | Debug console -> /dev/ttyACM1 (world-rw), 12MHz xtal |
| CAN Transceiver | NXP C26004 | TSSOP | HS-CAN interface |

### Audio & Display

| Component | Part Number | Package | Notes |
|-----------|-------------|---------|-------|
| Tuner/Audio DSP | NXP SAF7751HN/207 (P0WR92.00, EtD22482) | BGA | AM/FM/HD Radio tuner + audio processing |
| Audio Amplifier | NXP TDF8532 | — | External, connected via AVB Ethernet |
| Display Serializer | TI DS90UH949-Q1 (UH949Q, AT3S G4) | QFP-48 | FPD-Link III TX to display panel |
| Camera Deserializer | TI DS90UB954-Q1 (UB954Q, AVG3 G4) | QFP-48 | FPD-Link III RX hub for cameras |
| Backlight Driver | Analog Devices LT3899 (B64240) | QFN | Dual boost LED driver |

### Power

| Component | Part Number | Package | Notes |
|-----------|-------------|---------|-------|
| Power MOSFET/Reg | 96E840 PEm (2305 E4, 5971) | D2PAK | x3+ on board |
| Bulk Caps | 470uF/25V, 220uF/50V, 47uF/35V | SMD Electrolytic | Multiple |

---

## Software Stack

| Layer | Details |
|-------|---------|
| OS | Android 12 (API 32), AAOS |
| Hypervisor | Green Hills Software (GHS) |
| Y175 Build | W213E-Y175.5.2-SIHM22B-383.1, kernel 4.19.283, patch 2024-05-05 |
| Y181 Build | W231E-Y181.3.2-SIHM22B-499.3, kernel 4.19.305, patch 2025-06-05 |
| SELinux | Enforcing (both builds) |
| Verified Boot | Green, locked |
| Bootloader | Version 2344, A/B slots (_a active) |
| Key Services | gmprotokey (CSE), gm_vehicle_hal, gm_update_engine, gmcrashlogd |

### Partition Layout (26 physical + 4 logical, virtio /dev/vda)

Classic A/B (NOT virtual A/B — no COW snapshots). `ro.build.ab_update=true`, `ro.boot.dynamic_partitions=true`.

**Physical A/B** (7 pairs):

| Partition | Devices | Notes |
|---|---|---|
| ghs_isys | vda1/vda2 | GHS hypervisor — labels swap based on active slot |
| bootloader | vda5/vda6 | SoC bootloader |
| boot | vda7/vda8 | Android boot image |
| vbmeta | vda10/vda11 | AVB metadata (3,328 bytes each) |
| acpi | vda14/vda15 | ACPI tables |
| acpio | vda16/vda17 | ACPI overlays |
| cert | vda18/vda19 | Certificate store |

**Logical A/B** (inside single `super` vda13, ~9GB, `lp_metadata` / `dm-linear`):

| Partition | Size | Mount |
|---|---|---|
| system_{a,b} | ~3.0 GiB | / (ext4, ro, avb → dm-6) |
| vendor_{a,b} | ~445 MiB | /vendor (ext4, ro, avb → dm-7) |
| product_{a,b} | ~2.5 GiB | /product (ext4, ro, avb → dm-8) |
| odm_{a,b} | — | Overlaid under vendor |

**Single** (12): misc (vda9), data (vda26, ~39GB f2fs encrypted), metadata (vda12), config (vda22), calibration (vda23), persistent (vda20), teedata (vda21), update_cache (vda25), ghs_storage (vda3), ghs_log (vda24), ghs_abl_update (vda4), super (vda13, container)

**GHS is the A/B decision maker.** VMM reads AB0 metadata from misc, selects slot, loads boot, verifies vbmeta. If both Android slots fail, GHS still runs and can enter ELK/see-dealer/recovery. As long as ghs_isys boots (own A/B), the entire radio is recoverable. There is no recovery partition — GHS IS the recovery mechanism.

---

## Security Architecture

### Ghidra Analysis (9 passes, VIP firmware 86331656)

Binary: 1.9MB, RH850 (V850:LE:32:default), 6,251 functions

**The VIP contains ZERO cryptographic operations:**

| Check | Result |
|-------|--------|
| AES S-box (63h, 7Ch, 77h...) | NOT found |
| AES T-tables | NOT found |
| SHA-256 constants | NOT found |
| CSG hardware (0xFFD20000) | 0 of 6,251 functions access it |
| Software CMAC | NONE |
| XOR/shift crypto patterns | 1 false positive (switch dispatcher) |

### UDS SecurityAccess Flow ($27)

```
DPS/Tester                    VIP (RH850)                   SoC (A3960 CSE)
    |                            |                              |
    |-- RequestSeed ($27 01) --> |                              |
    |                            |-- IPC: Request seed -------->|
    |                            |<- IPC: ECUID(16)+Seed(32) --|
    |                            |   Store in RAM @ 0xfebda50f  |
    |<-- ECUID+Seed response ---|                              |
    |                            |                              |
    |-- SendKey ($27 02) -----> |                              |
    |                            |-- IPC: Forward key --------->|
    |                            |                     CSE does |
    |                            |                     AES-CMAC |
    |                            |                     verify   |
    |                            |<- IPC: Accept/Reject -------|
    |                            |   State: 0->1->4->5          |
    |<-- Success/Failure -------|                              |

4 independent security channels: Levels 0x10, 0x11, 0x12, 0x13
ECUID (constant): $004B41DC0000160006104145610114AC
```

### DPS Behavior Comparison

| Aspect | Y177 (gateway, LS-CAN) | Y181 (direct, HS-CAN, no gateway) |
|--------|------------------------|-----------------------------------|
| Module ID | 86283151 (AC=CM) | 86331656 (AC=CN) |
| Seed | Real random (different each time) | All 0xFF (33 bytes, deterministic) |
| Outcome | "Security validation facility failed" | GCI read completed |
| MEC | 0 | 207 |

All 4 DPS read sessions for Y181 returned identical results — fully deterministic in bench/BSOB mode. The all-0xFF seed maps to VIP function FUN_000b021e which fills the seed buffer at 0xfebe7220 with 0xFF when the SoC is not available.

### EEPROM SBI Bypass

| Offset | Stock | Modified | Framing | Role |
|--------|-------|----------|---------|------|
| 0x0441 | 00 | FF | Variable (was F0) | Primary SBI flag |
| 0x0A81 | 00 | FF | Variable (was C3) | Mirror |
| 0x1A01 | 00 | FF | Variable (was F0) | Second mirror |
| 0x0B41 | 00 | 01 | Variable (was 69) | Third location |

- Framing bytes change per recalibration/reload by VIP/SPS/DPS (NOT constants)
- Locate by offset, not by framing pattern
- OTA updates reset to 0x00 (re-locks ADB)
- Effect: Disables authorized ADB client requirement (shell uid=2000, not root)
- Last modifiable build: Y181 for RPO IOK

#### 0x0B41 — Debug Mode Flag (Unverified Hypotheses)

`0x0B41 = 0x01` is listed as "debug enabled" in the EEPROM map. Its effect beyond its role as a third SBI mirror is **not directly verified**. Two unconfirmed hypotheses:

1. **Unknown feature/access path unlock** — could enable engineering or factory features not exposed in normal operation.
2. **Verbose debug logging → file archiving → resource saturation** — debug mode may force the VIP or SoC to write high-volume logs to storage, raising I/O, storage consumption, and possibly CPU pressure. If the radio archives logs aggressively in this mode, it could act as an observable side channel (what gets logged?) or introduce instability under sustained load.

**Test approach:** Set `0x0B41 = 0x01` via XGecu, boot, monitor `/data/` and any `/mnt/vendor/` log paths for new files, watch `logcat` verbosity change, and check `df` over time for storage growth. Compare `dmesg` and `logcat` log levels to baseline (stock `0x0B41 = 0x00`). Low risk to test — swap EEPROM back if nothing useful surfaces.

### IFWI/TXE Boot Flash (IS25WP064A-JHLA3)

The 8MB ISSI IS25WP064A-JHLA3 (BGA) is **confirmed** as the Apollo Lake IFWI/TXE boot flash per Intel platform documentation. Apollo Lake has no internal NOR — an external 8MB SPI NOR on CS0 is mandatory for boot. This IC is the only non-SOIC flash on the board besides the Samsung eMMC.

#### Cross-Platform Confirmation

All three known A3960 AAOS deployments share this architecture:

| | GM gminfo37 | Fisker Ocean (X297) | Polestar 2 (IHU4) |
|---|---|---|---|
| **SoC** | Intel Atom x7-A3960 | Intel Atom x7-A3960 | Intel Atom x7-A3960 |
| **Manufacturer** | Harman/Samsung | Harman (Suzhou) | Aptiv (Delphi) |
| **FCC ID** | — | 2ACRL-X297 | LTQIHU4 |
| **RAM** | 8GB LPDDR4 (4x Micron) | 6GB LPDDR4 (4x Micron) | ~4GB LPDDR4 |
| **eMMC** | 64GB Samsung | 64GB (TBD) | 128GB |
| **Boot Flash** | 8MB SPI NOR (IS25WP064A) | 8MB SPI NOR (inferred) | 8MB SPI NOR (inferred) |
| **Security Engine** | TXE/CSE 3.0 | TXE 3.0 | TXE 3.0 |
| **OS** | AAOS 12 (API 32), GHS hypervisor | AAOS (TomTom, no GAS) | AAOS 9→10→11→12 |
| **Display** | 2400x960 (landscape) | ~2400x1600 (17.1" rotating) | 1152x1536 (portrait) |
| **Secondary MCU** | Renesas RH850 (TM52176) | NXP FS32K148U (Cortex-M4F) | — |

Sources: Intel E3900/A3900 Datasheet Addendum (CDI 336256), Apollo Lake SPI & SMIP Programming Guide (CDI 559702), Intel TXE FW Bring-Up Guide, FCC filings 2ACRL-X297 and LTQIHU4, Yole SystemPlus IHU4 teardown (Dec 2021).

#### IFWI Flash Layout (8MB)

```
Offset      Region                  Typical Size    Encrypted?
─────────────────────────────────────────────────────────────
0x000000    Flash Descriptor        4KB             No — signature 0x0FF0A55A at 0x10
0x001000    TXE Region              ~2-3MB          YES (AES-256, Intel keys)
~0x300000   IFWI/BIOS Region        ~4-5MB          Mixed
            ├─ Boot Partition 1 (BPDT)
            │  ├─ IBB (Initial Boot Block)          No (signed)
            │  ├─ OBB (OEM Boot Block)              No (signed)
            │  ├─ PMC firmware                      No (signed)
            │  ├─ Microcode                         YES (Intel encrypted)
            │  └─ SMIP                              No — platform strap config
            └─ Boot Partition 2 (A/B redundancy)
~0x7F0000   Device Expansion (PDR)  ~1MB            No — OEM data
```

#### Dump Feasibility

The IS25WP064A-JHLA3 package is WSON-8/BGA — requires a WSON-8 clip/adapter or TFBGA socket for the XGecu programmer. ISSI parts are well-supported in minipro/xgpro.

**What is readable in a raw dump:**
- Flash Descriptor — fully documented Intel structure
- UEFI/BIOS region (IBB/OBB) — Harman/GM boot config, secure boot keys, platform straps
- SMIP — hardware strap configuration (GPIO, SPI, clock settings)
- Boot Guard key hashes — reveals whose keys are in OTP fuses
- PMC firmware — power management controller binary
- TXE version/config — firmware version, OEM configuration data
- Device Expansion / PDR — OEM-configurable platform data

**What is NOT readable:**
- TXE code modules — AES-256 encrypted by Intel, opaque blobs
- Microcode — Intel encrypted
- AES-CMAC master key — stored in TXE Sealed Storage, encrypted with key derived from hardware fuses inside the A3960 die (inaccessible even with full dump)

**Analysis tools:** UEFITool (GUI, opens IFWI tree), MEAnalyzer (TXE/ME region), Intel FIT (Flash Image Tool), ifwitool (coreboot CLI)

#### Key Implications

1. AES-CMAC master key is unreachable — inside TXE Sealed Storage, encrypted with hardware fuse-derived key
2. SBI bypass makes the key irrelevant — EEPROM mod bypasses the entire security chain
3. VIP is security-transparent — no independent verification, pure relay
4. GHS hypervisor adds complexity — Android runs as a VM, not bare metal
5. OTA persistence is the main challenge — each update re-locks EEPROM
6. Bench mode is predictable — without gateway/SoC, VIP always returns 0xFF seeds
7. IFWI dump is useful for platform understanding but cannot reveal the master key
8. Boot Guard v2 root of trust anchored in TXE ROM — tampering with IFWI bricks boot

### Bootloader Unlock / Custom OS Feasibility

**Verdict: Not possible via IFWI modification. Boot Guard v2 is a hardware-enforced dead end.**

#### The Boot Guard Chain

```
A3960 OTP Fuses (irreversible, burned at factory)
    ↓ verify (RSA key hash match)
TXE ROM (mask ROM inside A3960 die, unmodifiable)
    ↓ verify (AES-256 + signature)
TXE FW in SPI flash (IS25WP064A)
    ↓ verify (OEM RSA signature)
IFWI/BIOS (signed with Harman/GM private key)
    ↓ verify
GHS Hypervisor (signed)
    ↓ verify
Android Verified Boot (vbmeta, locked)
    ↓
Android OS
```

Every link is cryptographically bound to the one above it. Breaking any single link requires either the private signing key for that level or a hardware vulnerability in the silicon.

#### Why IFWI Modification Fails

1. **OTP fuses are permanent** — During manufacturing, Harman/GM RSA key hashes are burned into one-time-programmable fuses inside the A3960 die. These are physically irreversible (antifuse technology).
2. **TXE ROM verifies on every boot** — Before any OEM code runs, the TXE mask ROM (hardcoded in silicon, not in flash) checks the IFWI signature against the fused key hashes.
3. **Signature mismatch = hard brick** — Not a soft warning. The platform halts entirely. No recovery, no fallback mode.
4. **No "virgin state" exists** — The fuses are burned. There is no way to return the A3960 to an unprogrammed state. Even erasing the entire SPI flash just produces a unit that won't boot.
5. **Writing a custom IFWI requires Harman/GM's RSA private key** — Without it, any modified image fails signature verification.

#### Why TXE Region Modification Fails

Even targeting the TXE firmware directly:
- TXE code modules are AES-256 encrypted with Intel's key (not OEM's)
- The TXE configuration (including Boot Guard policy) is signed
- No public Boot Guard bypass exists for Apollo Lake TXE 3.0
- Older Intel ME exploits (CVE-2019-0090, CVE-2017-5705) do not apply to this TXE generation

#### What Actually Works (Current Capabilities)

| Method | Access Level | Survives OTA? |
|--------|-------------|---------------|
| EEPROM SBI bypass (M24C64) | ADB shell, uid 2000 | No — OTA resets to 0x00 |
| Sideload APKs via ADB | App-level, sandboxed | Yes (if installed to /data) |
| Debug interfaces (ttyACM1, I2C) | Hardware-level, limited | Yes |
| IFWI dump + analysis | Read-only intelligence | N/A |

#### Partition Image Analysis (Y177 + Y181)

Both Y177 and Y181 partition images have been extracted and fully analyzed. **Nothing found to aid custom OS development or bootloader unlock.** This is expected — the partition images reside on the eMMC (top of boot chain) and contain only the Android layer. By the time Android boots, every layer below has already enforced signatures:

```
IFWI/TXE (SPI NOR, IS25WP064A) ← Boot Guard enforced HERE
    ↓ already verified
GHS Hypervisor (ghs_isys partition)
    ↓ already verified
vbmeta (signature chain)
    ↓ already verified
Android partitions (eMMC) ← Y177/Y181 images are HERE
```

The partition images cannot modify, influence, or bypass Boot Guard — that enforcement happens in a completely separate flash IC (IS25WP064A) and silicon (A3960 OTP fuses) before the eMMC is even accessed. Key observations:
- No bootloader unlock tokens, engineering flags, or debug keys found in any partition
- vbmeta is signed and chained — replacing it without the signing key triggers verified boot failure
- GHS hypervisor partitions (ghs_isys_a/b) are signed independently of Android
- The partition images are useful for app-level reverse engineering and understanding GM/Harman's AAOS customizations, but not for platform-level unlock

#### Theoretical Attack Vectors (None Currently Viable)

1. **Intel TXE silicon exploit** — A vulnerability in TXE 3.0 ROM that allows pre-Boot Guard code execution. None publicly known for Apollo Lake.
2. **Voltage glitching** — Physical fault injection during Boot Guard verification to skip the hash check. Requires expensive equipment (ChipWhisperer etc.), extremely timing-sensitive, not repeatable at scale.
3. **Drop-in replacement PCB** — Custom board with same connectors, unlocked SoC (e.g., standard Apollo Lake without Boot Guard). Theoretically possible but no one manufactures this.
4. **Qualcomm/other SoC swap** — Replace the Intel SOM entirely. Would require complete software rewrite.
5. **VIP→SoC IPC exploitation** — Using the VIP's authorized communication channel to command the SoC into a less-restricted state. See below.

### VIP→SoC Influence Path (Most Promising Research Direction)

The SBI bypass proves a **confirmed data flow** where an externally-writable value influences Android security behavior:

```
EEPROM (M24C64)          VIP (RH850)              SoC (Android)
    |                        |                        |
    |-- SBI flag (0xFF) ---->|                        |
    |                        |-- IPC: SBI state ----->|
    |                        |                        |-- ADB auth disabled
    |                        |                        |   (runtime config)
```

The VIP reads EEPROM at boot, sends state to the SoC via HDLC IPC, and the SoC **acts on it**. The SBI flag is just one byte in one channel — the VIP has an entire IPC protocol (v4.1.0, API 0404) with the SoC. The question: can any of those IPC messages influence the boot chain deeper than Android runtime config?

#### VIP Influence Surface

| VIP Function | What It Does | Potential Influence |
|---|---|---|
| SBI flags (EEPROM) | ADB auth control | **Proven** — runtime security config |
| SecurityAccess levels 0x10-0x13 | Unlock bitmask via SecWriteNVM (FUN_000b66a0) | Unknown — what operations do these gate? |
| ProtoKey IPC (FUN_000d2754) | Forwards security state to SoC | Unknown — what does the SoC do with this? |
| Power sequencing | Controls SoC power-on/off | Could force specific boot modes? |
| Boot slot selection | A/B partition management | Could influence which slot boots? |
| gm_update_engine interaction | OTA update state | Could trigger recovery/update mode? |
| VIN relearn / calibration | Factory provisioning state | Could signal "factory virgin" state? |
| MEC counter | Reprogramming event count (Y181=207) | Behavior at MEC=255 overflow? |

#### Timing Limitation

```
Boot sequence (time →)

TXE ROM → TXE FW → IFWI/UEFI → GHS Hypervisor → Android Init → Android Runtime
                                                                      ↑
                                                   VIP IPC reaches HERE
                                                   (not earlier)
```

The VIP boots independently on its RH850 core. Its IPC channel to the SoC is established **after** TXE → IFWI → GHS → Android have already completed verification. The SBI flag works because it affects an Android runtime setting, not a boot-time check. Boot Guard, vbmeta, and GHS verification complete before VIP IPC messages are processed.

#### Where This Gets Interesting

Despite the timing limitation, several scenarios could reach deeper:

1. **Factory/Engineering Mode** — If a VIP NVM state signals "module in factory provisioning," the SoC may boot into a less-restricted mode. GM SPS reprograms these modules through the VIP via CAN/UDS — that programming path exists.

2. **gm_update_engine** — OTA updates rewrite the EEPROM (re-locking SBI), proving the SoC can write to EEPROM via VIP IPC. If the update engine can write, can it be commanded to enter a special update/recovery mode via VIP state?

3. **SecurityAccess Levels** — The 4 levels (0x10-0x13) each persist an unlock bitmask via SecWriteNVM. What does each level gate? If one gates "allow SPS reprogramming," that's a path to writing arbitrary calibration data.

4. **ghs_abl_update Partition** — Dedicated GHS ABL (Android BootLoader?) update partition. If the VIP can trigger an update cycle and the payload could be controlled...

5. **MEC Counter** — Y181 bench unit shows MEC=207. Y177 via gateway shows MEC=0. Behavior differs significantly between them. What happens at MEC=255 (overflow)?

6. **SPS Programming Flow** — GM SPS sends CAN → VIP → SoC to reprogram modules. The VIP is a transparent relay with no crypto. Capturing and replaying this sequence could reveal the authorized reprogramming path.

#### Research Path Forward

| Step | Method | Goal |
|------|--------|------|
| 1 | Full EEPROM analysis vs VIP firmware | Map ALL VIP NVM read addresses beyond the 4 known SBI offsets |
| 2 | UDS service enumeration post-$27 unlock | After SecurityAccess (trivial with 0xFF seeds in bench mode), enumerate $2E (WriteDataByIdentifier), $31 (RoutineControl), $34/$36/$37 (RequestDownload/TransferData) |
| 3 | IPC sniffing (normal boot vs SPS programming) | Capture HDLC traffic on the VIP↔SoC link during both scenarios |
| 4 | Force VIP into programming session | $10 02 (DiagnosticSessionControl: Programming) or $10 03 (Extended), then $31 RoutineControl to trigger SoC-directed operations |
| 5 | SPS programming flow capture | Full CAN + IPC capture during authorized GM SPS reprogramming — reveals the legitimate programming channel |
| 6 | MEC boundary testing | Test behavior at MEC=254, 255, 0 (overflow) |

The VIP is the weakest link precisely because it's a simple relay with no crypto. If it can be commanded to tell the SoC "enter programming mode" or "factory reset to virgin state," and the SoC trusts that message, then Boot Guard is not broken but **sidestepped** through the authorized programming channel.

---

## Audio Signal Chain

```
AM/FM/HD Antenna
      |
  NXP SAF7751 (Tuner + Audio DSP)
      |  I2S/TDM
  Intel A3960 SoC
      |  AudioFlinger -> PulseAudio
  Intel I210 (GbE MAC)
      |  AVB Ethernet (gPTP Master, 1000Mbps)
  Broadcom BCM89551 (Ethernet Switch)
      |  AVB Ethernet
  NXP TDF8532 (External DSP/Amplifier)
      |
  Speakers
```

- Native: 48kHz, PCM 16-bit stereo
- 12+ output buses (media, nav, call, alarm, notification, etc.)
- 3 RX + 3 TX AVB streams, FIFO priority 50

---

## Display Signal Chain

```
Intel A3960 GPU (HD Graphics 505)
      |  Internal display pipe
  HWC 2.1 (hwcomposer.broxton)
      |  Triple-buffered, VSYNC 16.67ms
  TI DS90UH949-Q1 (FPD-Link III Serializer)
      |  FPD-Link III
  Display Panel: 2400x960 @ 60Hz
      |
  LT3899 (Backlight LED Driver)
```

> **Runtime-identified components** (not read at physical teardown — cross-ref `platform/hardware.md`; confirmed by the live Jun-2026 Y181 capture):
> - **Display panel:** Chimei Innolux (CMN) **DD134IA-01B**, 2400x960 @ 60Hz, density 200, ~13.4" (from EDID; the teardown captured resolution only — no panel maker/model was read off the assembly).
> - **Touch controller:** Atmel **maXTouch** on i2c bus 7 @ **0x4B** (from runtime i2c enumeration; not present in the board BOM above).
> - **GPU driver stack:** Mesa **21.1.5**, OpenGL ES **3.2**, Vulkan **1.1.0** (runtime; the BOM lists the HD 505 silicon only, no driver/API versions).
> - **Ethernet MAC:** the chip is physically marked **WGI210CL = Intel I210** rev A3 (BOM line: "Ethernet MAC"); some curated docs (`platform/hardware.md`, `MASTER_REFERENCE.md`, the Y177 `tech_specs`) label it **"I211"** — an unverified near-twin reading; the physical part marking says **I210**.

Camera input:
```
Camera(s)
      |  FPD-Link III
  TI DS90UB954-Q1 (Deserializer Hub)
      |  CSI-2
  Intel A3960 ISP
```

---

## Network Topology (from ADB Enumeration)

### Listening Ports
| Port | Address | Likely Service |
|------|---------|---------------|
| 53 | 127.0.0.1, 192.168.5.1, ::1, fe80:: | DNS |
| 7000 | 0.0.0.0, [::] | CINEMO/NME or GM service |
| 6363 | 0.0.0.0 | Unknown |
| 49156 | 0.0.0.0 | Ephemeral (media/IPC) |
| 9016 | 192.168.1.1 | Internal SoC service |
| 9002 | 192.168.1.1 | Internal SoC service |

### Internal Networks
- 192.168.1.x — SoC internal services
- 192.168.5.x — WiFi AP/hotspot

### UART Interfaces
| Device | Permissions | Notes |
|--------|------------|-------|
| /dev/ttyACM1 | crw-rw-rw- (world) | MCP2200 USB-UART — debug console |
| /dev/ttyS0 | crw-rw---- bluetooth | Bluetooth HCI |
| /dev/ttyS1-S3 | crw------- root | Reserved |

### I2C Buses
11 buses (i2c-0 through i2c-10), consistent across Y175/Y181:
- i2c-0, i2c-1: world-readable (root:root)
- i2c-2: system:system
- i2c-3: audioserver:audioserver (SAF7751 / TDF8532 control)
- i2c-7: system:system
- i2c-4,5,6,8,9,10: root-only

---

## VIP MCU Details (from VIP Log, Y175)

- Application Version: 2B.175.1.5 (Build: 24Apr23-2202)
- Bolo Version: B2.9C.01.01 (23Jul28-1212)
- ARXML Version: 22.22.158
- IPC: v4.1.0, API 0404, HDLC window 5, IFRAME timeout 50ms, UFRAME timeout 20ms
- HwVariant: 56, HwSubVariant: 0
- Suspend-to-RAM: enabled
- SOC thresholds: 90%/75%/60%, temp threshold: -10C
- Max suspend times: 84h/24h/16h (by SOC tier)
- Calibrations: VIN relearn, cluster animation, shutdown animation failsafe (15s)

---

## Deep EEPROM Analysis (Full 8KB Map)

### Framing Protocol
Four framing byte patterns: `69`, `F0`, `C3`, `5A`. Each data record: `[framing] [data] [framing] [FF padding]`.

### Structured Regions Beyond SBI Flags

| Offset | Framing | Data | Interpretation |
|--------|---------|------|----------------|
| 0x0040 | 69 | 0x27E6 (10,214) | **Boot/write counter** |
| 0x03A0 | 69 | 004B41DC...14AC | **ECUID** (16 bytes, matches UDS $27) |
| 0x0400 | 69 | 0x19, checksum 0xE4A4 | **Security level bitmask** (duplicated at 0x0420) |
| 0x0500 | F0 | "<SN_REDACTED>" | GM service part number fragment |
| 0x0580 | F0 | "20.02.2025" | **Last programming date** |
| 0x05A0 | F0 | "7310500000000X" | Calibration file ID |
| 0x05C0 | F0 | "XXXXXXXXXXXXXXXXX" | **VIN** |
| 0x0680 | 5A | "9999988888" | Placeholder/test data |
| 0x06E0 | F0 | 0x600202B1 | **HW Part Number** (matches VIP log) |
| 0x0B60 | C3 | 0xF70400 | **Unknown flag — NOT modified by SBI bypass** |
| 0x0C01 | 5A | 0x01 | **Non-zero flag — unknown function, untouched** |
| 0x0E00 | — | 142-byte block | **VIP calibration NVM** (timeout values, thresholds) |
| 0x0EC0 | 69 | 0x0186...SBAT data | **SBAT state** (keyNBID, appNBID) |
| 0x0EE0 | F0 | 0x7C4A, 0x8F42 | **DTC identifiers** |
| 0x0F00-0x12D9 | mixed | 21-point curves | **Brightness/audio calibration lookup tables** |
| 0x14A0 | 5A | "XXXXXXXX A" | **Short VIN + plant code** |
| 0x15E0 | 69 | boot counter area | **PLC_BootCounter region** |
| 0x1A80 | C3 | 0x0167 (359?) | **MEC NVM value** (differs from transmitted 0xFF) |
| 0x1AE0 | C3 | 0x06 | **SecurityAccess unlock bitmask** (which levels unlocked) |
| 0x1B60 | F0 | 0x92 (146), 0x035A (858) | **Two independent reflash/programming counters** |
| 0x1F60 | 69 | 97 bytes high-entropy | **Certificate/signed blob** (contains "15-47WYBN") |

### Undocumented Flags (from VIP firmware cross-reference)

| Offset | Firmware Refs | Current Value | Significance |
|--------|--------------|---------------|-------------|
| 0x0A00 | **871** | — | **Extremely high reference count — critical unknown function** |
| 0x0B00 | 311 | — | High reference count |
| 0x04A0 | 17 | — | Moderate references |
| 0x04C0 | 11 | — | Moderate references |
| 0x0A20 | — | — | Adjacent to 0x0A00 block |
| 0x0A40 | — | — | Adjacent |
| 0x0A60 | — | — | Adjacent |
| 0x0AC0 | — | — | Adjacent |
| 0x0B20 | — | — | Adjacent to 0x0B00 |
| 0x0BE0 | — | — | Near SBI region |

---

## Y177 vs Y181 Security Difference (Critical Finding)

**Y177 has a STUBBED security validation function. Y181 has the full implementation.**

| | Y177 (86283151) | Y181 (86331656) |
|---|---|---|
| FUN_000b67d0 | **4 bytes — always returns success** | 906 bytes — full state machine |
| SELinux | **PERMISSIVE** | Enforcing |
| MEC | 0 | 207 |
| Bootloader | 2121-1 | 2344 |
| SBI effect | Full bypass (stubbed validation) | ADB auth only |
| Kernel | 4.19.283 | 4.19.305 |

This is why the EEPROM SBI bypass had broader effect on Y177 — the security validation was a no-op. GM patched it in Y181.

---

## GHS Hypervisor Analysis (SOC_HOSTOS: 85098662)

Binary: 14.9MB, INTEGRITY IoT 2020.18.19, core 23739
Build path: `/home/mal/gm_release/MY22-026/final/iot/rtos/`

### GHS Tasks (14+)
VMM1, Camera, Audio, GPU, Chimes, Dirana, DisplayI2C, VIP, Lifecycle, OTA, Lines, Calibrations, TEE_Keymaster, TEE_HW_Crypto

### VMM Capabilities
- `ReadGuestMemory`, `WriteGuestMemory`, `ReadGuestVirtualAddress`
- `ASP_RunGuestVM`, `ASP_ResetVCpu`
- Uses Intel VT-x (VMX) and VT-d (IOMMU)
- Provides virtio block devices, virtio console, GHS PCM audio to Android guest

### GHS HOSTOS is IDENTICAL Between Y177 and Y181

Same SHA-256 (`317ae85c...`). The hypervisor, VMM, kernel, all RTOS modules — **unchanged**. Every difference between Y177 and Y181 is in the Android guest partitions only. The `AB0` metadata format and rollback enforcement logic are the same binary for both.

### A/B Metadata Format (Decoded from GHS VMM1 Binary)

**Magic: `"AB0"` (3 bytes) — NOT AOSP's `BABC`/`0x42414342`.** This is a GHS/GM-specific bootloader_control format.

| Field | Value |
|---|---|
| Magic | `"AB0"` (3 bytes, null-terminated) |
| Version | 1 (max supported) |
| CRC32 | Standard ISO 3309 (polynomial `0xEDB88320`, init `0xFFFFFFFF`, final XOR `~crc`) |
| Slot suffixes | `_a`, `_b` |
| Rollback check | `"rollback index is too old: %lu in image, but stored is %lu"` |

**Validation sequence** (from VMM1 rodata string ordering):
1. Read A/B metadata from `misc` partition
2. Check magic = `"AB0"`
3. **CRC32 validation** — NO cryptographic signature
4. Check version ≤ 1
5. Select slot by priority + remaining attempts
6. Load boot image for selected slot
7. Load + parse vbmeta (AVB 1.1, SHA-256)
8. Check rollback index (`%lu in image, but stored is %lu`)
9. Verify slot → on failure sets `ghs_androidboot.altsloterror={verify_failed|bad_image|no_remaining|rollback_error}`
10. Write updated metadata back to misc (`"VMM: A/B metadata updated"`)
11. If GHS and Android slot disagree: `"GHS: Android and INTEGRITY slot mismatch... Rebooting..."`

**4 CRC32 instances** in the binary (all software, no HW CRC32 instructions):

| Offset | Polynomial | Module | Purpose |
|---|---|---|---|
| 0x00B552AE | 0xEDB88320 | BSP/OTA | BSP checksum |
| 0x00CC9E96 | 0xEDB88320 | **VMM1** | **A/B metadata + GPT validation** |
| 0x00D25194 | 0xEDB88320 | Additional | GPT validation |
| 0x00024928 | 0x04C11DB7 | Early boot | Boot header verification |

### Boot Modes (from GHS binary strings)
- **Normal A/B**: Standard boot with slot selection
- **Recovery**: `boot-recovery` BCB command (no recovery partition — GHS IS the recovery mechanism)
- **See-Dealer**: `GHS: [LIFECYCLE] Booting 'see-dealer' mode` — dealer diagnostic/service mode
- **ELK (Emergency Linux Kernel)**: `GHS: [LIFECYCLE] Got request to boot to ELK` — minimal emergency kernel for catastrophic failures. Triggered via `ConnToOTA_BootELK` or `ConnToLifecycle_BootELK` IPC. State machine: `BootELKWaitForRespSent` → `BootELKSendAblUserCommand` (sends HECI command to ABL).
- **Diagnostic**: `Diagnostic channel active`

**There is NO recovery partition.** GHS itself is the recovery mechanism — it's always running as the hypervisor, has direct display access (camera overlays, error screens), and can rewrite any Android partition via its OTA module. As long as `ghs_isys` boots (which has its own A/B redundancy), the entire radio is recoverable.

### GHS as Recovery Architecture

```
GHS INTEGRITY Hypervisor (always running, bare metal on A3960)
    ├── VMM1: A/B boot selection, AVB verification, rollback enforcement
    ├── Camera: Direct display overlay (independent of Android guest)
    ├── OTA: ota-isys partition rewrite capability
    ├── Lifecycle: Boot failure detection → ELK / see-dealer / recovery
    ├── GPU/Display: Can render independently of Android guest
    └── Android Guest VM (may be broken/absent — GHS still runs)
         ├── plmanager → writes BCB to misc ("boot-recovery")
         ├── gm_update_engine → downloads/stages OTA packages
         └── ... (everything else)
```

When Android fails, GHS reads the BCB from misc and enters its own recovery flow. The "return to dealer" screen is rendered by GHS, not Android.

### 3x Failure Bypass
After 3 consecutive SoC startup failures, GHS disables hypervisor timer and CSM reset for that boot cycle. Lifecycle strings: `"Android failed to boot (count=%lu)"`, `"Too many failures, need to see dealer!"`.

### GHS Device Interfaces (from ADB)
`/dev/ghs/{textlog, audit, snapshot-dbg, ipc, cal, camera, chime, tee-att, emmc-health, ota-isys, gpu-dbg}`

---

## plmanager & misc Partition Analysis (Critical for Research Vector #1)

### plmanager — Power Lifecycle Manager (NOT boot_control HAL)

**PID 590, runs as root**, SELinux type: `hal_bootctl` + `hal_bootctl_server`
Binary: 288KB ELF x86-64, **Y177 and Y181 versions are byte-identical** (same MD5: `ba7c73ca8c50206604af9c0be9317c7b`)
HARMAN PAL SWUpdate SysState v22 (2018-05-29), HIDL service: `vendor.gm.powermode@1.0::IPowerModing`

**plmanager is NOT an Android boot_control HAL.** It contains zero references to `IBootControl`, `markBootSuccessful`, `getCurrentSlot`, `setActiveBootSlot`, or any standard A/B slot API. It is a **P**ower **L**ifecycle **Manager**.

| Capability | Detail |
|---|---|
| **misc partition** | `read write open` — writes **boot failure counter** and **BCB recovery commands** only (NOT rollback counters) |
| **GHS device** | `/dev/ghs/ota-isys` — coordinates reboot mode with GHS hypervisor |
| **VIP IPC** | `/dev/ipc/ipc` — PM + PLC channels to VIP MCU |
| **Intel MEI** | `/dev/mei` — Management Engine Interface |
| **Power control** | `sys.powerctl` — reboot/shutdown |
| **SysRq trigger** | `/proc/sysrq-trigger` — emergency kernel operations |
| **Safe mode** | `persist.vendor.safemode` / `ro.vendor.safemode` |
| **SWUpdate** | `swu_sysstate_enter_remote_reflash_programming_state` — OTA coordination |

**What plmanager writes to misc** (`/dev/block/by-name/misc`): Boot failure counter (`saveBootFailureCount`, `persist.vendor.pm.bfc`) and BCB commands (`boot-recovery` + `--show_return_to_dealer`). Error strings: "Cannot open/seek/write otafd misc !" — raw open→seek→write, no CRC32 validation.

**Boot failure flow**: checkBootFailure → verify GM image (`ro.build.display.id`) → watchdog timer → on timeout: increment counter → at threshold: "BOOT FAILURE!!! TOTAL FAILURE" → write `boot-recovery` to BCB → `set_boot_target` recovery → reboot → GHS enters see-dealer mode

### misc Partition (vda9) — No Integrity Protection

**Mounted with `defaults` only — NO AVB, NO dm-verity, NO encryption per fstab.**

| Property | Value |
|---|---|
| Device | `/dev/block/vda9` |
| Filesystem | Raw block (no filesystem, direct structure) |
| Mount flags | `defaults` — no integrity, no encryption |
| AVB | NOT applied to misc (only to boot, system, vendor) |
| dm-verity | `CONFIG_DM_VERITY_AVB` is **NOT set** in kernel config |
| SELinux label | `misc_block_device` |

This is significant: the GHS rollback counter stored in misc uses CRC32-only validation AND the partition itself has no external integrity protection. If the structure can be reverse-engineered, modification requires only recalculating a CRC32.

### abl-user-cmd_vendor — IFWI Flash Update Tool

9KB ELF x86-64, symlinked as `cmd_fw_update_vendor`. SELinux: `u:object_r:drmrpc_exec:s0` (drmrpc domain, NOT fw_update). Y177 and Y181 versions byte-identical.

**Usage**: `abl-user-cmd_vendor -i <device><partnum>:<path> [-s]`
- `-i` / `--ifwi-update`: IFWI update package path (format: `m1:@0` = mmcblk partition 1, default capsule)
- `-s` / `--store-in-cse`: Send command to Intel CSE via HECI (without this flag, just outputs to stdout)

**How it works**: Builds a CRC32C-protected command buffer (Castagnoli polynomial `0x82F63B78`), sends it to Intel Management Engine via `/dev/mei` using MKHI protocol (GUID `8e6a6715-9abc-4043-88ef-9e39c6f63e0f`, group 0x4D = ABL). The ME firmware orchestrates the actual SPI flash (IS25WP064A) update.

**Two IFWI update paths** (from `init.bxtp_gm.rc`):
1. **HECI path** (`vendor.ota.update.fw={a|b}`): `abl-user-cmd_vendor -s -i m1:@0` — live flash while system runs
2. **Capsule path** (`vendor.ota.recovery.fw={a|b}`): Write to `/sys/kernel/capsule/capsule_name` → reboot → ABL flashes during early boot

**BPDT signature**: `0x000055aa` — Intel Boot Partition Descriptor Table magic. Invalid signature triggers capsule recovery.

**IFWI error codes** (from `fw_update.sh`, set by ABL via `ABL.ifwifail`): 07=CSE error, 08=BIOS reg read fail, 09=SPI init fail, 0A=SPI write, 0B=SPI read, 0C=SPI erase, 0D=SPI verify

### GHS Partition Swap Mechanism

```
Active Slot _a:                    Active Slot _b:
  vda1 = ghs_isys_a (active)        vda1 = ghs_isys_b (active)
  vda2 = ghs_isys_b (inactive)      vda2 = ghs_isys_a (inactive)
```

GHS manages its own A/B slot independent of Android's boot_control HAL. The slot metadata in misc controls which ghs_isys partition boots.

### AVB Rollback Index

**vbmeta.rollback_index = 0** for both Y177 and Y181 in userspace. The actual rollback protection is managed below Android by GHS/ABL, stored in misc partition with CRC32-only integrity.

### SELinux Boot Parameter Anomaly

`ro.boot.selinux = permissive` appears in boot parameters, but runtime state is **Enforcing**. GHS hypervisor overrides the boot parameter and forces Enforcing mode. This means even if the boot parameter could be modified, GHS would still enforce SELinux policy — except on Y177 where SELinux was natively permissive.

### SELinux: Shell CANNOT Access misc (Confirmed)

**`neverallow` at `system/sepolicy/public/domain.te:632`** explicitly blocks shell from `misc_block_device`:
```
(neverallow base_typeattr_238 misc_block_device (blk_file (ioctl read write lock relabelfrom append link rename open)))
```

`base_typeattr_238` = every domain EXCEPT: `hal_bootctl_server`, `fastbootd`, `init`, `recovery`, `ueventd`, `uncrypt`, `update_engine`, `vendor_init`, `vendor_misc_writer`, `vold`. **Shell is NOT exempted.**

Shell can only `getattr` (stat) block devices — `ls -l /dev/block/vda9` works, but `dd`/`cat`/any read will fail with `avc: denied`.

**Who CAN access misc_block_device:**

| Domain | Permissions |
|---|---|
| `hal_bootctl_default` | Full (ioctl, read, write, getattr, lock, append, map, open) |
| `plmanager` | read, write, open |
| `update_engine_common` | Full |
| `init` | write, lock, append, map, open, relabelto |
| `uncrypt` | write, lock, append, map, open |
| `vendor_init` | write, lock, append, map, open |
| `vendor_misc_writer` | write, lock, append, map, open |
| `vold` | write, lock, append, map, open |
| `gm_update_engine` | **getattr ONLY** (cannot read or write!) |

**Critical finding**: `gm_update_engine` can only stat misc, not read/write it. But `update_engine_common` (standard AOSP update_engine) has FULL access. The path to misc must go through either `update_engine`, `plmanager`, or `init`.

### Implications for Research Vector #1

```
ADB shell (uid 2000)
    ✗ BLOCKED by neverallow — cannot read /dev/block/vda9
    ↓ must use an exempted process
update_engine (full access to misc)
    ↓ or
plmanager (read/write/open to misc, writes BCB + boot failure counter)
    ↓
misc partition (vda9)
    ↓ no AVB, no dm-verity, no encryption
GHS AB0 metadata
    ↓ CRC32-only validation (standard ISO 3309, 0xEDB88320)
Rollback counter
    ↓ modify + recalculate CRC32
Y177 downgrade possible?
```

**`update_engine`** is the most promising path — it has full misc access, is an Android process that can be interacted with, and is the standard mechanism for OTA updates. If it can be commanded to write modified AB0 metadata, or if its misc writes can be intercepted/redirected, the rollback counter can be changed.

---

## SBAT (Secure Boot Anti-Theft) Status

From Y175 VIP UART log:
```
keyNBID = 0x0000
appNBID = 0x0001
ECU_ID = 00 26 42 25 00 00 16 00 06 10 41 45 61 01 14 AC
First 10 bytes of SBAT = 00 00 00 00 00 00 00 00 00 00
SbaTicketValidation validation failed: 0x0
```

**SBAT ticket is all-zeros. Validation FAILED but boot continues normally.** SBAT failure is non-blocking — firmware replacement is not gated by SBA verification on this unit.

---

## IPC Channel Map (from VIP UART Log)

| Channel | Time (ms) | Role |
|---------|-----------|------|
| 12 | 688 | Early init |
| 14 | 690 | Boot reason (`SendLastBootReason`, BRR) |
| 17, 18 | 690-691 | Early init |
| 1-11, 13, 15, 16, 19, 20 | 4110-4115 | All channels XON together |
| 2 | 5628 | PlayAnimation |
| 16 | 5636 | PlayAnimation secondary |
| 5 | 5660 | Ethernet state |
| 8 | 5894 | **Calibration download** |
| 9 | 7428 | **ProtoKey** |
| 6 | 7519 | **Diagnostics (UDS SID/DID)** |
| 13 | 21733 | **OTA/Remote Reflash** (frequent connect/disconnect) |

### SoC Power Levels (VIP→SoC lifecycle)
| Level | Time | Meaning |
|-------|------|---------|
| 1 | 729ms | Kernel/hypervisor up |
| 2 | 1284ms | Secondary init |
| 3 | 5633ms | Services starting |
| 4 | 5637ms | **SoC fully booted (StartupComplete)** |

### Boot Reason Record (BRR)
`RstRsn=0x33, SoCReqType=0, RetRsn=0, UnqBtCnt=4066, RstFctr=0x201`

**SoCReqType=0 means normal boot.** This field exists as a mechanism for the VIP to encode boot type requests. Non-zero values could trigger recovery/fastboot/programming mode boot.

---

## ProtoKey Behavior (Y175 VIP Log)

Three-phase sequence during boot:
1. **t=0-18s**: BCM seeds INVALID (CAN not ready)
2. **t=7-58s**: All-zero seeds transmitted to SoC, **status=3** (unauthenticated). **Boot continues normally** — ProtoKey is soft security.
3. **t=67s**: BCM seeds become valid (`1a 6a 09 41...`, `10 7d 9e 16...`), status=1 (authenticated)

---

## MEC Counter Variation Across Units

| Unit/Build | MEC | Behavior |
|------------|-----|----------|
| Y175 (DPS A11_CSM_x80.Txt) | **244** | — |
| Y177 (via gateway) | **0** | Real seeds, SPS security validation failed |
| Y181 (bench, BSOB) | **207** | 0xFF seeds, GCI completed |
| Y175 VIP UART log | **0xFF** (transmitted) | MEC at maximum — manufacturing/test mode? |

MEC≠0 causes VIP to ignore hypervisor startup failures.
EEPROM NVM at 0x1A80 stores a different MEC value than what's transmitted (0x0167=359 vs transmitted 0xFF).

---

## Key Tools & Attack Surface

### Vendor Binaries of Interest
| Binary | Purpose |
|--------|---------|
| `plmanager` | **Power Lifecycle Manager** — root, 288KB, writes boot failure counter + BCB to misc, GHS ota-isys, VIP IPC, MEI, power control. NOT a boot_control HAL. |
| `abl-user-cmd_vendor` | **IFWI flash tool** — 9KB, sends CRC32C commands to Intel MEI/HECI for SPI flash updates. `-s -i m1:@0` = live HECI flash. drmrpc domain. |
| `IPCServer` | VIP IPC server daemon (runs as root on /dev/ttyS1 at 1Mbps) |
| `diagnosticsd` | UDS diagnostic daemon |
| `gm_protokey` | ProtoKey (CSE security) daemon |
| `gm_update_engine` | **GM proprietary OTA engine** — 667KB, HIDL HAL (vendor.gm.swupdate@1.0), replaces AOSP update_engine entirely. Red Bend rb_ua for delta patching. SHA-256+RSA signature verification. getattr-only on misc (delegates to hal_bootctl). No anti-rollback logic. |
| `rb_ua` | **Red Bend Update Agent** — 930KB, statically linked, scout_update mode. Actual delta-patching engine used by gm_update_engine. |
| `calserviced` | Calibration service (central authority) |
| `GHSCalibrations` | GHS hypervisor calibration service |
| `fw_update.sh` | Firmware update script |
| `svn-commit_vendor` | Firmware versioning tool |

### gm_update_engine — GM Proprietary OTA Engine

667KB ELF x86-64, runs as root, HIDL HAL at `/vendor/bin/hw/gm_update_engine`. **Completely replaces AOSP update_engine** — no standard update_engine binary exists on this platform. Source: `gmplatform/system/update_engine/impl/`. Y177/Y181 are slightly different builds (48-byte difference).

**HIDL services:**
- Provides: `vendor.gm.swupdate@1.0::IECUUpdate`, `IECUInformation`
- Consumes: `vendor.gm.powermode@1.0::IPowerModing`, `vendor.gm.diagnostics.internal@1.0`, `android.hardware.boot@1.0::IBootControl`

**Update flow:** libcurl download → SHA-256+RSA manifest verification (against `/etc/security/{development,production}/signingCA.cer`) → Red Bend `rb_ua` scout delta patching → A/B slot switch via hal_bootctl → reboot

**ECU update types:** HostOS (0x15), VIP Bootloader (0x47), VIP App (0x01), SoC Bootloader (0x48), Digital Tuner (0x33), Ethernet Switch (0x34), GPS (0x1D), SXM (0x1C)

**Critical SELinux limitation:** `gm_update_engine` has **getattr only** on misc_block_device. Cannot read or write misc. Delegates slot operations to `hal_bootctl_default` (which IS plmanager by type attribution).

**No anti-rollback in this binary.** Zero references to "downgrade", "rollback", or version comparison logic. All rollback enforcement is in GHS VMM.

**GHS/IPC connections (critical for ota-isys research):**
- `ipc_serverd` — GHS hypervisor IPC
- `gm_vnd_IPCServer` — VIP MCU link
- `ghs_device` — `/dev/ghs/*` ioctl access (includes `ota-isys`)
- `display_panel_device` — direct display access
- `ethctrlmgr` / `ethctrlswdlclient_socket` — Ethernet OTA delivery

**Red Bend config** (`/vendor/etc/swupdate/rb_ua.conf`):
```
work_dir=/update_cache/update/redbend
exec_path=/update_cache/update/redbend/rb
update_operation=scout_update
update_flavor=std
no_reboot=1
```

**Signing certificates**: `/etc/security/{development,production}/signingCA.cer` — SHA-256+RSA manifest verification

**GM power modes** (gates update operations): SLEEP(0x00), ANIMINIT(0x01), HMIINIT(0x02), START(0x04), RUN(0x05), PROPULSION(0x06), ACCESSORY(0x07), LOCALINFOTAINMENT(0x08), **REMOTEREFLASH(0x10)**

**Triggered by:** `gmConnectionService`, `gm_diagnosticsd` (not shell — no binder allow rule for shell)

### Who Writes What to misc (vda9)

```
misc partition layout (conceptual):
┌─────────────────────────────────────────────┐
│ AB0 metadata (magic, version, slot data,    │ ← Written by GHS VMM ONLY
│ rollback counter, CRC32)                    │   (hypervisor level, before/after Android)
├─────────────────────────────────────────────┤
│ BCB (Bootloader Control Block)              │ ← Written by plmanager
│ ("boot-recovery", "--show_return_to_dealer")│   (Android level, boot failure handler)
├─────────────────────────────────────────────┤
│ Boot failure counter                        │ ← Written by plmanager
│ (saveBootFailureCount, persist.vendor.pm.bfc)│  (Android level)
├─────────────────────────────────────────────┤
│ hal_bootctl slot selection                  │ ← Written by hal_bootctl_default
│ (via IBootControl HAL)                      │   (called by gm_update_engine)
└─────────────────────────────────────────────┘
```

**The AB0 rollback counter is GHS-managed.** No Android process writes to it. The only way to modify it from Android would be to raw-write to the correct offset in misc using a process with write access (plmanager, hal_bootctl_default, or the phantom AOSP update_engine type).

### ELK — Emergency Linux Kernel

**What it is:** GHS boot mode for catastrophic Android failure. A minimal Linux environment that boots via a completely different path than normal Android — bypassing the misc/BCB boot chain entirely.

**Boot path:** HECI → Intel CSE → ABL (boot target `OBBPELK`) — can boot even if eMMC is corrupted.

**Three trigger paths:**
1. **CAN diagnostic** — VIP J6_CDD module: `"[J6_CDD] Control Chan: Diag Elk Reboot Req"` → VIP forwards to GHS lifecycle → HECI command to ABL → `OBBPELK`. Exact UDS service/DID unknown.
2. **GHS lifecycle state machine** — Last resort after shutdown fails. State progression: `BootELKWaitForRespSent` → `BootELKSendAblUserCommand`. Triggers after repeated boot failure escalation.
3. **OTA IPC** — `ConnToOTA_BootELK` / `ConnToLifecycle_BootELK` IPC within GHS task architecture.

**ELK image location:** Unknown — NOT found in any update package (Y177/Y181) or extracted partition. Possibly embedded in GHS binary (85098662) or stored in SPI NOR flash alongside IFWI.

| Property | Known | Evidence |
|---|---|---|
| Boot path | OBBPELK via ABL | ABL strings in 85738845 |
| Trigger (CAN) | VIP J6_CDD diagnostic channel | VIP firmware: "Diag Elk Reboot Req" |
| Trigger (GHS) | Lifecycle state machine last-resort | State: BootELKSendAblUserCommand |
| Trigger (OTA) | ConnToOTA_BootELK IPC | GHS OTA task can trigger it |
| Boot mechanism | HECI → CSE → ABL (NOT BCB/misc) | Bypasses normal boot chain |
| Image location | Unknown — not in update packages | Possibly embedded in GHS binary or SPI flash |
| Display | Likely yes | Purpose is emergency/diagnostic |
| Update capability | Likely yes | ConnToOTA_BootELK exists |
| ADB/shell | Unknown | No evidence either way |
| SELinux | Unknown | Not Android, may not apply |
| Network | Possibly | OTA connection suggests it |

**Critical question:** Is ELK a full Linux with shell access (and possibly no SELinux, direct block device access), or a minimal graphical "return to dealer" screen? If the former, it bypasses the entire Android security stack and is accessible via CAN diagnostic commands that the VIP relays without crypto verification.

**Observed "return to dealer" incident:** The radio was caused to fail to boot by disabling system packages via `pm disable --user` for user 0 and user 10 from ADB shell. This entered the return-to-dealer screen. Recovery was done using a datawipe update package via USB (which resets `/data/` including `pm disable` state in `/data/system/`). **ADB/USB exposure was NOT checked during the return-to-dealer state.** This is the highest-priority test — the return-to-dealer screen may be ELK or a pre-Android state with relaxed security.

**Reproduction method:** From ADB shell, `pm disable --user 0 <critical-package>` persists in `/data/system/users/0/package-restrictions.xml` and survives reboot. GHS counts consecutive Android boot failures. After threshold (likely 3), escalates to return-to-dealer/ELK. Recovery: datawipe USB package clears `/data/`, re-enables packages.

**What to check during return-to-dealer state:**
1. `adb devices` — does device enumerate?
2. `adb shell id` — UID? root or shell?
3. `adb shell getenforce` — SELinux enforcing/permissive/disabled?
4. `adb shell ls -la /dev/block/by-name/misc` — misc access?
5. `adb shell cat /proc/partitions` — full partition table?
6. `lsusb` on host — does the USB device change VID/PID?
7. `adb shell dmesg` — kernel log, boot mode, SELinux status

### /dev/ghs/ota-isys — GHS Hypervisor Interface

**Device:** `/dev/ghs/ota-isys` — paravirtualized char device via `ghs_vmm_bc.ko` (CONFIG_GHS_VMM_BOOTLOADER_CONTROL=y)

**Two usage patterns:**
1. **Firmware streaming** — `libpal_swupdate_hostos.so` (9KB) implements write-chunk/read-ACK protocol for HostOS (GHS) and ABL firmware updates. Opens ota-isys, writes firmware chunks, reads ACK after each.
2. **Reboot mode control** — plmanager sends "GHS next reboot mode" commands. Sets reboot target for GHS decision-making at next boot.

**Who can access ota-isys:**
| Process | Access | SELinux Domain |
|---|---|---|
| gm_update_engine | ioctl, read, write, open | gm_update_engine |
| plmanager | read, write, open | hal_bootctl_server |
| vendor_init | read, write, open | vendor_init |
| ame_hal_service | ioctl, read, write, open | ame_hal_service |

**Cannot directly modify AB0 metadata** — that's GHS VMM internal state. But the ota-isys interface IS how Android tells GHS what to do. If there's a command to set rollback counter or override boot validation...

**libpal_swupdate_hostos.so protocol:**
```
swu_update_hostos(device, firmware_chunks)
  → open(/dev/ghs/ota-isys)
  → write(chunk_data)     // firmware data
  → read(ack_response)    // wait for GHS ACK
  → repeat until complete
  → close()
```

### USB Trigger Files (gm_update_engine)
- `gm_reboot_normal` — Exit failed/dealer screen
- `gm_usb_ignore_battery` — Skip battery check
- `gm_usb_auto_install` — Auto-install without prompt

### ProtoKey Recovery Files
- `/data/gmprotokey/trigger/.protokey_recovery`
- `/data/gmprotokey/trigger/.protokey_recovery_validation`
- `/data/gmprotokey/trigger/.protokey_recovery_salt`

### Network Architecture (Corrected)
```
eth0:       192.168.1.100/24   -- SoC (Android) internal Ethernet
vlan4@eth0: 172.16.4.100/24    -- VLAN 4 (Enhanced OnStar/EOCM diagnostics)
vlan5@eth0: 192.168.1.100/24   -- VLAN 5 (AVB/media)
br0:        192.168.5.1/24     -- WiFi bridge (AP mode)
192.168.1.1: NOT the SoC       -- GHS hypervisor or companion VM
```

### OEM Signing Certificate
- **Issuer**: `CN=GPD, OU=GMNA GPD PRODUCTION, O=GENERAL MOTORS LLC`
- **Subject**: `CN=GM Code Signature Server, OU=GM NA INFOTAINMENT, O=GM`
- **RSA-2048 public key extracted** from bootloader `.oemkeys` ELF section (can verify, cannot sign)

### Security DLL (S84.dll)
- 83,456 bytes PE32, Crypto++ 8.x
- Exports: `generate27Response` (RVA 0x59d8), `generateMAC` (RVA 0x58eb)
- PDB: `hz5m7m/Desktop/Work/GlobalB/Service84/AESCMAC`
- AES S-box at offset 0xdbb0, master key NOT in static data (dynamically loaded)
- **Frida capture script ready**: `frida_capture_key.js` hooks both exports + internal Rijndael key schedule at base+0x1600

### CalDef Variables of Interest
- `DEVICE_REGISTRATION_ENABLE_CHECK_OVERRIDE` — Device registration bypass?
- `GIS763_PROGRAMMING_ENABLED` — Programming mode enable flag
- `cal_vin_relearn_en` — VIN relearn enable
- `cal_local_infotainment_cancel_mode` — Cancel mode control
- `cal_suspend_to_ram_en` — S2R enable

---

## Key Catch-22 / Blockers

1. **SBI vs SPS paradox**: EEPROM bypassed → all-0xFF seeds → SPS refuses connection. EEPROM locked → valid seeds → SPS connects but no ADB. Cannot have both simultaneously.
2. **GHS rollback protection**: Y181→Y177 downgrade blocked by GHS at boot verification. GHS maintains own version counter in misc partition (CRC32-only), independent of vbmeta.rollback_index=0.
3. **GSI/DSU blocked**: SELinux dontaudit rule denies gm_update_engine access to GSI metadata, even though q-gsi/r-gsi/s-gsi public keys are present.
4. **Y181 security fix**: GM replaced 4-byte stub with 906-byte full validation. EEPROM bypass no longer triggers permissive SELinux on Y181.
5. **SELinux neverallow on misc**: Shell cannot read/write vda9. neverallow at domain.te:632 blocks all access except 9 exempted domains.
6. **plmanager is not what it seemed**: Power lifecycle manager, not boot_control HAL. Writes only boot failure counter + BCB to misc. GHS VMM manages AB0 rollback directly.
7. **No AOSP update_engine binary exists**: GM replaced it entirely with gm_update_engine. The AOSP `update_engine` SELinux type has full misc rw but no binary runs in that domain.
8. **gm_update_engine can only getattr on misc**: Cannot read or write. Delegates slot management to hal_bootctl. No anti-rollback logic in the binary.
9. **AB0 rollback counter written by GHS VMM only**: Not by any Android-side process. VMM reads/writes AB0 at hypervisor level, before and after Android boots. Android processes write to different regions of misc (BCB, boot failure counter).
10. **Shell is completely walled off**: Cannot binder-call update_engine or gm_update_engine (no allow rules). Can find services but cannot call them.

---

## Ranked Research Vectors

| # | Vector | Risk | Feasibility | Notes |
|---|--------|------|-------------|-------|
| 1 | **A/B metadata manipulation (vda9, CRC32-only)** | Medium | **Low-Medium** | AB0 format decoded (magic "AB0", CRC32). But AB0 is GHS-managed — no Android process writes it. Offline eMMC mod or /dev/ghs/ota-isys exploitation needed. |
| 2 | **EEPROM 0x0A00 investigation (871 firmware refs)** | Low | High | Physical EEPROM access already proven, just need to test values |
| 3 | **SoCReqType in BRR (boot type injection)** | Medium | Medium | Requires understanding VIP→SoC boot reason encoding |
| 4 | **ttyACM1 VIP UART from ADB shell** | Low | High | World-readable, already have shell access |
| 5 | **/dev/ghs/ota-isys exploration** | Medium | Medium | gm_update_engine has ghs_device ioctl + connects to ipc_serverd. This is the Android↔GHS OTA interface. Could it command GHS to modify AB0? REMOTEREFLASH power mode (0x10) exists. |
| 6 | **Frida S84.dll key capture** | Low | Medium | Script ready, needs Windows + DPS + MDI2 |
| 7 | **3x failure bypass exploitation** | Medium | Medium | Intentionally fail SoC boot 3 times to disable hypervisor checks |
| 8 | **MEC boundary testing (254/255/0)** | Low | Medium | Requires controlled MEC increment |
| 9 | **ICUSB state exploration** | Low | Medium | 4 key states, what does "both" enable? |
| 10 | **Y177 hybrid package** | High | Low | Y181 Android + Y177 VIP_APP — manifest signing is the blocker |
| 11 | **Network port exploration (6363, 7000, 49156)** | Low | High | Bound to 0.0.0.0, accessible from shell |
| 12 | **Kernel CVE exploitation** | High | Low | CVE-2024-53104 (USB), CVE-2024-36971 (net UAF) on 4.19.305 |

### Executive Summary: 6 Remaining Realistic Options (Post-Binary Analysis)

**Target:** Y177 downgrade — stubbed security (4-byte no-op) + SELinux PERMISSIVE.
**Blocker:** GHS AB0 rollback counter in misc (vda9) — CRC32-only, but written at hypervisor level only.

After exhaustive binary analysis of plmanager, gm_update_engine, abl-user-cmd_vendor, GHS HOSTOS, and SELinux policy, all software-only paths from ADB shell are blocked. The remaining realistic options are:

**Option 1: Offline eMMC Modification (Most Direct)**

Physically dump Samsung KLMCG4JEUD 64GB eMMC (BGA-153). Find misc partition. AB0 metadata likely at offset 0x800 within misc (standard AOSP bootloader_control offset). Search for "AB0" magic bytes, modify rollback counter, recalculate CRC32 (`poly=0xEDB88320, init=0xFFFFFFFF, final=~crc`), write back.

| Pro | Con |
|---|---|
| Bypasses all software security | Requires BGA-153 adapter + eMMC reader |
| No SELinux, no neverallow | Risk of damaging solder joints |
| CRC32 is trivial to recalculate | 64GB dump is large/slow |
| AB0 format is fully decoded | Must identify misc partition offset within eMMC |

**Option 2: Trigger ELK via VIP Diagnostic Channel**

VIP firmware has explicit ELK reboot support via J6_CDD. Boots via HECI → CSE → ABL (target OBBPELK), bypassing normal misc/BCB boot chain entirely. If ELK is a minimal Linux with no SELinux and direct block device access, it provides unrestricted misc write access.

Trigger: CAN bus diagnostic request to VIP (ECU 0x80) → J6_CDD forwards to GHS lifecycle → HECI to ABL. Requires knowing exact UDS service/DID for ELK reboot request.

**Option 3: Return-to-Dealer Screen → Check ADB/USB Exposure**

**OBSERVED:** The radio was previously caused to fail to boot and entered the return-to-dealer screen. Recovery was done via datawire update package. **ADB/USB was NOT checked during this state.** If the return-to-dealer screen exposes ADB (possibly with relaxed SELinux or different domain), it could provide direct misc write access. This is the easiest to test — just induce the state again and check `adb devices`.

**Option 4: 3x Boot Failure → ELK Escalation**

After 3 consecutive boot failures, GHS disables hypervisor timer + CSM reset. If failures continue to escalate, lifecycle state machine reaches `BootELKSendAblUserCommand` — the last resort.

From ADB shell, boot failures could be induced by:
- Killing critical system processes
- Corrupting files in /data/ that cause boot loops
- Setting powerctl_prop to trigger reboots

If repeated forced crashes → GHS counts failures → exceeds threshold → ELK boot... this is a possible path without CAN or dealer tools.

**Option 5: EEPROM 0x0A00 (The Wildcard)**

871 firmware references — completely unknown function. Physical EEPROM access already proven. Different values can be tested with XGecu. Could control VIP boot mode, IPC behavior, security posture, or update gating. Low risk (swap EEPROM back if nothing changes), high potential upside.

**Option 6: /dev/ghs/ota-isys HostOS Streaming**

The ota-isys interface accepts HostOS (GHS) and ABL firmware writes via chunk/ACK protocol (libpal_swupdate_hostos.so). gm_update_engine has ioctl/read/write/open access. If firmware validation is weak (header check only, no signature in streaming protocol), a modified GHS binary with neutered rollback check could theoretically be streamed.

Risk: GHS HOSTOS is 14.9MB and likely verified by CSE/ABL before executing. Highest-risk option.

**Recommended priority order:** Option 3 (check ADB during return-to-dealer — easiest, already been in this state) → Option 5 (EEPROM 0x0A00 — low risk, high unknown upside) → Option 1 (offline eMMC — most certain but requires hardware) → Option 2/4 (ELK trigger — need UDS command or boot failure escalation) → Option 6 (ota-isys streaming — highest risk).

**Key Catch-22s:**
1. EEPROM SBI bypass (ADB) → 0xFF seeds → SPS refuses
2. Shell cannot touch misc (neverallow)
3. gm_update_engine cannot touch misc (getattr only)
4. AB0 rollback written by GHS VMM, not Android
5. No AOSP update_engine binary exists to use its full misc permissions

**EEPROM offset 0x0A00 (871 firmware references)** is the most-referenced address in the entire VIP binary — an order of magnitude more than any other EEPROM location. Its function is completely undocumented. Testing different values at this offset (with physical EEPROM programmer) could reveal a critical control path.
