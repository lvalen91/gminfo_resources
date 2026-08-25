# Hand-editing `SCREEN_RESOLUTION` in CalSets.db and re-sealing the integrity fields

**Target:** GM MY22/Y181 IVI (Intel Apollo Lake SoC, GHS INTEGRITY host + Android 12L guest), 2024 Silverado head unit — the owner's own module.
**Goal:** flip `SCREEN_RESOLUTION` (CalType 4 enum) from `2` (1280×768) to `3` (1920×1080), recompute the 16‑bit checksum and the SHA‑256 so `diagnosticsd`/`calserviced` accept the change, and package it for a UDS `$34/$36/$37` transfer.

Everything below is grounded in the owner's own extracted artifacts:
- `scratchpad/diagx/calibrations__CalSets.db` (the live SQLite DB)
- `scratchpad/diagx/bin__diagnosticsd` (UDS receiver — checksum + SHA‑256 code)
- `scratchpad/diagx/bin__calserviced` (on‑device override applier — SQL + package format)
- corroborating notes in `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` and `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt`

Confidence tags: `[C]` confirmed from a binary/DB, `[I]` inferred, `[O]` open/needs a known‑good capture to pin.

---

## 0. The one thing to understand first: there are TWO integrity layers, and neither is a signature

`[C]` **The calibration blob is NOT signature‑protected.** There is no RSA/X.509/SecOC anywhere in the cal path — only two *recomputable* integrity fields. That is the whole reason a hand‑edit is possible:

| Layer | Where it runs | Integrity field(s) | On failure |
|---|---|---|---|
| **A — UDS transfer** | `diagnosticsd` on TCP `49156`, parses the `$34/$36/$37` calibration message | **16‑bit checksum** (`Calibration Request Checksum (0x%04X vs 0x%04X) failed`) + **SHA‑256** (`generateSHA256`, OpenSSL `SHA256_Init/Update/Final`) | `CAL_CHECKSUM_FAILURE` / `CAL_MESSAGE_DIGEST_FAILURE` |
| **B — on‑device apply** | `calserviced` inotify‑watches `/mnt/vendor/calibration/overrides/`, unzips a "mod file", writes rows into `CalSets.db` | **zip/package header CRC** (`header crc mismatch`, `bad header_len`) + a `MANIFEST_NOTICE` | package rejected, no rows applied |

`[C]` The **single hard gate** is UDS SecurityAccess `$27` in front of Layer A. That seed/key is validated *by the VIP (RH850) via PROTOKEY + the M24C64 EEPROM* — its algorithm is **not in the SoC firmware**, so you cannot derive it from these binaries. The checksum and SHA‑256 are trivially recomputable; `$27` is the wall. (See §7 for the local‑only routes that sidestep `$27`.)

`[C]` **What actually lives in the DB row is a bare SQLite value, not a blob.** Verified directly:

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
Across the whole `AllCalSets` table there are **zero** BLOB cells (1852 integer / 154 real / 567 text). **So the checksum and SHA‑256 do not wrap the DB cell — they wrap the transfer/override *container*.** Editing the DB directly (Layer B side) is one operation; sealing a UDS payload (Layer A) is the other. Both are documented below.

