# PATH_MAP: old path to new path (restructure of 2026-11-21)

Generated from the move manifest; every moved file is listed in the second table. File names did not change, so a citation by bare filename (for example `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md section 5.2`) is still valid; only the folder part moved.

## Directory-level moves

| Old | New |
|---|---|
| `0xdf0ea5, 0xdf104f` | `evidence/scratch/` |
| `platform/platform_originals_2026-11-18.zip, research/research_originals_2026-11-18.zip` | `evidence/archives/` |
| `enumeration/ (except scripts/)` | `evidence/enumeration/` |
| `enumeration/scripts/` | `tools/enumeration/` |
| `research/decompiled/` | `evidence/decompiled/` |
| `research/reports/` | `evidence/reports/` |
| `research/session_logs/` | `evidence/session-logs/` |
| `diagnostics/dps/` | `evidence/dps-logs/` |
| `research/scripts/ghidra_rh850/{85759599_rh850,85759599_rh850_backup_broken,hostos_x86,vipboot_rh850}/ (git-ignored)` | `evidence/ghidra-projects/` |
| `research/scripts/mdi2_client/` | `tools/analysis-scripts/mdi2_doip/` |
| `research/scripts/ (all other tracked files)` | `tools/analysis-scripts/` |
| `research/tools/` | `tools/bench/` |
| `mdi2_client/` | `tools/mdi2_client/` |
| `research/fuzz/` | `research/security/fuzz/` |
| `research/{calibration_prototypes,canbus_reset,type4_radio_info}/` | `research/eeprom-calibration/<same name>/` |

Research documents moved into topic subfolders: `research/<doc>` becomes `research/<topic>/<doc>` with topics `boot-update-recovery` (11 docs), `security` (4), `eeprom-calibration` (9), `mdi2-bench-sessions` (6), `rights-and-roadmap` (3), `provenance` (2). `research/README.md` stays in place as the hub.

## Per-file moves (1082 files)

