# Ground-Up AAOS Replacement — eMMC Wipe, No GM/GHS Code Retained

**Scope.** Requirements and gap analysis for a *complete* replacement: wipe the entire eMMC
(`block 0` up — every GM/Harman partition, not just the Android guest) and boot a self-built
AOSP/AAOS stack with **no GHS INTEGRITY hypervisor and no GM code retained**. This is a
different goal from [`AOSP_REPLACEMENT_RESEARCH.txt`](../rights-and-roadmap/AOSP_REPLACEMENT_RESEARCH.txt)
(AR), which scopes replacing *only* the Android guest while GHS stays in place as the vehicle-
integration layer — AR is kept separate per that doc's own note that the rights/remote/AOSP trio
is not merged; this doc does not restate AR's content, only points at it. Owner-stated intent:
GM's AAOS is "trash, bloated, poorly optimized" — the target is a correct, from-scratch build on
the owned hardware, not a patched derivative.

**Probe kernel's role, stated explicitly:** the bare-metal RAM-boot Linux in
[`../boot-update-recovery/elk-probe-builder/`](../boot-update-recovery/elk-probe-builder/) is an
**information-gathering and hardware-access tool** (eMMC read/write access, display/VIP/CAN
probing) — it is not a substrate this build runs on top of, and it is not itself a candidate
final-boot kernel. Its subsystem status is tracked in
[`SUBSYSTEM_BRINGUP_STATUS.md`](../boot-update-recovery/elk-probe-builder/SUBSYSTEM_BRINGUP_STATUS.md).

**Evidence tags** per repo convention (`research/README.md`): `[C]` confirmed, `[S]` static/
structural, `[I]`/`[inferred]`, `[U]` unverified/open, `[FW]` firmware-stated, `[X]` external.

---

## 1. The gate this design has to clear, stated once

Every path below eventually has to get a bootloader stage to execute un-OEM-signed code. The
root of trust for that decision is **not on eMMC**: `[C]` Intel CSE Boot Guard (SPI/OTP-fused,
enforcing per `FWSTS3`) measures IBBL/IBB/OBB from SPI, and the OBB component — Boot-Guard-signed,
holding the GM "OS-Kernel" RSA-2048 key — is what verifies the `ghs_isys` slot content at the
IAS/`ipk.` loader stage before anything in `bootloader_a/b` or `ghs_isys_a/b` (eMMC) runs. Full
derivation: [`BOOT_TRUST_ANCHOR_AND_KEYS.md`](../boot-update-recovery/BOOT_TRUST_ANCHOR_AND_KEYS.md).
Wiping eMMC does not remove or relocate this anchor.

`[C]` This is not theoretical for this project — it was hit directly. The slim-loader milestone
work (packed a minimal `ipk.` shim into the live `ghs_isys_a/b` slots) proved **format acceptance**
(magic/MB1/size/CRC32C gates, all recomputable) but the slot's real RSA-2048/SHA-256 signature
check — enforced upstream of eMMC — rejects anything not signed with the OEM key. A controlled
1-byte signature-corruption A/B test confirmed enforcement empirically (B rejected to fastboot
despite every recomputable check passing). Control-transfer into a custom shim was proven **only**
via the separate, unauthenticated ELK/Intel-fastboot RAM-boot path (volatile — gone at next cold
power-on unless ELK is re-entered and re-fed).

`[U]` ELK's own fastboot image-acceptance for a *flash* (not RAM-boot) write is separately
unconfirmed; `sys.oem_unlock_allowed=0` and a 2026-11-17 owner-requested `fastboot flashing
unlock` attempt timed out with no established result (`GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`
§"Owner-requested unlock attempt"). Both unlock gates (`oem_unlock_allowed` → `fastboot flashing
unlock`) remain closed with **no known software path** (AR §1.5/§4.2). The only path either
AR or this doc's own roadmap names past that is hardware-level: VIP JTAG, chip-off, or glitching
against Boot Guard/OEMLock — zero work started on this track (AR §7.3).

**Consequence for design:** a boot flow where the final AAOS kernel sits on eMMC and is loaded
*directly* by the IAS loader or ELK with no RAM-boot step at normal power-on is blocked today,
full stop — not by missing build work, but by an enforced signature check this project has
already independently measured. A boot flow where ELK is **manually, deliberately re-entered
every power-on** to stage a loader is not blocked — it is exactly the mechanism already proven
live (three independent entry methods: CAN routine F000/8180 RID 0xFF01, UDS profile 0x0D
CAN-only re-entry, cold MEI/CSE selector-2+reset). The owner has accepted manual ELK entry "for
the time being," which is what makes the rest of this doc buildable now instead of blocked on
hardware work with no committed timeline.

