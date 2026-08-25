# DPS Type4 Custom Calibration Archive — Building & Deploying a Hand-Edited `SCREEN_RESOLUTION`

**Target:** GM Infotainment 3.7/3.8 (A11 CSM / "gminfo37"), build W231E-Y181.3.2.
**Goal:** flip `SCREEN_RESOLUTION` from `2` (1280×768) to `3` (1920×1080) or `4` (2400×960) via a
custom Type4 archive pushed with the owner's DPS + Bosch MDI2, **bypassing the SPS catalog** that
would otherwise only offer GM-released part numbers.
**Status of this doc:** procedural guide grounded in the repo's prior RE. Read §1 first — it corrects
a common misconception about what a DPS Type4/`.cfx` archive actually *is*, because it changes which of
the two build paths (§4 vs §5) will actually move the enum.

---

## 0. TL;DR — the honest answer up front

1. **A DPS "Type4 Application" is a UDS-driving program, not a data patch.** The archive carries a PE32
   `.dll` (interpreter that drives `$10/$27/$31/$34-37/$11` via `tisvcsv4.dll`) plus a `.cfx` **XML
   workflow** file (button text + action IDs). The `.cfx` is **not** where `SCREEN_RESOLUTION` lives.
   You cannot "type 1920×1080 into a `.cfx`" and have it flash — that's a category error the earlier
   corpus explicitly warns about (`.cfx` = "UI/workflow configuration only, NOT raw binary data").
2. **The `SCREEN_RESOLUTION` value lives in the SoC-side `CalSets.db`** as a `CalType 4` (enum) row,
   current `CalValue 2`, `EnumID _PWvKYIQHEeWHkIX-EVZFdA`. The blob that carries it is written through
   the **calibration-programming path** (`$34/$36/$37` → `/mnt/vendor/calibration/overrides/` →
   `calserviced` applies it), **not** through a Type4 `.cfx`.
3. **There is no RSA/X.509 signature on the cal blob.** Integrity is a **16-bit checksum +
   SHA-256 only** — both recomputable by whoever edits the blob. So "custom / not-from-catalog" is
   *not* a cryptographic wall at the CSM.
4. **The one real wall is UDS `$27` SecurityAccess**, whose key algorithm is anchored in the VIP
   PROTOKEY + EEPROM and is *not* present in the SoC firmware to derive. Standalone DPS cannot compute
   it (it normally calls the GM backend). **This is the gate, not a signature and not the catalog.**
5. **The SPS catalog restriction is a DPS/TIS2Web front-end policy, not an on-radio check.** It is
   enforced by matching part numbers against `tis2web.txt`/the GM backend inside the tool. It can be
   sidestepped two ways: (§4) build a hand-rolled SPAT archive so DPS flashes files the catalog never
   offered, or (§5) skip DPS entirely and drive the MDI2 as a raw J2534/DoIP UDS device. **Neither
   removes the `$27` gate.**

So: **building the custom archive is straightforward; whether it *deploys* comes down entirely to
whether you can satisfy `$27` on the calibration security level.** See §6 for the accept/reject matrix.

---

## 1. Two things both called "calibration" — do not conflate them

| | **CalDef / `.cfx` (Type4/SPS side)** | **`CalSets.db` enum (the actual value)** |
|---|---|---|
| What it is | XML workflow: `<Config><Text><Action>` | SQLite row: `AllCalSets` + `EnumSets` |
| Where | Inside the DPS/SPAT archive `bin/` | `/mnt/vendor/calibration/database/CalSets.db` on the SoC |
| Holds `SCREEN_RESOLUTION`? | **No** (workflow only) | **Yes** — `CalType 4`, `CalValue 2`, EnumID `_PWvKYIQHEeWHkIX-EVZFdA` |
| Written by | DPS flashes the archive; DLL drives UDS | `$34/$36/$37` cal transfer → `calserviced` inotify apply |
| Integrity | package `.smd` signature (module-level) | 16-bit checksum + SHA-256, **no signature** |

The Type4 archive is the *transport wrapper and workflow*; the enum change is the *payload the transport
carries*. You need the archive (or a raw UDS session) to move a payload the catalog won't give you — but
the payload itself is a `CalSets.db` cal blob, not a `.cfx`.

---

## 2. CalGroup / Blob-ID mapping — how to identify which blob is the cal

### 2.1 DPS blob IDs (from `SPSToolBridge.LOG`)
DPS enumerates every file in a programming event as a **Blob**. Grab the log from a real SPS session at
`C:\Users\<user>\sps\SPSToolBridge.LOG`. Format:

