# Enumeration Captures

ADB / fastboot enumeration snapshots of the GM Info 3.7 (gminfo37 / A11 Radio) head unit,
collected with `scripts/gm_aaos_enum.sh` + `scripts/quick_security_check.sh` from an
unprivileged shell (uid 2000, SELinux Enforcing). Each set has the same template:
`raw/` (individual command outputs) + summary files + `enumeration_report.txt` +
`pulled_files/*.cil` + `pull_failures.txt`.

## Capture sets (chronological)

| Set | Date | Firmware | Notes |
|-----|------|----------|-------|
| `Y175/` | 2026-01-17 | Y175 (`W213E-Y175.5.2-SIHM22B-383.1`, kernel 4.19.283) | Older build |
| `Y181/` (root) | 2025-12-20 | Y181.3.2 (`W231E-Y181.3.2-SIHM22B-499.3`, kernel 4.19.305) | First Y181 dump |
| `Y181/apr2026/` | 2026-04-07 | Y181.3.2 (same) | Adds `network_scan.txt`, `ghs_attack_surface.txt`, `vulnerability_assessment.txt`, `accounts.txt` |
| `Y181/jun2026/` | 2026-06-21 | Y181.3.2 (same) | **Newest / most authoritative.** Live runtime snapshot; see `CLAIMS_VERIFICATION.md` |
| `VIP_log_2B.174.4.1_10JUL24.txt` | 2024-07-10 | — | VIP MCU UART boot log |

**Authoritative capture:** `Y181/jun2026/` is the newest and its
[`CLAIMS_VERIFICATION.md`](Y181/jun2026/CLAIMS_VERIFICATION.md) cross-checks repo claims against
live evidence (GPU Mesa 21.1.5, Vulkan 1.1.0, c2.android SW decoders, listening ports). Prefer it
over the older sets when they disagree. For corrected facts across the whole repo, see
[`../VERIFICATION.md`](../VERIFICATION.md).

## Notes / caveats

- **The three Y181 sets are the same firmware** (`Y181.3.2`, build 2025-07-22), re-dumped to
  capture runtime deltas — they are *not* different builds. Consequently the static-image
  artifacts are duplicated across them: `raw/kernel_config.txt` (172 KB) and the pulled
  `plat_sepolicy.cil` (~1.8 MB) / `vendor_sepolicy.cil` (~458 KB) are byte-identical in all three,
  and ~60% of `raw/*` is byte-identical between the Dec-2025 and Jun-2026 sets. Only genuinely
  time-varying files differ (`processes`, `logcat`, `meminfo`, `open_ports`, `all_properties`, …).
  This is ~8–10 MB of redundancy retained for self-contained snapshots; it has **not** been
  de-duplicated (doing so would break each set's self-containment — a deliberate open choice).
- **Permission-limited files** (empty/stub): `dmesg.txt`, `world_writable.txt`,
  `rollback_index.txt`, `partitions.txt`, `usb_devices.txt` are empty or denied because the
  capture shell is unprivileged (uid 2000). `pull_failures.txt` in each set records what could
  not be pulled. These are expected, not collection errors.
- **PII/redaction:** device serial and VIN are redacted (`<DEVSERIAL_REDACTED>`,
  `XXXXXXXXXXXXXXXXX`) in most files. Redaction has been applied unevenly across sets — if you
  add or regenerate captures, run the redaction step over `serial.txt`, `all_properties.txt`,
  `accounts.txt`, `logcat.txt`, and `enumeration_report.txt`.
