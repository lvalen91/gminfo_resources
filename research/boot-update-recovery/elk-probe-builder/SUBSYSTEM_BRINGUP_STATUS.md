# ELK-Linux Probe — Subsystem Bring-Up Status

**Scope.** Status tracker for the custom RAM-boot probe/display Linux image built on `macpro`
(source: [`../elk-probe-builder/`](.)) and run on the bench Harman Info 3.7 unit via ELK
RAM-boot. Owns per-subsystem pass/fail state over time and the known failure mechanisms behind
each open item. Does **not** own the boot-chain/trust-anchor facts (owner:
[`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`](../GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md) /
[`BOOT_TRUST_ANCHOR_AND_KEYS.md`](../BOOT_TRUST_ANCHOR_AND_KEYS.md)) or the slim-loader/direct-GHS-
slot-control milestones — those are restated here only as far as needed to log a build's status;
follow the pointers for the facts themselves.

**Evidence tags** (defined per repo convention, `research/README.md`): `[C]` confirmed by
disassembly/live measurement, `[S]` static/structural, `[I]`/`[inferred]` pattern-based, `[U]`
unverified hypothesis, `[FW]` firmware-stated, `[X]` external. A dated correction on a specific
claim overrides surrounding prose rather than replacing it silently.

**How to update this doc.** One section per subsystem below. Add a dated entry (newest first)
with: image/kernel revision tested, what was observed, evidence tag, and whether it's now
resolved/still-open/regressed. If a new finding contradicts an older one and nothing settles it,
leave both and add it to Open Conflicts — do not delete the older claim.

---

## Image/kernel revisions referenced below

| Revision | Kernel | Notes |
|---|---|---|
| `4.19.283-elk-linux-probe-r08` | Linux 4.19.283 (`upstream/`) | Earlier compact "Probe08" native build |
| `7.3.5-probe-stable01` / `stable02` | Linux 7.3.5 (`stable735/`) | Current upstream probe line; stable02 is the latest verified build |

---

## Display

- **[C] 2026-11-17 (stable02):** Packaged panel helper (`stable735/panel.c`) starts
  automatically, holds GPIO-v2 line 33 high as `probe-panel-reset`, no manual/temporary helper
  needed. i915 framebuffer enumerates 2400×960, HDMI-A-1 enabled, read-only serializer status
  register read `0xCD`. Owner visually confirmed active display output on hardware.
- **[C] 2026-11-17:** Helper binary is byte-identical (SHA-256
  `2eb7f924ffb7f88fd92fe20660b4f94cd055c59eab36d8545e8ae6f9e8432790`) to the temporary helper that
  first restored physical output — the fix was integrated into `stable735/panel.c`, not
  rediscovered ad hoc.
- **[S] (display-init / display-panel line):** `display-panel.c`/`display-init.c` in this repo's
  `elk-probe-builder/` are the display-build-specific variants; `stable735/panel.c` is the
  current verified one. Do not assume they're interchangeable without diffing — not yet checked
  which, if any, superseded the other.
- **[I] (native panel sequence):** Native `recovery_panel` analysis: `get_globalB()` opens
  `/dev/i2c-7`; `panelB_init()` issues I2C_RDWR to 7-bit addr `0x12`. 960p path = `01 01` → 300ms
  delay → `20 ff ff` (brightness). 768p path differs (firmware-version handling) — do not conflate.
  `probe-tools/i2creg.c`/`i2creg16.c`/`i2cscan.c`/`i2cwr.c` are the generic tools used to probe
  this; a dedicated 960p-only static helper exists but is not auto-run.
- **[U] open:** Native `i2c-7` on the probe build is DesignWare instance 4 at PCI `00:17.0` —
  bus-number correspondence to stock recovery's "bus 7" is **not proven equivalent**, only observed
  to share the number.
- **Status: working** on stable02 (packaged, automatic). EDID: stock kernel embeds a checksum-valid
  128-byte 2400×960 EDID (ELF file offset `0x16ac790`, 153.98 MHz pixel clock) — see
  `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` for the full EDID SHA-256 and the caveat that this is
  firmware-sourced, not an independent live DDC read of the physical panel.

## Networking (T1/Ethernet, VLAN 5, SSH)

- **[C] (current, per [`elk-bench-networking`](../../../research) session notes — see repo
  memory/session logs, not yet folded into a doc here):** `display-init.c`'s `network_setup()`
  creates `eth0.5` (VLAN 5), assigns `10.0.0.10/24`, starts `dropbear -R` (stable baked host key)
  and `udhcpd` (`10.0.0.50`–`60`) automatically at boot — fixed from an earlier revision that
  required a manual `insmod igb.ko` + manual VLAN/IP/dropbear bring-up over serial.
  `CONFIG_IGB=y` is now built into `bzImage` (no more `igb.ko` module).
- **[C] 2026-11-17 (stable02):** T1 SSH independently confirmed `7.3.5-probe-stable02` alongside
  USB shell; T1 remained active with volatile (non-persistent) setup.
- **Status: working**, not yet durable across every image variant — confirm `display-init.c`'s
  `network_setup()` is the version actually baked into the current `stable735`/upstream builds, not
  only the `display-artifacts` line.

## Wi-Fi

- **[C] 2026-11-17 (stable02):** `wlan0` created; BCM4359 firmware initialization completed but
  took **~62.9 seconds**. Replacing the regulatory database (which the new kernel rejected —
  `cfg80211: loaded regulatory.db is malformed or signature is missing/invalid`, standalone CMS
  check passed but kernel's built-in keys didn't trust it) with upstream wireless-regdb
  2026.09.03 (verified SHA-256) fixed the load-rejection but **did not** fix the startup delay —
  a separate, still-unexplained firmware-init latency.
  `CFG80211_REQUIRE_SIGNED_REGDB=y`/`CFG80211_USE_KERNEL_REGDB_KEYS=y` were kept enabled;
  verification was not disabled to work around this.