```
Blob name: 10011000.dll, Blob ID: 0,  Blob Size: 234283   <- Utility (PE32 interpreter, ALWAYS Blob ID 0)
Blob name: 10000001.cfx, Blob ID: 1,  Blob Size: 124      <- Calibration workflow (.cfx XML)
Blob name: 10013941.dll, Blob ID: 16, Blob Size: 267107   <- second utility
Blob name: 10013940.cfx, Blob ID: 17, Blob Size: 499      <- second cal
```

Rule: **Blob ID 0 = utility `.dll`** (the interpreter/opcode driver). **Odd/subsequent IDs = `.cfx`
calibration workflow files.** `8xxxxxxx` bare filenames = GM part-number firmware/partition images.
A known-good real Type4 example lives in this repo: `research/canbus_reset/` — `10017908.dll`
(`GbPowerModeList.dll`, exports `CMessage/GetResult/Launch/SetInternal`, imports `tisvcsv4.dll`,
calls `CBuildService::SetInitToType4Mode()`) + `10017909.cfx` (`<Action Id="2068"><Text Id="881">Reset
ECU`). That pair *is* a minimal Type4 app; clone its shape.

### 2.2 VIP CalGroup indices (the other "cal" numbering — don't confuse with Blob IDs)
The VIP MCU serves cal groups 0–14 to the SoC over IPC on boot (`[J6_CDD] Calibration_Request_CalGroup:
GetCal Index = X`). These are **VIP-firmware** cals (timing/power), one-way VIP→SoC, and are **not** the
`SCREEN_RESOLUTION` store. Ignore them for this task — `SCREEN_RESOLUTION` is a **SoC/Android**
calibration in `CalSets.db`, reached via the SoC calibration-programming path, not VIP CalGroups.

### 2.3 The `CalSets.db` row you are actually editing (verified from the extracted DB)
```
Table AllCalSets:
 _id        = __-Jk4IQIEeWHkIX-EVZFdA
 CalDefFile = GIS738_RVCVIDEOROBUSTNESSREQUIREMENT  (version 7)
 CalName    = SCREEN_RESOLUTION
 CalType    = 4        (4 = enumeration)
 CalValue   = 2        (current: 1280x768)
 EnumID     = _PWvKYIQHEeWHkIX-EVZFdA

Table EnumSets (EnumID _PWvKYIQHEeWHkIX-EVZFdA):
 0 = SIZE_800_BY_480
 1 = SIZE_1280_BY_720
 2 = SIZE_1280_BY_768   <- current
 3 = SIZE_1920_BY_1080
 4 = SIZE_2400_BY_960   <- panel native (per hardware/teardown.md)
```
That is the exact identity map to carry into whichever blob format the module's cal loader expects.

---

## 3. Step (a)+(b)+(c): extract baseline, edit the enum, recompute integrity

### (a) Extract a baseline
Two sources, pick by what you can reach:
- **Offline (recommended for building):** pull `CalSets.db` from a vendor image and read the row:
  ```bash
  sqlite3 CalSets.db \
    "SELECT _id,CalName,CalType,CalValue,EnumID FROM AllCalSets WHERE CalName='SCREEN_RESOLUTION';"
  ```
  (Extracted copy already in this session at
  `.../scratchpad/soc_extract/rootfs/vendor/calibrations/CalSets.db`.)
- **On the wire:** open a default/extended UDS session to the CSM and read the cal with `$22`/`$1A`
  (reads are effectively open — no `$27` needed to *read*). Capture the raw response bytes; that is your
  baseline **cal blob** with its existing checksum + SHA-256 trailer.

### (b) Modify the enum
Change the value field from `2` → `3` (1920×1080) or `4` (2400×960, panel-native). In the DB it is a
one-cell update; in a captured **cal blob** it is the single enum byte inside the data region. Keep the
`EnumID` and `CalType` identical — you are only re-selecting an already-defined enum member, so it stays
inside `Min/Max` and the enum table already contains the target, which maximizes the chance the loader
accepts it.

### (c) Recompute integrity — **both** fields, in order
The cal path enforces exactly two integrity checks and **no signature**:
1. **16-bit checksum** — failure raises `CAL_CHECKSUM_FAILURE`. Recompute over the data region per the
   blob's header (sum/CRC-16; confirm width against a known-good captured blob by zeroing the field and
   re-summing until it matches the original).
2. **SHA-256** — failure raises `CAL_MESSAGE_DIGEST_FAILURE` (`generateSHA256`). Recompute over the
   defined digest span and write it into the trailer.