---

## 2. Boot-flow design options (the question assigned to this doc)

### Option A — custom kernel resident on eMMC, loaded directly, no per-boot ELK step
**Status: blocked, not a near-term design.** Requires defeating the Boot-Guard-rooted signature
check at the IAS-loader/`ghs_isys` boundary (or at ELK/kernelflinger's own image-acceptance,
whichever stage is kept). No known software bypass exists; the only documented route is a
hardware-level Boot Guard/OEMLock defeat (AR §7.3), unstarted. Not ruled in or out as an eventual
goal — just not where near-term design effort should go.

### Option B — ELK manually entered each boot → stages a slim-loader → loads the real AAOS kernel from eMMC
**Status: buildable now, extends proven work.** ELK's RAM-boot accepts arbitrary unsigned
payloads (that's the probe kernel's entire delivery mechanism today). The `slim-loader/`
component already built (bare-metal `.code64`-entry ELF/`ipk.` shim, `pack_ipk.py`/`verify_ipk.py`)
is the right shape for this role, but its current purpose was proving control-transfer into the
`ghs_isys` slot specifically — for this design it would instead need to: (1) be fed via ELK
RAM-boot directly (skip the slot/signature question entirely, since ELK's RAM-boot path doesn't
go through that gate), (2) probe/enumerate the eMMC device, (3) read the real AAOS
kernel+initramfs from a defined eMMC location, (4) hand off execution to it.

`[U]` open, unresearched by this project: **the actual hand-off mechanism for step 4.** Linux
`kexec` is the obvious analogy but is compiled **out** in every kernel config checked here —
the probe kernel's `kernel.config`/`probe03.config` both carry `# CONFIG_KEXEC is not set`, and
GM's own stock Y181 kernel has it disabled too. Two sub-options, neither yet evaluated:
  - Build the slim-loader as a true minimal bare-metal stage (no Linux at all, extending what it
    already is) that does its own eMMC block I/O and a raw ELF/Multiboot jump into the real AAOS
    kernel — consistent with its current design, but eMMC block I/O from a from-scratch bare-metal
    stage (no driver stack) is nontrivial and unstarted.
  - Build/boot a *minimal* Linux first stage with `CONFIG_KEXEC`/`CONFIG_KEXEC_FILE` enabled
    specifically for this role, then `kexec` into the real AAOS kernel. Simpler I/O story (real
    eMMC/MMC driver stack available), but reintroduces a full Linux boot as a staging step — needs
    its own config, separate from the probe kernel (which this doc's scope note above says is not
    to be built on top of).

Neither sub-option has prototype work; this is the single largest open item in this doc.

---

## 3. AOSP/AAOS build requirements — gap table

