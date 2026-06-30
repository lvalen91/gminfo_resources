# GM AAOS SECURITY RESEARCH MASTER REFERENCE

**Platform:** GM Info 3.7 (A11 CSM) | **Android:** 12 API 32 | **Build:** W231E-Y181.3.2-SIHM22B-499.3
**Date:** 2026-01-05 | **Classification:** Security Research

---

## 1. HARDWARE ARCHITECTURE

### 1.1 Dual-Processor System

| Component | Chip | Purpose |
|-----------|------|---------|
| **SoC** | Intel Atom x7-A3960 | Android host, 4-core 2.4GHz, 8GB LPDDR4 (~6GB to guest) |
| **VIP MCU** | Renesas RH850/P1M-E | Security gateway, CAN bus, EEPROM control |
| **GPU** | Intel HD 505 | Gen9, 18 EUs, HW decode H264/HEVC/VP9 |
| **Display** | 13.4" 2400x960 60Hz | Chimei Innolux DD134IA-01B |

### 1.2 Storage & Memory

| Component | Spec | Notes |
|-----------|------|-------|
| eMMC | 64GB | Samsung KLMCG4JEUD |
| RAM | 8GB LPDDR4 (~6GB to guest) | Shared with GPU |
| EEPROM | ST M24C64 8KB | I2C, security flags |
| SPI Flash | IS25LP016D 2MB | **BCM89551 Ethernet-switch firmware** (corrected per `hardware/teardown.md`, dump-confirmed — NOT logs/backup). Separate 8MB IS25WP064A = Apollo Lake IFWI/TXE boot flash. |

### 1.3 Connectivity

| Interface | Details |
|-----------|---------|
| Ethernet | Intel **I210 (WGI210CL)**, 1Gbps, VLANs 4/5 (physical part per `hardware/teardown.md`; "I211" was an unverified near-twin reading) |
| WiFi | Broadcom BCM, 802.11ac dual-band |
| Bluetooth | 5.0, HFP/A2DP/AVRCP/PBAP/MAP |
| CAN Bus | Via VIP MCU (RH850) |

---

## 2. BOOT CHAIN & SECURITY

### 2.1 Boot Sequence

```
Intel CSE (hardware root) → Intel ABL → GHS INTEGRITY → Android
```

| Stage | Component | Signing | Rollback Protection |
|-------|-----------|---------|---------------------|
| 1 | Intel CSE | Fused keys | Hardware |
| 2 | SOC_BOOT (23) | **NONE** | None |
| 3 | SOC_ABL (72) | **NONE** | Intel CSE validates |
| 4 | SOC_HOSTOS/GHS | TSS signed | GHS enforced |
| 5 | Android (vbmeta) | RSA-4096/SHA256 | AVB + GHS |

### 2.2 GHS INTEGRITY Hypervisor

**Version:** 2020.18.19 | **Core:** 23739 | **Modules:** 11500

- Runs BELOW Android with direct hardware access
- Validates vbmeta at boot, enforces rollback protection
- Controls camera feed (works during Android reboot)
- Independent TCP/IP stack (kethernet)
- VMM can read/write guest (Android) memory

**Key GHS Capabilities:**
- `ReadGuestMemory` / `WriteGuestMemory` - Direct Android RAM access
- `KETH_WritePacket` / `KETH_ReadPacket` - Independent networking
- Intel IPU4 direct camera access
- Intel HECI communication (Management Engine)

### 2.3 A/B Partition Layout

| Partition | Device | Size | Purpose |
|-----------|--------|------|---------|
| ghs_isys_a/b | vda1/2 | 16MB | GHS hypervisor |
| ghs_storage | vda3 | 128KB | GHS persistent |
| ghs_ivi_a/b | vda4/5 | 192MB | GHS IVI data |
| boot_a/b | vda7/8 | 128MB | Android boot |
| misc | vda9 | 1MB | A/B metadata, rollback index |
| vbmeta_a/b | vda10/11 | 64KB | AVB metadata |
| super | vda13 | 8.6GB | system/vendor/product (corrected: was "vda21" — vda21 is teedata; super=vda13 per teardown.md/AOSP_REPLACEMENT/BOOT_CHAIN + the live enum) |

---

## 3. MODULE SIGNING STATUS

### 3.1 Unsigned Modules (Flashable via DPS)

| Module | ID | Component | Notes |
|--------|-----|-----------|-------|
| SOC_BOOT | 23 | Intel bootloader | No signature |
| VIP_BOOT | 71 | RH850 bootloader | Internal Harman checksum |
| SOC_ABL | 72 | Android bootloader | Intel CSE validates internally |
| SOC_UTILS | 24 | Utilities | No signature |
| SXM | 28 | SiriusXM | No signature |
| GPS | 29 | GPS module | No signature |
| TUNER | 51 | Radio tuner | No signature |
| ETH_SWITCH | 52 | Ethernet config | No signature |
| SOC_ACPIO | 55 | ACPI tables | No signature |
| SOC_VBMETA | 56 | AVB metadata | No signature (breaks AVB) |
| SOC_PRODUCT | 57 | Product partition | No signature |

