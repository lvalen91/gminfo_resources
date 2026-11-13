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
- Target address is **not validated**; source address gates a trust tier (`0x00FA` factory tester, `0x00F1`, `0xF0`; untrusted → `generalReject 0x10`).
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

## 4. Direct DB edit (Layer B — simplest, if you already have a `vendor_cald` foothold)

`[C]` This mirrors exactly what `calserviced` does internally (`UPDATE AllCalSets set CalVersion=?, CalValue=?, OverRiden=? WHERE _id=?`, then `UPDATE AllCalSets SET CalValue=%u WHERE _id="UPDATE_INDICATOR"`):

```sql
-- flip the enum, mark it overridden, bump the row's CalVersion
UPDATE AllCalSets
   SET CalValue = 3,
       OverRiden = 1,
       CalVersion = CalVersion + 1
 WHERE _id = '__-Jk4IQIEeWHkIX-EVZFdA';   -- SCREEN_RESOLUTION

-- force consumers to re-read (only if the row exists in your DB copy)
UPDATE AllCalSets SET CalValue = CalValue + 1 WHERE _id = 'UPDATE_INDICATOR';
```
Because the cell is a native integer, no checksum/SHA applies at this layer — the *package* CRC (§3c) is what `calserviced` checks, and if you write the DB in place you have bypassed the package entirely. The catch is filesystem access: `/mnt/vendor/calibration/` is `vendor_cald` context (dir mode 770), reachable only from an on‑device root/`vendor_cald` foothold, not from adb‑shell or the wire. `research/T1…` §3b notes a `*.calovride` `OVERRIDE_BACKDOOR` in `calserviced` that applies overrides skipping `$27` — check whether it is compiled into this release before relying on it.

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