| Area | What's known/already done | What's still needed |
|---|---|---|
| **Board/device tree** | Celadon `device-androidia` (`celadon/s/mr0/apollo`, Android 12/Apollo Lake) identified as the closest public analog — clone commands ready in [`GORDON_PEAK_CELADON_INTELLIGENCE.md`](../boot-update-recovery/GORDON_PEAK_CELADON_INTELLIGENCE.md). Not yet forked or adapted. That doc itself flags the TI949 serializer and GHS/VIP integration as "distinct vendor dependencies not covered by it" — doubly true here since GHS is gone entirely, not just unused. | Fork `device-androidia` + `device-intel-sepolicy`; write real panel/serializer board config (portable from working probe-kernel panel bring-up — see Display row, `SUBSYSTEM_BRINGUP_STATUS.md`); design a **new eMMC partition layout** (no reason to keep GM's `vda1`-`vda26` scheme) |
| **Kernel line** | Two candidate trees exist locally: `lts` (4.19.283, Android-GKI-flavored — carries `build.config.gki*`) and `stable735` (7.3.5, current probe-kernel bring-up line). Both already carry `CONFIG_ANDROID_BINDER_IPC`, `BINDERFS`, `ASHMEM`, `CGROUPS`/`CPUSETS`/`PSI`, `F2FS_FS`, `OVERLAY_FS` — a real head start, not a from-scratch Android kernel config job. | **Unresearched: which line AAOS/AOSP Android-12-era build tooling actually expects.** GKI ABI commitments are version-coupled; 7.3.5 is far newer than any shipped Android GKI branch and compatibility with AOSP build/sepolicy tooling targeting Android 12 is unverified. `CONFIG_SECURITY_SELINUX` is currently **off** in both probe configs — fine for early bring-up (permissive-equivalent) but AOSP's own init/sepolicy tooling assumes kernel SELinux support exists; low-cost to turn on now even if run permissive |
| **Vehicle HAL** | `probe-tools/vip-link.c`, `vip-link-inspect.c`, `vip-uart-probe.c` are the only proven direct-VIP access tools. VIP HDLC Tx/Rx and CAN power-state handling were separately exercised and passed on an earlier probe build. | Full HAL from scratch — **larger scope than AR's guest-replacement case**, because there GHS stays and proxies chimes/camera-switching/CAN; here there is no GHS to proxy anything, so steering/speed/gear/chimes/camera-arbitration all move into this HAL directly against VIP |
| **Audio HAL** | None. Existing audio docs (`audio/audio_subsystem.md`) describe the **GHS-mediated** AAOS-guest audio architecture (PCM passthrough, AVB/`eavb` stack) — not applicable once GHS is removed. | Identify the actual audio codec/hardware path independent of GHS PCM passthrough — unresearched; probe-kernel audio bring-up is currently "not working, no attempt made" (`SUBSYSTEM_BRINGUP_STATUS.md`), so even the raw driver layer underneath this HAL doesn't exist yet |
| **Camera HAL** | None. LVDS camera inputs currently not working at the raw kernel/driver level on the probe kernel either. | Raw driver bring-up first (same prerequisite logic as before — can't build a HAL against a device node that doesn't work), then HAL |
| **Display** | **Working** — panel bring-up (`stable735/panel.c`/`display-panel.c`) is proven on hardware: automatic GPIO-reset-hold, i915 framebuffer 2400×960, serializer status read confirmed, owner visually verified. | Port into the board-config/device-tree layer; low risk, already de-risked |
| **Storage/signing** | Stock eMMC partition map and its signing requirements are documented (`platform/partitions_storage.md`, this doc §1 above) but are being discarded, not reused. | New partition layout undesigned. Decide whether to keep any AVB/vbmeta-style verification (now with your own keys, for update-chain hygiene) or drop it entirely — open owner decision, not a technical blocker either way |
| **Toolchain/build host** | `macpro` already proven for kernel cross-builds and image packaging (`stable735`/`upstream` build scripts, QEMU pre-flight checks). Celadon's `CIV_01.22.03.32_A12` repo manifest is the nearest known-reference AOSP build target, explicitly flagged in `GORDON_PEAK_CELADON_INTELLIGENCE.md` as unverified against this exact board. | A full AOSP `repo sync`/`lunch`/`make` build is far heavier (disk, time) than anything built on `macpro` so far — not yet sized/tested at that scale |

---

## 4. Net: what's actually left before this is "begin-able"

1. **Resolve §2's Option B hand-off mechanism** (bare-metal eMMC-reading shim vs. minimal-Linux-
   with-kexec staging kernel) — this blocks everything downstream, since it determines what the
   slim-loader needs to become.
2. **Fork and adapt a board/device tree** (Celadon `device-androidia` starting point) — can start
   in parallel, doesn't depend on #1.
3. **Pick the kernel line** (4.19 "lts" GKI vs. 7.3.5) against actual AOSP Android-12 tooling
   requirements — unresearched, needed before any AAOS-side build attempt, independent of #1/#2.
4. **Finish raw driver bring-up for touch/audio/camera/Wi-Fi-association** on the probe kernel
   first (its actual job, per this doc's scope note) — HALs for audio/camera can't be scoped
   against drivers that don't exist yet.
5. **Write the Vehicle HAL and new eMMC partition layout** — both are from-scratch work with no
   blocking dependency on hardware-level Boot Guard defeat, since Option B doesn't need it.

Nothing above requires the hardware-level Boot Guard/OEMLock defeat (Option A) to begin. That
track (VIP JTAG/chip-off, AR §7.3) stays a separate, long-term, currently-unstarted line of work —
relevant only if "manual ELK entry every boot" stops being acceptable later.

## Open conflicts

None yet. This doc is new; check `research/README.md`'s corpus-wide Open Conflicts section before
treating §1's signature-enforcement framing as settled if later bench work contradicts it.