### 3.2 Signed Modules (Require GM TSS Keys)

| Module | ID | Sign Type |
|--------|-----|-----------|
| SOC_HOSTOS | 21 | TSS |
| VIP_APP | 70 | TSS |
| All Android partitions | - | AVB |

---

## 4. VIP & EEPROM SECURITY

### 4.1 EEPROM Security Flags

| Address | Purpose | Locked Value | Bypass Value | CRC Protected |
|---------|---------|--------------|--------------|---------------|
| 0x0440 | ADB Security #1 | C3 00 C3 | 5A FF 5A | **NO** |
| 0x0A80 | ADB Security #2 | C3 00 C3 | 5A FF 5A | **NO** |
| 0x0B40 | Debug Mode | 69 00 | 69 01 | **NO** |

**Key Finding:** Security flags are OUTSIDE CRC-protected regions. CRC NOT enforced at boot time (tested: VIN=0xFF, module still boots).

### 4.2 Bypass Mechanism (Y177 Only)

```
EEPROM (0x0440=5AFF5A) → VIP reads → Security func @ 0xb67d0 → IPC to SoC → SELinux mode
```

**Y177:** Security function STUBBED (4 bytes, always returns 0)
**Y181:** Security function IMPLEMENTED (906 bytes, validates state)

### 4.3 VIP-to-SoC Communication

| Channel | Purpose |
|---------|---------|
| 0 | Core IPC control |
| 1-2 | PROTOKEY / Security seed |
| 3-5 | J6_CDD Diagnostics |
| 6-8 | Power Level Control |
| 9-12 | Calibration updates |
| 13-20 | System state / Extension |

**Seed Response:**
- `0xFF` (32 bytes) = Bypass mode, ADB accessible
- `ECUID + Challenge` = Secured, requires GM Secure Client

### 4.4 VIP Calibrations from EEPROM

| Calibration | Default | Purpose |
|-------------|---------|---------|
| cal_suspend_to_ram_en | 1 | S2R enabled |
| cal_background_sleep_timeout_sec | 10 | Sleep timeout |
| cal_startup_fault_timeout_sec | 15 | Startup fault |
| cal_shutdown_animation_failsafe | 15 | Shutdown failsafe |
| cal_vin_relearn_en | 1 | VIN relearn |

---

## 5. FIRMWARE VERSIONS & DIFFERENCES

### 5.1 Y177 vs Y181 Comparison

| Property | Y177 | Y181 |
|----------|------|------|
| VIP_APP File | 86283151 | 86331656 |
| Build Date | Feb 28, 2025 | Jun 19, 2025 |
| Functions | 10,340 | 10,350 |
| Security @ 0xb67d0 | **4 bytes (stubbed)** | **906 bytes (full)** |
| EEPROM Bypass | Works | Works |
| SELinux on bypass | Permissive | Enforcing |

### 5.2 GM Security Response (Post-Disclosure)

**Layer 1:** VIP firmware fix (0xb67d0 implementation)
**Layer 2:** Calibration file 85783460 resets security flags
**Layer 3:** USB updates reset EEPROM

---

## 6. UPDATE & DOWNGRADE PROTECTION

### 6.1 Update Process

```
USB/OTA → gm_update_engine → Red Bend UA → Partition write → GHS verification → Boot
```

**Manifest Flag:** `version check disabled` only affects write phase, NOT GHS verification.

### 6.2 GHS Rollback Protection

| Scenario | Result |
|----------|--------|
| Y181 → Y181 | SUCCESS (reinstall allowed) |
| Y177 → Y181 | SUCCESS (upgrade allowed) |
| Y181 → Y177 | **BLOCKED** by GHS |

**Error:** `VMM: ERROR: rollback index is too old: %lu in image, but stored is %lu`

**Storage:** Rollback index in misc partition (vda9), CRC-validated by GHS.

### 6.3 Recovery Triggers

| USB File | Effect |
|----------|--------|
| gm_reboot_normal | Exit "Update Failed" screen |
| gm_usb_ignore_battery | Skip battery check |

---

## 7. NETWORK & REMOTE ACCESS

### 7.1 Internal Network (VLANs)

**VLAN 5 (192.168.1.x):**
- .100 CSM_ETH (Radio)
- .101 ADB
- .107 CGM Host (Telematics)
- .112 CGM_ETH

