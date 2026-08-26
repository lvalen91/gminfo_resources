# Android-Side ProtoKey/SBI Trace — Aug 2026

**Goal:** backward-trace the SBI/EEPROM bypass's effect on the Android side
(kernel init, ramdisk, vendor/system) rather than continuing to fight the
VIP's proprietary V850 firmware. Cross-check against older corpus research
on the ADB-cert-disablement topic.

**Headline result: recovered the real raw `SOC_SYSTEM` (3.2GB) and
`SOC_VENDOR` (466MB) partition images**, closing a blocker that affected
multiple threads this session (`diagnosticsd` and `gm_protokey` were both
previously "permission denied on live device, binary unavailable"). Real
`gm_protokey` binary extracted and decompiled — corrects a load-bearing
assumption in the existing corpus about what `vendor.gm.security.state`
actually means.

---

## 1. How the partition images were found and read

- `firmware/update_packages/Y181/extractions/ramdisk.cpio.gz` is
  mislabeled — it's **LZ4-compressed, not gzip** (same provenance-drift
  pattern seen elsewhere in this corpus: `lz4 -d` works, `gunzip` doesn't).
  Real cpio payload extracts cleanly once decompressed correctly.
- `firmware/update_packages/Y181/86331654` (3.2GB) and `.../86331650`
  (466MB) are **real raw ext4 partition images** (not zips, despite one
  earlier `file` misidentification) — confirmed by a valid ext4 superblock
  (`debugfs show_super_stats`) and a genuine AVB footer (`AVBf` magic) at
  the end of each file. Per `delivery_manifest.csv`: `86331654` =
  `SOC_SYSTEM`, `86331650` = `SOC_VENDOR`.
- **No mount needed** — `e2fsprogs`'s `debugfs` (already installed via
  Homebrew) reads/lists/dumps files directly from the raw image on macOS,
  which has no native ext4 support. This is the reusable technique for any
  future work needing files from these two images.

## 2. Ramdisk: real init.rc / SELinux property-label evidence

Extracted the real boot ramdisk and confirmed, directly (not by citation):
- `vendor.gm.security.state` — a real, `vendor_gm_security_state_prop`-labeled
  persistent property.
- `/data/vendor/gm/security/` (labeled `gm_protokey_valid_file`) and
  `/data/gmprotokey/` (labeled `gm_protokey_system_file`) — real paths,
  matching `UNTRIED_ATTACK_VECTORS.md` vectors #7 and #8 exactly.
- Real `vendor_sepolicy.cil` grep confirms `vendor.gm.security.state` is
  **set by** `gm_protokey`/`gm_protokey_system`, and **read by** four other
  domains: `gm_authManager`, `gmConnectionService`, `platform_app` (all
  privileged apps), `system_app` (all system apps).

## 3. `com.gm.android.gmauthmanagerservice` — real APK recovered, decompiled, and RULED OUT as the bypass consumer

Confirmed live and running on-device (`processes.txt`:
`system  1742  ... com.gm.android.gmauthmanagerservice`). Found and
extracted `GMAuthManagerService.apk` (2,038,667 B) and
`GMAuthTokenService.apk` (62,161 B) from the real `/system/priv-app/` and
`/system/app/` trees inside the recovered `SOC_SYSTEM` image. Decompiled
both cleanly with `jadx` (492 real Java source files for the first, 1
class failed decompilation, not fatal).

**Real code found:** `GMAdbAuth.java`, `GMAdbPolicy.java`,
`GMAdbAuthService.java`, `GMAdbSocketServer.java`, `GMUpdateCertificate.java`,
`GMOcspCheckFrequencyHandler.java`, `ClientCertificateRevokedReceiver.java` —
this is the complete implementation of GM's **legitimate, signed-policy ADB
grant mechanism** (dealer/Techline tooling): AES-encrypted policy files,
VIN/CSM-ID matching, X.509 cert-chain signature verification, OCSP
revocation checking, expiration enforcement.