Blob layout is `[header + checksum + data + SHA256]`. Order matters: edit data → fix the 16-bit checksum
→ then compute SHA-256 over the span that includes the corrected checksum (verify span against a
known-good blob). Because there is **no RSA/SecOC** anywhere in the cal path, once these two match the
module has no cryptographic basis to reject the *content*.

---

## 4. Step (d)+(e), PATH A: package as a DPS Type4/SPAT archive and flash from DPS

Use this if you want the change to go through the owner's DPS UI (logging, MDI2 routing, power-mode
checks all handled for you) and you specifically want to defeat the **catalog** restriction while still
using the tool.

### 4.1 Archive (zip) layout
DPS Archive Creator / SPAT consumes a zip whose interior mirrors a real SPS event:

```
CustomType4_SCREENRES.zip
├── Vit2File.vit            # binary file index (see 4.2)
├── SPSToolBridge.txt       # Blob name/ID map (see 2.1) — lists every file + Blob ID
├── tis2web.txt             # Vehicle -> Part# map (see 4.3); the catalog-bypass lever
├── delivery_manifest.csv   # human-readable file list + sign attributes (see 4.4)
├── <name>.mnf              # update manifest / workflow script (gmext.* calls)   [optional for Type4-app]
├── <name>.smd              # package signature (module-level)                    [see 6.3]
└── bin/                    # gzip-compressed payload files
    ├── 10011000.dll        # Blob ID 0: utility interpreter (reuse canbus_reset DLL shape)
    ├── 100000XX.cfx        # Type4 workflow XML (button/action) — drives the cal write
    └── 8xxxxxxx            # the cal PART FILE carrying your edited SCREEN_RESOLUTION blob
```

The **edited cal blob from §3 goes in as the part-number payload file** (`8xxxxxxx`), *not* inside the
`.cfx`. The `.cfx` only names the action; the `.dll` drives the `$34/$36/$37` transfer of the part file.

### 4.2 `Vit2File.vit` (binary index)
```
Offset 0x60: "GMSUPPLIERNO_001"   (supplier tag)
then per entry: [ModuleID byte][Filename padded to 20 chars][0xFF padding]
```
Add one entry per file in `bin/`, using the same Module ID you target (CSM = `0x80`). Match the byte
layout of a real `.vit` exactly — the header magic and 20-char pad are load-bearing.

### 4.3 `tis2web.txt` — the actual catalog-bypass point
```
A11  00  N/A  85577468
A11  02  N/A  87863250
...
A11  <opt> N/A <YOUR_PART_NUMBER>   <- point an option code at your custom cal part file
```
The SPS catalog restriction is DPS consulting this vehicle→part map (and the backend) to decide which
parts it will offer. By authoring the archive's own `tis2web.txt` and referencing your `8xxxxxxx` cal
file, DPS will flash a part the online catalog never listed. **This is the bypass** — and note it is a
*front-end* trick: it changes what DPS is willing to send, nothing about what the CSM will accept.

### 4.4 `delivery_manifest.csv`
Fields: `Part Number, Part ID, Description, DLS/PLS, Model Year, Product Code, Release Type, Sign Type,
Signing Attribute, Module ID, CVN, EWO, Fill/Pad Byte, ... File, Bypass P/N & Module ID Check, From/To
Part Number, ...`. Set **`Sign Type = NONE`** for the cal (calibrations are not module-signed) and set
**`Bypass P/N & Module ID Check = TRUE`** so DPS doesn't refuse the non-catalog part number.

### 4.5 Import & flash
1. `RunMe.exe` (DPS Archive Creator V2) → import the staged folder → it produces the SPAT `.zip`.
2. In DPS: connect MDI2 (J2534), select the custom archive, run the programming sequence.
3. DPS will drive: `$10 03` (extended) → `$27` seed/key → `$34` RequestDownload → `$36` TransferData
   (your cal blob, ~4 KB chunks) → `$37` TransferExit → optional `$11` reset. Power mode must be Run/
   Service or the BCM power-mode check aborts (as seen in the canbus_reset Type4 app).

**Where this path stops:** at the `$27` step DPS asks the GM backend for the key. Standalone / offline it
**cannot unlock** the calibration security level. See §5 for the owner's actual lever and §6 for outcomes.

---

## 5. Step (d)+(e), PATH B: skip DPS, drive the MDI2 as a raw UDS device (owner's real route)

The MDI2 is a full J2534 / DoIP transport; **only DPS constrains itself to SPS policy, the hardware does
not.** This removes the catalog entirely and lets you present the cal blob directly.