**VLAN 4 (172.16.4.x):**
- .12/.13/.15 EOCM (Enhanced OnStar)

### 7.2 Remote Access Paths

| Path | Components | Works w/o Radio |
|------|------------|-----------------|
| Telematics | LTE → CGM → CAN → ECUs | YES |
| Infotainment | WiFi/LTE → Android → VIP → CAN | NO |

**Critical:** OnStar/Telematics operates INDEPENDENTLY of radio.

### 7.3 GM Cloud Endpoints

| Server | Port | Purpose |
|--------|------|---------|
| vtmpub.oboservices.mobi | 443 | OTA/OMA-DM |
| vehicle.api.gm.com | 443 | Device registration |
| vehicle.api.gm.com | 20445 | Security event logging |
| vehicle.api.gm.com | 20647 | Account auth |

### 7.4 Key Services

| Service | Binary | Capabilities |
|---------|--------|--------------|
| gmConnectionService | com.gm.domain.server.delayed | REBOOT, SECURE_SETTINGS, update trigger |
| gm_update_engine | /vendor/bin/hw/gm_update_engine | Root, block device write, rb_ua exec |
| Red Bend UA | /vendor/bin/rb_ua | Mandatory updates, self-update |

---

## 8. I2C ACCESS ANALYSIS

### 8.1 Device Permissions

| Device | Permissions | Owner | Access |
|--------|-------------|-------|--------|
| /dev/i2c-0 | crw-rw-rw- | root | **WORLD** |
| /dev/i2c-1 | crw-rw-rw- | root | **WORLD** |
| /dev/i2c-4-6 | crw------- | root | Root only |

**Used For Apple MFi?**

---

## 9. PRIVACY CAPABILITIES (GHS Level)

### 9.1 Technical Capabilities

| Capability | Evidence | Risk |
|------------|----------|------|
| Camera capture | Intel IPU4 driver, StartCapture | CRITICAL |
| Independent networking | kethernet TCP/IP, KETH_WritePacket | CRITICAL |
| Guest memory access | ReadGuestMemory, WriteGuestMemory | CRITICAL |
| Audio capture | gm_audio_passthru, Audio DSP | HIGH |
| Screen capture | ConnToVMM_Display, GPU connections | HIGH |
| Covert communication | Intel HECI, IPC channels | HIGH |

### 9.2 Data Exfiltration Path

```
Camera/Audio/Screen → GHS Buffer → KETH_WritePacket → WiFi/Ethernet/HECI → Remote
```

**Note:** Technical capability ≠ active surveillance. No evidence of exfiltration, but capability exists.

---

## 10. DPS CAPABILITIES

### 10.1 What DPS CAN Do

- Read DIDs: $F090, $F098, $F099, $F0B4, $F0F0, $F0F3 (ECUID)
- Flash UNSIGNED modules (23, 24, 28, 29, 51, 52, 55, 56, 57, 71, 72)
- Clear/modify calibration via DID writes
- Execute routine controls ($31)
- Request security seed ($27)

### 10.2 What DPS CANNOT Do

- Write EEPROM security addresses (0x0440, 0x0A80)
- Flash TSS-signed modules without GM keys
- Issue SBAT tickets
- Access fastboot/recovery mode
- Bypass AVB protection

---

## 11. KEY FINDINGS SUMMARY

### 11.1 Security Vulnerabilities

1. **VIP_BOOT (71) and SOC_ABL (72) are UNSIGNED** - flashable without GM keys
2. **EEPROM security flags outside CRC protection** - modifiable without recalculation
3. **CRC NOT enforced at boot** - tested with invalid VIN
5. **Y177 security function stubbed** - Possibly changed SELinux or AVB

### 11.4 Critical GHS / Build Findings (2026-06-29)

- **GHS HOSTOS (85098662) is byte-for-byte identical between Y177 and Y181** — the misc/vda9 rollback counter is the ONLY discriminator between builds.
- **'VMM: Warning: A/B metatdata CRC failure!' (ghs_str.txt:43973) is a WARNING string, not an abort** — CRC failure in misc may be non-fatal. Untested.
- **RSA-1024 private key found in ghs_integrity.elf at offset 12924442** — only private key in the entire corpus; function unknown. See research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md.

### 11.5 Critical Untried Paths (2026-06-29)

