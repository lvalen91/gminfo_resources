# Hand-editing `SCREEN_RESOLUTION` in CalSets.db and re-sealing the integrity fields

**Target:** GM MY22/Y181 IVI (Intel Apollo Lake SoC, GHS INTEGRITY host + Android 12L guest), 2024 Silverado head unit — the owner's own module.
**Scope:** the `SCREEN_RESOLUTION` database row and lower-layer integrity routines. Recomputing these fields is not a demonstrated method for making the radio accept a modified signed calibration container.

**Corrected 2026-11-11:** all 14 stock CSM containers have independently verified RSA-2048 signatures and production-CA signer-record signatures. The [central reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) owns the reconciled signature, seed/key and runtime-enforcement evidence.

Everything below is grounded in the owner's own extracted artifacts:
- `scratchpad/diagx/calibrations__CalSets.db` (the older captured SQLite DB)
- `scratchpad/diagx/bin__diagnosticsd` (UDS receiver — checksum + SHA‑256 code)
- `scratchpad/diagx/bin__calserviced` (on‑device override applier — SQL + package format)
- corroborating notes in `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` and `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt`

Confidence tags: `[C]` confirmed from a binary/DB, `[I]` inferred, `[O]` open/needs a known‑good capture to pin.

---

## 0. Database values, transport integrity and signed-container authenticity

The earlier claim that calibration containers have no RSA signature was false. All 14 stock
CSM containers carry verified RSA-2048 PKCS#1 v1.5/SHA-256 signatures. Their signer records
also authenticate under the original Y181 production CA. Keyless checksums and hashes are
lower-layer integrity fields; recomputing them does not produce a new valid signature.
The exact active UDS signature/root verifier remains open, so package-format proof must not
be presented as an isolated explanation for a live NRC `0x72`.

| Layer | Evidence | Acceptance limit |
|---|---|---|
| Diagnostic authorization | SBI-dependent UDS `$27`; stock LTZ write reported successful | Does not establish acceptance of arbitrary content |
| Transport integrity | Additive checksum routine and SHA-256 comparison in native analysis | Does not replace signed-container authenticity |
| CSM signed format | 14/14 stock header and signer-record signatures independently verified | Modified-package acceptance/runtime enforcement still unresolved |
| Local database/override application | Native integer values and privileged calibration store | A separate filesystem/SELinux access path, not a wire-side bypass |

**Baseline corrected 2026-11-12:** the older captured DB below records value 2.
The Y181B recovery export instead records **`SCREEN_RESOLUTION=4`**
(`SIZE_2400_BY_960`, `OverRiden=8`), with 2574 total rows. Both ZIPs contain
the same exported DB. See the [vehicle baseline](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12).
No accepted custom write or transition from the older snapshot is inferred.

`[C]` **What lives in the older DB row is a bare SQLite value, not a blob.** Verified directly:

```
_id      = __-Jk4IQIEeWHkIX-EVZFdA
CalName  = SCREEN_RESOLUTION
CalType  = 4         (enum)
CalValue = 2         typeof() = 'integer'  ← a native SQLite integer, length 1, NOT a BLOB
CalVersion = 4
OverRiden  = 0
Encode = NULL   ArrayLen = NULL
EnumID = _PWvKYIQHEeWHkIX-EVZFdA
```
Across the whole `AllCalSets` table there are **zero** BLOB cells (1852 integer / 154 real / 567 text). **So the checksum and SHA‑256 do not wrap the DB cell — they wrap the transfer/override *container*.** Editing the DB directly (Layer B side) is one operation; sealing a UDS payload (Layer A) is the other. The distinction is documented below; a custom UDS deployment is not established.

Enum options (`EnumSets`, confirmed):
```
0 = SIZE_800_BY_480
1 = SIZE_1280_BY_720
2 = SIZE_1280_BY_768   ← older captured DB
3 = SIZE_1920_BY_1080  ← earlier proposed target, not a verified write
4 = SIZE_2400_BY_960   ← Y181B exported DB, 2026-11-12; panel native
```

---

## 1. Checksum algorithm — FULLY reverse‑engineered (this is the load‑bearing result)

It is **not a CRC.** It is a 16‑bit additive checksum with a fixed XOR finalizer. Recovered verbatim from `bin__diagnosticsd` `fcn.00028d20` (the routine `createCalibrationRequest` calls, then compares against the stored 16‑bit field):

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

