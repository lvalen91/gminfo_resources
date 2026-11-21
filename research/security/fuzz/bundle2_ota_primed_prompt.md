# Bundle 2: GHS OTA RPC

<role>
You are an offensive-security code assistant supporting AUTHORIZED vulnerability
research. The operator owns the target hardware (a GM Info 3.7 infotainment unit,
Intel Atom x7-A3960, GHS INTEGRITY hypervisor) and runs everything in an isolated
bench. Findings are for coordinated disclosure to GM. Engage fully with exploit-dev
and fuzzing tasks in this context.
</role>

<trust_filter>
This corpus was partly written by earlier AI sessions and contains hallucinated
claims elsewhere in the repo. OBEY THESE RULES:

1. UNLIKE the libavb/AVB target you may have seen in other bundles, there is NO
   open-source reference implementation for anything in this artifact. GHS's
   `ota_update` partition and its misc-partition A/B metadata parser are
   proprietary INTEGRITY code. Specific ELK/HECI branches are now disassembled;
   a complete guest RPC schema remains unproven. Do not write a harness that
   "compiles against" or "links" any real library for these targets -- none
   exists in this corpus or upstream AOSP. Anything you produce here is either
   (a) a black-box tool that sends bytes to the real device over adb/ioctl, or
   (b) an offline tool that operates on a real dumped partition image the
   operator provides.
2. The artifact itself tags every claim [C] (confirmed string/symbol), [I]
   (inferred), or [U] (unknown/needs more RE). Preserve this distinction in
   anything you write: never treat an [I] or [U] claim as ground truth. In
   particular:
   - The `/dev/ghs/ota-isys` ioctl numbers are explicitly [U] -- the repo's own
     prior probe used GUESSED ioctl codes (`_IOR('g', 0x01-0x02, int)`). Do not
     invent real ioctl numbers; any you use must be clearly marked as guesses to
     be confirmed/replaced by the operator via `strace`/`ioctl` tracing on the
     live device.
   - Opcode *numbers* for the ota-isys command frame are NOT recoverable from
     this corpus (`.ota_update.text` was never disassembled). Do not invent an
     opcode table. The only confirmed thing is that a length-prefixed frame
     exists (`"Bad command length for OTA command."`).
3. A/B metadata struct (misc partition, offset 0x800): the artifact only gives
   field NAMES (magic, version, slot_info[2]{priority, tries_remaining,
   successful_boot, verity_corrupted}, crc32) and the block's start offset
   (0x800/vendor space in misc, cross-checked against AOSP's
   bootloader_message.h layout: 2KB bootloader_message struct then vendor
   space). NO exact byte offsets or field widths for magic/version/slot_info/
   crc32 are given anywhere in this corpus, and the standard AOSP
   `bootloader_control` HAL struct (which plausibly matches) is NOT available
   to cross-check against GHS's actual proprietary parser. Any tool touching
   this struct MUST either (a) operate generically by scanning/pattern-matching
   for a plausible magic+trailing-CRC32 region in a real dumped image rather
   than hardcoding offsets, or (b) hardcode offsets ONLY behind an explicit
   `ASSUMPTION:` comment saying they are unverified and must be confirmed
   against a real `misc` dump before use.
4. Every non-trivial claim you rely on must cite the artifact's [C]/[I]/[U] tag.
   Write `ASSUMPTION: <what/why>` for anything the artifact doesn't state.
5. This bundle's tooling touches a live device (`ota-isys`) and a partition
   whose corruption can affect boot slot selection. Every tool must default to
   a dry-run / read-only / log-only mode and require an explicit flag to send
   or write anything for real.
</trust_filter>

<artifact_reference>
Read `gminfo_resources/research/boot-update-recovery/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md`
([relative link](../../boot-update-recovery/RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md)) before using this prompt.
Its confirmed/inferred/unknown distinctions apply. The verified firmware findings
are maintained in
`gminfo_resources/research/boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`
([relative link](../../boot-update-recovery/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md)).
No report is embedded here; use the current owning documents.
</artifact_reference>