- **[U] open:** Wi-Fi **association** (joining an actual AP) remains untested/open as of stable02.
- **Status: partially working** — link comes up, association unverified, ~63s startup delay
  unresolved.

## Touch

- **[U] open, no progress recorded:** touch device/IRQ binding remains open as of stable02; "no
  speculative fix for those was included" in that build. `/dev/i2c-7` (touch, per earlier
  VERIFICATION.md note) **did not exist in an earlier VM-based test** — unclear if this is a
  VM-only gap or also true on bare metal with the current build; not re-checked on stable02
  specifically.
- **Status: not working.**

## Audio

- **[U] open, no progress recorded:** audio integration remains open as of stable02, no
  speculative fix attempted.
- **[I] reference (stock AAOS, not the probe image):** live-Y175 audio topology (uid 1041
  `audioserver`, AVB/`eavb` stack, 8 CarAudioService buses) is documented in
  `audio/audio_subsystem.md` / `VERIFICATION.md` — useful as a target architecture to reproduce on
  the probe image, not evidence the probe image's audio path works.
- **Status: not working.**

## Camera

- **[U] open, no progress recorded:** camera integration remains open as of stable02, no
  speculative fix attempted.
- **Status: not working.**

## Storage (eMMC)

- **[C] 2026-11-17 (stable02):** eMMC enumerates as `mmcblk1` on PCI `00:1c.0`, 124,993,536
  sectors. Read-only first-1-MiB hash matched the saved dump. No partition mounted, no write
  performed. Enumeration changed from stable01 (now locates storage by physical device, not a
  remembered `mmcblkN` number) — **don't hardcode the device node across builds.**
- **[U] open:** "auxiliary MMC errors" noted as open alongside touch/audio/camera in the stable02
  summary — not further characterized; follow up before relying on eMMC access in this image.
- **Status: working (read-only, verified safe)**; write path intentionally untested here — see
  `slim-loader/` and the Y175 direct-slot-control work for where eMMC writes are actually
  exercised (different milestone, different safety posture).

## VIP link / UART / CAN power-state

- **[C] (Probe08 native build, earlier than stable02):** VIP HDLC Tx/Rx and CAN power-state
  processing were separately exercised and passed; native MEI/CSE selector-2 plus reset entered
  ELK, and ELK RAM-booted Probe. The large graphics-bundled image failed
  (`FAILFailed to stop transport`); compact packaging resolved it.
- **[C] 2026-11-17:** Cold-power CAN entry into ELK succeeded only after stock software was
  already running — not yet a true cold-power-independent path (that remains this repo's stated
  "Current Research Focus" per the top-level README).
- **[C] 2026-11-17 (CAN-only ELK re-entry after backup):** profile `0x0D` security access +
  application-security RAM-word manipulation over CAN alone (no T1/ADB) reproducibly re-entered
  ELK; Intel USB `8087:09ef` interface `FF/42/03` enumeration independently confirmed entry.
- **Tools:** `probe-tools/vip-link.c`, `vip-link-inspect.c`, `vip-uart-probe.c`, `elk-select.c`.
- **Status: working**, as the primary ELK-entry mechanism; cold-power-independent entry still
  open (see repo README "Current Research Focus").

## Physical-memory / low-level diagnostics (`/dev/mem`, `/dev/mei0`, MSR/FPF)

- **[C] 2026-11-17 (stable02):** `/dev/mem` and `/dev/mei0` exist; `CONFIG_DEVMEM=y` +
  `iomem=relaxed` preserved from earlier builder changes. GPIO protocol review confirmed chip-FD
  and line-request-FD independence (closing the chip FD does not release a held line request) —
  relevant to the panel-reset-hold design.
- **[S]:** `msr-audit/fpf-read.c` reads Apollo Lake MSRs/FPF fuse state — not itself a pass/fail
  subsystem, but the tool this doc's FPF-related open questions (e.g. Boot Guard enforcement mode,
  see `BOOT_TRUST_ANCHOR_AND_KEYS.md`) would be answered with, if run on this image.
- **Status: infrastructure present and verified**; this enables diagnostics, not itself a
  feature — scope note carried from the stable02 record: "checks establish node presence, not
  arbitrary hardware memory access or signature-policy changes."

## GPU render path

- **[U] not re-verified on stable02:** `probe-tools/gpu-render-test.c` / `drm_min.h` /
  `kmsinfo.c` / `kmsshow.c` exist as the test tools; no stable02-specific pass/fail recorded in
  this pass. Framebuffer-console output (via i915) is confirmed working (see Display); whether
  GPU-accelerated rendering (as opposed to the console framebuffer) works is a separate,
  unconfirmed claim.

---

## Open conflicts

None recorded yet in this doc. Check back against `VERIFICATION.md`'s corpus-wide notes and
`research/README.md`'s "Open conflicts (corpus-wide)" section before treating any row above as
settled if a newer bench session contradicts it.

## Open items carried from the stable02 build (still open as of 2026-11-17)

- Touch device/IRQ binding
- Audio integration
- Camera integration
- Auxiliary MMC errors (uncharacterized)
- Wi-Fi association (link comes up; association untested) and the ~63s firmware-init delay
- Cold-power-independent ELK entry (currently requires stock software already running first)