- Accumulator is 16‑bit modular; the `movsx` sign‑extension is cosmetic (the low 16 bits are preserved regardless of sign), so it reduces to `(Σ bytes) mod 0x10000`.
- Final constant is **`0xA55A`**.
- The earlier native parse interpretation reads a 16-bit word at message offset 3. Its wire mapping must be established for the actual message path; it is not an in-container field in the stock CSM envelope.

---

## 2. SHA-256 scope in stock CSM containers

**Verified offline 2026-11-11 for all 14 stock files:** the 32 bytes at container offset
`0x1e` equal `SHA256(container[858:end])`. Module data begins at `0x35a`, fourteen bytes before
gzip CalOvride XML at `0x368`. The earlier inferred whole-blob/trailing-digest layout is
withdrawn. This is a plain digest, but its stored value lies inside the RSA-signed header.

Native symbols `generateSHA256`, `SHA256_Init/Update/Final` and `CAL_MESSAGE_DIGEST_FAILURE`
identify a separate integrity check. They do not establish absence of signature verification
elsewhere or prove that a modified signed container will be accepted.

---

## 3. Container / header layout

### 3a. UDS framing on TCP 49156 (`diagnosticsd`, GM‑custom UDS‑over‑TCP, *not* DoIP)
`[C]` (from `T1_NETWORK…` §2)
```
[ SRC addr : 2 bytes BE ][ TGT addr : 2 bytes BE ][ LEN : 4 bytes BE ][ UDS payload ... ]
```
- **Corrected 2026-11-14:** use canonical target `0x0084` and tester F4.
  The binary checks logical addresses; old FA/F1/F0 trust-tier claims were
  unverified. Extended session plus the documented 31-FF/12-zero exchange
  returned `67 02`; see [validated T1 sequence](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14). This does not establish container-write acceptance.
- `readHeader` / `Error when receiving header, expected: %d, actual: %d` frame the PDU.

### 3b. Calibration message parse header (`createCalibrationRequest`, `fcn.0002fde0`)
`[C]` for offsets 3–4 and the data start in this native message parser; `[I]` for bytes 0–2 and its mapping to the active stock CSM transfer. This is not the stock CSM container header:
```
offset 0 : 1  subfunction/format selector   -> jump table @0x14ca8 picks Init($34)/Transfer($36)/Finalize($37)
offset 1 : 1  (secondary selector / reserved)
offset 2 : 1  length/element-count byte (validated against the PDU's reported payload size at [msg+0x18])
offset 3 : 2  CHECKSUM word in the native parse view; wire endianness/path needs validation
offset 5 : .. calibration DATA payload         ( add r13,5 ; data begins here )
```
`[C]` sub‑service string evidence: `DIAG_DATA_TRANSFER (0x36)`, `Init Request`, `Calibration Transfer Request`, `Calibration Finalize Start/Complete`. So:

| Builder (`CalibrationParseFactory`) | UDS service |
|---|---|
| `createCalibrationInitRequest` | **`$34` RequestDownload** |
| `createCalibrationTransferRequest` | **`$36` TransferData** (`DIAG_DATA_TRANSFER 0x36`) |
| `createCalibrationFinalizeRequest` | **`$37` RequestTransferExit** (digest verified here) |

### 3c. `calserviced` override package (Layer B)
`[C]` A **zip** ("mod file") dropped in `/mnt/vendor/calibration/overrides/`. `processZippedModFile` reads a package header (`header_len`, `header crc mismatch` → its own CRC over the header, `incorrect header check` is the zlib inflate error), contains a `MANIFEST_NOTICE`, unzips, then applies rows to `/mnt/vendor/calibration/database/CalSets.db`, and finally bumps `UPDATE_INDICATOR` so the display stack re‑reads.

---

### 3d. UDS override reachability and per-value write stub (2026-11-15)

**Override is a storage/application concept, not proof of an unsigned UDS
setter.** Stock LTZ CSM packages supply override modules applied over the base
calibration database. The normal UDS download/transfer/finalization path is a
package path; neither its name nor the `OverRiden` DB field establishes a
separate arbitrary per-row wire command. `OverRiden` records module ownership,
not a Boolean engineering-edit flag.

