# Y177 (Y177.6.1 GAS) — SELinux / policy artifacts

**Provenance:** extracted 2026-09-26 from the Y177 USB update package (NOT a live-device pull) —
`firmware/update_packages/Y177/` blobs `86283152` (SOC_SYSTEM), `86283156.zip` (SOC_VENDOR),
`86283160` (SOC_PRODUCT), all ext4 inside zips per `delivery_manifest.csv`. There is **no live Y177
`getenforce` capture** (no Y177 device was enumerated); do not fabricate a `raw/selinux_status.txt`.

`pulled_files/`:
- `plat_sepolicy.cil`, `vendor_sepolicy.cil`, `plat_pub_versioned.cil`, `product_sepolicy.cil` — CIL policy sources.
- `sepolicy` — the monolithic loaded binary policy (byte-identical to vendor `precompiled_sepolicy`, sha `027861ca…`).
- `build.prop` — `/system/build.prop`.

**Established facts (see `../../research/UNTRIED_ATTACK_VECTORS.md` for the full chain):**
- `ro.build.type=user`, `ro.secure=1`, `ro.debuggable=0`, release-keys → locked user build.
- **0 permissive domains** across all CIL sources.
- `plat_sepolicy.cil` is **byte-identical to Y181's** → no permissive policy change existed Y177→Y181.
- Boot cmdline (`86283154`) effective final tokens: `enforcing=1 androidboot.selinux=enforcing buildvariant=user`.
- Conclusion: **Y177 boots SELinux Enforcing.** The "VIP forces permissive" theory is refuted; there is
  no VIP/MEC→SELinux lever (unlike the deliberate ADB `is_secure_mode` hook).
