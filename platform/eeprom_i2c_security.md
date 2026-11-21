# EEPROM / I2C Security

Pointer-only doc, trimmed 2026-11-21. The EEPROM memory map, the Seed-Bypass-Indicator (SBI)
mechanism — primary SBI data byte `0x0441`, **backup SBI data byte `0x0A81`** (not `0x0A80`,
which is a marker byte, not the data byte) — the VIP CalGroup RE findings, the I2C bus table, and
the GPIO/serial/kernel local hardware attack surface are all owned by
[`../research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](../research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
(ELA) — read that doc for all of the above, not this one.

This doc previously carried a full prose duplicate of that content, including the `0x0A80` data-byte
error above. As of 2026-11-21 the duplicate is removed: every fact it carried that was not already
in ELA has been folded into ELA (§2, §5.1, §5.2, §5.4, §7, §8, §8.1); see ELA's "Known discrepancy"
note (§0) and History §12 (2026-11-21 entry) for the full account of what moved where.

**Related:** [security.md](security.md) (Android security posture, ProtoKey/ADB auth, kernel
mitigations, SELinux denials — owns the MEC/ADB-unlock *consequence* of the SBI flag),
[hardware_specs.md](../hardware/specs.md) (physical I2C adapter/controller enumeration, VIP MCU part
number, UART/serial hardware), [ota_update_stack.md](ota_update_stack.md) (OTA signing). External:
`../eeprom/` (EEPROM programming workflow/tooling — this doc does not duplicate or edit that
directory) and [ELA](../research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md) (primary EEPROM research,
authoritative for everything not reproduced here — which, after this trim, is everything).

## Platform-specific live captures

These are the platform-tree live-capture facts this doc originates; they are cited here as the
source of record, and the full underlying detail is folded into ELA (§2, §8, §8.1) so it is not
left as a second prose copy.

- `[C]` live-Y175 2026-10-05 (`dev_listing.txt`): SELinux-enforcing device-node labels for
  `i2c-0..3`/`i2c-7` (`saturnhd_device`, `i2c_device`, `dirana3_device`, `display_panel`), and the
  GPIO (`/dev/gpiochip0-3` root-only) and serial (`ttyS1` root-only, `ttyACM1` `sxm_device`)
  permission/label confirmations — see [ELA §8](../research/eeprom-calibration/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
  and ELA §8.1.
- `[C]` live-Y175 2026-10-05: Android security posture on the captured unit — `ro.secure=1`,
  `ro.adb.secure=1`, `ro.debuggable=0`, adb shell as normal uid 2000 (`u:r:shell:s0`); the unit was
  in secured operation, not the SBI-bypass path — see ELA §2.
- `world_writable.txt` (same capture pass): exactly two world-writable nodes on the live unit, both
  stock memcg `cgroup.event_control` — no GPIO path among them — see ELA §8.1.