| Mechanism | Evidence / current limit |
|---|---|
| UDS package programming (`34`/`36`/`37`, with surrounding session/routine flow) | Stock LTZ succeeded using MDI2. Modified LTZ attempts failed with NRC72; the rejecting check was not isolated. |
| UDS clear-all (`31 01 02 49` on the tested Android route) | Live success and `clearAllOverrides` log; this erases overrides and previously led to NoCalibration after reboot. It is not a value setter. |
| Local override-file/database path | Exists in calibration service code; filesystem, UID and SELinux access are separate gates. No direct T1 arbitrary-value deployment demonstrated. |
| Per-value PAL request | Y175 export exists, but its traced execute body only constructs a fixed-status response. No verified per-value UDS setter follows from it. |

**New native trace:** cleanroom `os/vendor/lib64/libpal_calibrations.so`,
x86-64 ELF, SHA-256
`a340fc27e97c05bca6522833a75077fbfc908f7b683d6f2a73009e3f7f03999f`.
At ELF RVA `0x28DF0`, `writeCalValueRequest::execute(palCalibrationCore const&)`
allocates a `writeCalValueResponse` with status **`0x12`**. It does not invoke a
calibration-write callback or use the supplied core to update a value. The
constructor at RVA `0x22230` initializes the response and logs; it does not
apply an override. The internal status enum is not independently identified
here and must not be interpreted as a UDS NRC. `verify()` at RVA `0x28C60`
checks request shape, not proof that execute supports writing.

`Ipc::sendOverride()` at RVA `0x1F620` sends a fixed control request through
the calibration IPC path (`/dev/ipc/ipc`) and tracks a request state. Its log
strings refer to `getOverrideBuffer`; the symbol is not a public API accepting
an arbitrary calibration name/value. No wire-side route to a custom setter
was recovered in this trace. Ghidra used an analysis image base of `0x100000`;
addresses above are **ELF-relative**, not live ASLR addresses.

The Y175 `calserviced` binary also contains the `OVERRIDE_BACKDOOR` warning
and `.calovride` suffix. This local development mechanism must not be equated
with UDS programming or presumed shell-writable. The compiled main/parser path is now traced in §3e below; live privilege,
loader eligibility and accepted deployment remain unverified. See also the
[calibration-service reachability audit](SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md).
The initial read-only phase performed no calibration write, clear, file
deployment or DB edit. Subsequent temporary/USB file placement is recorded
in section3e; no override application was demonstrated.