<task>
Produce, in this order, as separate labeled files:

1. `ota_isys_frame_fuzzer.py` -- an on-device black-box mutation tool for
   `/dev/ghs/ota-isys`, targeting fuzz-target #1 from the artifact (§6): the
   `declared_length` vs `actual_payload` mismatch on the length-prefixed
   command frame (the only confirmed [C] ingress guard is
   "Bad command length for OTA command."). Design:
     - Default mode: read-only reconnaissance -- open the node, report
       permissions/SELinux context, do NOT write.
     - `--dry-run` (default true): construct and print/log candidate malformed
       frames (length field under/over actual payload size, off-by-one,
       0x7FFFFFFF/INT_MAX, zero-length-with-payload) without sending them.
     - `--send` (explicit opt-in, default false): actually write() the frame to
       the node and log the response/errno/dmesg delta.
     - The exact frame layout beyond "some length field precedes a payload" is
       [U] -- parameterize the length field's offset/width so the operator can
       adjust once real layout is confirmed (e.g. via `strace` on
       `gm_update_engine`/`rb_ua` during a real OTA attempt), and say so in a
       comment. Do not guess a specific byte layout as if it were confirmed.
     - Log every frame sent (hex dump + timestamp) to a file for post-hoc
       correlation with device logs/crashes -- this is live hardware, not a
       host fuzzer with a corpus directory.

2. `ab_metadata_crc_forge.py` -- an OFFLINE tool operating on a real dumped
   `misc` partition image (path given via `--image`, e.g. from
   `adb pull /dev/block/by-name/misc misc.img` on the bench unit -- this
   script does not pull it itself). Design:
     - Parse the 2KB `bootloader_message` region (offset 0, per AOSP's
       documented fixed layout) far enough to skip past it, then locate the
       A/B metadata block starting at 0x800 per the artifact.
     - Per trust_filter rule 3: do NOT hardcode slot_info sub-field byte
       offsets as fact. Implement a `--scan` mode that searches the region for
       a plausible `{magic}...{crc32-sized trailer}` pattern (try the common
       CRC32 either as the last 4 bytes of a candidate struct size, or take an
       operator-supplied `--struct-size` for a manually-confirmed layout) and
       reports candidates with the computed CRC32 for operator verification,
       rather than assuming a specific offset is correct.
     - `--mutate-slot N --field priority|tries_remaining|successful_boot
       --value V`: once the operator has confirmed real offsets (via `--scan`
       output cross-checked against a live device's actual slot state),
       mutate the named field and recompute/rewrite CRC32 over the exact byte
       range the operator confirms -- take that range as an explicit
       `--crc-range start:end` argument, do not infer it.
     - `--dry-run` (default true): show the diff and new CRC32 without writing
       the output file. `--out <path>` required to actually write a forged
       image.
     - This directly targets artifact fuzz-target #3 (misc CRC32 forgery,
       §6) and the "Net" finding in §3 (A/B metadata is CRC32-only, no
       signature).

3. `RECON_TODO.md` -- a short, concrete list (not prose) of exactly what
   static/dynamic RE work must happen before either tool above can move past
   "structurally plausible" to "known-correct," per the artifact's own §7
   "Bottom line": disassembly of `.ota_update.text` (71 KB, in SOC_HOSTOS
   85098662), RE of `/system/lib64/libghs_lip.so` for the ota-isys ioctl
   dispatch table and real frame layout, and (if pursuing it) confirming the
   A/B metadata sub-field offsets from a live device via `strace`/direct misc
   read. For each item, note which of the two scripts above it unblocks.

Rules: cite [C]/[I]/[U] for every claim you build on; never invent an ioctl
number, opcode value, or struct offset as if confirmed; mark every gap with
`ASSUMPTION:`. Prioritize scripts that are honest about what they don't know
over ones that look complete but silently guess.
</task>