- **CRITICAL UNTRIED:** `/data/vendor/gm/security/.validation` deletion → TOFU PAL key re-provisioning (INVENTORY.md bypass #3)
- **CRITICAL UNTRIED:** `androidboot.bootreason=warm` → gm_protokey validation skip (INVENTORY.md bypass #2)

See research/UNTRIED_ATTACK_VECTORS.md for full ranked list.

### 11.2 Security Mitigations

1. **GHS rollback protection** - blocks downgrades at boot verification
2. **Y181 security function implemented** - Fixed VIP Stub
3. **Calibration file security reset** - defense-in-depth
4. **TSS signing for critical modules** - SOC_HOSTOS, VIP_APP signed
5. **Intel CSE hardware root** - fused keys, hardware protection

### 11.3 OEM Key (Extracted)

```
RSA-2048 Public Key (for signature VERIFICATION only)
Modulus: d8:04:af:e3:d3:84:6c:7e:0d:89:3d:c2:8c:d3:12:55...
Exponent: 65537 (0x10001)
Source: SOC Bootloader .oemkeys section
```

Private key NOT extractable (GM infrastructure).

---

## 12. RESEARCH PRIORITIES

| Priority | Task | Status |
|----------|------|--------|
| 1 | I2C EEPROM mapping (which bus?) | Research needed |
| 2 | Harman checksum RE (VIP_BOOT) | Research needed |
| 3 | Y177 downgrade via hybrid package | Blocked by GHS |
| 4 | misc partition A/B metadata structure | Research needed |
| 5 | Factory reset rollback index impact | Unknown |
| 6 | /data/vendor/gm/security/.validation deletion → TOFU re-provisioning | **UNTRIED** (bypass #3) |
| 7 | androidboot.bootreason=warm → gm_protokey skip | **UNTRIED** (bypass #2) |
| 8 | misc/vda9 rollback counter zeroing (GHS HOSTOS identical Y177=Y181) | **UNTRIED** — highest downgrade leverage |
| 9 | Gordon Peak / Intel Celadon open-source axis | See GORDON_PEAK_CELADON_INTELLIGENCE.md |

---

## 13. FILE QUICK REFERENCE

### 13.1 Key Binaries

| File | Component | Location |
|------|-----------|----------|
| 85098662 | SOC_HOSTOS (GHS) | update_packages/ |
| 86331656 | VIP_APP Y181 | update_packages/Y181/ |
| 86283151 | VIP_APP Y177 | update_packages/Y177/ |
| 85056831 | VIP_BOOT | update_packages/ |
| 85738845 | SOC Bootloader | update_packages/ |
| 86331644 | vbmeta Y181 | update_packages/Y181/ |

### 13.2 Key Logs

| File | Content |
|------|---------|
| A11_CSM_x80.Txt | DPS log - bypassed state |
| Y177update_CSM.Txt | DPS log - normal state |
| VIP_log_*.txt | VIP UART logs |

### 13.3 EEPROM Dumps

| File | State |
|------|-------|
| ADB_enabled.bin | Bypassed (0x0440=5AFF5A) |
| Y181/original.bin | Locked (0x0440=C300C3) |

### 13.4 Research Documents (added 2026-06-29)

| File | Content |
|------|---------|
| research/GORDON_PEAK_CELADON_INTELLIGENCE.md | Gordon Peak MRB and Intel Project Celadon intelligence: cloneable repos, what's NDA-gated, research axis mapping |
| research/session_logs/RESEARCH_STATE_MAP_JUN2026.md | Complete research state map as of Jun 2026: timeline, what was tried, key discoveries, dead ends, where research stopped |
| research/UNTRIED_ATTACK_VECTORS.md | Prioritized list of attack vectors identified but not yet executed; ranked by impact on Y177 downgrade goal |
| research/security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md | RSA-1024 private key found in ghs_integrity.elf at offset 12924442; only private key in entire corpus; function unknown |
| platform/intel_apl_external_resources.md | Index of all external Intel APL resources: cloned repos in ~/Downloads/github/, PDFs, patents, NDA-gated items |

---

## 14. TOOLS & COMMANDS

### 14.1 Analysis Tools

```bash
# Ghidra - RH850 processor module for VIP firmware
# radare2 - x86 analysis for GHS/Android
# avbtool - vbmeta parsing
# minipro/XGecu - EEPROM programming
```

### 14.2 ADB Commands (When Available)

```bash
# System info
getprop | grep -E "ro\.(build|product|gm)\."
dumpsys car_service

# Partition info
ls -la /dev/block/by-name/
cat /proc/partitions

# I2C scan (if tools available)
i2cdetect -y 0
i2cdetect -y 1
```

---

## 15. LEGAL NOTICE

This document is for **security research and educational purposes only**.

- Technical capability ≠ active surveillance
- Analysis based on static firmware examination
- Modification of vehicle systems may void warranty
- Consult legal counsel for specific advice
- Right-to-repair laws vary by jurisdiction

---

**Document Version:** 1.0
**Consolidated from:** 19 source documents (~526KB → ~20KB)
**Analysis Method:** Static binary analysis (radare2, Ghidra, strings)