| Old | New |
|---|---|
| `0xdf0ea5` | `evidence/scratch/0xdf0ea5` |
| `0xdf104f` | `evidence/scratch/0xdf104f` |
| `diagnostics/dps/A11_CSM.ProgramLog.Txt` | `evidence/dps-logs/A11_CSM.ProgramLog.Txt` |
| `diagnostics/dps/A11_CSM_x80.Txt` | `evidence/dps-logs/A11_CSM_x80.Txt` |
| `diagnostics/dps/Y177update_CSM.Txt` | `evidence/dps-logs/Y177update_CSM.Txt` |
| `enumeration/README.md` | `evidence/enumeration/README.md` |
| `enumeration/VIP_log_2B.174.4.1_10JUL24.txt` | `evidence/enumeration/VIP_log_2B.174.4.1_10JUL24.txt` |
| `enumeration/Y175/Y175_VIP.log` | `evidence/enumeration/Y175/Y175_VIP.log` |
| `enumeration/Y175/enumeration_report.txt` | `evidence/enumeration/Y175/enumeration_report.txt` |
| `enumeration/Y175/pull_failures.txt` | `evidence/enumeration/Y175/pull_failures.txt` |
| `enumeration/Y175/pulled_files/plat_sepolicy.cil` | `evidence/enumeration/Y175/pulled_files/plat_sepolicy.cil` |
| `enumeration/Y175/pulled_files/vendor_sepolicy.cil` | `evidence/enumeration/Y175/pulled_files/vendor_sepolicy.cil` |
| `enumeration/Y175/raw/all_properties.txt` | `evidence/enumeration/Y175/raw/all_properties.txt` |
| `enumeration/Y175/raw/binder_services.txt` | `evidence/enumeration/Y175/raw/binder_services.txt` |
| `enumeration/Y175/raw/car_service.txt` | `evidence/enumeration/Y175/raw/car_service.txt` |
| `enumeration/Y175/raw/cmdline.txt` | `evidence/enumeration/Y175/raw/cmdline.txt` |
| `enumeration/Y175/raw/cpuinfo.txt` | `evidence/enumeration/Y175/raw/cpuinfo.txt` |
| `enumeration/Y175/raw/current_user.txt` | `evidence/enumeration/Y175/raw/current_user.txt` |
| `enumeration/Y175/raw/debug_props.txt` | `evidence/enumeration/Y175/raw/debug_props.txt` |
| `enumeration/Y175/raw/disk_usage.txt` | `evidence/enumeration/Y175/raw/disk_usage.txt` |
| `enumeration/Y175/raw/display_info.txt` | `evidence/enumeration/Y175/raw/display_info.txt` |
| `enumeration/Y175/raw/dmesg.txt` | `evidence/enumeration/Y175/raw/dmesg.txt` |
| `enumeration/Y175/raw/fingerprint.txt` | `evidence/enumeration/Y175/raw/fingerprint.txt` |
| `enumeration/Y175/raw/fstab.txt` | `evidence/enumeration/Y175/raw/fstab.txt` |
| `enumeration/Y175/raw/ghs_props.txt` | `evidence/enumeration/Y175/raw/ghs_props.txt` |
| `enumeration/Y175/raw/gm_props.txt` | `evidence/enumeration/Y175/raw/gm_props.txt` |
| `enumeration/Y175/raw/i2c_devices.txt` | `evidence/enumeration/Y175/raw/i2c_devices.txt` |
| `enumeration/Y175/raw/init_rc_files.txt` | `evidence/enumeration/Y175/raw/init_rc_files.txt` |
| `enumeration/Y175/raw/init_services.txt` | `evidence/enumeration/Y175/raw/init_services.txt` |
| `enumeration/Y175/raw/kernel_config.txt` | `evidence/enumeration/Y175/raw/kernel_config.txt` |
| `enumeration/Y175/raw/kernel_version.txt` | `evidence/enumeration/Y175/raw/kernel_version.txt` |
| `enumeration/Y175/raw/logcat.txt` | `evidence/enumeration/Y175/raw/logcat.txt` |
| `enumeration/Y175/raw/meminfo.txt` | `evidence/enumeration/Y175/raw/meminfo.txt` |
| `enumeration/Y175/raw/mounts.txt` | `evidence/enumeration/Y175/raw/mounts.txt` |
| `enumeration/Y175/raw/network_interfaces.txt` | `evidence/enumeration/Y175/raw/network_interfaces.txt` |
| `enumeration/Y175/raw/open_ports.txt` | `evidence/enumeration/Y175/raw/open_ports.txt` |
| `enumeration/Y175/raw/partitions.txt` | `evidence/enumeration/Y175/raw/partitions.txt` |
| `enumeration/Y175/raw/proc_partitions.txt` | `evidence/enumeration/Y175/raw/proc_partitions.txt` |
| `enumeration/Y175/raw/processes.txt` | `evidence/enumeration/Y175/raw/processes.txt` |
| `enumeration/Y175/raw/rollback_index.txt` | `evidence/enumeration/Y175/raw/rollback_index.txt` |
| `enumeration/Y175/raw/selinux_status.txt` | `evidence/enumeration/Y175/raw/selinux_status.txt` |
| `enumeration/Y175/raw/serial.txt` | `evidence/enumeration/Y175/raw/serial.txt` |
| `enumeration/Y175/raw/service_list.txt` | `evidence/enumeration/Y175/raw/service_list.txt` |
| `enumeration/Y175/raw/system_bin.txt` | `evidence/enumeration/Y175/raw/system_bin.txt` |
| `enumeration/Y175/raw/system_root.txt` | `evidence/enumeration/Y175/raw/system_root.txt` |
| `enumeration/Y175/raw/tty_devices.txt` | `evidence/enumeration/Y175/raw/tty_devices.txt` |
| `enumeration/Y175/raw/uart_devices.txt` | `evidence/enumeration/Y175/raw/uart_devices.txt` |
| `enumeration/Y175/raw/usb_devices.txt` | `evidence/enumeration/Y175/raw/usb_devices.txt` |
| `enumeration/Y175/raw/vendor_bin.txt` | `evidence/enumeration/Y175/raw/vendor_bin.txt` |
| `enumeration/Y175/raw/vendor_root.txt` | `evidence/enumeration/Y175/raw/vendor_root.txt` |
| `enumeration/Y175/raw/world_writable.txt` | `evidence/enumeration/Y175/raw/world_writable.txt` |
| `enumeration/Y175/rollback_assessment.txt` | `evidence/enumeration/Y175/rollback_assessment.txt` |
| `enumeration/Y175/security_summary.txt` | `evidence/enumeration/Y175/security_summary.txt` |
| `enumeration/Y175/uart_summary.txt` | `evidence/enumeration/Y175/uart_summary.txt` |
| `enumeration/Y177/README.md` | `evidence/enumeration/Y177/README.md` |
| `enumeration/Y177/pulled_files/build.prop` | `evidence/enumeration/Y177/pulled_files/build.prop` |
| `enumeration/Y177/pulled_files/plat_pub_versioned.cil` | `evidence/enumeration/Y177/pulled_files/plat_pub_versioned.cil` |
| `enumeration/Y177/pulled_files/plat_sepolicy.cil` | `evidence/enumeration/Y177/pulled_files/plat_sepolicy.cil` |
| `enumeration/Y177/pulled_files/product_sepolicy.cil` | `evidence/enumeration/Y177/pulled_files/product_sepolicy.cil` |
| `enumeration/Y177/pulled_files/sepolicy` | `evidence/enumeration/Y177/pulled_files/sepolicy` |
| `enumeration/Y177/pulled_files/vendor_sepolicy.cil` | `evidence/enumeration/Y177/pulled_files/vendor_sepolicy.cil` |
| `enumeration/Y181/apr2026/enumeration_report.txt` | `evidence/enumeration/Y181/apr2026/enumeration_report.txt` |
| `enumeration/Y181/apr2026/ghs_attack_surface.txt` | `evidence/enumeration/Y181/apr2026/ghs_attack_surface.txt` |
| `enumeration/Y181/apr2026/network_scan.txt` | `evidence/enumeration/Y181/apr2026/network_scan.txt` |
| `enumeration/Y181/apr2026/pulled_files/plat_sepolicy.cil` | `evidence/enumeration/Y181/apr2026/pulled_files/plat_sepolicy.cil` |
| `enumeration/Y181/apr2026/pulled_files/vendor_sepolicy.cil` | `evidence/enumeration/Y181/apr2026/pulled_files/vendor_sepolicy.cil` |
| `enumeration/Y181/apr2026/raw/accounts.txt` | `evidence/enumeration/Y181/apr2026/raw/accounts.txt` |
| `enumeration/Y181/apr2026/raw/all_properties.txt` | `evidence/enumeration/Y181/apr2026/raw/all_properties.txt` |
| `enumeration/Y181/apr2026/raw/arp_table.txt` | `evidence/enumeration/Y181/apr2026/raw/arp_table.txt` |
| `enumeration/Y181/apr2026/raw/binder_services.txt` | `evidence/enumeration/Y181/apr2026/raw/binder_services.txt` |
| `enumeration/Y181/apr2026/raw/bluetooth.txt` | `evidence/enumeration/Y181/apr2026/raw/bluetooth.txt` |
| `enumeration/Y181/apr2026/raw/car_service.txt` | `evidence/enumeration/Y181/apr2026/raw/car_service.txt` |
| `enumeration/Y181/apr2026/raw/cmdline.txt` | `evidence/enumeration/Y181/apr2026/raw/cmdline.txt` |
| `enumeration/Y181/apr2026/raw/connectivity.txt` | `evidence/enumeration/Y181/apr2026/raw/connectivity.txt` |
| `enumeration/Y181/apr2026/raw/cpuinfo.txt` | `evidence/enumeration/Y181/apr2026/raw/cpuinfo.txt` |
| `enumeration/Y181/apr2026/raw/current_user.txt` | `evidence/enumeration/Y181/apr2026/raw/current_user.txt` |
| `enumeration/Y181/apr2026/raw/debug_props.txt` | `evidence/enumeration/Y181/apr2026/raw/debug_props.txt` |
| `enumeration/Y181/apr2026/raw/disk_usage.txt` | `evidence/enumeration/Y181/apr2026/raw/disk_usage.txt` |
| `enumeration/Y181/apr2026/raw/display_info.txt` | `evidence/enumeration/Y181/apr2026/raw/display_info.txt` |
| `enumeration/Y181/apr2026/raw/dmesg.txt` | `evidence/enumeration/Y181/apr2026/raw/dmesg.txt` |
| `enumeration/Y181/apr2026/raw/fingerprint.txt` | `evidence/enumeration/Y181/apr2026/raw/fingerprint.txt` |
| `enumeration/Y181/apr2026/raw/fstab.txt` | `evidence/enumeration/Y181/apr2026/raw/fstab.txt` |
| `enumeration/Y181/apr2026/raw/ghs_props.txt` | `evidence/enumeration/Y181/apr2026/raw/ghs_props.txt` |
| `enumeration/Y181/apr2026/raw/gm_props.txt` | `evidence/enumeration/Y181/apr2026/raw/gm_props.txt` |
| `enumeration/Y181/apr2026/raw/gm_update_service.txt` | `evidence/enumeration/Y181/apr2026/raw/gm_update_service.txt` |
| `enumeration/Y181/apr2026/raw/gpio.txt` | `evidence/enumeration/Y181/apr2026/raw/gpio.txt` |
| `enumeration/Y181/apr2026/raw/hal_list.txt` | `evidence/enumeration/Y181/apr2026/raw/hal_list.txt` |
| `enumeration/Y181/apr2026/raw/i2c_devices.txt` | `evidence/enumeration/Y181/apr2026/raw/i2c_devices.txt` |
| `enumeration/Y181/apr2026/raw/init_rc_files.txt` | `evidence/enumeration/Y181/apr2026/raw/init_rc_files.txt` |
| `enumeration/Y181/apr2026/raw/init_services.txt` | `evidence/enumeration/Y181/apr2026/raw/init_services.txt` |
| `enumeration/Y181/apr2026/raw/ip_addr.txt` | `evidence/enumeration/Y181/apr2026/raw/ip_addr.txt` |
| `enumeration/Y181/apr2026/raw/ip_route.txt` | `evidence/enumeration/Y181/apr2026/raw/ip_route.txt` |
| `enumeration/Y181/apr2026/raw/kernel_config.txt` | `evidence/enumeration/Y181/apr2026/raw/kernel_config.txt` |
| `enumeration/Y181/apr2026/raw/kernel_modules.txt` | `evidence/enumeration/Y181/apr2026/raw/kernel_modules.txt` |
| `enumeration/Y181/apr2026/raw/kernel_version.txt` | `evidence/enumeration/Y181/apr2026/raw/kernel_version.txt` |
| `enumeration/Y181/apr2026/raw/logcat.txt` | `evidence/enumeration/Y181/apr2026/raw/logcat.txt` |
| `enumeration/Y181/apr2026/raw/meminfo.txt` | `evidence/enumeration/Y181/apr2026/raw/meminfo.txt` |
| `enumeration/Y181/apr2026/raw/mounts.txt` | `evidence/enumeration/Y181/apr2026/raw/mounts.txt` |
| `enumeration/Y181/apr2026/raw/network_interfaces.txt` | `evidence/enumeration/Y181/apr2026/raw/network_interfaces.txt` |
| `enumeration/Y181/apr2026/raw/open_ports.txt` | `evidence/enumeration/Y181/apr2026/raw/open_ports.txt` |
| `enumeration/Y181/apr2026/raw/packages.txt` | `evidence/enumeration/Y181/apr2026/raw/packages.txt` |
| `enumeration/Y181/apr2026/raw/partitions.txt` | `evidence/enumeration/Y181/apr2026/raw/partitions.txt` |
| `enumeration/Y181/apr2026/raw/proc_partitions.txt` | `evidence/enumeration/Y181/apr2026/raw/proc_partitions.txt` |
| `enumeration/Y181/apr2026/raw/processes.txt` | `evidence/enumeration/Y181/apr2026/raw/processes.txt` |
| `enumeration/Y181/apr2026/raw/selinux_status.txt` | `evidence/enumeration/Y181/apr2026/raw/selinux_status.txt` |
| `enumeration/Y181/apr2026/raw/serial.txt` | `evidence/enumeration/Y181/apr2026/raw/serial.txt` |
| `enumeration/Y181/apr2026/raw/service_list.txt` | `evidence/enumeration/Y181/apr2026/raw/service_list.txt` |
| `enumeration/Y181/apr2026/raw/settings_global.txt` | `evidence/enumeration/Y181/apr2026/raw/settings_global.txt` |
| `enumeration/Y181/apr2026/raw/settings_secure.txt` | `evidence/enumeration/Y181/apr2026/raw/settings_secure.txt` |
| `enumeration/Y181/apr2026/raw/settings_system.txt` | `evidence/enumeration/Y181/apr2026/raw/settings_system.txt` |
| `enumeration/Y181/apr2026/raw/system_bin.txt` | `evidence/enumeration/Y181/apr2026/raw/system_bin.txt` |
| `enumeration/Y181/apr2026/raw/system_root.txt` | `evidence/enumeration/Y181/apr2026/raw/system_root.txt` |
| `enumeration/Y181/apr2026/raw/tty_devices.txt` | `evidence/enumeration/Y181/apr2026/raw/tty_devices.txt` |
| `enumeration/Y181/apr2026/raw/uart_devices.txt` | `evidence/enumeration/Y181/apr2026/raw/uart_devices.txt` |
| `enumeration/Y181/apr2026/raw/usb_devices.txt` | `evidence/enumeration/Y181/apr2026/raw/usb_devices.txt` |
| `enumeration/Y181/apr2026/raw/vehicle_properties.txt` | `evidence/enumeration/Y181/apr2026/raw/vehicle_properties.txt` |
| `enumeration/Y181/apr2026/raw/vendor_bin.txt` | `evidence/enumeration/Y181/apr2026/raw/vendor_bin.txt` |
| `enumeration/Y181/apr2026/raw/vendor_root.txt` | `evidence/enumeration/Y181/apr2026/raw/vendor_root.txt` |
| `enumeration/Y181/apr2026/raw/world_writable.txt` | `evidence/enumeration/Y181/apr2026/raw/world_writable.txt` |
| `enumeration/Y181/apr2026/security_summary.txt` | `evidence/enumeration/Y181/apr2026/security_summary.txt` |
| `enumeration/Y181/apr2026/settings_capability_unlock_Y181.txt` | `evidence/enumeration/Y181/apr2026/settings_capability_unlock_Y181.txt` |
| `enumeration/Y181/apr2026/settingsprovider_defaults_Y181.txt` | `evidence/enumeration/Y181/apr2026/settingsprovider_defaults_Y181.txt` |
| `enumeration/Y181/apr2026/vulnerability_assessment.txt` | `evidence/enumeration/Y181/apr2026/vulnerability_assessment.txt` |
| `enumeration/Y181/enumeration_report.txt` | `evidence/enumeration/Y181/enumeration_report.txt` |
| `enumeration/Y181/fastboot_enum_20251220_081738.txt` | `evidence/enumeration/Y181/fastboot_enum_20251220_081738.txt` |
| `enumeration/Y181/fastboot_enum_20251220_081748.txt` | `evidence/enumeration/Y181/fastboot_enum_20251220_081748.txt` |
| `enumeration/Y181/jun2026/CLAIMS_VERIFICATION.md` | `evidence/enumeration/Y181/jun2026/CLAIMS_VERIFICATION.md` |
| `enumeration/Y181/jun2026/claims_probe.txt` | `evidence/enumeration/Y181/jun2026/claims_probe.txt` |
| `enumeration/Y181/jun2026/enumeration_report.txt` | `evidence/enumeration/Y181/jun2026/enumeration_report.txt` |
| `enumeration/Y181/jun2026/pull_failures.txt` | `evidence/enumeration/Y181/jun2026/pull_failures.txt` |
| `enumeration/Y181/jun2026/pulled_files/plat_sepolicy.cil` | `evidence/enumeration/Y181/jun2026/pulled_files/plat_sepolicy.cil` |
| `enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` | `evidence/enumeration/Y181/jun2026/pulled_files/vendor_sepolicy.cil` |
| `enumeration/Y181/jun2026/raw/all_properties.txt` | `evidence/enumeration/Y181/jun2026/raw/all_properties.txt` |
| `enumeration/Y181/jun2026/raw/binder_services.txt` | `evidence/enumeration/Y181/jun2026/raw/binder_services.txt` |
| `enumeration/Y181/jun2026/raw/car_service.txt` | `evidence/enumeration/Y181/jun2026/raw/car_service.txt` |
| `enumeration/Y181/jun2026/raw/cmdline.txt` | `evidence/enumeration/Y181/jun2026/raw/cmdline.txt` |
| `enumeration/Y181/jun2026/raw/cpuinfo.txt` | `evidence/enumeration/Y181/jun2026/raw/cpuinfo.txt` |
| `enumeration/Y181/jun2026/raw/current_user.txt` | `evidence/enumeration/Y181/jun2026/raw/current_user.txt` |
| `enumeration/Y181/jun2026/raw/debug_props.txt` | `evidence/enumeration/Y181/jun2026/raw/debug_props.txt` |
| `enumeration/Y181/jun2026/raw/disk_usage.txt` | `evidence/enumeration/Y181/jun2026/raw/disk_usage.txt` |
| `enumeration/Y181/jun2026/raw/display_info.txt` | `evidence/enumeration/Y181/jun2026/raw/display_info.txt` |
| `enumeration/Y181/jun2026/raw/dmesg.txt` | `evidence/enumeration/Y181/jun2026/raw/dmesg.txt` |
| `enumeration/Y181/jun2026/raw/fingerprint.txt` | `evidence/enumeration/Y181/jun2026/raw/fingerprint.txt` |
| `enumeration/Y181/jun2026/raw/fstab.txt` | `evidence/enumeration/Y181/jun2026/raw/fstab.txt` |
| `enumeration/Y181/jun2026/raw/ghs_props.txt` | `evidence/enumeration/Y181/jun2026/raw/ghs_props.txt` |
| `enumeration/Y181/jun2026/raw/gm_props.txt` | `evidence/enumeration/Y181/jun2026/raw/gm_props.txt` |
| `enumeration/Y181/jun2026/raw/i2c_devices.txt` | `evidence/enumeration/Y181/jun2026/raw/i2c_devices.txt` |
| `enumeration/Y181/jun2026/raw/init_rc_files.txt` | `evidence/enumeration/Y181/jun2026/raw/init_rc_files.txt` |
| `enumeration/Y181/jun2026/raw/init_services.txt` | `evidence/enumeration/Y181/jun2026/raw/init_services.txt` |
| `enumeration/Y181/jun2026/raw/kernel_config.txt` | `evidence/enumeration/Y181/jun2026/raw/kernel_config.txt` |
| `enumeration/Y181/jun2026/raw/kernel_version.txt` | `evidence/enumeration/Y181/jun2026/raw/kernel_version.txt` |
| `enumeration/Y181/jun2026/raw/logcat.txt` | `evidence/enumeration/Y181/jun2026/raw/logcat.txt` |
| `enumeration/Y181/jun2026/raw/meminfo.txt` | `evidence/enumeration/Y181/jun2026/raw/meminfo.txt` |
| `enumeration/Y181/jun2026/raw/mounts.txt` | `evidence/enumeration/Y181/jun2026/raw/mounts.txt` |
| `enumeration/Y181/jun2026/raw/network_interfaces.txt` | `evidence/enumeration/Y181/jun2026/raw/network_interfaces.txt` |
| `enumeration/Y181/jun2026/raw/open_ports.txt` | `evidence/enumeration/Y181/jun2026/raw/open_ports.txt` |
| `enumeration/Y181/jun2026/raw/partitions.txt` | `evidence/enumeration/Y181/jun2026/raw/partitions.txt` |
| `enumeration/Y181/jun2026/raw/proc_partitions.txt` | `evidence/enumeration/Y181/jun2026/raw/proc_partitions.txt` |
| `enumeration/Y181/jun2026/raw/processes.txt` | `evidence/enumeration/Y181/jun2026/raw/processes.txt` |
| `enumeration/Y181/jun2026/raw/rollback_index.txt` | `evidence/enumeration/Y181/jun2026/raw/rollback_index.txt` |
| `enumeration/Y181/jun2026/raw/selinux_status.txt` | `evidence/enumeration/Y181/jun2026/raw/selinux_status.txt` |
| `enumeration/Y181/jun2026/raw/serial.txt` | `evidence/enumeration/Y181/jun2026/raw/serial.txt` |
| `enumeration/Y181/jun2026/raw/service_list.txt` | `evidence/enumeration/Y181/jun2026/raw/service_list.txt` |
| `enumeration/Y181/jun2026/raw/system_bin.txt` | `evidence/enumeration/Y181/jun2026/raw/system_bin.txt` |
| `enumeration/Y181/jun2026/raw/system_root.txt` | `evidence/enumeration/Y181/jun2026/raw/system_root.txt` |
| `enumeration/Y181/jun2026/raw/tty_devices.txt` | `evidence/enumeration/Y181/jun2026/raw/tty_devices.txt` |
| `enumeration/Y181/jun2026/raw/uart_devices.txt` | `evidence/enumeration/Y181/jun2026/raw/uart_devices.txt` |
| `enumeration/Y181/jun2026/raw/usb_devices.txt` | `evidence/enumeration/Y181/jun2026/raw/usb_devices.txt` |
| `enumeration/Y181/jun2026/raw/vendor_bin.txt` | `evidence/enumeration/Y181/jun2026/raw/vendor_bin.txt` |
| `enumeration/Y181/jun2026/raw/vendor_root.txt` | `evidence/enumeration/Y181/jun2026/raw/vendor_root.txt` |
| `enumeration/Y181/jun2026/raw/world_writable.txt` | `evidence/enumeration/Y181/jun2026/raw/world_writable.txt` |
| `enumeration/Y181/jun2026/rollback_assessment.txt` | `evidence/enumeration/Y181/jun2026/rollback_assessment.txt` |
| `enumeration/Y181/jun2026/security_check.txt` | `evidence/enumeration/Y181/jun2026/security_check.txt` |
| `enumeration/Y181/jun2026/security_summary.txt` | `evidence/enumeration/Y181/jun2026/security_summary.txt` |
| `enumeration/Y181/jun2026/uart_summary.txt` | `evidence/enumeration/Y181/jun2026/uart_summary.txt` |
| `enumeration/Y181/pull_failures.txt` | `evidence/enumeration/Y181/pull_failures.txt` |
| `enumeration/Y181/pulled_files/plat_sepolicy.cil` | `evidence/enumeration/Y181/pulled_files/plat_sepolicy.cil` |
| `enumeration/Y181/pulled_files/vendor_sepolicy.cil` | `evidence/enumeration/Y181/pulled_files/vendor_sepolicy.cil` |
| `enumeration/Y181/raw/all_properties.txt` | `evidence/enumeration/Y181/raw/all_properties.txt` |
| `enumeration/Y181/raw/binder_services.txt` | `evidence/enumeration/Y181/raw/binder_services.txt` |
| `enumeration/Y181/raw/car_service.txt` | `evidence/enumeration/Y181/raw/car_service.txt` |
| `enumeration/Y181/raw/cmdline.txt` | `evidence/enumeration/Y181/raw/cmdline.txt` |
| `enumeration/Y181/raw/cpuinfo.txt` | `evidence/enumeration/Y181/raw/cpuinfo.txt` |
| `enumeration/Y181/raw/current_user.txt` | `evidence/enumeration/Y181/raw/current_user.txt` |
| `enumeration/Y181/raw/debug_props.txt` | `evidence/enumeration/Y181/raw/debug_props.txt` |
| `enumeration/Y181/raw/disk_usage.txt` | `evidence/enumeration/Y181/raw/disk_usage.txt` |
| `enumeration/Y181/raw/display_info.txt` | `evidence/enumeration/Y181/raw/display_info.txt` |
| `enumeration/Y181/raw/dmesg.txt` | `evidence/enumeration/Y181/raw/dmesg.txt` |
| `enumeration/Y181/raw/fingerprint.txt` | `evidence/enumeration/Y181/raw/fingerprint.txt` |
| `enumeration/Y181/raw/fstab.txt` | `evidence/enumeration/Y181/raw/fstab.txt` |
| `enumeration/Y181/raw/gm_props.txt` | `evidence/enumeration/Y181/raw/gm_props.txt` |
| `enumeration/Y181/raw/i2c_devices.txt` | `evidence/enumeration/Y181/raw/i2c_devices.txt` |
| `enumeration/Y181/raw/init_rc_files.txt` | `evidence/enumeration/Y181/raw/init_rc_files.txt` |
| `enumeration/Y181/raw/init_services.txt` | `evidence/enumeration/Y181/raw/init_services.txt` |
| `enumeration/Y181/raw/kernel_config.txt` | `evidence/enumeration/Y181/raw/kernel_config.txt` |
| `enumeration/Y181/raw/kernel_version.txt` | `evidence/enumeration/Y181/raw/kernel_version.txt` |
| `enumeration/Y181/raw/logcat.txt` | `evidence/enumeration/Y181/raw/logcat.txt` |
| `enumeration/Y181/raw/meminfo.txt` | `evidence/enumeration/Y181/raw/meminfo.txt` |
| `enumeration/Y181/raw/mounts.txt` | `evidence/enumeration/Y181/raw/mounts.txt` |
| `enumeration/Y181/raw/network_interfaces.txt` | `evidence/enumeration/Y181/raw/network_interfaces.txt` |
| `enumeration/Y181/raw/open_ports.txt` | `evidence/enumeration/Y181/raw/open_ports.txt` |
| `enumeration/Y181/raw/partitions.txt` | `evidence/enumeration/Y181/raw/partitions.txt` |
| `enumeration/Y181/raw/proc_partitions.txt` | `evidence/enumeration/Y181/raw/proc_partitions.txt` |
| `enumeration/Y181/raw/processes.txt` | `evidence/enumeration/Y181/raw/processes.txt` |
| `enumeration/Y181/raw/selinux_status.txt` | `evidence/enumeration/Y181/raw/selinux_status.txt` |
| `enumeration/Y181/raw/serial.txt` | `evidence/enumeration/Y181/raw/serial.txt` |
| `enumeration/Y181/raw/service_list.txt` | `evidence/enumeration/Y181/raw/service_list.txt` |
| `enumeration/Y181/raw/system_bin.txt` | `evidence/enumeration/Y181/raw/system_bin.txt` |
| `enumeration/Y181/raw/system_root.txt` | `evidence/enumeration/Y181/raw/system_root.txt` |
| `enumeration/Y181/raw/tty_devices.txt` | `evidence/enumeration/Y181/raw/tty_devices.txt` |
| `enumeration/Y181/raw/usb_devices.txt` | `evidence/enumeration/Y181/raw/usb_devices.txt` |
| `enumeration/Y181/raw/vendor_bin.txt` | `evidence/enumeration/Y181/raw/vendor_bin.txt` |
| `enumeration/Y181/raw/vendor_root.txt` | `evidence/enumeration/Y181/raw/vendor_root.txt` |
| `enumeration/Y181/raw/world_writable.txt` | `evidence/enumeration/Y181/raw/world_writable.txt` |
| `enumeration/Y181/security_check.txt` | `evidence/enumeration/Y181/security_check.txt` |
| `enumeration/Y181/security_summary.txt` | `evidence/enumeration/Y181/security_summary.txt` |
| `enumeration/scripts/gm_aaos_enum.sh` | `tools/enumeration/gm_aaos_enum.sh` |
| `enumeration/scripts/quick_security_check.sh` | `tools/enumeration/quick_security_check.sh` |
| `mdi2_client/.gitignore` | `tools/mdi2_client/.gitignore` |
| `mdi2_client/README.md` | `tools/mdi2_client/README.md` |
| `mdi2_client/docs/ACCESS.md` | `tools/mdi2_client/docs/ACCESS.md` |
| `mdi2_client/docs/CALIBRATION_WRITE.md` | `tools/mdi2_client/docs/CALIBRATION_WRITE.md` |
| `mdi2_client/docs/PROTOCOL.md` | `tools/mdi2_client/docs/PROTOCOL.md` |
| `mdi2_client/keys.example.json` | `tools/mdi2_client/keys.example.json` |
| `mdi2_client/mdi2/__init__.py` | `tools/mdi2_client/mdi2/__init__.py` |
| `mdi2_client/mdi2/battery_voltage.py` | `tools/mdi2_client/mdi2/battery_voltage.py` |
| `mdi2_client/mdi2/calibration_payloads.py` | `tools/mdi2_client/mdi2/calibration_payloads.py` |
| `mdi2_client/mdi2/calibration_pre_reset_simulation.py` | `tools/mdi2_client/mdi2/calibration_pre_reset_simulation.py` |
| `mdi2_client/mdi2/calibration_readback.py` | `tools/mdi2_client/mdi2/calibration_readback.py` |
| `mdi2_client/mdi2/calibration_transaction.py` | `tools/mdi2_client/mdi2/calibration_transaction.py` |
| `mdi2_client/mdi2/can_transport.py` | `tools/mdi2_client/mdi2/can_transport.py` |
| `mdi2_client/mdi2/capture_read_transport.py` | `tools/mdi2_client/mdi2/capture_read_transport.py` |
| `mdi2_client/mdi2/captured_events.py` | `tools/mdi2_client/mdi2/captured_events.py` |
| `mdi2_client/mdi2/cli.py` | `tools/mdi2_client/mdi2/cli.py` |
| `mdi2_client/mdi2/const.py` | `tools/mdi2_client/mdi2/const.py` |
| `mdi2_client/mdi2/container.py` | `tools/mdi2_client/mdi2/container.py` |
| `mdi2_client/mdi2/crypto.py` | `tools/mdi2_client/mdi2/crypto.py` |
| `mdi2_client/mdi2/data/did_map.json` | `tools/mdi2_client/mdi2/data/did_map.json` |
| `mdi2_client/mdi2/data/ecu_map.json` | `tools/mdi2_client/mdi2/data/ecu_map.json` |
| `mdi2_client/mdi2/discovery.py` | `tools/mdi2_client/mdi2/discovery.py` |
| `mdi2_client/mdi2/dpdu.py` | `tools/mdi2_client/mdi2/dpdu.py` |
| `mdi2_client/mdi2/dpdu_replay.py` | `tools/mdi2_client/mdi2/dpdu_replay.py` |
| `mdi2_client/mdi2/ecu_catalog.py` | `tools/mdi2_client/mdi2/ecu_catalog.py` |
| `mdi2_client/mdi2/framing.py` | `tools/mdi2_client/mdi2/framing.py` |
| `mdi2_client/mdi2/live_calibration.py` | `tools/mdi2_client/mdi2/live_calibration.py` |
| `mdi2_client/mdi2/live_programming_transport.py` | `tools/mdi2_client/mdi2/live_programming_transport.py` |
| `mdi2_client/mdi2/logs.py` | `tools/mdi2_client/mdi2/logs.py` |
| `mdi2_client/mdi2/ltz_preflight.py` | `tools/mdi2_client/mdi2/ltz_preflight.py` |
| `mdi2_client/mdi2/ltz_reference_manifest.py` | `tools/mdi2_client/mdi2/ltz_reference_manifest.py` |
| `mdi2_client/mdi2/ltz_workflow_simulation.py` | `tools/mdi2_client/mdi2/ltz_workflow_simulation.py` |
| `mdi2_client/mdi2/messages.py` | `tools/mdi2_client/mdi2/messages.py` |
| `mdi2_client/mdi2/module_reader.py` | `tools/mdi2_client/mdi2/module_reader.py` |
| `mdi2_client/mdi2/programming_adapter_simulation.py` | `tools/mdi2_client/mdi2/programming_adapter_simulation.py` |
| `mdi2_client/mdi2/programming_transport.py` | `tools/mdi2_client/mdi2/programming_transport.py` |
| `mdi2_client/mdi2/security_cmac.py` | `tools/mdi2_client/mdi2/security_cmac.py` |
| `mdi2_client/mdi2/transport.py` | `tools/mdi2_client/mdi2/transport.py` |
| `mdi2_client/mdi2/uds_generic.py` | `tools/mdi2_client/mdi2/uds_generic.py` |
| `mdi2_client/mdi2/vip_dev_memory.py` | `tools/mdi2_client/mdi2/vip_dev_memory.py` |
| `mdi2_client/requirements.txt` | `tools/mdi2_client/requirements.txt` |
| `mdi2_client/scripts/calibrate_ltz.sh` | `tools/mdi2_client/scripts/calibrate_ltz.sh` |
| `mdi2_client/scripts/calibration_compare.py` | `tools/mdi2_client/scripts/calibration_compare.py` |
| `mdi2_client/scripts/mdi2_9052_decrypt.py` | `tools/mdi2_client/scripts/mdi2_9052_decrypt.py` |
| `mdi2_client/scripts/mdi2_key.py` | `tools/mdi2_client/scripts/mdi2_key.py` |
| `mdi2_client/scripts/read_csm_x80.py` | `tools/mdi2_client/scripts/read_csm_x80.py` |
| `mdi2_client/scripts/scratch/radio_cal_decode.py` | `tools/mdi2_client/scripts/scratch/radio_cal_decode.py` |
| `mdi2_client/scripts/sweep_security_access.py` | `tools/mdi2_client/scripts/sweep_security_access.py` |
| `mdi2_client/scripts/write_custom_cal_can.py` | `tools/mdi2_client/scripts/write_custom_cal_can.py` |
| `mdi2_client/tests/test_battery_voltage.py` | `tools/mdi2_client/tests/test_battery_voltage.py` |
| `mdi2_client/tests/test_calibration_pre_reset_simulation.py` | `tools/mdi2_client/tests/test_calibration_pre_reset_simulation.py` |
| `mdi2_client/tests/test_calibration_readback.py` | `tools/mdi2_client/tests/test_calibration_readback.py` |
| `mdi2_client/tests/test_calibration_transaction.py` | `tools/mdi2_client/tests/test_calibration_transaction.py` |
| `mdi2_client/tests/test_can_transport.py` | `tools/mdi2_client/tests/test_can_transport.py` |
| `mdi2_client/tests/test_capture_read_transport.py` | `tools/mdi2_client/tests/test_capture_read_transport.py` |
| `mdi2_client/tests/test_captured_events.py` | `tools/mdi2_client/tests/test_captured_events.py` |
| `mdi2_client/tests/test_cli_security.py` | `tools/mdi2_client/tests/test_cli_security.py` |
| `mdi2_client/tests/test_discovery.py` | `tools/mdi2_client/tests/test_discovery.py` |
| `mdi2_client/tests/test_ecu_catalog.py` | `tools/mdi2_client/tests/test_ecu_catalog.py` |
| `mdi2_client/tests/test_live_calibration.py` | `tools/mdi2_client/tests/test_live_calibration.py` |
| `mdi2_client/tests/test_live_programming_transport.py` | `tools/mdi2_client/tests/test_live_programming_transport.py` |
| `mdi2_client/tests/test_logs.py` | `tools/mdi2_client/tests/test_logs.py` |
| `mdi2_client/tests/test_ltz_preflight.py` | `tools/mdi2_client/tests/test_ltz_preflight.py` |
| `mdi2_client/tests/test_ltz_workflow_simulation.py` | `tools/mdi2_client/tests/test_ltz_workflow_simulation.py` |
| `mdi2_client/tests/test_module_reader.py` | `tools/mdi2_client/tests/test_module_reader.py` |
| `mdi2_client/tests/test_programming_adapter_simulation.py` | `tools/mdi2_client/tests/test_programming_adapter_simulation.py` |
| `mdi2_client/tests/test_programming_transport.py` | `tools/mdi2_client/tests/test_programming_transport.py` |
| `mdi2_client/tests/test_security_cmac.py` | `tools/mdi2_client/tests/test_security_cmac.py` |
| `mdi2_client/tests/test_service_transport.py` | `tools/mdi2_client/tests/test_service_transport.py` |
| `mdi2_client/tests/test_vip_dev_memory.py` | `tools/mdi2_client/tests/test_vip_dev_memory.py` |
| `platform/platform_originals_2026-11-18.zip` | `evidence/archives/platform_originals_2026-11-18.zip` |
| `research/AE_RESEARCH_HANDOFF.md` | `research/mdi2-bench-sessions/AE_RESEARCH_HANDOFF.md` |
| `research/AOSP_REPLACEMENT_RESEARCH.txt` | `research/rights-and-roadmap/AOSP_REPLACEMENT_RESEARCH.txt` |
| `research/AUG24_SESSION_FULL_PCAP_TIMELINE.md` | `research/mdi2-bench-sessions/AUG24_SESSION_FULL_PCAP_TIMELINE.md` |
| `research/BOOT_CHAIN_ANALYSIS.txt` | `research/boot-update-recovery/BOOT_CHAIN_ANALYSIS.txt` |
| `research/BOOT_TRUST_ANCHOR_AND_KEYS.md` | `research/boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md` |
| `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt` | `research/eeprom-calibration/CALDEF_VIP_CALIBRATION_ANALYSIS.txt` |
| `research/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md` | `research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md` |
| `research/CSE_HECI_ORCHESTRATION_ANALYSIS.md` | `research/boot-update-recovery/CSE_HECI_ORCHESTRATION_ANALYSIS.md` |
| `research/DPS_AND_MODIFICATION_LANDSCAPE.txt` | `research/eeprom-calibration/DPS_AND_MODIFICATION_LANDSCAPE.txt` |
| `research/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` | `research/eeprom-calibration/DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` |
| `research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` | `research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` |
| `research/EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md` | `research/eeprom-calibration/EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md` |
| `research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` | `research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` |
| `research/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt` | `research/boot-update-recovery/GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt` |
| `research/GHS_FILE_MAP_85098662.md` | `research/boot-update-recovery/GHS_FILE_MAP_85098662.md` |
| `research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` | `research/boot-update-recovery/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md` |
| `research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md` | `research/boot-update-recovery/GM_INFO37_BOOT_CHAIN_ANALYSIS.md` |
| `research/GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS.txt` | `research/rights-and-roadmap/GM_LOCKDOWN_ANALYSIS_AND_COUNTERARGUMENTS.txt` |
| `research/GM_REMOTE_ACCESS_ANALYSIS.txt` | `research/rights-and-roadmap/GM_REMOTE_ACCESS_ANALYSIS.txt` |
| `research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` | `research/eeprom-calibration/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` |
| `research/GORDON_PEAK_CELADON_INTELLIGENCE.md` | `research/boot-update-recovery/GORDON_PEAK_CELADON_INTELLIGENCE.md` |
| `research/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` | `research/security/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` |
| `research/INVENTORY.md` | `research/provenance/INVENTORY.md` |
| `research/MDI2_DPDU_API_PROTOCOL_AUG2026.md` | `research/mdi2-bench-sessions/MDI2_DPDU_API_PROTOCOL_AUG2026.md` |
| `research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` | `research/mdi2-bench-sessions/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` |
| `research/MDI2_RAW_UDS_BYPASS_GUIDE.md` | `research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md` |
| `research/PROVENANCE_AUDIT_AUG2026.md` | `research/provenance/PROVENANCE_AUDIT_AUG2026.md` |
| `research/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md` | `research/boot-update-recovery/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md` |
| `research/SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md` | `research/security/SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md` |
| `research/UNTRIED_ATTACK_VECTORS.md` | `research/security/UNTRIED_ATTACK_VECTORS.md` |
| `research/USB_ADB_SESSION_FINDINGS_2026-10-10.md` | `research/mdi2-bench-sessions/USB_ADB_SESSION_FINDINGS_2026-10-10.md` |
| `research/VIP_CONTROL_ANALYSIS.txt` | `research/eeprom-calibration/VIP_CONTROL_ANALYSIS.txt` |
| `research/VIP_FIRMWARE_Y177_Y181_COMPARISON.md` | `research/boot-update-recovery/VIP_FIRMWARE_Y177_Y181_COMPARISON.md` |
| `research/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md` | `research/security/VMM1_PARSER_FUZZ_TARGETS_ANALYSIS.md` |
| `research/calibration_glossary.md` | `research/eeprom-calibration/calibration_glossary.md` |
| `research/calibration_prototypes/a11_gmbrand_gmc_single.calovride` | `research/eeprom-calibration/calibration_prototypes/a11_gmbrand_gmc_single.calovride` |
| `research/calibration_prototypes/a11_ltz_gmtrim_highcountry.calovride.xml` | `research/eeprom-calibration/calibration_prototypes/a11_ltz_gmtrim_highcountry.calovride.xml` |
| `research/canbus_reset/10017909.cfx.xml` | `research/eeprom-calibration/canbus_reset/10017909.cfx.xml` |
| `research/canbus_reset/CANBUS_RESET_ANALYSIS.txt` | `research/eeprom-calibration/canbus_reset/CANBUS_RESET_ANALYSIS.txt` |
| `research/decompiled/bootloader_a/ANALYSIS.md` | `evidence/decompiled/bootloader_a/ANALYSIS.md` |
| `research/decompiled/bootloader_a/dispatch_table.txt` | `evidence/decompiled/bootloader_a/dispatch_table.txt` |
| `research/decompiled/bootloader_a/ipk_checksum_loop.disasm.txt` | `evidence/decompiled/bootloader_a/ipk_checksum_loop.disasm.txt` |
| `research/decompiled/bootloader_a/ipk_handler_fcn12808b00.disasm.txt` | `evidence/decompiled/bootloader_a/ipk_handler_fcn12808b00.disasm.txt` |
| `research/decompiled/bootloader_a/soc_abl.elf` | `evidence/decompiled/bootloader_a/soc_abl.elf` |
| `research/decompiled/bootloader_a/soc_abl_elf2.elf` | `evidence/decompiled/bootloader_a/soc_abl_elf2.elf` |
| `research/decompiled/elk_strings.txt` | `evidence/decompiled/elk_strings.txt` |
| `research/decompiled/ghs_analysis.txt` | `evidence/decompiled/ghs_analysis.txt` |
| `research/decompiled/ghs_isys_a_secinfo_region_map_Y175.txt` | `evidence/decompiled/ghs_isys_a_secinfo_region_map_Y175.txt` |
| `research/decompiled/ghs_str.txt` | `evidence/decompiled/ghs_str.txt` |
| `research/decompiled/ghs_strings.txt` | `evidence/decompiled/ghs_strings.txt` |
| `research/decompiled/ifwi_Y175/README.md` | `evidence/decompiled/ifwi_Y175/README.md` |
| `research/decompiled/ifwi_Y175/cse_unpacked/BPDT [4].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/BPDT [4].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/BPDT [4].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/BPDT [4].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/FTPR.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/FTPR.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/FTPR.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/FTPR.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/RTFD.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/RTFD.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bios.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bios.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/alt_bpm_key` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/alt_bpm_key` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/alt_bpm_key.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/alt_bpm_key.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/crypto_dis` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/crypto_dis` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/crypto_dis.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/crypto_dis.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/emu_fuse_map` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/emu_fuse_map` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/emu_fuse_map.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/emu_fuse_map.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/fuse_ip_base` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/fuse_ip_base` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/fuse_ip_base.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/fuse_ip_base.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/plat_n_sku` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/plat_n_sku` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/plat_n_sku.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/bup_sku/plat_n_sku.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ct` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ct` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ct.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ct.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/dataclear` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/dataclear` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/dataclear.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/dataclear.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/heci_guids` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/heci_guids` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/heci_guids.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/heci_guids.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ivi_no_svn1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ivi_no_svn1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ivi_no_svn1.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/ivi_no_svn1.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/mbp` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/mbp` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/mbp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/mbp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/oem_imr_data` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/oem_imr_data` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/oem_imr_data.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/oem_imr_data.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/si_features` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/si_features` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/si_features.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/bup/si_features.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/cls.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/cls.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/app_data.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/app_data.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/app_files.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/app_files.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/sys.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_ivm/sys.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/keys.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/keys.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/sds.sdb` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/sds.sdb` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/sds.sdb.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/sds.sdb.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/svl.vdb` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/svl.vdb` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/svl.vdb.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/svl.vdb.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/tas.tdb` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/tas.tdb` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/tas.tdb.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/dal_sdm/tas.tdb.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio/bxt_cse_pins` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio/bxt_cse_pins` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio/bxt_cse_pins.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/gpio/bxt_cse_pins.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham/SDTNonces` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham/SDTNonces` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham/SDTNonces.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/hotham/SDTNonces.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/INTC_pdt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/INTC_pdt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/INTC_pdt.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/INTC_pdt.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/trace_config` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/trace_config` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/trace_config.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ish_srv/trace_config.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/camera_mask` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/camera_mask` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/camera_mask.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/camera_mask.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/port_cfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/port_cfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/port_cfg.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/port_cfg.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_ctl` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_ctl` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_ctl.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_ctl.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_touch` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_touch` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_touch.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/iunit/sec_touch.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/arben` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/arben` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/arben.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/arben.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/svns` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/svns` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/svns.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/loadmgr/svns.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/manuf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/manuf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/attkb_mfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/attkb_mfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/attkb_mfg.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/attkb_mfg.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/eom` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/eom` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/eom.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/eom.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/fpf_commit` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/fpf_commit` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/fpf_commit.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/fpf_commit.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/manuf_lock` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/manuf_lock` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/manuf_lock.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/manuf_lock.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/spi_access` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/spi_access` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/spi_access.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca/spi_access.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca_temp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mca_temp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/device_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/device_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/device_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/device_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/eid_db` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/eid_db` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/eid_db.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/eid_db.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/pg_info` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/pg_info` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/pg_info.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/mctp/pg_info.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/nvinf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/nvinf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/guc_hash` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/guc_hash` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/guc_hash.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/guc_hash.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/hdcp_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/hdcp_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/hdcp_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/hdcp_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/kf1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/kf1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/kf1.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/kf1.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_cert` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_cert` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_cert.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_cert.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_port` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_port` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_port.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/lspcon_port.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/pr_time` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/pr_time` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/pr_time.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/pr_time.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/time_offset` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/time_offset` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/time_offset.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/time_offset.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/vga_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/vga_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/vga_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/vga_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m0` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m0` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m0.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m0.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m1.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m1.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m2` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m2` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m2.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m2.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m3` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m3` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m3.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m3.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m4` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m4` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m4.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m4.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m5` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m5` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m5.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m5.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m6` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m6` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m6.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m6.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m7` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m7` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m7.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m7.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m8` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m8` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m8.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m8.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m9` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m9` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m9.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_k_m9.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_srm_ver` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_srm_ver` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_srm_ver.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/widi_srm_ver.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek_nvar` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek_nvar` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek_nvar.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_cek_nvar.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_keybox` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_keybox` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_keybox.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/pavp/wv_keybox.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/auto_config` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/auto_config` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/auto_config.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/auto_config.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/flash_test` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/flash_test` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/flash_test.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/flash_test.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/live_results` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/live_results` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/live_results.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/Bist/live_results.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/DnxCblCo` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/DnxCblCo` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/DnxCblCo.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/DnxCblCo.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/IBB_sig` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/IBB_sig` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/IBB_sig.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/IBB_sig.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/NpkPtiDis` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/NpkPtiDis` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/NpkPtiDis.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/NpkPtiDis.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr/cfg_rules` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr/cfg_rules` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr/cfg_rules.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/cfgmgr/cfg_rules.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid1.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid1.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid2` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid2` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid2.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid2.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid3` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid3` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid3.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/sysintid3.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/uncfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/uncfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/uncfg.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/hci/uncfg.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/lcl_eom_st` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/lcl_eom_st` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/lcl_eom_st.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/lcl_eom_st.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/config_state` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/config_state` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/config_state.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/config_state.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/ftpm_enable` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/ftpm_enable` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/ftpm_enable.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/ftpm_enable.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/sku_boot_sts` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/sku_boot_sts` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/sku_boot_sts.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/sku_boot_sts.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/tls_blob` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/tls_blob` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/tls_blob.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/tls_blob.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/uncfg_needed` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/uncfg_needed` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/uncfg_needed.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/uncfg_needed.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/vpro_allowed` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/vpro_allowed` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/vpro_allowed.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/policy/skumgr/vpro_allowed.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/PttProf` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/PttProf` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/PttProf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/PttProf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/dynamic.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/dynamic.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/reserved.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/reserved.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/transact.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/ptt/transact.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/sigma.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/sigma.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/tcb.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home/tcb.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home_records.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/Intel Configuration/home_records.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/RTFD.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/RTFD.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bios.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bios.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/alt_bpm_key` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/alt_bpm_key` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/alt_bpm_key.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/alt_bpm_key.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/crypto_dis` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/crypto_dis` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/crypto_dis.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/crypto_dis.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/emu_fuse_map` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/emu_fuse_map` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/emu_fuse_map.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/emu_fuse_map.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/fuse_ip_base` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/fuse_ip_base` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/fuse_ip_base.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/fuse_ip_base.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/plat_n_sku` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/plat_n_sku` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/plat_n_sku.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/bup_sku/plat_n_sku.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/ct` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/ct` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/ct.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/ct.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/dataclear` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/dataclear` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/dataclear.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/dataclear.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/heci_guids` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/heci_guids` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/heci_guids.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/heci_guids.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/mbp` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/mbp` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/mbp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/mbp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/oem_imr_data` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/oem_imr_data` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/oem_imr_data.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/oem_imr_data.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/si_features` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/si_features` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/si_features.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/bup/si_features.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/cls.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/cls.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/app_data.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/app_data.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/app_files.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/app_files.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/sys.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_ivm/sys.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_sdm.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_sdm.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_sdm/keys.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/dal_sdm/keys.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio/bxt_cse_pins` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio/bxt_cse_pins` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio/bxt_cse_pins.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/gpio/bxt_cse_pins.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham/SDTNonces` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham/SDTNonces` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham/SDTNonces.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/hotham/SDTNonces.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/INTC_pdt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/INTC_pdt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/INTC_pdt.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/INTC_pdt.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/trace_config` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/trace_config` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/trace_config.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ish_srv/trace_config.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/camera_mask` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/camera_mask` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/camera_mask.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/camera_mask.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/port_cfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/port_cfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/port_cfg.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/port_cfg.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_ctl` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_ctl` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_ctl.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_ctl.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_touch` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_touch` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_touch.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/iunit/sec_touch.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr/arben` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr/arben` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr/arben.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/loadmgr/arben.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/manuf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/manuf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/attkb_mfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/attkb_mfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/attkb_mfg.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/attkb_mfg.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/eom` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/eom` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/eom.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/eom.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/manuf_lock` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/manuf_lock` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/manuf_lock.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/manuf_lock.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/spi_access` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/spi_access` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/spi_access.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca/spi_access.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca_temp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mca_temp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/device_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/device_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/device_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/device_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/eid_db` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/eid_db` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/eid_db.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/eid_db.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/pg_info` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/pg_info` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/pg_info.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/mctp/pg_info.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/nvinf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/nvinf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/guc_hash` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/guc_hash` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/guc_hash.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/guc_hash.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/hdcp_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/hdcp_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/hdcp_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/hdcp_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/lspcon_port` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/lspcon_port` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/lspcon_port.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/lspcon_port.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/vga_ports` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/vga_ports` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/vga_ports.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/vga_ports.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/wv_cek_nvar` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/wv_cek_nvar` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/wv_cek_nvar.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/pavp/wv_cek_nvar.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist/auto_config` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist/auto_config` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist/auto_config.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/Bist/auto_config.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/DnxCblCo` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/DnxCblCo` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/DnxCblCo.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/DnxCblCo.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/NpkPtiDis` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/NpkPtiDis` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/NpkPtiDis.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/NpkPtiDis.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr/cfg_rules` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr/cfg_rules` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr/cfg_rules.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/cfgmgr/cfg_rules.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid1.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid1.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid2` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid2` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid2.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid2.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid3` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid3` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid3.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/hci/sysintid3.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr/ftpm_enable` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr/ftpm_enable` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr/ftpm_enable.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/policy/skumgr/ftpm_enable.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/PttProf` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/PttProf` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/PttProf.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/PttProf.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/dynamic.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/dynamic.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/reserved.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/reserved.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/transact.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/ptt/transact.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/sigma.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/sigma.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/tcb.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home/tcb.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home_records.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/OEM Configuration/home_records.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/bup.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/fitc.cfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/fitc.cfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/intl.cfg.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/kernel.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/oem.key` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/oem.key` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/oem.key.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/oem.key.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/rot.key` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/rot.key` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/rot.key.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/rot.key.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/FTPR 0000 [0x220000]/syslib.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/BPM.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/BPM.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/BPM.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/BPM.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBB` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBB` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBL` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBL` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IBBP 0000 [0x28C000]/IBBP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ISHC.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ISHC.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ISHC.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ISHC.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/ISHC 0001 [0x2CB000]/ish_main.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/IUNP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/IUNP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/IUNP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/IUNP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/IUNP 0001 [0x413000]/iunit.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/NFTP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/NFTP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/NFTP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/NFTP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/adspa.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/busdrv.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/cls.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/crypto.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_ivm.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_lnch.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/dal_sdm.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/evtdisp.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/fpf.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/gpio.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hci.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/heci.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/hotham.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ipc_drv.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_bup.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ish_srv.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/iunitcse.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/loadmgr.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/maestro.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_boot.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mca_srv.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/mctp.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pavp.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pm.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/pmdrv.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/policy.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/prtc.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/ptt.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/sigma.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/storage.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tcb.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/tls_iso.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vdm.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/NFTP 0000 [0x30B000]/vfs.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000]/ELK` | `evidence/decompiled/ifwi_Y175/cse_unpacked/OBBP 0000 [0x501000]/ELK` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCC003.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/PMCP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/PMCP 0001 [0x210000]/pmc.dat.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/RBEP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/RBEP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/RBEP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/RBEP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/RBEP 0000 [0x205000]/rbe.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/S-BPDT 0000 [0x500200].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/S-BPDT 0000 [0x500200].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/S-BPDT 0001 [0x2CA000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/S-BPDT 0001 [0x2CA000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/SMIP.man` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/SMIP.man` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/SMIP.man.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/SMIP.man.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip.met` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip.met` |
| `research/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip.met.txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/SMIP 0000 [0x201000]/smip.met.txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000].txt` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000].txt` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000]/upatch1` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000]/upatch1` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000]/upatch2` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UCOD 0000 [0x283000]/upatch2` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UEP 0000 [0x200210].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UEP 0000 [0x200210].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UEPB 0000 [0x200200].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UEPB 0000 [0x200200].bin` |
| `research/decompiled/ifwi_Y175/cse_unpacked/UTOK 0000 [0x2C8000].bin` | `evidence/decompiled/ifwi_Y175/cse_unpacked/UTOK 0000 [0x2C8000].bin` |
| `research/decompiled/ifwi_Y175/elk/abl_main.elf` | `evidence/decompiled/ifwi_Y175/elk/abl_main.elf` |
| `research/decompiled/ifwi_Y175/elk/elf0_0x22c.elf` | `evidence/decompiled/ifwi_Y175/elk/elf0_0x22c.elf` |
| `research/decompiled/ifwi_Y175/elk/elf1_0x10a334.elf` | `evidence/decompiled/ifwi_Y175/elk/elf1_0x10a334.elf` |
| `research/decompiled/ivcspsa_decomp.c` | `evidence/decompiled/ivcspsa_decomp.c` |
| `research/decompiled/sa015bcr_decomp.c` | `evidence/decompiled/sa015bcr_decomp.c` |
| `research/decompiled/vip_inspect.txt` | `evidence/decompiled/vip_inspect.txt` |
| `research/decompiled/vmm1_all.c` | `evidence/decompiled/vmm1_all.c` |
| `research/decompiled/vmm1_decomp.txt` | `evidence/decompiled/vmm1_decomp.txt` |
| `research/fuzz/bundle1_avb_primed_prompt.md` | `research/security/fuzz/bundle1_avb_primed_prompt.md` |
| `research/fuzz/bundle1_correction_prompt.md` | `research/security/fuzz/bundle1_correction_prompt.md` |
| `research/fuzz/bundle1_output.md` | `research/security/fuzz/bundle1_output.md` |
| `research/fuzz/bundle1_output_qwen.md` | `research/security/fuzz/bundle1_output_qwen.md` |
| `research/fuzz/bundle1_output_qwen_pass2.md` | `research/security/fuzz/bundle1_output_qwen_pass2.md` |
| `research/fuzz/bundle2_correction_prompt.md` | `research/security/fuzz/bundle2_correction_prompt.md` |
| `research/fuzz/bundle2_ota_primed_prompt.md` | `research/security/fuzz/bundle2_ota_primed_prompt.md` |
| `research/fuzz/bundle2_output_qwen.md` | `research/security/fuzz/bundle2_output_qwen.md` |
| `research/fuzz/bundle2_output_qwen_pass2.md` | `research/security/fuzz/bundle2_output_qwen_pass2.md` |
| `research/fuzz/synthesis_output_qwen.md` | `research/security/fuzz/synthesis_output_qwen.md` |
| `research/fuzz/synthesis_prompt.md` | `research/security/fuzz/synthesis_prompt.md` |
| `research/fuzz/v2/avb_bundle1_fuzzer.c` | `research/security/fuzz/v2/avb_bundle1_fuzzer.c` |
| `research/fuzz/v2/build.sh` | `research/security/fuzz/v2/build.sh` |
| `research/fuzz/v2/gen_seeds.py` | `research/security/fuzz/v2/gen_seeds.py` |
| `research/fuzz/v2/seeds/O1_desc_off_highdword.bin` | `research/security/fuzz/v2/seeds/O1_desc_off_highdword.bin` |
| `research/fuzz/v2/seeds/O1_desc_off_smallwrap.bin` | `research/security/fuzz/v2/seeds/O1_desc_off_smallwrap.bin` |
| `research/fuzz/v2/seeds/O1_desc_sz_highdword.bin` | `research/security/fuzz/v2/seeds/O1_desc_sz_highdword.bin` |
| `research/fuzz/v2/seeds/O2_total_len_overflow.bin` | `research/security/fuzz/v2/seeds/O2_total_len_overflow.bin` |
| `research/fuzz/v2/seeds/O3_desc_payload_overflow.bin` | `research/security/fuzz/v2/seeds/O3_desc_payload_overflow.bin` |
| `research/fuzz/v2/seeds/O3_non_div8.bin` | `research/security/fuzz/v2/seeds/O3_non_div8.bin` |
| `research/fuzz/v2/seeds/O5_boot_hdr_kernel_size_wrap.bin` | `research/security/fuzz/v2/seeds/O5_boot_hdr_kernel_size_wrap.bin` |
| `research/fuzz/v2/seeds/O5_boot_hdr_page_size_huge.bin` | `research/security/fuzz/v2/seeds/O5_boot_hdr_page_size_huge.bin` |
| `research/fuzz/v2/seeds/O5_boot_hdr_page_size_zero.bin` | `research/security/fuzz/v2/seeds/O5_boot_hdr_page_size_zero.bin` |
| `research/fuzz/v2/seeds/O6_rollback_highdword.bin` | `research/security/fuzz/v2/seeds/O6_rollback_highdword.bin` |
| `research/fuzz/v2/seeds/T1_toctou_placeholder.bin` | `research/security/fuzz/v2/seeds/T1_toctou_placeholder.bin` |
| `research/fuzz/v2_bundle2/ab_metadata_crc_forge.py` | `research/security/fuzz/v2_bundle2/ab_metadata_crc_forge.py` |
| `research/fuzz/v2_bundle2/ota_isys_frame_fuzzer.py` | `research/security/fuzz/v2_bundle2/ota_isys_frame_fuzzer.py` |
| `research/reports/avb_audit.out` | `evidence/reports/avb_audit.out` |
| `research/reports/crypto_findings.json` | `evidence/reports/crypto_findings.json` |
| `research/reports/file_map.tsv` | `evidence/reports/file_map.tsv` |
| `research/reports/forensic_out.txt` | `evidence/reports/forensic_out.txt` |
| `research/reports/ivcs_dec.log` | `evidence/reports/ivcs_dec.log` |
| `research/reports/sa015_dec.log` | `evidence/reports/sa015_dec.log` |
| `research/research_originals_2026-11-18.zip` | `evidence/archives/research_originals_2026-11-18.zip` |
| `research/scripts/Decomp.java` | `tools/analysis-scripts/Decomp.java` |
| `research/scripts/DecompExports.java` | `tools/analysis-scripts/DecompExports.java` |
| `research/scripts/DumpVmm.java` | `tools/analysis-scripts/DumpVmm.java` |
| `research/scripts/GhsDump.java` | `tools/analysis-scripts/GhsDump.java` |
| `research/scripts/VipInspect.java` | `tools/analysis-scripts/VipInspect.java` |
| `research/scripts/__pycache__/avb_audit.cpython-314.pyc` | `tools/analysis-scripts/__pycache__/avb_audit.cpython-314.pyc` |
| `research/scripts/avb_audit.py` | `tools/analysis-scripts/avb_audit.py` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.gpr` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.gpr` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.lock` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.lock` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/idata/~index.dat` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/idata/~index.dat` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/project.prp` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/project.prp` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/user/~index.dat` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/user/~index.dat` |
| `research/scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/versioned/~index.dat` | `tools/analysis-scripts/avb_audit.py_ghidra/avb_audit.py_ghidra.rep/versioned/~index.dat` |
| `research/scripts/crypto_scan.py` | `tools/analysis-scripts/crypto_scan.py` |
| `research/scripts/forensic.py` | `tools/analysis-scripts/forensic.py` |
| `research/scripts/ghidra_rh850/hostos_symbols_all.tsv` | `tools/analysis-scripts/ghidra_rh850/hostos_symbols_all.tsv` |
| `research/scripts/ghidra_rh850/hostos_symbols_funcobj.tsv` | `tools/analysis-scripts/ghidra_rh850/hostos_symbols_funcobj.tsv` |
| `research/scripts/ghidra_rh850/probe_out.log` | `tools/analysis-scripts/ghidra_rh850/probe_out.log` |
| `research/scripts/ghidra_rh850/step10_deep.py` | `tools/analysis-scripts/ghidra_rh850/step10_deep.py` |
| `research/scripts/ghidra_rh850/step10_out.log` | `tools/analysis-scripts/ghidra_rh850/step10_out.log` |
| `research/scripts/ghidra_rh850/step11_out.log` | `tools/analysis-scripts/ghidra_rh850/step11_out.log` |
| `research/scripts/ghidra_rh850/step11_sbi.py` | `tools/analysis-scripts/ghidra_rh850/step11_sbi.py` |
| `research/scripts/ghidra_rh850/step12_groups.py` | `tools/analysis-scripts/ghidra_rh850/step12_groups.py` |
| `research/scripts/ghidra_rh850/step12_out.log` | `tools/analysis-scripts/ghidra_rh850/step12_out.log` |
| `research/scripts/ghidra_rh850/step13_out.log` | `tools/analysis-scripts/ghidra_rh850/step13_out.log` |
| `research/scripts/ghidra_rh850/step13_writers.py` | `tools/analysis-scripts/ghidra_rh850/step13_writers.py` |
| `research/scripts/ghidra_rh850/step14_af1be.py` | `tools/analysis-scripts/ghidra_rh850/step14_af1be.py` |
| `research/scripts/ghidra_rh850/step14_out.log` | `tools/analysis-scripts/ghidra_rh850/step14_out.log` |
| `research/scripts/ghidra_rh850/step15_out.log` | `tools/analysis-scripts/ghidra_rh850/step15_out.log` |
| `research/scripts/ghidra_rh850/step15_r28.py` | `tools/analysis-scripts/ghidra_rh850/step15_r28.py` |
| `research/scripts/ghidra_rh850/step16_encoding.py` | `tools/analysis-scripts/ghidra_rh850/step16_encoding.py` |
| `research/scripts/ghidra_rh850/step16_out.log` | `tools/analysis-scripts/ghidra_rh850/step16_out.log` |
| `research/scripts/ghidra_rh850/step16b_encoding.py` | `tools/analysis-scripts/ghidra_rh850/step16b_encoding.py` |
| `research/scripts/ghidra_rh850/step17_out.log` | `tools/analysis-scripts/ghidra_rh850/step17_out.log` |
| `research/scripts/ghidra_rh850/step17_scan.py` | `tools/analysis-scripts/ghidra_rh850/step17_scan.py` |
| `research/scripts/ghidra_rh850/step18_consumers.py` | `tools/analysis-scripts/ghidra_rh850/step18_consumers.py` |
| `research/scripts/ghidra_rh850/step18_out.log` | `tools/analysis-scripts/ghidra_rh850/step18_out.log` |
| `research/scripts/ghidra_rh850/step19_chain.py` | `tools/analysis-scripts/ghidra_rh850/step19_chain.py` |
| `research/scripts/ghidra_rh850/step19_out.log` | `tools/analysis-scripts/ghidra_rh850/step19_out.log` |
| `research/scripts/ghidra_rh850/step1_probe.py` | `tools/analysis-scripts/ghidra_rh850/step1_probe.py` |
| `research/scripts/ghidra_rh850/step20_out.log` | `tools/analysis-scripts/ghidra_rh850/step20_out.log` |
| `research/scripts/ghidra_rh850/step20_ptrscan.py` | `tools/analysis-scripts/ghidra_rh850/step20_ptrscan.py` |
| `research/scripts/ghidra_rh850/step21_xrefcheck.py` | `tools/analysis-scripts/ghidra_rh850/step21_xrefcheck.py` |
| `research/scripts/ghidra_rh850/step22_commitfns.py` | `tools/analysis-scripts/ghidra_rh850/step22_commitfns.py` |
| `research/scripts/ghidra_rh850/step22_out.log` | `tools/analysis-scripts/ghidra_rh850/step22_out.log` |
| `research/scripts/ghidra_rh850/step23_eeec8.py` | `tools/analysis-scripts/ghidra_rh850/step23_eeec8.py` |
| `research/scripts/ghidra_rh850/step23_out.log` | `tools/analysis-scripts/ghidra_rh850/step23_out.log` |
| `research/scripts/ghidra_rh850/step24_f2064.py` | `tools/analysis-scripts/ghidra_rh850/step24_f2064.py` |
| `research/scripts/ghidra_rh850/step25_out2.log` | `tools/analysis-scripts/ghidra_rh850/step25_out2.log` |
| `research/scripts/ghidra_rh850/step25_save.py` | `tools/analysis-scripts/ghidra_rh850/step25_save.py` |
| `research/scripts/ghidra_rh850/step26_77a00.py` | `tools/analysis-scripts/ghidra_rh850/step26_77a00.py` |
| `research/scripts/ghidra_rh850/step26_out.log` | `tools/analysis-scripts/ghidra_rh850/step26_out.log` |
| `research/scripts/ghidra_rh850/step27_decomp.py` | `tools/analysis-scripts/ghidra_rh850/step27_decomp.py` |
| `research/scripts/ghidra_rh850/step27_out.log` | `tools/analysis-scripts/ghidra_rh850/step27_out.log` |
| `research/scripts/ghidra_rh850/step28_out.log` | `tools/analysis-scripts/ghidra_rh850/step28_out.log` |
| `research/scripts/ghidra_rh850/step28_probe.py` | `tools/analysis-scripts/ghidra_rh850/step28_probe.py` |
| `research/scripts/ghidra_rh850/step29_ground_truth.py` | `tools/analysis-scripts/ghidra_rh850/step29_ground_truth.py` |
| `research/scripts/ghidra_rh850/step29_out.log` | `tools/analysis-scripts/ghidra_rh850/step29_out.log` |
| `research/scripts/ghidra_rh850/step2_disasm.py` | `tools/analysis-scripts/ghidra_rh850/step2_disasm.py` |
| `research/scripts/ghidra_rh850/step2_out.log` | `tools/analysis-scripts/ghidra_rh850/step2_out.log` |
| `research/scripts/ghidra_rh850/step30_followup.py` | `tools/analysis-scripts/ghidra_rh850/step30_followup.py` |
| `research/scripts/ghidra_rh850/step30_out.log` | `tools/analysis-scripts/ghidra_rh850/step30_out.log` |
| `research/scripts/ghidra_rh850/step31_out.log` | `tools/analysis-scripts/ghidra_rh850/step31_out.log` |
| `research/scripts/ghidra_rh850/step31_ptrscan.py` | `tools/analysis-scripts/ghidra_rh850/step31_ptrscan.py` |
| `research/scripts/ghidra_rh850/step3_jumptable.py` | `tools/analysis-scripts/ghidra_rh850/step3_jumptable.py` |
| `research/scripts/ghidra_rh850/step3_out.log` | `tools/analysis-scripts/ghidra_rh850/step3_out.log` |
| `research/scripts/ghidra_rh850/step4_disasm2.py` | `tools/analysis-scripts/ghidra_rh850/step4_disasm2.py` |
| `research/scripts/ghidra_rh850/step4_out.log` | `tools/analysis-scripts/ghidra_rh850/step4_out.log` |
| `research/scripts/ghidra_rh850/step5_handlers.py` | `tools/analysis-scripts/ghidra_rh850/step5_handlers.py` |
| `research/scripts/ghidra_rh850/step5_out.log` | `tools/analysis-scripts/ghidra_rh850/step5_out.log` |
| `research/scripts/ghidra_rh850/step6_out.log` | `tools/analysis-scripts/ghidra_rh850/step6_out.log` |
| `research/scripts/ghidra_rh850/step6_xrefs.py` | `tools/analysis-scripts/ghidra_rh850/step6_xrefs.py` |
| `research/scripts/ghidra_rh850/step7_callers.py` | `tools/analysis-scripts/ghidra_rh850/step7_callers.py` |
| `research/scripts/ghidra_rh850/step7_out.log` | `tools/analysis-scripts/ghidra_rh850/step7_out.log` |
| `research/scripts/ghidra_rh850/step8_final.py` | `tools/analysis-scripts/ghidra_rh850/step8_final.py` |
| `research/scripts/ghidra_rh850/step8_out.log` | `tools/analysis-scripts/ghidra_rh850/step8_out.log` |
| `research/scripts/ghidra_rh850/step9_handler_types.py` | `tools/analysis-scripts/ghidra_rh850/step9_handler_types.py` |
| `research/scripts/ghidra_rh850/step9_out.log` | `tools/analysis-scripts/ghidra_rh850/step9_out.log` |
| `research/scripts/ghidra_rh850/vipapp/p0_probe.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/p0_probe.py` |
| `research/scripts/ghidra_rh850/vipapp/p0b_list.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/p0b_list.py` |
| `research/scripts/ghidra_rh850/vipapp/s10_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s10_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s10_sweep.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s10_sweep.py` |
| `research/scripts/ghidra_rh850/vipapp/s11_residue.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s11_residue.py` |
| `research/scripts/ghidra_rh850/vipapp/s12_xref_eeprom.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s12_xref_eeprom.py` |
| `research/scripts/ghidra_rh850/vipapp/s13_coverage_scoped.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s13_coverage_scoped.py` |
| `research/scripts/ghidra_rh850/vipapp/s14_scalar_scan.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s14_scalar_scan.py` |
| `research/scripts/ghidra_rh850/vipapp/s15_check_str.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s15_check_str.py` |
| `research/scripts/ghidra_rh850/vipapp/s16_callers.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s16_callers.py` |
| `research/scripts/ghidra_rh850/vipapp/s17_sanity.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s17_sanity.py` |
| `research/scripts/ghidra_rh850/vipapp/s18_find_gp.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s18_find_gp.py` |
| `research/scripts/ghidra_rh850/vipapp/s19_find_tp.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s19_find_tp.py` |
| `research/scripts/ghidra_rh850/vipapp/s1_import.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s1_import.py` |
| `research/scripts/ghidra_rh850/vipapp/s20_decompile.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s20_decompile.py` |
| `research/scripts/ghidra_rh850/vipapp/s21_scan_table_refs.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s21_scan_table_refs.py` |
| `research/scripts/ghidra_rh850/vipapp/s22_decompile2.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s22_decompile2.py` |
| `research/scripts/ghidra_rh850/vipapp/s23_callers2.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s23_callers2.py` |
| `research/scripts/ghidra_rh850/vipapp/s24_scalar_scan2.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s24_scalar_scan2.py` |
| `research/scripts/ghidra_rh850/vipapp/s25_xref_swc.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s25_xref_swc.py` |
| `research/scripts/ghidra_rh850/vipapp/s26_decompile_swc.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s26_decompile_swc.py` |
| `research/scripts/ghidra_rh850/vipapp/s27_disasm_ctx.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s27_disasm_ctx.py` |
| `research/scripts/ghidra_rh850/vipapp/s28_sbi_scan.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s28_sbi_scan.py` |
| `research/scripts/ghidra_rh850/vipapp/s29_sbi_context.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s29_sbi_context.py` |
| `research/scripts/ghidra_rh850/vipapp/s2_probe_head.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s2_probe_head.py` |
| `research/scripts/ghidra_rh850/vipapp/s30_container.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s30_container.py` |
| `research/scripts/ghidra_rh850/vipapp/s31_wide_dump.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s31_wide_dump.py` |
| `research/scripts/ghidra_rh850/vipapp/s32_jumptable_entry.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s32_jumptable_entry.py` |
| `research/scripts/ghidra_rh850/vipapp/s33_eeprom_err_strings.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s33_eeprom_err_strings.py` |
| `research/scripts/ghidra_rh850/vipapp/s33_find_prologue.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s33_find_prologue.py` |
| `research/scripts/ghidra_rh850/vipapp/s33_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s33_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s34_eeprom_readapi.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s34_eeprom_readapi.py` |
| `research/scripts/ghidra_rh850/vipapp/s34_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s34_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s35_ctx.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s35_ctx.py` |
| `research/scripts/ghidra_rh850/vipapp/s35_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s35_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s36_bufscan.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s36_bufscan.py` |
| `research/scripts/ghidra_rh850/vipapp/s36_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s36_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s37_ee8k.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s37_ee8k.py` |
| `research/scripts/ghidra_rh850/vipapp/s37_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s37_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s3_analyze.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s3_analyze.py` |
| `research/scripts/ghidra_rh850/vipapp/s3_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s3_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s4_check_entry.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s4_check_entry.py` |
| `research/scripts/ghidra_rh850/vipapp/s5_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s5_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s5_seed.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s5_seed.py` |
| `research/scripts/ghidra_rh850/vipapp/s6_aggressive.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s6_aggressive.py` |
| `research/scripts/ghidra_rh850/vipapp/s6_out.log` | `tools/analysis-scripts/ghidra_rh850/vipapp/s6_out.log` |
| `research/scripts/ghidra_rh850/vipapp/s7_coverage.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s7_coverage.py` |
| `research/scripts/ghidra_rh850/vipapp/s9_gaps.py` | `tools/analysis-scripts/ghidra_rh850/vipapp/s9_gaps.py` |
| `research/scripts/ghidra_rh850/vipboot/all_disasm.txt` | `tools/analysis-scripts/ghidra_rh850/vipboot/all_disasm.txt` |
| `research/scripts/ghidra_rh850/vipboot/s10_sweep.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s10_sweep.py` |
| `research/scripts/ghidra_rh850/vipboot/s11_out.log` | `tools/analysis-scripts/ghidra_rh850/vipboot/s11_out.log` |
| `research/scripts/ghidra_rh850/vipboot/s11_residue.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s11_residue.py` |
| `research/scripts/ghidra_rh850/vipboot/s12_i2c_strings.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s12_i2c_strings.py` |
| `research/scripts/ghidra_rh850/vipboot/s13_dump_disasm.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s13_dump_disasm.py` |
| `research/scripts/ghidra_rh850/vipboot/s14_decompile.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s14_decompile.py` |
| `research/scripts/ghidra_rh850/vipboot/s1_import.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s1_import.py` |
| `research/scripts/ghidra_rh850/vipboot/s2_vectors.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s2_vectors.py` |
| `research/scripts/ghidra_rh850/vipboot/s3_setup.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s3_setup.py` |
| `research/scripts/ghidra_rh850/vipboot/s4_prune.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s4_prune.py` |
| `research/scripts/ghidra_rh850/vipboot/s5_uninit_and_seed.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s5_uninit_and_seed.py` |
| `research/scripts/ghidra_rh850/vipboot/s6_analyze.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s6_analyze.py` |
| `research/scripts/ghidra_rh850/vipboot/s6_out.log` | `tools/analysis-scripts/ghidra_rh850/vipboot/s6_out.log` |
| `research/scripts/ghidra_rh850/vipboot/s7_coverage.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s7_coverage.py` |
| `research/scripts/ghidra_rh850/vipboot/s8_aggressive.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s8_aggressive.py` |
| `research/scripts/ghidra_rh850/vipboot/s8b_aggressive.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s8b_aggressive.py` |
| `research/scripts/ghidra_rh850/vipboot/s9_gaps.py` | `tools/analysis-scripts/ghidra_rh850/vipboot/s9_gaps.py` |
| `research/scripts/ghidra_rh850/x86_step1_64_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step1_64_out.log` |
| `research/scripts/ghidra_rh850/x86_step1_import.py` | `tools/analysis-scripts/ghidra_rh850/x86_step1_import.py` |
| `research/scripts/ghidra_rh850/x86_step1_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step1_out.log` |
| `research/scripts/ghidra_rh850/x86_step2_64_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step2_64_out.log` |
| `research/scripts/ghidra_rh850/x86_step2_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step2_out.log` |
| `research/scripts/ghidra_rh850/x86_step2_symbols.py` | `tools/analysis-scripts/ghidra_rh850/x86_step2_symbols.py` |
| `research/scripts/ghidra_rh850/x86_step3_64_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step3_64_out.log` |
| `research/scripts/ghidra_rh850/x86_step3_aif_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step3_aif_out.log` |
| `research/scripts/ghidra_rh850/x86_step3_coverage.py` | `tools/analysis-scripts/ghidra_rh850/x86_step3_coverage.py` |
| `research/scripts/ghidra_rh850/x86_step3_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step3_out.log` |
| `research/scripts/ghidra_rh850/x86_step3b_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step3b_out.log` |
| `research/scripts/ghidra_rh850/x86_step4_64_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step4_64_out.log` |
| `research/scripts/ghidra_rh850/x86_step4_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step4_out.log` |
| `research/scripts/ghidra_rh850/x86_step4_tasks.py` | `tools/analysis-scripts/ghidra_rh850/x86_step4_tasks.py` |
| `research/scripts/ghidra_rh850/x86_step5_inspect.py` | `tools/analysis-scripts/ghidra_rh850/x86_step5_inspect.py` |
| `research/scripts/ghidra_rh850/x86_step5_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step5_out.log` |
| `research/scripts/ghidra_rh850/x86_step6_aif.py` | `tools/analysis-scripts/ghidra_rh850/x86_step6_aif.py` |
| `research/scripts/ghidra_rh850/x86_step6_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step6_out.log` |
| `research/scripts/ghidra_rh850/x86_step6b_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step6b_out.log` |
| `research/scripts/ghidra_rh850/x86_step7_out.log` | `tools/analysis-scripts/ghidra_rh850/x86_step7_out.log` |
| `research/scripts/ghidra_rh850/x86_step7_xrefs.py` | `tools/analysis-scripts/ghidra_rh850/x86_step7_xrefs.py` |
| `research/scripts/ghs_dump.py` | `tools/analysis-scripts/ghs_dump.py` |
| `research/scripts/mdi2_client/mdi2_doip_direct.py` | `tools/analysis-scripts/mdi2_doip/mdi2_doip_direct.py` |
| `research/scripts/mdi2_client/requirements.txt` | `tools/analysis-scripts/mdi2_doip/requirements.txt` |
| `research/scripts/r2script.txt` | `tools/analysis-scripts/r2script.txt` |
| `research/session_logs/RESEARCH_STATE_MAP_JUN2026.md` | `evidence/session-logs/RESEARCH_STATE_MAP_JUN2026.md` |
| `research/session_logs/project_research_20DEC25_0917.txt` | `evidence/session-logs/project_research_20DEC25_0917.txt` |
| `research/session_logs/quick_security.txt` | `evidence/session-logs/quick_security.txt` |
| `research/session_logs/security_assessment_20DEC25.txt` | `evidence/session-logs/security_assessment_20DEC25.txt` |
| `research/tools/SPSToolBridge.txt` | `tools/bench/SPSToolBridge.txt` |
| `research/tools/aaos_audio_probe/.gitignore` | `tools/bench/aaos_audio_probe/.gitignore` |
| `research/tools/aaos_audio_probe/AndroidManifest.xml` | `tools/bench/aaos_audio_probe/AndroidManifest.xml` |
| `research/tools/aaos_audio_probe/README.md` | `tools/bench/aaos_audio_probe/README.md` |
| `research/tools/aaos_audio_probe/build.sh` | `tools/bench/aaos_audio_probe/build.sh` |
| `research/tools/aaos_audio_probe/src/org/gminfo/audioprobe/MainActivity.java` | `tools/bench/aaos_audio_probe/src/org/gminfo/audioprobe/MainActivity.java` |
| `research/tools/bench_can/bench_can_validation.py` | `tools/bench/bench_can/bench_can_validation.py` |
| `research/tools/bench_can/boot_radio_elk.py` | `tools/bench/bench_can/boot_radio_elk.py` |
| `research/tools/bench_can/elk_raw_boot.py` | `tools/bench/bench_can/elk_raw_boot.py` |
| `research/tools/bench_can/gcs_gt.py` | `tools/bench/bench_can/gcs_gt.py` |
| `research/tools/bench_can/radio_on.py` | `tools/bench/bench_can/radio_on.py` |
| `research/tools/bench_can/radio_owner.py` | `tools/bench/bench_can/radio_owner.py` |
| `research/tools/bench_can/replay_can_keepalive.py` | `tools/bench/bench_can/replay_can_keepalive.py` |
| `research/tools/bench_can/replay_can_power_on_keepalive.py` | `tools/bench/bench_can/replay_can_power_on_keepalive.py` |
| `research/tools/bench_can/replay_original_can_capture.py` | `tools/bench/bench_can/replay_original_can_capture.py` |
| `research/tools/bench_can/reset_vip_can.py` | `tools/bench/bench_can/reset_vip_can.py` |
| `research/tools/bench_can/test_bench_can_validation.py` | `tools/bench/bench_can/test_bench_can_validation.py` |
| `research/tools/bench_can/test_boot_radio_elk.py` | `tools/bench/bench_can/test_boot_radio_elk.py` |
| `research/tools/bench_can/test_elk_raw_boot.py` | `tools/bench/bench_can/test_elk_raw_boot.py` |
| `research/tools/bench_can/test_radio_on.py` | `tools/bench/bench_can/test_radio_on.py` |
| `research/tools/build_ipk_entry_probe.py` | `tools/bench/build_ipk_entry_probe.py` |
| `research/tools/can_bench_emulator.py` | `tools/bench/can_bench_emulator.py` |
| `research/tools/ghs_probe/AndroidManifest.xml` | `tools/bench/ghs_probe/AndroidManifest.xml` |
| `research/tools/ghs_probe/CMakeLists.txt` | `tools/bench/ghs_probe/CMakeLists.txt` |
| `research/tools/ghs_probe/ghs_probe.c` | `tools/bench/ghs_probe/ghs_probe.c` |
| `research/tools/run_can_bench.sh` | `tools/bench/run_can_bench.sh` |
| `research/tools/test_build_ipk_entry_probe.py` | `tools/bench/test_build_ipk_entry_probe.py` |
| `research/tools/test_can_bench_emulator.py` | `tools/bench/test_can_bench_emulator.py` |
| `research/tools/tis2web.txt` | `tools/bench/tis2web.txt` |
| `research/type4_radio_info/10018100.dll` | `research/eeprom-calibration/type4_radio_info/10018100.dll` |
| `research/type4_radio_info/10018101.cfx` | `research/eeprom-calibration/type4_radio_info/10018101.cfx` |
| `research/type4_radio_info/README.md` | `research/eeprom-calibration/type4_radio_info/README.md` |
| `research/type4_radio_info/RadioControllerInfo.cpp` | `research/eeprom-calibration/type4_radio_info/RadioControllerInfo.cpp` |
| `research/type4_radio_info/RadioControllerInfo.def` | `research/eeprom-calibration/type4_radio_info/RadioControllerInfo.def` |
| `research/type4_radio_info/RadioControllerInfo_Type4.zip` | `research/eeprom-calibration/type4_radio_info/RadioControllerInfo_Type4.zip` |
| `research/type4_radio_info/build.bat` | `research/eeprom-calibration/type4_radio_info/build.bat` |
| `research/type4_radio_info/build_clang.bat` | `research/eeprom-calibration/type4_radio_info/build_clang.bat` |
| `research/type4_radio_info/make_spat.py` | `research/eeprom-calibration/type4_radio_info/make_spat.py` |
| `research/type4_radio_info/radioinfo.tbl` | `research/eeprom-calibration/type4_radio_info/radioinfo.tbl` |
| `research/type4_radio_info/tisvcsv4_iface.h` | `research/eeprom-calibration/type4_radio_info/tisvcsv4_iface.h` |
