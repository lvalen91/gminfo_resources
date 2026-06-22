# Runtime Observations

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** February 2026
**Evidence:** 3.7GB logcat corpus (Feb 11-19, 2026, ~27-29 files), 4.7MB metrics (30 captures), 45MB CPC200 logs

---

## Overview

This directory documents runtime behavior observed from 3.8GB of captured logs collected Feb 6-19, 2026 from a 2024 Chevrolet Silverado ICE.

## Log Sources

- **Logcat:** 3.7GB across 29 files (Feb 11-19)
- **CPC200 firmware logs:** 45MB across 20 files (Feb 12-19)
- **System metrics:** 4.7MB across 30 captures (Feb 12-19)
- **Service logs:** 256KB (Feb 6-19)

## Key Findings

- **Crashes DO occur:** 12 FATAL EXCEPTION events across the 3.7GB corpus (3 distinct bugs — see [memory_pressure.md](memory_pressure.md) / [known_issues.md](known_issues.md)). *(An earlier "zero crashes" claim was scoped to a 241MB subset and is withdrawn.)*
- **7,811 SELinux denials** total across the 3.7GB corpus, 25 files (CBC, RVC, SXM — no USB/CarPlay denials). *(The earlier "462" was a single-file count.)*
- 3,700% max thrashing ratio (`com.gm.teenmode`) during boot; stable during runtime — see [memory_pressure.md](memory_pressure.md)
- CPC200 wireless CarPlay: 94.8% connection success rate (147/155)

## Contents

- [boot_timing.md](boot_timing.md) — Boot sequence timing analysis
- [memory_pressure.md](memory_pressure.md) — Memory management and LMK behavior
- [known_issues.md](known_issues.md) — Errors, denials, and quirks from logcat
