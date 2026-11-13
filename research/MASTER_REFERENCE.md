# GM Info 3.7 research index

**Main consolidated investigation:**
[GHS boot, recovery, MEC and update evidence](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md).

Canonical repository path:
`gminfo_resources/research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`.

The consolidated source owns the combined Y181B findings, addresses,
fingerprints, corrections and unresolved questions. This index routes other
subjects to their owners instead of maintaining another copy of their facts.

| Subject | Owning document |
|---|---|
| Y181B USB exports, archive hashes, capture comparison and chronology limits | [Consolidated source §0.2–§0.3](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#02-y181b-recovery-usb-capture-verified-2026-11-12) |
| Measured Y181B recovery E820 map and grant/visibility limits | [GHS inventory §7A.3](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md#7a3-guest-memory) |
| Exported Y181B vehicle calibration baseline | [Vehicle configuration](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12) |
| Recovery/dealer modes, fastbootd, ELK IPC/HECI/ACPI and root/debug gates | [Consolidated source §2.3](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#23-special-boot-modes) |
| MEC, certificate authentication, readings and registration/reset limits | [Consolidated source §2.3.7](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration) |
| Recovery options and dealer wipe/Red Bend/formatter | [Consolidated source §4.2](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#42-internal-recovery-argument-file-and-accepted-options) |
| Encoded USB markers and log capture | [Consolidated source §4.5](GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#45-known-usb-trigger-files) |
| GHS tasks, device grants, VM configuration and privacy | [GHS inventory](GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md) |
| HostOS section/file layout | [HostOS file map](GHS_FILE_MAP_85098662.md) |
| EEPROM layout, VIP code and calibration boundaries | [EEPROM audit](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md) |
| EEPROM hardware workflow | [EEPROM guide](../eeprom/README.md) |
| Hardware components and connectors | [Teardown](../hardware/teardown.md), [connectors](../hardware/connectors.md) |
| Platform boot-chain overview | [Boot chain](../platform/boot_chain.md) |
| Security architecture, signing and Boot Guard | [Security architecture](../platform/security.md) |
| AAOS updater/Binder stack | [OTA stack](../platform/ota_update_stack.md) |
| Module-programming responsibilities | [Programming roles](../platform/ota_programming_roles.md) |
| Firmware-version inventory | [Firmware versions](../platform/firmware_versions.md) |
| Downgrade observations and historical tests | [Downgrade analysis](GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt) |
| Update-process observations | [Update-process analysis](UPDATE_PROCESS_ANALYSIS.txt) |
| Vehicle network and diagnostic transport | [Vehicle network](../platform/vehicle_network.md), [Ethernet UDS](../diagnostics/ethernet_uds_diagnosticsd.md) |
| Guest/host RPC research hypotheses | [RPC research](RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md) |
| External Intel/Celadon resources | [External resources](../platform/intel_apl_external_resources.md), [Celadon research](GORDON_PEAK_CELADON_INTELLIGENCE.md) |
| Unverified research leads | [Untried vectors](UNTRIED_ATTACK_VECTORS.md) |

Paths beginning `gminfo_resources/` name the repository root and remain
portable across machines. Relative Markdown links resolve within the checkout.
External firmware evidence uses the `GM_RESEARCH/` role defined by the
consolidated source; no Mac account or mount path is required.