- **Transport:** MDI2 native DoIP (Ethernet, port 13400) works cross-platform; or the SoC's own
  `diagnosticsd` UDS-over-TCP on `eth0:49156` (GM 8-byte framing, target address unvalidated).
- **Stack:** `pip3 install udsoncan doipclient python-can`.
- **Sequence:** `$10 03` → `$27 01` (seed) → `$27 02` (key) → `$34` → `$36` (chunks) → `$37` → `$11`.
  Templates: `research/MDI2_RAW_UDS_BYPASS_GUIDE.md` §2 (seed test) and §3 (`$34/$36/$37` cal write).

**The `$27` problem is identical here** — DoIP doesn't compute the GM key either. What is different for
*this owner* is the EEPROM lever:

- The owner already flips the **M24C64 SBI bytes** `0x0441`/`0x0A81` → `0xFF`, which makes the VIP return
  an **all-`0xFF` seed** and skips PROTOKEY/BCM auth (the ADB bypass). Verified effect: DPS logs show the
  all-FF seed state (`A11_CSM_x80.Txt`) vs a real 32-byte ECUID+challenge (`Y177update_CSM.Txt`).
- **Open, unproven question (do not overclaim):** the SBI flip is demonstrated to open the **ADB** `$27`,
  but it is *not yet shown* to open the **calibration/diagnostic** `$27` level. Same VIP/PROTOKEY/EEPROM
  subsystem and anchor, but not a proven single flag. If a *different* EEPROM flag governs the cal
  security level, candidates to probe (one at a time, backup first) are `0x04A0`, `0x04C0`, `0x0A40`,
  `0x0BE0` (near the secure-IPC / feature-flag regions). This is the concrete next experiment, not a
  settled result.
- **Software-only variant:** `calserviced` reportedly contains an `OVERRIDE_BACKDOOR` that applies
  `*.calovride` files **skipping `$27` entirely**, but it needs a `vendor_cald`-context filesystem write
  (dir mode 770) — reachable only from an on-box foothold (e.g. the SBI-enabled ADB shell), not from the
  wire. Whether it survives in this release is undetermined; check `calserviced` `main()`.

So Path B's realistic best case for the owner: **SBI-enabled ADB shell → drop the edited override zip
(`processZippedModFile` / `apply_overrides`) into `/mnt/vendor/calibration/overrides/` → `calserviced`
applies it on inotify → `CalSets.db` updated → reboot.** That never touches `$27` at all and is the
cleanest route if the `vendor_cald` write is reachable.

---

## 6. Step (f): what happens — accepted vs rejected by the CSM

There is **no single "reject unsigned cal" behavior**, because the cal path has no signature. Outcome is
decided by three independent checks, in this order:

| Stage | Check | Pass | Fail |
|---|---|---|---|
| 1. DPS front-end (Path A only) | Part# in catalog / `tis2web.txt` | proceeds | **catalog refusal** (the SPS restriction). Bypassed by §4.3 or by using Path B. |
| 2. Security | UDS `$27` seed/key on the **cal** level | transfer allowed | `$7F 27 35` (Invalid Key) or `$7F 34 33` (securityAccessDenied). **The real wall.** DPS offline can't compute the key; the EEPROM/SBI lever (§5) is the owner's only candidate. |
| 3a. Integrity | 16-bit checksum | continue | `CAL_CHECKSUM_FAILURE` → blob rejected, cal unchanged |
| 3b. Integrity | SHA-256 digest | **applied** | `CAL_MESSAGE_DIGEST_FAILURE` → blob rejected, cal unchanged |

**Key conclusions:**
- **"Custom / not from SPS catalog" is NOT rejected by the CSM cryptographically.** The catalog is a
  tool-side policy (stage 1). If you satisfy stages 2 and 3, the module applies your edited enum because
  it has no notion of "GM-released vs hand-made" — only checksum + SHA-256 + `$27`.