The [central signing reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
owns the verified stock signatures and unresolved runtime enforcement.
The [diagnostic recovery reference](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved)
owns the destructive clear and recovery outcome. A future override test must
identify an implemented setter/loader, its actual authorization and a
recoverable value; renaming a modified signed package is not such a path.

### 3e. Standalone XML loader, runtime controls and visual-test limits (2026-11-15)

**Constraint:** preserve the loaded stock calibration and display parameters.
Calibration clearing is forbidden. The initial loader/launcher inspection
performed no clear/erase, programming, override deployment, DB edit or reboot.
A temporary Android launcher-entry change was attempted and rejected.
The later USB discovery experiments below placed a single-brand XML on USB
without demonstrating calibration application.

**A compiled plaintext XML loader exists.** The Y175 cleanroom
`os/vendor/bin/calserviced` is x86-64 ELF, SHA-256
`36d66b4050c5ba14d173ae691c332d4e25118ec3b15b5a24c9f31d82726c9559`.
This native executable has not been byte-matched to the live protected file.
Targeted analysis at ELF RVAs:

| Entry | RVA | Observed behavior |
|---|---:|---|
| `calserviced_main` | `0x4D4D0` | Compares base/current DB versions, handles pending override directory and replay/rebuild branches. |
| `process_dir_members` | `0x58610` | A `.calovride` match reaches `apply_overrides(1, path)` directly, without the compressed-module parser in that branch. |
| `processZippedModFile` | `0x58A70` | Separate compressed module extraction/application path. |
| `apply_overrides` | `0x57330` | Opens current DB, prepares statements, begins a transaction, parses XML, updates the indicator and ends the transaction. |
| `xml_start_element` / `xml_char_data` / `xml_end_element` | `0x56B30` / `0x56600` / `0x57000` | Parse/validate entries, bind row ID and ownership, then execute prepared statements. |

The main path tests the pending override directory, emits the development
warning and calls `process_dir_members(..., ".calovride", 0)`. The warning's
log-verbosity condition does not remove the following loader call. Thus the
entry is compiled into this Y175 package; prior statements based solely on
strings are superseded **for compiled code presence**, not live authorization.

The prepared scalar statement is:

```sql
UPDATE AllCalSets set CalVersion=?, CalValue=?, OverRiden=? WHERE _id=?
```

Other prepared statements validate existing type/range/enum/subset metadata
and support a broader calibration-record update. The raw value `1` passed
to `apply_overrides` becomes its module/ownership context: `xml_char_data`
binds that value to parameter 3 of the scalar UPDATE (and parameter 6 of the
broader UPDATE), the `OverRiden` field. It must not be assumed harmless or
interchangeable with a stock module's ownership.
A targeted XML can therefore be structurally narrower than clear-all, but
it still modifies **persistent calibration**, including version/ownership.
It is not a temporary UI setting or a public UDS per-value setter.

Startup also has branches that copy the base DB and replay applied modules
when the current database is missing, invalid or version-mismatched. After
processing pending files it can call `requestShutdownOnNextPowerCycle` and
set the J5 indicator. Transaction use does not prove that every malformed or
partially invalid XML rolls back every change. These branches, parser
validation, ownership and exact restoration must be established on an
isolated database/VM before treating a one-item deployment as recoverable.
No local loader/file test was run against the radio.

**Visual target: GMC red HomeScreen.** The live HomeScreen APK matched the
Y175 cleanroom APK exactly (SHA-256
`772e0135de7eb70f7d4b88369d0e2ea35bb865206b00993599e616130c9d5693`).
Its obfuscated `z0.b` (`ThemeUtils.kt`) constructs a CalibrationManager and
reads `GMBrand`, `GMModel` and `GMTrim`. Brand 3 selects CHEVY_THEME except
model 10 (Corvette); brand 4 retains GMC_THEME. The result is cached on the
instance; the inspected class has a getter and no theme setter. This is
consumer-side proof, not a calibration-write mechanism.

The current user-10 Chevrolet framework overlay is immutable. Installed
mutable overlays were Maps cruise overlays, not a GMC theme control. Shipped
GMC framework/app overlay manifests specify static overlays and required
`persist.vendor.gm.brand=GM_Brand_GMC`; they were not registered as an
available mutable GMC switch. The live `persist.sys.cal.brand` remained
Chevrolet. No brand property or overlay was changed.

**VM evidence boundary:** the existing Y175 VM notes document direct DB edits
from Cadillac brand 2 to Chevrolet brand 3 (with model/name edits), followed
by a verified accent change across reboots. They also report that calserviced
overwrote a property-only theme attempt. This supports the calibration→UI
consumer chain. The VM uses hardware/IPC adaptations and its DB access does
not prove radio filesystem permissions, a UDS setter, signature acceptance
or safe loader behavior. No VM disk was changed for this review.

**Bounded non-calibration attempt:** for user 10, the myChevrolet launcher
activity `com.gm.mybrand/.splash.view.SplashActivity` was initially available
with default component state. A component-only disable was rejected:

```text
java.lang.SecurityException: Shell cannot change component state for com.gm.mybrand/com.gm.mybrand.splash.view.SplashActivity to 2
```

The precautionary default-state request was also rejected (same message ending
`to 0`). Readback still showed package state `enabled=0` (default), no explicit
component override, and the launcher activity available. This does **not**
mean restoration succeeded after a change: the initial mutation itself
failed. The attempt was an ADB PackageManager operation, not UDS. No positive
visual override was demonstrated. A 2400×960 HomeScreen capture confirmed the
Chevrolet appearance and the myChevrolet tile before the attempted change.

**Single-file deployment attempt, 2026-11-15:** the owner authorized a GMC
theme trial. The prepared [one-value artifact](calibration_prototypes/a11_gmbrand_gmc_single.calovride)
contains exactly one OverrideValue: GMBrand's existing CalID, stock LTZ
Version 1, Enumeration Value 4 (GMC). Its source element was extracted from
stock LTZ part 85045371 after verifying the pinned CSM-container SHA-256
`27aa0cb3427225518e51cd1a5c53d6139462609ea11df106bf27bde2a7136231`.
The 308-byte XML excludes every display/other calibration entry. Well-formed
XML and exact one-entry scope were checked offline; native-loader acceptance
was not established.

The file was successfully staged in `/data/local/tmp`, which is outside the
watched calibration directory. Copying it to a staging name on the calibration
filesystem failed:

```text
cp: /mnt/vendor/calibration/.a11_gmbrand_gmc_single.stage: Permission denied
adbd cannot run as root in production builds
```

The second line is the response to the standard `adb root` request. The file
was **not installed into the loader's input directory or applied**. The
calibration directories remained inaccessible to this shell. Brand readback
remained `GM_Brand_Chevrolet` and the myChevrolet launcher entry remained
available. No calibration-changing UDS request or reboot was sent. The staged
copy is an inactive test artifact, not a pending override that a reboot will
load. Activating it still requires an authorized privileged writer and a
readable current state/rollback; user authorization alone does not change
Android's filesystem or SELinux permissions.

**Updater follow-up, 2026-11-15:** a legitimate privileged file mover exists:
DevCaloverrideInstaller copies registered type2 package files to the protected
calibration destination and requests recovery. Current Y175 discovery selects
that type only on non-user builds. The shown installer body has no equivalent
build check, but no production-shell method to register an arbitrary XML
package has been established. Native mounted-media handling copies to update
staging rather than the calibration destination. A separate HIDL raw-file
copier exists, but current shell lookup is denied by SELinux; an authorized
client/proxy route remains unproven. Those gates
and the ABFT0475 descriptor are narrower open boundaries; see the [owning updater analysis](../platform/ota_update_stack.md#current-y175-development-calibration-import-route-2026-11-15).
The earlier 308-byte `/data/local/tmp` file remains inactive. A subsequent
authorized USB experiment wrote the same XML byte-exactly to the FAT32 drive
root through MediaStore and remounted the volume. USBNotifier logged
`onUsbMounted: 0`; no calibration-discovery/install event or application was
demonstrated. Native tracing and a live manifest marker then established an
eight-character basename requirement. The XML now remains on USB as
`a11brand.calovride`; the superseded descriptive-name USB copy was removed.
A temporary auto-install marker did not register a package. See the owning
updater reference for the user10 MediaStore method and distinction between mount-callback success,
protected staging and actual installation. The existence of the copier or
USB file does not make the blocked shell copy a successful installation.

**Reboot scope:** a successful persistent theme change may require consumer
process restart or Android reboot because the theme is cached. Reboot does
not apply a denied command. No reboot/power cycle is needed for the rejected
launcher test; no reboot was issued. A future experiment needs a named
calibration/runtime target, an implemented authorized route and a rollback
covering value, version, ownership and any affected child records.

## 4. Direct DB edit (Layer B — simplest, if you already have a `vendor_cald` foothold)

`[C]` This mirrors exactly what `calserviced` does internally (`UPDATE AllCalSets set CalVersion=?, CalValue=?, OverRiden=? WHERE _id=?`, then `UPDATE AllCalSets SET CalValue=%u WHERE _id="UPDATE_INDICATOR"`):

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
**2026-11-14 schema correction:** `OverRiden` must not be treated as a
Boolean flag. In the owner-supplied update-cache DB, all 982 nonzero values
match `ModuleData.ModID`; that table records 14 applied override packages.
The SQL above is a template, not a validated deployment: determine the correct
module ownership semantics before assigning `<OVERRIDE_MODULE_ID>`. Neither
this field nor a nonzero count proves a manual modification. The archive
omits the actual `.cmod` files and is not a complete erase-recovery backup.
See the [owning calibration baseline](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12).

The cell is a native integer; the package checksum/digest is not stored around
each DB cell. Direct DB modification would require filesystem authorization,
not merely recalculating transfer integrity. Corrected 2026-11-15: the directory
is labeled `calibration_data_file` and owned by Unix identity `vendor_cald`
(mode 770); the daemon's SELinux domain is `calserviced`. A root UID alone does
not establish the required SELinux access. Ordinary ADB shell has no verified
write path. The local `.calovride` entry conditions and format remain separate
from UDS and signed-container acceptance; see §3d.

A local override package must match the actual `calserviced` parser and the production-build entry point. The strings alone do not establish the precise package header/CRC format, and a generic ZIP wrapper is not a proven accepted artifact. A direct database edit also requires the appropriate privileges and has not established the intended display behavior.

---

## 5. Offline checks and the withdrawn re-sealing script

The previous `calseal.py build` example assembled a guessed five-byte native message header
and digest. It did not create a valid signed CSM container and was not a validated flash
procedure. That builder and the executable deployment examples have been removed.

Useful read-only checks are:

```python
checksum = (sum(native_message_body) & 0xffff) ^ 0xa55a
assert hashlib.sha256(stock_csm_container[858:]).digest() == stock_csm_container[30:62]
```

The first formula concerns the native transport message body; the second concerns the stock
container. They operate on different byte ranges and are not a complete signing procedure.
The exact RSA signed spans and reproducible public-key checks are in the
[central reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

## 6. What is established for `$27` and custom writes

The reported 2026-11-10 stock LTZ write used the radio's SBI-dependent all-FF SecurityAccess
exchange, then transferred and finalized all 14 stock containers successfully. That proves
authorization for the stock write in that state. It does not prove a custom package is accepted.
The real-seed CMAC implementation remains unverified on hardware.

Modified-package attempts were rejected with `7F 36 72` after recomputing the payload digest.
The source notes alternately blamed a stale chunk checksum and RSA verification; no isolated
test settled the cause. Failed attempts removed target slots and required stock restoration.
The former claim that `$27` is the only wire-side wall is withdrawn.

Local `*.calovride`/database application, a development override installer, and the named
Signature-Bypass Ticket are different candidate paths. None is established here as a usable
production custom-calibration bypass. An ADB shell alone does not prove `vendor_cald` access.
Do not infer a security flag from an EEPROM address without the current evidence in the
[central reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

## 7. Validation boundary

A successful future custom-write result must establish the active build-specific loader,
complete protocol acknowledgements and post-reset database/display behavior. Matching stock
metadata or computing a correct checksum/digest does not establish those results. A direct
SQLite value change is also not proof that the display accepts the selected mode.

**Correction reason/date (2026-11-11):** preserve the useful checksum disassembly and database
identity while removing the false unsigned-container premise, guessed builder, and unsupported
acceptance claims. No custom package was generated or flashed for this documentation update.

---

## Appendix — provenance
- Checksum algorithm: `bin__diagnosticsd` `fcn.00028d20`, called from `createCalibrationRequest` (`fcn.0002fde0`), string `Calibration Request Checksum (0x%04X vs 0x%04X) failed`. **Directly disassembled — high confidence.**
- SHA‑256: `SHA256_Init/Update/Final` imports + `generateSHA256` symbol + `CAL_MESSAGE_DIGEST_FAILURE`; used in `UDSTransferDataRequestHandler.cpp` finalize path.
- Native-message header offsets 3–4 (checksum) and data-at-5: disassembled in `createCalibrationRequest`; bytes 0–2 and wire mapping require validation. This is not the CSM signed header.
- DB facts: queried live from `scratchpad/diagx/calibrations__CalSets.db`.
- `$27`/VIP/EEPROM anchoring and the two write paths: `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md`, `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt`.

## Direct T1 override-clear result (2026-11-14)

**Historical result before LTZ restoration; calibration clearing is now
forbidden. This records the earlier outcome, not a current test procedure.**

This is separate from edited-package transfer or direct SQL mutation. The
explicitly authorized native 0249 start completed over T1, returned 71 01 02 49
and produced the daemon's ALL OVERRIDES CLEARED log. All 14 reported current
calibration-module identities changed to 70008/00. MEC remained FF and no MEC
reset/write was issued. The archived 982 nonzero OverRiden rows describe the
pre-clear exported snapshot; no post-clear live SQLite row count was obtained.
See the [owning clear record](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).

**Post-power-cycle correction, 2026-11-14:** the owner subsequently rebooted
by removing/restoring power. RH850 entered `NoCalibration (0xe)` after the
startup fault timeout; the display reported bad/incomplete calibration.
T1 diagnostic reads still worked, MEC stayed FF, and all 14 cleared module
identities remained base 70008/00. USB ADB did not reappear. See the
[owning post-boot finding](../diagnostics/diagnosticsd_routines_and_recovery.md#owner-power-cycle-after-clear-nocalibration-fault-2026-11-14).

**Recovery completed, 2026-11-14:** the main MDI2 client restored the pinned
stock LTZ package to this cleared A11. The exact 70008/00 profile required a
one-time in-memory source exception; the erased VIN was restored from the
owner's supplied value before programming. All 14 slots and VIN matched
post-reset readback; F0F1/F0F2 were `0000`. Later UART boots reached HMI ready
with calibration state `2`, and the owner confirmed normal radio operation.
ADB and final MEC were not rechecked. See the
[completed MDI2 recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
