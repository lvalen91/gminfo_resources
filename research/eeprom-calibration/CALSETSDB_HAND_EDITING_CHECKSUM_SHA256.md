# CalSets.db Reverse Engineering

**Target:** GM MY22/Y181 IVI (Intel Apollo Lake SoC, GHS INTEGRITY host + Android 12L guest),
2024 Silverado head unit — the owner's own module.

**Scope — what lives here:** the `SCREEN_RESOLUTION` / `AllCalSets` database row model, the
`calserviced`/`diagnosticsd` checksum and SHA-256 integrity routines, the native CAN calibration
message header and `calserviced` override-package (`.calovride`) container format, direct-DB-edit
(Layer B) mechanics, the theme/brand/UI calibration-definition inventory, and the GMBrand and
`SCREEN_RESOLUTION` live CAN trials.

**What does NOT live here:**
- SELinux/DAC reachability for the `calserviced`/`vendor_cald` write path (CIL rules,
  write-allow/neverallow lists, feasibility verdict) → owned by
  [`SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md`](SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md).
  This doc states only the directory/UID/domain facts needed to explain why a DB edit requires a
  foothold, and points there for the reachability analysis itself.
- CAN613/614 scoped-VIP-RAM-write mechanism, the signed-header-rejection trial chronology, and the
  full custom-calibration trial/supersession log (SXM-disable, clear-all/recovery, stock LTZ
  restoration) → owned by
  [`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) and the
  `../diagnostics/` tree (`diagnosticsd_security_access.md`,
  `diagnosticsd_routines_and_recovery.md`). This doc cites those trials only where they bear
  directly on a CalSets.db/checksum fact, and keeps the GMBrand and `SCREEN_RESOLUTION` CAN
  trials here per this doc's own charter (they are the live demonstrations of the DB/container
  facts above, not generic CAN/UDS procedure).
- Signature/seed-key/SecurityAccess conclusions (RSA-2048 verification detail, CMAC, SBI gating) →
  owned by [`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- Vehicle calibration baseline (2,574-row Y181B export) → owned by
  `../platform/vehicle_config.md`.
- Updater/`DevCaloverrideInstaller`/USB MediaStore deployment mechanics → owned by
  `../platform/ota_update_stack.md`.
- Full stock-LTZ CAN5 rewrite bench result → owned by `../platform/can_network.md`.

Evidence tags: `[C]` confirmed from a binary/DB, `[I]` inferred, `[O]` open/needs a known-good
capture to pin.

Source artifacts: `scratchpad/diagx/calibrations__CalSets.db` (older captured SQLite DB),
`scratchpad/diagx/bin__diagnosticsd` (UDS receiver — checksum + SHA-256 code),
`scratchpad/diagx/bin__calserviced` (on-device override applier — SQL + package format).

**Note on scope of the "not demonstrated" caveat:** this doc's header caveat ("not a demonstrated
method for making the radio accept a modified signed calibration container") is about
**signed-container forgery** specifically — no resigned/forged CSM container has ever been
accepted. It does not mean no custom write has succeeded. **Accepted custom CAN/VIP writes** (the
CAN613/614 scoped-VIP-RAM method — SXM-disable, GMBrand=0, a transient `SCREEN_RESOLUTION` value)
have been achieved and are documented below and in DTW; none of them involved forging a signature,
they bypass the signature check by writing through a different, narrower channel. Keep these two
claims distinct when reading §§3e and 6.

---

## 0. Database values, transport integrity and signed-container authenticity

All 14 stock CSM containers carry independently verified RSA-2048 PKCS#1 v1.5/SHA-256 signatures,
and their signer records authenticate under the original Y181 production CA (the earlier claim
that calibration containers have no RSA signature was false).

> **History:** corrected 2026-11-11 — see
> [GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md), the
> central reference for the reconciled signature/seed-key/runtime-enforcement evidence.

Keyless checksums and hashes (§§1-2 below) are lower-layer integrity fields; recomputing them does
not produce a new valid signature. The 2026-11-16 CAN5/PEC0015 trace confirms a tested VIP
signed-header rejection — see DTW's
[verification record](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-direct-can5-repeat-and-header-signature-rejection-confirmed).
Package-format proof alone, or a generic UDS NRC `0x72`, must not be generalized to other routes,
root checks, or security profiles.

| Layer | Evidence | Acceptance limit |
|---|---|---|
| Diagnostic authorization | SBI-dependent UDS `$27`; stock LTZ write succeeded | Does not establish acceptance of arbitrary content |
| Transport integrity | Additive checksum (§1) + SHA-256 comparison (§2) | Does not replace signed-container authenticity |
| CSM signed format | Stock signatures verified; signature-only CAN5 control rejected with matching PEC0015 evidence | Confirmed on tested Y175 CAN5 profiles 01/03/05; other routes/profiles not demonstrated — see DTW |
| CAN613/614 scoped VIP-RAM write | Custom SXM-disable (slot 0C) accepted; original marker words restored | Retained across a 10.5-second supply-off cycle; owner-confirmed — see DTW's [success record](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-successful-custom-sxm-calibration-through-can613614) |
| Local database/override application | Native integer values + privileged calibration store | A filesystem/SELinux access path (§4), not a wire-side bypass |

**Baseline:** the older captured DB records `SCREEN_RESOLUTION = 2` (`SIZE_1280_BY_768`). The
Y181B recovery export instead records `SCREEN_RESOLUTION = 4` (`SIZE_2400_BY_960`,
`OverRiden = 8`), 2,574 total rows; both ZIPs contain the same exported DB.

> **History:** corrected 2026-11-12. No accepted custom write or transition from the older
> snapshot is inferred — the two DBs are independent captures. See the
> [vehicle baseline](../platform/vehicle_config.md#y181b-exported-baseline-2026-11-12).

`[C]` What lives in the older DB row is a bare SQLite integer, not a BLOB. Verified directly:

```
_id      = __-Jk4IQIEeWHkIX-EVZFdA
CalName  = SCREEN_RESOLUTION
CalType  = 4         (enum)
CalValue = 2         typeof() = 'integer'  ← native SQLite integer, length 1, NOT a BLOB
CalVersion = 4
OverRiden  = 0
Encode = NULL   ArrayLen = NULL
EnumID = _PWvKYIQHEeWHkIX-EVZFdA
```

Across the whole `AllCalSets` table there are zero BLOB cells (1,852 integer / 154 real / 567
text). The checksum and SHA-256 do not wrap the DB cell — they wrap the transfer/override
**container**. Editing the DB directly (Layer B, §4) is one operation; sealing a UDS payload
(Layer A) is a separate one. A custom UDS deployment was subsequently accepted using the separate
CAN613/614 VIP-RAM condition (DTW's success record above); recomputing the digest alone remains
insufficient on its own.

Enum options (`EnumSets`, confirmed):
```
0 = SIZE_800_BY_480
1 = SIZE_1280_BY_720
2 = SIZE_1280_BY_768   ← older captured DB
3 = SIZE_1920_BY_1080  ← earlier proposed target, not a verified write
4 = SIZE_2400_BY_960   ← Y181B exported DB, 2026-11-12; panel native
```

---

## 1. Checksum algorithm — fully reverse-engineered (load-bearing result)

It is **not a CRC**. It is a 16-bit additive checksum with a fixed XOR finalizer. Recovered
verbatim from `bin__diagnosticsd`'s `fcn.00028d20` (the routine `createCalibrationRequest` calls,
then compares against the stored 16-bit field):

```asm
fcn.00028d20 (buf=rdi, len=rsi):
    test esi, esi            ; len == 0 ?
    jle  .empty
    mov  ecx, esi            ; counter = len
    xor  edx, edx            ; running sum = 0
.loop:
    movzx eax, byte [rdi]     ; eax = *buf   (zero-extended)
    add   rdi, 1
    add   eax, edx            ; eax = byte + running_sum
    add   rcx, -1             ; counter--
    movsx edx, ax             ; running_sum = (int16)(low 16 bits)
    jne  .loop
    xor  eax, 0xA55A          ; finalize
    ret                       ; returns AX (16-bit)
.empty:
    mov  ax, 0xA55A           ; 0 XOR 0xA55A
    ret
```

Exactly equivalent to:

```python
def cal_checksum16(data: bytes) -> int:
    s = 0
    for b in data:
        s = (s + b) & 0xFFFF        # the movsx only sign-extends; low 16 bits are the sum mod 65536
    return s ^ 0xA55A               # 16-bit result, printed as 0x%04X
```

- Accumulator is 16-bit modular; the `movsx` sign-extension is cosmetic (the low 16 bits are
  preserved regardless of sign), so it reduces to `(Σ bytes) mod 0x10000`.
- Final constant is **`0xA55A`**.
- The native parser reads a 16-bit word at message offset 3 (§3b). This field's wire mapping to
  the public UDS path still needs an independent trace; it is not an in-container field of the
  stock CSM envelope (§2).

---

## 2. SHA-256 scope in stock CSM containers

The 32 bytes at container offset `0x1e` equal `SHA256(container[858:end])`. Module data begins at
`0x35a`, fourteen bytes before the gzip CalOvride XML at `0x368`. This is a plain digest, but its
stored value lies inside the RSA-signed header.

> **History:** verified offline 2026-11-11 for all 14 stock files. The earlier inferred
> whole-blob/trailing-digest layout is withdrawn in favor of the offset/scope above.

Native symbols `generateSHA256`, `SHA256_Init/Update/Final` and `CAL_MESSAGE_DIGEST_FAILURE`
identify a separate integrity check. They do not establish absence of signature verification
elsewhere, or that a modified signed container will be accepted.

---

## 3. Container / header layout

### 3a. UDS framing on TCP 49156 (`diagnosticsd`, GM-custom UDS-over-TCP, not DoIP)

`[C]`
```
[ SRC addr : 2 bytes BE ][ TGT addr : 2 bytes BE ][ LEN : 4 bytes BE ][ UDS payload ... ]
```
`readHeader` / `Error when receiving header, expected: %d, actual: %d` frame the PDU. The target
address and T1 SecurityAccess sequence are owned by
`../diagnostics/diagnosticsd_security_access.md`
([live correction, 2026-11-14](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14));
this does not establish container-write acceptance and is not restated here.

### 3b. Calibration message parse header (`createCalibrationRequest`, `fcn.0002fde0`)

This is an internal **native CAN** calibration message, not the public TCP RequestDownload
payload. The native pipeline selects bus type 2 and internal service values 10-12; the TCP
`34/36/37` interceptor instead uses the Java installer/staging-file path — do not send this
private header as ordinary TCP `34` parameters.

> **History:** clarified 2026-11-16, correcting an earlier draft that conflated this header with
> the public UDS path. The full stock-LTZ CAN5 rewrite that uses this pipeline is owned by
> [`../platform/can_bench_experiments.md`](../platform/can_bench_experiments.md#full-genuine-ltzhc-rewrite-through-canable--2026-11-16).

`[C]` native parser offsets (mapping through the CAN-side bridge to public UDS still needs an
independent trace; this is **not** the stock CSM container header, §2):
```
offset 0 : 1  subfunction selector: 1=Init, 2=Transfer, 3=Finalize
offset 1 : 1  (secondary selector / reserved)
offset 2 : 1  body length + 2 (native reported-length check at [msg+0x18])
offset 3 : 2  big-endian checksum: (sum(body) & 0xFFFF) XOR 0xA55A
offset 5 : .. calibration DATA payload         ( add r13,5 ; data begins here )
```

| Builder (`CalibrationParseFactory`) | Internal operation |
|---|---|
| `createCalibrationInitRequest` | Initialize: moduleID BE16, size BE32, filename16; minimum body 22 bytes |
| `createCalibrationTransferRequest` | Transfer: offset BE32 followed by data |
| `createCalibrationFinalizeRequest` | Finalize: SHA-256 digest, 32 bytes |

The builder names identify internal operations; their correspondence to public UDS service names
does not establish that the external payloads are identical.

### 3c. `calserviced` override package (Layer B container)

`[C]` The method name `processZippedModFile` does not establish a ZIP archive. In the pinned Y175
`calserviced` reference, RVA `0x58A70` reads a 0x368-byte header and inflates the inner gzip,
matching the genuine unwrapped CSM layout. The override storage/application path processes module
metadata and database rows; it is distinct from a bare XML/database write.

> **History:** clarified 2026-11-16. Historical header-CRC strings and zlib errors do not replace
> the independently verified CSM signatures in §0.

### 3d. UDS override reachability and per-value write stub

**"Override" is a storage/application concept, not proof of an unsigned UDS setter.** Stock LTZ
CSM packages supply override modules applied over the base calibration database; neither the
package-path name nor the `OverRiden` DB field (§4) establishes a separate arbitrary per-row wire
command. `OverRiden` records module ownership, not a Boolean engineering-edit flag.

| Mechanism | Evidence / current limit |
|---|---|
| UDS package programming (`34`/`36`/`37` + session/routine flow) | Stock LTZ/HC succeeded via CANable/CAN5 with readback verification. A signature-only control and the slot 0C SXM edit were rejected at block 01 with immediate PEC0015 — matches the VIP header-verification branch; genuine slot 0C was restored. Full chronology: DTW's [confirmed rejection](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-direct-can5-repeat-and-header-signature-rejection-confirmed). |
| UDS clear-all (`31 01 02 49`) | Live success and `clearAllOverrides` log; erases overrides, led to `NoCalibration` after reboot once (history below). Not a value setter. |
| Local override-file/database path | Exists in calibration service code; filesystem/UID/SELinux access are separate gates (§4, and SVC). No direct T1 arbitrary-value deployment demonstrated. |
| Per-value PAL request | Traced execute body only constructs a fixed-status response (below). No verified per-value UDS setter follows from it. |

**Native trace:** cleanroom `os/vendor/lib64/libpal_calibrations.so`, x86-64 ELF, SHA-256
`a340fc27e97c05bca6522833a75077fbfc908f7b683d6f2a73009e3f7f03999f`. At ELF RVA `0x28DF0`,
`writeCalValueRequest::execute(palCalibrationCore const&)` allocates a `writeCalValueResponse`
with status `0x12`; it does not invoke a calibration-write callback or use the supplied core to
update a value (the status enum is not independently identified and must not be read as a UDS
NRC). `Ipc::sendOverride()` at RVA `0x1F620` sends a fixed control request over the calibration
IPC path (`/dev/ipc/ipc`) and tracks request state; its log strings reference `getOverrideBuffer`,
not a public API accepting an arbitrary calibration name/value. No wire-side route to a custom
setter was recovered in this trace. (Ghidra analysis image base `0x100000`; addresses above are
ELF-relative, not live ASLR addresses.)

The Y175 `calserviced` binary also contains the `OVERRIDE_BACKDOOR` warning string and `.calovride`
suffix (§3e). This local development mechanism must not be equated with UDS programming or
presumed shell-writable — **the SELinux/DAC reachability question for this write path is owned by
[`SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md`](SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md)**, not
restated here. The destructive clear and recovery outcome referenced above is owned by
`../diagnostics/diagnosticsd_routines_and_recovery.md` (§6 below has the full pointer). A future
override-write claim must identify an implemented setter/loader, its actual authorization, and a
recoverable value — renaming a modified signed package is not such a path.

### 3e. Standalone XML loader, theme/UI inventory, and GMBrand/`SCREEN_RESOLUTION` live trials

**A compiled plaintext XML loader exists.** The Y175 cleanroom `os/vendor/bin/calserviced` is
x86-64 ELF, SHA-256 `36d66b4050c5ba14d173ae691c332d4e25118ec3b15b5a24c9f31d82726c9559` (not
byte-matched to the live protected file). Targeted RE:

| Entry | RVA | Observed behavior |
|---|---:|---|
| `calserviced_main` | `0x4D4D0` | Compares base/current DB versions, handles pending override directory and replay/rebuild branches. |
| `process_dir_members` | `0x58610` | A `.calovride` match reaches `apply_overrides(1, path)` directly, bypassing the compressed-module parser on that branch. |
| `processZippedModFile` | `0x58A70` | Separate compressed-module extraction/application path (§3c). |
| `apply_overrides` | `0x57330` | Opens current DB, prepares statements, begins a transaction, parses XML, updates the indicator, ends the transaction. |
| `xml_start_element` / `xml_char_data` / `xml_end_element` | `0x56B30` / `0x56600` / `0x57000` | Parse/validate entries, bind row ID and ownership, execute prepared statements. |

The main path tests the pending-override directory, emits a development-build warning, and calls
`process_dir_members(..., ".calovride", 0)` regardless of the warning's log-verbosity condition —
i.e. the loader is compiled into this Y175 package (compiled-code presence only, not live
authorization). The prepared scalar statement:

```sql
UPDATE AllCalSets set CalVersion=?, CalValue=?, OverRiden=? WHERE _id=?
```

`xml_char_data` binds the raw value `1` to parameter 3 of this statement (and parameter 6 of a
broader prepared UPDATE) — the `OverRiden` field, i.e. module/ownership context, not a harmless
flag (schema detail and History in §4). A targeted XML can be structurally narrower than clear-all
but still modifies persistent calibration (version/ownership included); it is not a temporary UI
setting or a public UDS per-value setter. Startup branches also copy the base DB and replay
applied modules when the current DB is missing/invalid/version-mismatched, and can call
`requestShutdownOnNextPowerCycle`; transaction use does not prove every malformed/partially-invalid
XML rolls back cleanly. No local loader/file test was run against the radio to confirm this.

**GMBrand/HomeScreen theme consumer.** The live HomeScreen APK matches the Y175 cleanroom APK
exactly (SHA-256 `772e0135de7eb70f7d4b88369d0e2ea35bb865206b00993599e616130c9d5693`). Its obfuscated
`z0.b` (`ThemeUtils.kt`) builds a `CalibrationManager` and reads `GMBrand`/`GMModel`/`GMTrim`.
Brand 3 selects `CHEVY_THEME` (except model 10, Corvette); brand 4 retains `GMC_THEME`; the
constructor's fallback is also `GMC_THEME`, so `GMBrand = 0` (`GM_Brand_None`) retains
`GMC_THEME` in this consumer rather than selecting a blank/unbranded UI. The result is cached on
the instance (getter only, no theme setter) — this is consumer-side proof, not a calibration-write
mechanism on its own.

> **History:** the GMC-fallback-for-brand-0 reading was a static-analysis prediction as of
> 2026-11-16. **Settled 2026-11-17:** after the live CAN trial below, ADB returned,
> `persist.sys.cal.brand` read `GM_Brand_None` (model unchanged, `Silverado`), and the owner
> confirmed a visible theme change (GMC-style HomeScreen accents, more traditional appearance in
> Settings). This establishes brand-0 application and a visible effect; it does not catalogue
> every asset/overlay as GMC, and is not an alias claim equating `0` with GMC.

The current user-10 Chevrolet framework overlay is immutable in this build: installed mutable
overlays were Maps-cruise overlays only, not a GMC theme control; shipped GMC framework/app
overlay manifests specify static overlays and require `persist.vendor.gm.brand=GM_Brand_GMC`, and
were not registered as an available mutable switch. `persist.sys.cal.brand` stayed Chevrolet prior
to the trial below — no brand property or overlay was changed by inspection alone.

**Theme/UI calibration-definition inventory (checked-in GIS-646 V7.0.8 definitions).** A definition
inventory only — not evidence every control is consumed by the installed Y175 UI, and no
additional theme/UI calibration was written while compiling it:

| Area | Defined controls | Scope |
|---|---|---|
| Brand/model/trim | GMBrand, GMModel, GMTrim | Brand graphics/highlighting, model selection, trim-specific welcome behavior. The HomeScreen consumer above reads all three. |
| Welcome/startup/shutdown | WELCOME_ANIMATION_ENABLED; VEHICLE_ANIMATION_WELCOME_TYPE / STARTUP_TYPE / SHUTDOWN_TYPE | Brand-animation selectors; shutdown enum covers full black, fade to black, play animation. Asset availability is build-specific. |
| Application visibility | APPLICATION_HOMESCREEN_*_ENABLED, including THEMES | Home-screen/app-tray entries; a visible Themes entry does not establish an installed theme engine or process control. |
| Ordering/pages | ApplicationOrdering*; AppTray_ApplicationOrdering1-12; DefaultNumOfPages | Home-screen/app-tray ordering and page count. |
| Porch view | Porch_View_Enabled; Navigation_Zone_Enabled | Porch-view availability and its navigation zone. An explicit `true` override was accepted on 2026-11-17 (UI effect unverified); the HomeScreen also only permits 1920x1080/1280x768 via `SCREEN_RESOLUTION` (source HC is 2400x960). See DTW's [trial](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-explicit-porch-view-enable-trial). |
| Status-bar navigation | HomeBackSelection | Home-vs-Back behavior at the documented status-bar position. |
| Display geometry | SCREEN_RESOLUTION; DISPLAY_SCREEN_SIZE | Display/camera configuration; physical panel timing and successful screen-layout changes remain unverified here (trial below is value-transfer-only). |
| Transient UI timing | QUICKSTATUSPANEWIDGET_AUTOMATICDISMISSALTIME; POPUPWIDGET_AUTODISMISSFADEOUTTIME; ZoomBubbleDuration | Pane dismissal, pop-up fade, zoom-bubble duration. Some legacy definitions target other radio variants. |
| Touch feedback | DEFAULT_AUDIO_TOUCH_FEEDBACK_SETTING; ENABLE_MENU_AUDIO_TOUCH_FEEDBACK | Default touch audio and menu exposure. |

GMTrim enum: HighCountry=1, TrailBoss=2, Z71=3, AT4=4, Denali=5, UltimateDenali=6, Stingray=9,
Z06=10, ERay=11, ZR1=12, ZORA=13, WT=14, LT=15, LTZ=16, SLE=17, SLT=18 (enum names/values only, not
a claim this build ships every corresponding animation). Source owners: GIS500_UI,
GIS501_HomeScreenUI, BrandAnimationsAudioCues, DisplayGesturesAndTimeouts under the checked-in
`reference/GIS-646_CalDef_Database_Info3.7_and_Info3.8_V7.0.8_19April2023/caldefs`.

**CAN readback boundary (2026-11-16).** A fresh CAN `22 F1 82` returned 28 module-identity records
including slot04/85045386 and slot08/87846432. The matching HC source containers encode GMBrand=3
(Chevrolet)/GMModel=4 (Silverado)/GMTrim=1 (HighCountry) in slot04, and `SCREEN_RESOLUTION=4`
(2400x960) in slot08 — these are **archive-derived expected values corroborated by current module
identity, not individual live CAN value readbacks** (modified slot0C already shows identity can
stay unchanged after a payload change). No value-level CAN handler for these settings was
identified in this check; the CAN613/614 route addresses VIP memory and has not been mapped to the
SoC calibration database holding these entries. HC slot04/part85045386 contains GMBrand CalID
`_6jigAG6rEeSIp5iyPWbHnw`, override version 1, enumeration value 3 (SHA-256
`46777ba9b55859b27472e9b6294a0d0cbea4cdccfaf423301fc0e598c859ba30`) — brand-0 changes that
enumeration value to 0, an inner compressed-XML record, not a fixed CAN payload bit or verified
live RAM bit address. `DISPLAY_SCREEN_SIZE` is absent from the HC override containers; its
separate camera-related definition defaults to 0 (2940x816), a default, not a live observation —
do not confuse it with `SCREEN_RESOLUTION`.

**GMBrand-zero CAN trial, 2026-11-16, settled 2026-11-17.** The owner authorized the same
CAN613/614 scoped-memory method for brand 0. Pre-trial: `persist.sys.cal.brand` =
`GM_Brand_Chevrolet`, model = `Silverado`, clock matched the Mac. Only slot04/part85045386 was
rebuilt (GMBrand enumeration 3→0); XML record comparison confirmed every other record/CalID set
unchanged. Slot 0C (SXM/CarPlay/Android Auto false overrides) was not transferred or restored in
this trial.

- Original slot04 SHA-256: `46777ba9b55859b27472e9b6294a0d0cbea4cdccfaf423301fc0e598c859ba30`.
- Custom slot04 (13,237 bytes) SHA-256: `85dc07017fdf255aefdcdfd21c0046322966874d23097038eabba6c3c71cf931`.

Only the inner gzip and payload digest were regenerated; the original signer record and header
signature were retained (this is the accepted-custom-CAN-write path, §"Note on scope" above — not
a forged signature). Profile 01 programming preparation succeeded; the same scoped CAN613/614
intervention temporarily set the two verifier words, both verified before transfer.
`RequestDownload` returned `74 20 0F FF`; all 13 data blocks returned matching `76` counters
`01`-`0D`; transfer exit returned `77`. Both verifier words were restored to zero and read back;
immediate PEC was `0000` and `F1 82` matched the pre-write baseline. Immediate cleanup for this
GMBrand-0 trial returned `7F 10 22`, `7F 28 7F`, and `7F 85 7F`; default-session requests were
accepted; a subsequent immediate status request timed out. The custom module was retained;
genuine recovery was not invoked at this point.

> **History:** at the transfer checkpoint ADB was temporarily unavailable and the owner-visible
> result was pending (a static GMC-theme-fallback prediction only; do not treat transfer
> acknowledgment alone as proof of a cold-cycle-persistent, visually-confirmed brand change).
> **Settled 2026-11-17:** ADB returned (`sys.boot_completed=1`); the live brand property had
> changed `GM_Brand_Chevrolet` → `GM_Brand_None` (model unchanged); the radio clock was
> resynchronized from the Mac; all 14 calibration-slot statuses read `00`, F0F1/F0F2 read `0000`.
> The owner confirmed the theme changed. This establishes application of brand 0 and a visible
> effect; it does not independently catalogue every asset/overlay as GMC, and no separate
> physical supply-off persistence test has been run for brand 0 specifically.

**VM evidence boundary.** Existing Y175 VM notes document direct DB edits from Cadillac brand 2 to
Chevrolet brand 3 (plus model/name edits) followed by a verified accent change across reboots, and
report `calserviced` overwriting a property-only theme attempt — supporting the
calibration→UI-consumer chain in general. The VM uses hardware/IPC adaptations; its DB access does
not prove radio filesystem permissions, a UDS setter, signature acceptance, or safe loader
behavior on the physical unit. No VM disk was changed for this review.

**Bounded non-calibration attempt.** For user 10, the myChevrolet launcher activity
(`com.gm.mybrand/.splash.view.SplashActivity`) was initially available with default component
state. A component-disable attempt was rejected:
```text
java.lang.SecurityException: Shell cannot change component state for com.gm.mybrand/com.gm.mybrand.splash.view.SplashActivity to 2
```
The precautionary default-state request was also rejected (same message, target `0`); readback
still showed `enabled=0` (default), no explicit component override, launcher activity available —
the initial mutation itself failed, so this is not evidence restoration "succeeded." The attempt
was an ADB PackageManager operation, not UDS; no positive visual override was demonstrated. A
2400x960 HomeScreen capture confirmed the Chevrolet appearance and myChevrolet tile before the
attempted change.

**Single-file `.calovride` deployment and USB MediaStore attempt, 2026-11-15.** A one-value
artifact (`calibration_prototypes/a11_gmbrand_gmc_single.calovride`, outside the excluded
`calibration_prototypes/` subtree per this reorg's rules — link only, not opened) containing
exactly one `OverrideValue` (GMBrand, stock LTZ Version 1, enumeration value 4/GMC, 308-byte XML).
Its source element was extracted from stock LTZ part 85045371 after verifying the pinned
CSM-container SHA-256 `27aa0cb3427225518e51cd1a5c53d6139462609ea11df106bf27bde2a7136231`. It
was staged successfully to `/data/local/tmp` (outside the watched calibration directory); copying
it onto the calibration filesystem failed with `Permission denied` (`adbd` cannot run as root in
production builds). It was never installed into the loader's input directory; brand readback
stayed `GM_Brand_Chevrolet`. A follow-on authorized USB MediaStore deployment wrote the same XML
byte-exactly to FAT32 as `a11brand.calovride`; no calibration-discovery/install event was
demonstrated. Full updater/installer mechanics (`DevCaloverrideInstaller`, build-type gating, the
HIDL raw-file copier, ABFT0475) are owned by
[`../platform/ota_update_stack.md`](../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15)
and are not restated here.

**Reboot scope.** A persistent theme change may require a consumer process restart or Android
reboot (theme is cached); reboot does not apply a denied command. No reboot was needed or issued
for the rejected launcher test above.

---

## 4. Direct DB edit (Layer B — simplest, given a `vendor_cald` foothold)

`[C]` This mirrors what `calserviced` does internally (§3e: `UPDATE AllCalSets set CalVersion=?,
CalValue=?, OverRiden=? WHERE _id=?`, then `UPDATE AllCalSets SET CalValue=%u WHERE
_id="UPDATE_INDICATOR"`):

```sql
-- flip the enum, mark it overridden, bump the row's CalVersion
UPDATE AllCalSets
   SET CalValue = 3,
       OverRiden = <OVERRIDE_MODULE_ID>,
       CalVersion = CalVersion + 1
 WHERE _id = '__-Jk4IQIEeWHkIX-EVZFdA';   -- SCREEN_RESOLUTION

-- force consumers to re-read (only if the row exists in your DB copy)
UPDATE AllCalSets SET CalValue = CalValue + 1 WHERE _id = 'UPDATE_INDICATOR';
```

`OverRiden` is **not** a Boolean flag: in the owner-supplied update-cache DB, all 982 nonzero
values match `ModuleData.ModID` (that table records 14 applied override packages). The SQL above
is a template, not a validated deployment — determine the correct module-ownership semantics
before assigning `<OVERRIDE_MODULE_ID>`; neither this field nor a nonzero count proves a manual
modification. The archive omits the actual `.cmod` files and is not a complete erase-recovery
backup.

> **History:** schema correction, 2026-11-14. See the
> [owning calibration baseline](../platform/vehicle_config.md#y181b-exported-baseline-2026-11-12)
> for the exported row counts this correction is based on.

The cell is a native integer; no package checksum/digest is stored around each DB cell. Direct DB
modification requires filesystem authorization, not merely recalculating transfer integrity: the
directory is labeled `calibration_data_file`, owned by Unix identity `vendor_cald` (mode 770), and
the daemon's SELinux domain is `calserviced`. A root UID alone does not establish the required
SELinux access, and ordinary ADB shell has no verified write path here.

> **History:** directory/ownership facts corrected 2026-11-15. The full SELinux/DAC reachability
> audit for this path (CIL rule IDs, write-allow/neverallow lists, feasibility verdict) is owned by
> [`SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md`](SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md) and
> is not restated here.

A local override package must match the actual `calserviced` parser and the production-build entry
point (§3e); the strings alone do not establish the precise package header/CRC format, and a
generic ZIP wrapper is not a proven accepted artifact. A direct database edit also requires the
appropriate privileges and has not established the intended display behavior on its own.

---

## 5. Offline checks and the (removed) re-sealing script

A previous `calseal.py build` example assembled a guessed five-byte native message header and
digest. It did not create a valid signed CSM container and was not a validated flash procedure;
that builder and its executable-deployment examples have been removed from this doc — no stale
example is left standing.

Useful read-only checks:

```python
checksum = (sum(native_message_body) & 0xffff) ^ 0xa55a
assert hashlib.sha256(stock_csm_container[858:]).digest() == stock_csm_container[30:62]
```

The first formula concerns the native transport message body (§1); the second concerns the stock
container (§2). They operate on different byte ranges and are not a complete signing procedure.
The exact RSA signed spans and reproducible public-key checks are owned by
[`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

---

## 6. What is established for `$27` and custom writes

The 2026-11-10 stock LTZ write used the radio's SBI-dependent all-FF SecurityAccess exchange, then
transferred and finalized all 14 stock containers successfully — proof of authorization for the
stock write in that state, not proof that a custom package is accepted. The real-seed CMAC
implementation remains unverified on hardware (owned by GSK).

Modified-package attempts were rejected with `7F 36 72` after recomputing the payload digest. The
2026-11-16 signature-only control, immediate PEC0015, and VIP-branch trace confirm header-signature
rejection for the tested Y175 CAN5 path; the same-day SXM-disable trials reproduced PEC0015 under
profiles 03/05 with successful genuine recovery, and a same-session stock restoration succeeded.
The full chronology (including the Engineering09-granted-but-`021E`-denied finding) is owned by
[`DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md) and is not
restated here. **The former claim that `$27` is the only wire-side wall is withdrawn** — the
signed-container check is a second, independent wall (§0).

As stated in this doc's header: **signed-container forgery** (a modified/resigned CSM container
accepted by the radio) has never been achieved by any route tried so far. **Accepted custom
CAN/VIP writes** (§3e's GMBrand-0 and SXM-disable trials, §"SCREEN_RESOLUTION CAN trial" below) have
been achieved, via the CAN613/614 scoped-VIP-RAM method, which does not forge a signature — it
writes through a narrower channel that the signature check does not gate the same way. Local
`*.calovride`/database application (§§3e-4), a development override installer, and the named
Signature-Bypass Ticket are different, still-unestablished candidate paths; none is a demonstrated
production custom-calibration bypass. An ADB shell alone does not prove `vendor_cald` access (§4,
SVC). Do not infer a security flag from an EEPROM address without the current evidence in GSK.

---

## 7. Validation boundary

A successful future custom-write result must establish the active build-specific loader, complete
protocol acknowledgements, and post-reset database/display behavior. Matching stock metadata or
computing a correct checksum/digest (§§1-2) does not establish those results on its own. A direct
SQLite value change (§4) is also not proof that the display accepts the selected mode.

---

## Historical trial record

### Direct T1 override-clear result (2026-11-14) — superseded

Calibration clearing is now forbidden; this is a historical outcome, not a current procedure. The
explicitly authorized native `02 49` start completed over T1, returned `71 01 02 49`, and produced
the daemon's `ALL OVERRIDES CLEARED` log; all 14 reported calibration-module identities changed to
`7 0008/00`. MEC remained `FF`; no MEC reset/write was issued. After an owner-initiated power
cycle, RH850 entered `NoCalibration (0xe)`; T1 reads still worked and MEC stayed `FF`. The main
MDI2 client then restored the pinned stock LTZ package (requiring a one-time in-memory source
exception and VIN restoration from the owner's supplied value); all 14 slots and VIN matched
post-reset readback, and later UART boots reached HMI-ready with calibration state `2`. Full
clear/fault/recovery narrative and anchors:
[clear](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved),
[fault](../diagnostics/diagnosticsd_routines_and_recovery.md#owner-power-cycle-after-clear-nocalibration-fault-2026-11-14),
[recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).

> **History:** per the later [full stock LTZ rewrite](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-17-full-stock-ltz-restoration-after-feature-trials),
> this and the Brand-0/other custom trials were superseded 2026-11-17 — their observations remain
> historical evidence, not the current installed configuration.

### `SCREEN_RESOLUTION` 1280x768 CAN trial — 2026-11-17

After the full stock LTZ restore and an owner-observed CAN factory reset, fresh `F1 82` still
matched the LTZ set and all 14 `F0F0` statuses read `00`. The trial changed only
`SCREEN_RESOLUTION` (`__-Jk4IQIEeWHkIX-EVZFdA`) from enum 4 (`SIZE_2400_BY_960`) to enum 2
(`SIZE_1280_BY_768`), preserving the existing override version 1 in slot08/part87846432.
`GIS738_RVCVideoRobustnessRequirement.enumdef` confirms the enum mapping; current definition
version 4 does not require changing the source override version for this value-only test.

- Pinned stock container SHA-256: `c97114731de14bc5f748f98ed10f931fb5e0a432b40bb1e75c01efd43b7055b4`.
- Candidate (1,542 bytes) SHA-256: `68e230c8ad7f7c71f3124bf8ca3e204f1dc8d8cfb2f78c74575c72e3d56a1608`.

XML record comparison verified identical ID sets and exactly one changed record; the original
signer/header bytes were preserved except the updated payload digest (an accepted-custom-write, not
a forgery — see §"Note on scope"). Stock slot08 was held as the recovery payload; other slots were
not rewritten.

Profile 01 preparation and temporary verifier words were accepted. Download returned `74 20 0F FF`,
data blocks returned `76 01`/`76 02`, exit returned `77`, PEC was `0000`, `F1 82` unchanged.
Verifier words were restored and read back. **The owner subsequently reported visible tearing
artifacts resembling a failed calibration: the transfer itself succeeded but the display outcome
was unacceptable.** The original 1,563-byte stock slot08 was restored (both blocks + exit `77`
accepted, PEC `0000`, `F1 82` unchanged, without modifying verifier RAM words); the owner confirmed
the display returned to normal after rollback. Settled CAN checks found all 14 module statuses `00`
and F0F1/F0F2 `0000`. Do not describe the 1280x768 trial as a successful display configuration
merely because its transfer was accepted — the panel-timing/UI-layout outcome was negative and the
change was rolled back. The earlier porch-view override (§3e) was removed by the stock LTZ restore
and was not re-added here; the programmed set is again all stock LTZ.

---

## Appendix — provenance

- Checksum algorithm: `bin__diagnosticsd` `fcn.00028d20`, called from `createCalibrationRequest`
  (`fcn.0002fde0`), string `Calibration Request Checksum (0x%04X vs 0x%04X) failed`. Directly
  disassembled — high confidence.
- SHA-256: `SHA256_Init/Update/Final` imports + `generateSHA256` symbol + `CAL_MESSAGE_DIGEST_FAILURE`;
  used in `UDSTransferDataRequestHandler.cpp` finalize path.
- Native-message header offsets 3-4 (checksum) and data-at-5: disassembled in
  `createCalibrationRequest`; bytes 0-2 and the full wire mapping require further validation. Not
  the CSM signed header.
- DB facts: queried live from `scratchpad/diagx/calibrations__CalSets.db`.
- `$27`/VIP/EEPROM anchoring and the two write paths: cross-referenced in
  `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` and
  `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt` (both retired/folded elsewhere per the reorg plan;
  not independently re-verified by this doc).