- **Unsigned is fine for calibrations.** Module *firmware* is RSA/TSS-signed (stage would be a signature
  check and you'd get rejected without GM keys), but the **calibration blob is not** — confirmed: no
  RSA/X.509/SecOC anywhere in the cal path.
- **The decisive gate is `$27`.** If the calibration security level is locked and you cannot derive the
  key, the transfer (`$34`) is denied and nothing is written — regardless of how perfect your blob is.
- **If all three pass:** `calserviced` writes the new `SCREEN_RESOLUTION` into `CalSets.db`; on reboot
  the display/RRO/DisplayArea stack reads the new enum. Expected accept.
- **A malformed blob does not brick** — a failed checksum/SHA just leaves the prior cal in place; the cal
  store is override-based and DPS/SPS can re-flash the stock cal to restore.

---

## 7. Risk / safety checklist — before touching the live radio

- [ ] **Back up first.** Read and save the current `CalSets.db` / the current `SCREEN_RESOLUTION` cal
      blob (via `$22`/`$1A` or file pull) so you can restore. Save the stock part number too.
- [ ] **Back up the EEPROM** (full M24C64 8 KB dump) before any SBI/flag experiments. Have both the
      stock and modified dumps on hand (repo already keeps `eeprom/bins/…`).
- [ ] **Change ONE thing at a time.** Only the enum value; keep `EnumID`, `CalType`, `Min/Max` untouched.
- [ ] **Pick an in-range enum member.** `3` and `4` are already defined in `EnumSets`; do not invent a
      value outside 0–4.
- [ ] **Verify both integrity fields against a known-good blob** (zero-and-recompute to confirm checksum
      width and SHA span) *before* sending — a wrong span silently fails at stage 3.
- [ ] **Power mode Run/Service, stable 12 V supply / battery maintainer.** The Type4 flow aborts on BCM
      power-mode failure; a brownout mid-`$36` is the real bricking risk, not the cal content.
- [ ] **Don't poke EEPROM structure *base* addresses** (`0x0A00`/`0x0B00`) while probing cal-gate flag
      candidates — only the flagged data bytes (`0x04A0/0x04C0/0x0A40/0x0BE0`), one at a time, restore
      from backup between tries.
- [ ] **Expect OTA/SPS to revert.** EEPROM SBI flips and cal overrides are reset by GM OTA/SPS; treat any
      success as non-persistent and re-appliable, and be ready to re-flip after an update.
- [ ] **Panel reality check.** `4 = 2400×960` is the panel-native res; `3 = 1920×1080` is not the panel's
      timing. If the display/compositor doesn't like the enum, worst case is a blank/garbled screen until
      you restore the cal — recoverable, but test with restore-path ready.
- [ ] **Legal/warranty.** This modifies a safety-adjacent module (the CSM also drives the rear-view
      camera robustness cals in the *same* CalDef file, `GIS738_RVCVIDEOROBUSTNESSREQUIREMENT`). Bench-
      unit first; don't do first attempts on a vehicle you rely on.

---

## 8. Source map (repo evidence behind each claim)

- Type4 app is a UDS-driving DLL + `.cfx` workflow: `research/canbus_reset/CANBUS_RESET_ANALYSIS.txt`,
  `research/canbus_reset/10017909.cfx.xml` (`SetInitToType4Mode`, exports, `$27` required).
- `.cfx` = workflow not data; SPAT/Archive-Creator layout; Blob-ID map; `tis2web.txt`/`Vit2File.vit`:
  `research/GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt` §15.9–15.10, §10; `research/DPS_SECURITY_ANALYSIS.txt`
  §8.2; `research/DPS_AND_MODIFICATION_LANDSCAPE.txt` §7.5–7.8; `research/tools/SPSToolBridge.txt`.
- Cal blob has no signature, only 16-bit checksum + SHA-256; `$27` is the sole gate; `calserviced`/
  overrides path; `OVERRIDE_BACKDOOR`: `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` §3b/§4/§5,
  `research/MDI2_RAW_UDS_BYPASS_GUIDE.md` §3/§5.
- `SCREEN_RESOLUTION` identity (CalType 4, value 2, EnumID, 5 enum members): verified live from
  `scratchpad/soc_extract/rootfs/vendor/calibrations/CalSets.db`; corroborated
  `research/PROVENANCE_AUDIT_AUG2026.md` #39, `research/T1_...AUG2026.md` §3b.
- MDI2 = full J2534/DoIP, not locked to DPS; raw `$27`/`$34-37` templates: `research/MDI2_RAW_UDS_BYPASS_GUIDE.md`.
- `$27` seed all-FF vs 32-byte ECUID+challenge; MEC counter; SBI flags: `research/DPS_AND_MODIFICATION_LANDSCAPE.txt`
  §7.1–7.3, `.llm_index.jsonl` DPS log entries (`A11_CSM_x80.Txt`, `Y177update_CSM.Txt`).
- EEPROM SBI (`0x0441/0x0A81`) and cal-gate flag candidates: `research/T1_...AUG2026.md` §4,
  `platform/security.md`.
```