Enum options (`EnumSets`, confirmed):
```
0 = SIZE_800_BY_480
1 = SIZE_1280_BY_720
2 = SIZE_1280_BY_768   ← current
3 = SIZE_1920_BY_1080  ← target for 2→3
4 = SIZE_2400_BY_960   (panel native per hardware/teardown.md)
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
- Stored little‑endian as a 16‑bit word inside the request header (see §3).

---

## 2. SHA‑256 scope

`[C]` Standard **OpenSSL SHA‑256** (`SHA256_Init` → `SHA256_Update` → `SHA256_Final`), wrapped as `gm::diag::Util::generateSHA256(std::string&)`. A mismatch raises `CAL_MESSAGE_DIGEST_FAILURE`. The digest is checked around the transfer/finalize path (`UDSTransferDataRequestHandler.cpp`, `Calibration Finalize` … `handleFinalize`), i.e. it covers the **calibration data image that was streamed in `$36`**, and is verified at `$37` (transfer exit).

`[I]` Scope = the concatenated calibration payload bytes (the same bytes the §1 checksum covers), not the outer UDS framing and not the 32‑byte digest field itself. A plain 32‑byte hex/binary SHA‑256, no HMAC, no salt (no key material is referenced near the call).

`[O]` **The exact byte range is the only thing you should not take on faith.** Whether the hash includes the 5‑byte parse header, or only the data after it, and whether the digest sits in the `$37` finalize message or trails the image, must be pinned against **one known‑good captured transfer**. §6 gives a `solve` mode that does exactly this — it brute‑checks candidate ranges until both the stored checksum and the stored digest reproduce, so you never have to guess.

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
`[C]` for offsets 3–4 and the data start; `[I]` for the field semantics of bytes 0–2:
```
offset 0 : 1  subfunction/format selector   -> jump table @0x14ca8 picks Init($34)/Transfer($36)/Finalize($37)
offset 1 : 1  (secondary selector / reserved)
offset 2 : 1  length/element-count byte (validated against the PDU's reported payload size at [msg+0x18])
offset 3 : 2  CHECKSUM, 16-bit little-endian  ( movzx eax, word[r13+3] )
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

For a **package** you drop into the overrides dir instead of touching the DB, build the zip that `processZippedModFile` expects (header + CRC + manifest + the per‑row override); that CRC is a standard zlib/zip CRC‑32 over the header block — recompute it with `zlib.crc32`. The §5 script emits the DB‑row form; the zip wrapper is mechanical once you have a known‑good sample to match the manifest fields.

---

## 5–6. Python: extract → modify enum → recompute checksum → recompute SHA‑256 → repackage, with a `solve` validator

Save as `calseal.py`. Two modes:
- `solve` — feed it a **known‑good captured `$36` image** (+ its stored checksum/digest) and it discovers the exact checksum range and SHA range, so §2/§3b are confirmed for *your* build, not assumed.
- `build` — flip the enum and emit a re‑sealed payload using the ranges `solve` confirmed.

```python
#!/usr/bin/env python3
# calseal.py — CalSets SCREEN_RESOLUTION edit + integrity re-seal
import argparse, hashlib, sqlite3, sys, struct

XOR_FINAL = 0xA55A
SCREEN_RES_ID = "__-Jk4IQIEeWHkIX-EVZFdA"

def cal_checksum16(data: bytes) -> int:
    """Confirmed from bin__diagnosticsd fcn.00028d20."""
    s = 0
    for b in data:
        s = (s + b) & 0xFFFF
    return s ^ XOR_FINAL

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

# ---------- (a) extract the current value straight from the DB ----------
def db_get(db):
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT _id,CalType,CalValue,CalVersion,typeof(CalValue) "
        "FROM AllCalSets WHERE CalName='SCREEN_RESOLUTION'").fetchone()
    con.close()
    if not row: sys.exit("SCREEN_RESOLUTION not found")
    print(f"[extract] _id={row[0]} CalType={row[1]} value={row[2]} "
          f"ver={row[3]} storage={row[4]}")
    return row

# ---------- (e) write the enum back into the DB (Layer B) ----------
def db_set(db, new_val:int):
    con = sqlite3.connect(db)
    con.execute("UPDATE AllCalSets SET CalValue=?, OverRiden=1, "
                "CalVersion=CalVersion+1 WHERE _id=?", (new_val, SCREEN_RES_ID))
    con.execute("UPDATE AllCalSets SET CalValue=CalValue+1 "
                "WHERE _id='UPDATE_INDICATOR'")     # no-op if row absent
    con.commit(); con.close()
    print(f"[write] SCREEN_RESOLUTION := {new_val} (OverRiden=1, CalVersion bumped)")

# ---------- solve: confirm checksum & SHA ranges against a known-good image ----------
def solve(blob: bytes, stored_cksum:int, stored_digest:bytes):
    n = len(blob)
    ck_hits, sh_hits = [], []
    for start in range(0, min(16, n)):
        for end in range(n, max(n-16, start), -1):
            seg = blob[start:end]
            if cal_checksum16(seg) == stored_cksum: ck_hits.append((start,end))
            if stored_digest and sha256(seg) == stored_digest: sh_hits.append((start,end))
    print("[solve] checksum range(s):", ck_hits or "NONE — check endianness/field position")
    print("[solve] sha256   range(s):", sh_hits or "NONE")
    return ck_hits, sh_hits

# ---------- (b/c/d/f) build a re-sealed $36 payload ----------
def build(data_payload: bytes, subfunc:int, count:int,
          cksum_range=None, sha_range=None):
    """data_payload = the calibration DATA (offset-5 bytes) with the enum already flipped.
       Returns (parse_msg, digest). cksum_range/sha_range default to 'whole data payload'
       — override with what solve() reported for your build."""
    body = data_payload if cksum_range is None else data_payload[cksum_range[0]:cksum_range[1]]
    cksum = cal_checksum16(body)                          # (c) recompute 16-bit checksum
    header = bytes([subfunc & 0xFF, 0x00, count & 0xFF]) + struct.pack("<H", cksum)
    parse_msg = header + data_payload                     # 5-byte header + data (offset 5)
    sha_src = data_payload if sha_range is None else data_payload[sha_range[0]:sha_range[1]]
    digest = sha256(sha_src)                              # (d) recompute SHA-256 (32 bytes)
    print(f"[build] checksum=0x{cksum:04X}  digest={digest.hex()}")
    return parse_msg, digest

def frame_uds(src:int, tgt:int, uds_payload: bytes) -> bytes:
    """(f) GM UDS-over-TCP framing for port 49156."""
    return struct.pack(">HHI", src, tgt, len(uds_payload)) + uds_payload

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract"); p.add_argument("db")
    p = sub.add_parser("dbset"); p.add_argument("db"); p.add_argument("value", type=int)
    p = sub.add_parser("solve")
    p.add_argument("blob"); p.add_argument("cksum", type=lambda x:int(x,0))
    p.add_argument("--digest", default="")
    p = sub.add_parser("build")
    p.add_argument("data"); p.add_argument("--subfunc", type=lambda x:int(x,0), default=0x36)
    p.add_argument("--count", type=int, default=0)
    a = ap.parse_args()
    if a.cmd=="extract": db_get(a.db)
    elif a.cmd=="dbset": db_set(a.db, a.value)
    elif a.cmd=="solve":
        blob=open(a.blob,"rb").read()
        solve(blob, a.cksum, bytes.fromhex(a.digest) if a.digest else b"")
    elif a.cmd=="build":
        data=open(a.data,"rb").read()
        msg,dig = build(data, a.subfunc, a.count)
        open("cal_parse_msg.bin","wb").write(msg)
        open("cal_digest.bin","wb").write(dig)
        print("[build] wrote cal_parse_msg.bin, cal_digest.bin")
```

**Typical run:**
```bash
# (a) see the current value
python3 calseal.py extract calibrations__CalSets.db

# confirm the algorithm scope against a real captured $36 image (do this once)
python3 calseal.py solve good_cal36.bin 0x1234 --digest <64-hex>
#   -> prints the exact byte ranges that reproduce the stored checksum & digest

# (b/c/d/f) flip the enum inside the data payload, re-seal
python3 calseal.py build cal_data_res3.bin --subfunc 0x36 --count <n>

# (e) OR just edit the DB directly if you have the vendor_cald foothold
python3 calseal.py dbset CalSets.db 3
```

`(b) parse/modify the enum`: `SCREEN_RESOLUTION` is a single‑element enum, so "the data" is just the one integer `2` → set it to `3`. If your captured cal record encodes it in a wider field, `solve` tells you which byte moved between two dumps that differ only by resolution.

---

## 7. `$27` — the actual wall, and the owner's lever

`[C]` The checksum/SHA are free; **the only thing that stops a wire‑side write is UDS SecurityAccess `$27`**, and its seed/key is computed in the **VIP (RH850)** from **PROTOKEY + the M24C64 EEPROM**, not in the SoC — so it cannot be derived from `bin__diagnosticsd`. Practical routes the corpus identifies:
- **Direct DB / override package** (§4) once you have a `vendor_cald` foothold — no `$27` at all.
- **`*.calovride` OVERRIDE_BACKDOOR** in `calserviced` — skips `$27`; verify it is compiled into this release (`scratchpad/diagx/bin__calserviced` `main()` path) `[O]`.
- **EEPROM lever** — the owner already writes the M24C64 (the `0x0441/0x0A81` SBI "0xFF" ADB bypass). The same VIP subsystem anchors the cal `$27` level, but it is **not yet proven** that any single EEPROM flag opens the *calibration* gate the way `0x0440` opens ADB — that is the open experiment (candidates `0x04A0/0x04C0/0x0A40/0x0BE0`, one at a time, backup first) `[O]`.

---

## 8. Validate before you send

1. **Round‑trip the checksum:** `cal_checksum16(cal_checksum16-covered bytes)` of your *unmodified* captured record must equal its stored `0x%04X` field. If not, fix the range/endianness with `solve` before trusting the edit.
2. **Round‑trip the SHA:** same for the digest — reproduce the stored 32‑byte digest on the *unmodified* image first.
3. **DB sanity:** after `dbset`, re‑query — `CalValue` must read back `3`, `typeof()` still `integer`, `OverRiden=1`, `CalVersion` incremented. Enum value must be within `Min..Max`/options (0–4); `diagnosticsd` also range‑checks element count vs the reported payload size (header byte 2), so keep `count` consistent.
4. **Dry‑run the transfer parse locally:** feed `cal_parse_msg.bin` through your own copy of the §1 checksum and §2 hash and confirm they equal the fields you embedded — this is precisely what `createCalibrationRequest` → `fcn.00028d20` and the `$37` finalize do on‑device.
5. **Keep a restore image:** snapshot `CalSets.db` (and, if you touch it, the EEPROM region) before writing; `OTA/SPS` will reset overrides and re‑lock EEPROM SBI flags, so keep the re‑apply steps handy.
6. **Reversibility:** to revert, `dbset … 2` (and `OverRiden=0`), or `clearAllOverrides` (`DELETE FROM AllCalSets WHERE OverRiden=1`) which `calserviced` exposes.

---

## Appendix — provenance
- Checksum algorithm: `bin__diagnosticsd` `fcn.00028d20`, called from `createCalibrationRequest` (`fcn.0002fde0`), string `Calibration Request Checksum (0x%04X vs 0x%04X) failed`. **Directly disassembled — high confidence.**
- SHA‑256: `SHA256_Init/Update/Final` imports + `generateSHA256` symbol + `CAL_MESSAGE_DIGEST_FAILURE`; used in `UDSTransferDataRequestHandler.cpp` finalize path.
- Header offsets 3–4 (checksum) and data‑at‑5: disassembled in `createCalibrationRequest`. Bytes 0–2 semantics inferred from the jump table + length check.
- DB facts: queried live from `scratchpad/diagx/calibrations__CalSets.db`.
- `$27`/VIP/EEPROM anchoring and the two write paths: `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md`, `research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt`.
</content>
</invoke>