**Confirmed by exhaustive grep across every file in the app: this code path
does NOT read `vendor.gm.security.state`, `ro.adb.secure`, `ro.debuggable`,
or SELinux enforcement mode at all.** The only `SystemProperties` reads in
the whole app are `persist.gm.register.vin`, `persist.gm.register.csm`,
`persist.gm.trust_sys_time`, `sys.gmsec.ocsp_freq`, `sys.gmsec.exp_enforce`
— none related to the VIP/EEPROM signal.

**Conclusion: `gm_authManager`'s read permission on
`vendor_gm_security_state_prop` (real, per SELinux policy) is not exercised
by its current Java-layer code.** This is a real negative result, not an
unexamined gap — either the permission is legacy/unused, or it's consumed
by a native library bundled in the APK that `jadx` doesn't decompile
(not checked this pass). This app is the *legitimate* ADB path, structurally
separate from the SBI-bypass ("traditional non-GM-cert ADB") path.

## 4. `gm_protokey` — real binary recovered, decompiled, and a corpus assumption corrected

Extracted `/vendor/bin/gm_protokey` (21,720 B, real x86-64 PIE ELF, stripped)
directly from the recovered `SOC_VENDOR` image — this exact binary was
"Permission Denied from uid=2000" on every prior live-device attempt
documented in this corpus (`diagnostics/ethernet_uds_diagnosticsd.md`).
Also recovered `/vendor/bin/diagnosticsd` (426,824 B — exact byte-size match
to the value already documented from live enumeration, confirming this is
genuinely the same binary) as a bonus, closing a gap from this session's
earlier DoS-finding work (`DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026.md`),
where the binary itself was never available.

Imported cleanly into Ghidra (real ELF, no reconstruction needed — a much
easier target than the VIP's proprietary V850 firmware). Decompiled all 160
functions. Found the exact property-write call:

```c
// FUN_001045c0 @ 001045c0
void FUN_001045c0(char *param_1)
{
  ...
  iVar1 = property_get("vendor.gm.security.state", local_78, ...);
  if (0 < iVar1) {
    iVar1 = strncmp(param_1, local_78, 0x5c);
    if (iVar1 != 0) {
      property_set("vendor.gm.security.state", param_1);
      __android_log_buf_print(3, 4, "GM_PROTO_KEY",
        "Current security state : %s => %s", local_78, param_1);
    }
  }
}
```

**Correction to a load-bearing assumption:** the entire binary contains
exactly **four** distinct state-name strings ever passed to this setter:
`"data_locked"`, `"initializing"`, `"warm_reboot"`, `"stopped"`. There is
**no** `"bypassed"`/`"secured"`/`"enforced"`/`"permissive"` string anywhere
in the binary. **`vendor.gm.security.state` is a lifecycle/boot-state
indicator (has protokey processing completed, or is data-decryption still
gated), not a direct bypass/security-outcome flag** the way
`platform/security.md`'s "gm_protokey detects bypass → SELinux PERMISSIVE"
framing implies. `main()`'s logic: on first boot, state starts at
`"initializing"`; otherwise `"system enters DATA_LOCKED mode"` and state is
set to `"data_locked"` while waiting for protokey to complete — this reads
as gating **Android's data-encryption unlock**, not SELinux enforcement
directly. What actually flips SELinux mode (if this binary does that at
all) was not located in this 160-function binary.

**Real next lead, not yet pulled:** `gm_protokey` dynamically links
`libpal_security.so` (confirmed present in the same `SOC_VENDOR` image,
135,600 B, at `/vendor/lib64/libpal_security.so`) — at only 21KB, `gm_protokey`
itself is almost certainly a thin daemon wrapper; the real VIP-IPC/crypto
logic (reading the seed, deciding pass/fail, and whatever *does* set
SELinux mode) most likely lives in that library, not yet extracted or
analyzed this pass.

## 5. Correction to `MASTER_REFERENCE.md`'s Y175/Y177/Y181 table (owner-supplied)

> **SUPERSEDED 2026-08-25.** Y175 VIP_APP was subsequently reacquired and diffed three-way
> against Y177/Y181: the VIP security function is a **full ~906-byte validator in Y175, Y177,
> AND Y181** — there is **no stub in Y175 or any build** (the stub reading was a fixed-address
> misparse of shifted code). So the "Permissive due to a stubbed VIP function in Y175" theory
> below is refuted at the VIP layer; SELinux mode is OS-side, and the VIP function gates ADB/seed
> auth. See `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2 and the Y175 partition investigation. The
> paragraph below is retained as the session's historical reasoning.

The project owner corrected a misreading during this session: the
"SELinux Permissive on bypass" behavior was **theorized for Y175** (due to
a stubbed VIP security function), **later fixed in Y177**. This session's
earlier reading of `MASTER_REFERENCE.md §5.1`'s table (columns labeled
"Y177 | Y181", showing "Permissive | Enforcing" for the SELinux-on-bypass
row) had been taken at face value as "Y177=Permissive" — per the owner,
that's a mislabel; the Permissive behavior belongs to Y175, not Y177.
**Y175 firmware/artifacts are not available in this corpus to independently
verify** — this is owner-supplied domain knowledge, not independently
re-derived here. `platform/security.md`'s general "gm_protokey detects
bypass → PERMISSIVE" framing (no cited evidence found near it) is doubly
suspect now: likely describing Y175-era behavior, generalized incorrectly,
AND (per §4 above) not clearly matching what the real Y181 `gm_protokey`
binary's code actually does. **`MASTER_REFERENCE.md`'s table itself still
needs a fix** (change "Y177" column label/data to "Y175" if that's what it
was actually describing) — not done in this pass, flagged for follow-up.

## 6. `libpal_security.so` — full request/response chain traced, ZERO content validation found (HEADLINE FINDING)

Extracted `/vendor/lib64/libpal_security.so` (135,600 B, real x86-64 ELF,
source path embedded in binary: `/gmplatform/gm/gmsecurity/vip/private/pal_security.cpp`)
from the recovered `SOC_VENDOR` image. Decompiled all 509 functions
(`libpal_security_decompiled.c`, 639,392 B, persisted). This is the direct
VIP↔SoC IPC library (`NVipPal` C++ namespace, `CommIPC` transport class) that
`gm_protokey` links against. **The full request→response→consumption chain
is now traced end to end, with every gate identified:**

```
gm_protokey main()
  → protokey_pal_register_callback(&FUN_00103a50)   [gm_protokey's callback,
                                                        aka "protokey_pal_set_key"]
    → DAT_00123508 = callback_ptr
    → pal_security_init()                            [libpal_security.so @ 0010f000]
        loops pal_sec_open_ipc_channel() until connected
        → spawns background thread: pal_sec_do_work  [@ 0010d6e0]

pal_sec_do_work()  (background thread loop, while DAT_00123508 != 0)
  → pal_sec_send_protokey_request()  [@ 0010e320]
      CommIPC::writeMessage(ipc_handle, protokey_request_byte, 1)   // 1-byte req to VIP
  → CommIPC::readMessage(ipc_handle, buf, 0x200)                    // blocking read
  → pal_sec_parse_message(buf, len)  [@ 0010e850]
      GATE 1: len == 0x11 (17 bytes: 1 status byte + 16 key bytes) else reject
              ("Wrong protokey size. Expected: %u. Actual: %zu.")
      → pal_sec_check_protokey_status(buf[0])  [@ 0010f4b0]
          GATE 2: switch on VIP's self-reported status byte —
            1 = success (only case returning 0/pass)
            2 = ICUSB not enabled   5 = invalid parameters
            3 = BIS key not valid   6 = ICUSB busy
            4 = protokey gen fail   7 = ICUS key program failed
                                    8 = secret key load failure
            default = "wrong status message"
          any non-1 value → 0xffffffff (fail), loop retries
      if GATE 1 and GATE 2 both pass:
          local_48/uStack_40 = buf[1..16]     // 16 key bytes copied VERBATIM,
                                               // no transform, no check
          (*DAT_00123508)(&local_48, 0x10)    // → calls gm_protokey's FUN_00103a50
          DAT_00123510 = 1                    // "key received" flag

gm_protokey :: FUN_00103a50(key_ptr, key_len)   ["protokey_pal_set_key"]
  __android_log_buf_print(..., "Protokey callback invoked by PAL")
  GATE 3: key_ptr != 0 && key_len != 0   (pointer/length sanity only)
  __android_log_buf_print(..., "Received valid ProtoKey from PAL.")
  → dispatches key via C++ vtable call on a singleton object (DAT_00107d68+0x30)
    (downstream consumer not further resolved this pass — no vold/keystore/
    fscrypt strings found anywhere in gm_protokey, so it's either an internal
    class or reached via a library not covered by string search)
```

**There is no cryptographic or content validation of the 16-byte key
material anywhere in this chain, on either the transport library
(`libpal_security.so`) or the consuming daemon (`gm_protokey`).** The three
gates that exist are: (1) exact message length, (2) the VIP's own
self-reported one-byte status code, (3) a non-null pointer/length check.
None of them inspect the key bytes themselves — not an entropy check, not a
known-bad-value check, not a signature/MAC. **The entire trust boundary
between the VIP and Android collapses to a single byte: the VIP's
self-reported status code.** If the VIP reports `status = 1`, Android accepts
whatever 16 bytes follow, unconditionally.

**This directly answers the user's original question.** It doesn't by itself
prove the SBI bypass forces `status = 1` from the VIP (that mechanism is
VIP-side, in the still-unresolved `FUN_ram_000b67d0` seed/key state machine —
see `eeprom/CORRECTIONS_AUG2026.md`), but it proves conclusively that **if**
the VIP can be made to report success for a degenerate/non-genuine key (which
is exactly what the SBI-driven CAN `$27` seed evidence already suggests),
**there is no independent SoC-side check that would catch or reject it.**
The Android side is a pure length/status gate with no cryptographic
verification of its own — the security model is "trust the VIP completely,"
which is precisely the kind of single point of failure the SBI/EEPROM bypass
appears to be exploiting.

## 7. Summary of concrete next steps

1. ~~Extract and analyze `libpal_security.so`~~ — **done, see §6.**
2. **Check the native side of `GMAuthManagerService.apk`** for any bundled
   `.so` that reads `vendor.gm.security.state` — the Java layer doesn't,
   but a native library might (not checked this pass).
3. **Fix `MASTER_REFERENCE.md`'s Y175/Y177/Y181 table** per the owner's
   correction (§5 above) — still not applied.
4. Now that `diagnosticsd` is recovered too, the DoS finding
   (`DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026.md`) can be
   re-verified against the real binary instead of black-box-only evidence,
   and its "exact source-level cause" open item (single dispatcher vs.
   fixed pool) can likely now be resolved via real disassembly.
5. **Resolve the vtable sink at `DAT_00107d68+0x30`** in `gm_protokey` — the
   final consumer of the accepted key (§6). Not yet identified; likely an
   internal storage/state class given no vold/keystore/fscrypt strings exist
   in the binary. Would show exactly what changes on disk/in-process once a
   key is accepted (candidates: the `gm_protokey_valid_file`/
   `gm_protokey_system_file` paths under `/data/vendor/gm/security/` and
   `/data/gmprotokey/` identified in §2).
6. **Still fully open, VIP-side (out of scope for this Android-side trace):**
   what drives the VIP to emit `status = 1` for a degenerate/SBI-bypassed
   seed in the first place — the `FUN_ram_000b67d0` state machine and its
   callers, per `eeprom/CORRECTIONS_AUG2026.md`.

## Artifacts

- Real partition images (not persisted — too large, stay at their
  existing corpus location):
  `firmware/update_packages/Y181/86331654` (SOC_SYSTEM, 3.2GB),
  `firmware/update_packages/Y181/86331650` (SOC_VENDOR, 466MB).
- Extracted binaries, persisted:
  `GM_research/.../analysis/extracted_artifacts/vendor_binaries_real/`
  (`gm_protokey`, `diagnosticsd`, `libpal_security.so`).
- Decompiled output, persisted in the same directory:
  `gm_protokey_decompiled.c` (160 functions),
  `libpal_security_decompiled.c` (509 functions).
- Decompiled APKs: `/tmp/gm_auth_apks/` (not yet persisted).
