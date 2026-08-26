# End-to-End Workflow — Writing a Custom `SCREEN_RESOLUTION` Calibration to Your Own Radio

**Author:** Fable synthesis agent (2026-08-17)
**Subject:** Owner's own 2024 Silverado head unit — gminfo37 / Y181, Harman CSM radio, module `0x80`,
ECUID `004B41DC0000160006104145610114AC`. Owner's own licensed Bosch GM MDI2 (EL-52100-AM) + GM DPS 4.56.
**Goal:** Write a hand-edited `SCREEN_RESOLUTION` enum (2 → 3 or 2 → 4) to the owner's own radio and see the
display resolution change.

This is a synthesis of the prior analyses in this session and the repo research tree. It assembles them
into one runnable procedure. Each step lists the source finding, the exact commands/code, the expected
outcome, and what to do if it fails.

---

## 0. What is (and isn't) proven — read this first

Three assumptions the task grants me, and the evidence status behind each:

| Assumption | Status | Source |
|---|---|---|
| **SBI flip works** (EEPROM `0x0440`/`0x0A80` data byte → `0xFF` bypasses the VIP `$27` seed) | **Confirmed on VIP side** by disassembly; **measured** on the owner's own bypassed module (all-0xFF seed across 4 read sessions) | `eeprom_security_opus_B.md` §1-2, `dps_seed_fable_B.md` Q4, provenance #2-4 |
| **`$27` bypass works SoC-side** (diagnosticsd accepts the 0xFF-seed handshake for the *programming* level) | **Inferred, NOT proven** — this is the one link that must be confirmed on the bench (Step 2) | `eeprom_security_opus_B.md` §2 nuance, `dps_seed_fable_B.md` Q4 |
| **Checksum + SHA-256 recompute is feasible** (no RSA/X.509/SecOC on the cal blob) | **Confirmed** — cal integrity is a 16-bit checksum + SHA-256 only, both recomputable | `dps_seed_fable_B.md` Q3, provenance #34, T1 §102-104 |

**The load-bearing facts that make this possible:**
- `SCREEN_RESOLUTION` is a `CalType 4` enum in `CalSets.db`; current value **2 = 1280×768**; options
  `0:800×480 · 1:1280×720 · 2:1280×768 · 3:1920×1080 · 4:2400×960` (native panel = option 4). CalDef
  `GIS738_RVCVIDEOROBUSTNESSREQUIREMENT` v7. **Exact match verified in `CalSets.db`** (provenance #39 —
  "strongest single verification in the corpus").
- The cal blob is **not** signature-protected — the only barrier past `$27` is recomputing two integrity
  fields.
- The MDI2 is a plain J2534 / ISO-13400 DoIP pass-thru with **no service allow-list** — raw `$27`/`$34`/
  `$36`/`$37` go straight through. DPS's "lock" is self-imposed SPS policy, not a device restriction
  (`mdi2_j2534_compat_opus.md` §2-3).

**Two independent write surfaces exist. Pick one:**
- **Path A — UDS over the wire** (this document's spine): `diagnosticsd` on `eth0:49156` (or DoIP through
  the MDI2 to the CSM). Gate = `$27`, defeated by the SBI flip **if** the SoC honors it (Step 2 decides).
- **Path B — `calserviced` `OVERRIDE_BACKDOOR`**: drop a `*.calovride` file into
  `/mnt/vendor/calibration/overrides/`, which `calserviced` applies **skipping `$27` entirely**. Needs
  `vendor_cald`-context on-device filesystem write (dir mode 770) — not reachable from net/adb. Use this
  only if you already have a privileged on-device foothold. Covered as the fallback in Step 5B.

---

## 1. PREREQUISITES CHECKLIST

Work through this before touching the radio. Do not proceed until every box is checked or consciously
waived.

### 1.1 SBI flip verified (the `$27` lever)
- [ ] EEPROM dumped from the radio's M24C64 (8192 bytes).
- [ ] Byte at **`0x0440`** data position = `0xFF` (primary SBI). Stock is `C3 00 C3 00`; bypass is the
      data byte flipped to `FF` (marker-agnostic — only the data byte matters).
- [ ] Byte at **`0x0A80`** data position = `0xFF` (backup SBI). **Both** must be set for a clean bypass;
      GM now inits `0x0A80` to locked, so check it explicitly.

Verify a dump you already have on disk:

```bash
# 0x0440 primary SBI, 0x0A80 backup SBI — inspect the data bytes
xxd -s 0x0440 -l 4 /path/to/your_eeprom_dump.bin      # expect: 5aff 5aff  (or 69ff on HC variant) → data=FF
xxd -s 0x0A80 -l 4 /path/to/your_eeprom_dump.bin      # expect: 5aff 5aff / 69ff 69ff → data=FF
```

**Expected:** both show the data byte `FF`. Marker byte (`5A`/`69`/`C3`) varies by trim (LTZ vs HC) and
does not matter — the VIP reads only the data byte (provenance #4).

**Note on Y181 hardening (CORRECTED 2026-08-25):** there was no un-stubbing — the *ADB* validator
`fcn.000b67d0` is a full ~906-byte function in both Y177 and Y181 (and Y175); see
`VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2. The
DCM `$27` twin validator (`fcn.000b6bcc`, called by the SecurityAccess handler `fcn.000864de`) reads the
SBI **identically in both versions and was never part of the fix** — so an SBI flip that makes the VIP
emit the 0xFF `$27` seed is *not* re-blocked by Y181 on the VIP side (`eeprom_security_opus_B.md` §2, §5).

### 1.2 MDI2 connectivity (the transport)
- [ ] MDI2 (EL-52100-AM, FW 9.1.2375.152) connected to the vehicle OBD-II and powered (9–15 VDC).
- [ ] MDI2 Ethernet reachable from your laptop. Find its IP (link-local `169.254.x.x` or a static per your
      setup) and confirm the DoIP port is open.
- [ ] Python UDS stack installed.

```bash
pip3 install udsoncan doipclient python-can can-isotp

# Confirm the MDI2 DoIP port answers (adjust IP)
MDI2_IP=192.168.1.100
nc -z -v -w3 $MDI2_IP 13400 && echo "DoIP port open"
```

**DoIP gotcha (`mdi2_j2534_compat_opus.md` §3):** the tester source address is version-dependent —
**`0x0E80`** for a DoIP v3 entity, **`0x0EF5`** for v2. Learn the announced version from the Vehicle
Announcement/VID response and present the matching SA, or routing activation is refused. Standard
activation type is `0x00` (default), 7-byte request, no GM OEM auth suffix.

### 1.3 CalSets.db extracted (the source blob)
- [ ] You have a copy of the radio's `CalSets.db` (SQLite), located on the device at
      `/mnt/vendor/calibration/database/CalSets.db`.
- [ ] You can read the `AllCalSets` and `EnumSets` tables from it.

If you have not extracted it yet, see **Step 3**. If you already have a firmware extract in the tree, the
DB is under the vendor calibration path in your `scratchpad/diagx` / vendor extract.

### 1.4 Safety / recovery
- [ ] You have the **unmodified** `CalSets.db` and EEPROM dump saved off-device (your rollback).
- [ ] You accept that `3:1920×1080` and `4:2400×960` are non-default; `4` is the native panel. Start with
      a value the panel can actually display (prefer `4` native, or `3`) to make the change visible while
      minimizing the chance of an unreadable screen.

---

## 2. SEED TEST — confirm the all-0xFF `$27` bypass end-to-end

**Purpose:** This is the one *inferred* link (SoC honoring the bypass). Confirm it before editing anything.
Send `$27 01` at the programming level and check whether the returned seed is all-`0xFF` and whether a
dummy `$27 02` key is accepted.

Save as `seed_test.py`:

```python
#!/usr/bin/env python3
"""
Seed test: confirm the EEPROM SBI flip makes $27 return an all-0xFF seed and
accept any key, on the CSM radio, over the MDI2 DoIP link.

Source: MDI2_RAW_UDS_BYPASS_GUIDE.md, eeprom_security_opus_B.md §7.
"""
from doipclient import DoIPClient
from udsoncan.client import Client
from udsoncan import services
import udsoncan.configs

MDI2_IP  = "192.168.1.100"   # <-- your MDI2 Ethernet IP
CSM_ADDR = 0x745F            # <-- CSM (Infotainment radio) DoIP target address; adjust per VID response
TESTER_SA = 0x0E80          # <-- 0x0E80 for DoIP v3, 0x0EF5 for v2 (see 1.2)

# Levels: L1 diag = 27 01/02 ; L3 programming = 27 03/04 ; L5 EOL = 27 05/06.
# A cal WRITE uses the programming level. Test BOTH: L1 first (known-bypassed), then L3.
def run(level_seed, level_key, label):
    conn = DoIPClient(MDI2_IP, 13400, ecu_logical_address=CSM_ADDR,
                      client_logical_address=TESTER_SA)
    client = Client(conn, config=udsoncan.configs.default_client_config)
    try:
        client.open()
        print(f"\n=== {label}: extended session ($10 03) ===")
        client.change_session(0x03)                     # extended diagnostic
        print(f"=== {label}: request seed ($27 {level_seed:02X}) ===")
        resp = client.request_seed(level_seed)
        seed = resp.service_data.seed
        print(f"[+] seed ({len(seed)} B): {seed.hex().upper()}")
        if seed == b'\xFF' * len(seed):
            print(f"[SUCCESS] {label}: seed is ALL-0xFF -> SBI bypass ACTIVE on this level")
            print(f"[*] sending dummy key ($27 {level_key:02X} = 00000000)...")
            client.send_key(level_key, b'\x00\x00\x00\x00')
            print(f"[SUCCESS] {label}: key ACCEPTED (no 0x7F 27 35) -> level UNLOCKED")
            return True
        else:
            print(f"[INFO] {label}: seed is NOT all-0xFF -> real challenge; bypass not honored here")
            return False
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    diag_ok = run(0x01, 0x02, "L1 diagnostic")
    prog_ok = run(0x03, 0x04, "L3 programming")   # <-- the one that matters for a cal write
    print("\n==== VERDICT ====")
    print(f"L1 diagnostic bypass: {'YES' if diag_ok else 'NO'}")
    print(f"L3 programming bypass: {'YES' if prog_ok else 'NO'}  <-- must be YES to use Path A")
```

Run it:

```bash
python3 seed_test.py
```

**Expected outcomes:**
- **Best case:** both L1 and **L3 programming** return all-`0xFF` seeds and accept the dummy key →
  Path A (UDS write) is open. Proceed to Step 3.
- **Partial (the documented risk):** L1 diagnostic returns all-`0xFF` (matches the measured bypass) but
  **L3 programming returns a real 16-byte challenge** or rejects the key with `7F 27 35`. This is exactly
  the unproven link — the SBI covers ADB/diag but not necessarily programming. → Go to Step 2 troubleshooting.
- **No bypass at all:** even L1 returns a real challenge → the SBI flip is not in effect. Re-verify 1.1.

**Troubleshooting (Step 2):**
- *No DoIP connection* → wrong SA (try `0x0EF5`), wrong `CSM_ADDR`, or routing activation refused. Do a raw
  Vehicle Identification request first to learn the entity's announced DoIP version and logical address,
  then set `TESTER_SA` accordingly.
- *L1 bypassed but L3 not* → the SBI flip governs the VIP/PROTOKEY layer for ADB/diag but the SoC's
  `diagnosticsd` programming-level `$27` may validate independently. Two options:
  1. **Capture the real programming key once** (Step 6, Frida on `S84.dll!generateMAC` during a legit DPS
     unlock of your own radio) and use it instead of the dummy key — you then don't need the bypass at all.
  2. **Switch to Path B** (`calserviced` `OVERRIDE_BACKDOOR`, Step 5B) which skips `$27` entirely.
- *Seed all-0xFF but key rejected* → the handler may want a non-zero key echo; try `27 02` with the seed
  bytes themselves, or the level's documented default. If still rejected, the SoC is enforcing — use Path B.

---

## 3. CAL EXTRACTION — pull `SCREEN_RESOLUTION` out of `CalSets.db`

`CalSets.db` is a standard SQLite database. Copy it off-device (adb pull if you have shell, or from your
firmware extract) and inspect it.

```bash
# Locate the DB in a firmware extract, or pull from device
# On-device path: /mnt/vendor/calibration/database/CalSets.db
cp /path/to/extract/mnt/vendor/calibration/database/CalSets.db ./CalSets.db.orig
cp CalSets.db.orig CalSets.db          # work on a copy; keep .orig as rollback
```

Save as `read_cal.py`:

```python
#!/usr/bin/env python3
"""Read the SCREEN_RESOLUTION cal + its enum options from CalSets.db."""
import sqlite3, sys

db = sqlite3.connect("CalSets.db")
db.row_factory = sqlite3.Row

# List tables first (schema varies slightly by build)
print("Tables:", [r[0] for r in db.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")])

# The verified layout: AllCalSets holds CalID/CalType/CalValue; EnumSets holds the option map.
print("\n-- SCREEN_RESOLUTION row(s) --")
for r in db.execute("""
        SELECT * FROM AllCalSets
        WHERE CalDefFileName LIKE '%RVCVIDEOROBUSTNESS%'
           OR CalDefFileName LIKE '%SCREEN_RESOLUTION%'
           OR CalType = 4"""):
    print(dict(r))

print("\n-- enum options --")
for r in db.execute("SELECT * FROM EnumSets"):   # expect 5 rows: 0..4 -> resolutions
    print(dict(r))
db.close()
```

```bash
python3 read_cal.py
```

**Expected outcome:** the `AllCalSets` row shows `CalType 4`, `CalValue 2`, `CalDefFileName`
`GIS738_RVCVIDEOROBUSTNESSREQUIREMENT`, version 7; `EnumSets` shows exactly five rows
`0:800×480 · 1:1280×720 · 2:1280×768 · 3:1920×1080 · 4:2400×960` (provenance #39 — exact match).

If the exact table/column names differ, dump the schema (`.schema` in `sqlite3 CalSets.db`) and adjust the
column names — but the CalType/CalValue/enum data is confirmed present.

---

## 4. HAND-EDIT + RECOMPUTE (checksum + SHA-256)

Change `CalValue` from `2` (1280×768) to your target — recommend **`4` (2400×960, native panel)** or
**`3` (1920×1080)** — then recompute the two integrity fields the cal path checks: a **16-bit checksum**
(`CAL_CHECKSUM_FAILURE`) and a **SHA-256 digest** (`CAL_MESSAGE_DIGEST_FAILURE` / `generateSHA256`). There
is **no** RSA/X.509/SecOC signature to satisfy (provenance #34).

> **Which layout are you editing?** Two representations exist:
> - **(4A) The SQLite `CalSets.db` directly** — for Path B (`calovride`) or when you rebuild the on-device
>   DB. Edit the row, then recompute whatever integrity column the set carries.
> - **(4B) A transferable cal blob** for Path A (`$34/$36/$37`). The blob is
>   `[header][checksum(16-bit)][cal data][SHA-256]`. Edit the enum byte in the data region, recompute both.
>
> Both use the same two integrity primitives below. The exact checksum span (which bytes are summed) and
> the digest span must match what the loader verifies; start with "checksum over the cal-set record,
> SHA-256 over the full blob excluding the digest field itself" and adjust if the loader rejects (Step 5
> troubleshooting).

### 4A. Edit the SQLite row

```python
#!/usr/bin/env python3
"""Set SCREEN_RESOLUTION CalValue 2 -> 4 (native panel) in CalSets.db."""
import sqlite3
NEW_VALUE = 4                                  # 3=1920x1080, 4=2400x960(native)
db = sqlite3.connect("CalSets.db")
cur = db.execute("""UPDATE AllCalSets SET CalValue=?
                    WHERE CalType=4
                      AND CalDefFileName LIKE '%RVCVIDEOROBUSTNESS%'""", (NEW_VALUE,))
print(f"rows updated: {cur.rowcount}")
db.commit(); db.close()
```

### 4B. Recompute the integrity fields on a transferable blob

```python
#!/usr/bin/env python3
"""
Recompute the 16-bit checksum + SHA-256 for an edited cal blob.

Cal blob layout (confirmed shape; adjust offsets to your build):
  [ 0x00 : header .......................... ]
  [ CKSUM_OFF : 2-byte 16-bit checksum ...... ]
  [ DATA_OFF  : cal data (the enum byte) .... ]
  [ SHA_OFF   : 32-byte SHA-256 ............. ]  (trailing)

No RSA/CMAC/SecOC — these two fields are the ONLY integrity gates (provenance #34, T1 §102-104).
"""
import hashlib, struct, sys

BLOB      = bytearray(open("screen_res.cal", "rb").read())
CKSUM_OFF = 0x10        # <-- set to your blob's checksum field offset
DATA_OFF  = 0x20        # <-- start of the checksummed cal-data region
SHA_OFF   = len(BLOB) - 32   # SHA-256 is the trailing 32 bytes
ENUM_OFF  = 0x24        # <-- byte holding the SCREEN_RESOLUTION enum

# 1. Write the new enum value
BLOB[ENUM_OFF] = 4      # 2 -> 4

# 2. 16-bit checksum over the cal-data region (sum of bytes mod 65536; try one's/two's
#    complement variants if the loader rejects — see troubleshooting).
data = BLOB[DATA_OFF:SHA_OFF]
cksum = sum(data) & 0xFFFF
struct.pack_into("<H", BLOB, CKSUM_OFF, cksum)   # try ">H" (big-endian) if rejected

# 3. SHA-256 over everything except the digest field itself
digest = hashlib.sha256(BLOB[:SHA_OFF]).digest()
BLOB[SHA_OFF:SHA_OFF+32] = digest

open("screen_res_patched.cal", "wb").write(BLOB)
print(f"checksum=0x{cksum:04X}  sha256={digest.hex()}")
print("wrote screen_res_patched.cal")
```

**Expected outcome:** a patched blob (or DB) whose enum byte reads `4`, with a self-consistent 16-bit
checksum and SHA-256. Keep the original as rollback.

**Endianness / span caveats:** the VIP data is big-endian; the checksum field endianness and the exact
checksummed span are build-specific. If Step 5 returns `CAL_CHECKSUM_FAILURE` or
`CAL_MESSAGE_DIGEST_FAILURE`, iterate on: little vs big-endian checksum word; checksum span
(include/exclude header); and whether SHA covers the checksum field. There are only a few combinations —
brute-force them against the loader's accept/reject.

---

## 5A. UDS TRANSFER — write the blob over the wire (Path A)

Only do this if Step 2 confirmed the **L3 programming** level is unlocked (bypass honored) **or** you have
captured the real programming key (Step 6). Save as `write_cal.py`:

```python
#!/usr/bin/env python3
"""
Write the patched SCREEN_RESOLUTION cal to the CSM via $10 02 -> $27 -> $34/$36/$37 -> $11.
Path A: MDI2 DoIP to the radio (or point at diagnosticsd eth0:49156 directly).
"""
from doipclient import DoIPClient
from udsoncan.client import Client
from udsoncan import services, MemoryLocation, DataFormatIdentifier
import udsoncan.configs

MDI2_IP  = "192.168.1.100"
CSM_ADDR = 0x745F
TESTER_SA = 0x0E80
PROG_KEY = b'\x00\x00\x00\x00'     # dummy for bypass; or the captured real key (Step 6)
BLOB = open("screen_res_patched.cal", "rb").read()

conn = DoIPClient(MDI2_IP, 13400, ecu_logical_address=CSM_ADDR,
                  client_logical_address=TESTER_SA)
cfg = dict(udsoncan.configs.default_client_config)
cfg['data_identifiers'] = {}
client = Client(conn, config=cfg)
try:
    client.open()
    print("[*] $10 02 programming session")
    client.change_session(0x02)                        # PROGRAMMING session (flash level)
    print("[*] $27 03 request seed (programming)")
    seed = client.request_seed(0x03).service_data.seed
    print(f"    seed={seed.hex().upper()}")
    client.send_key(0x04, PROG_KEY)                    # dummy for bypass, real key otherwise
    print("[+] $27 unlocked")

    print(f"[*] $34 RequestDownload ({len(BLOB)} bytes)")
    client.request_download(MemoryLocation(address=0x00000000, memorysize=len(BLOB),
                            address_format=32, memorysize_format=32),
                            dfi=DataFormatIdentifier(compression=0, encryption=0))
    print("[*] $36 TransferData")
    CHUNK = 0x400
    seq = 1
    for i in range(0, len(BLOB), CHUNK):
        client.transfer_data(seq & 0xFF, BLOB[i:i+CHUNK])
        seq += 1
    print("[*] $37 RequestTransferExit")
    client.request_transfer_exit()
    print("[+] transfer complete; $11 01 ECUReset")
    client.ecu_reset(services.ECUReset.ResetType.hardReset)
    print("[SUCCESS] cal written; module resetting")
finally:
    client.close()
```

```bash
python3 write_cal.py
```

**Expected outcome:** each service returns positive (`0x50`/`0x67`/`0x74`/`0x76`/`0x77`/`0x51`), no
`7F .. 35` (security) or `7F .. 24/72/13` (sequence/programming/length). `$37` triggering the SoC-side
checksum+SHA verification is where a bad recompute surfaces as a negative response.

**Alternative endpoint:** instead of the MDI2 DoIP to the CSM, you can point the same `$34/$36/$37`
sequence at `diagnosticsd` directly on `eth0:49156` (GM-custom UDS-over-TCP) if you are on the vehicle's
service Ethernet — the write lands in `/mnt/vendor/calibration/overrides/`, then `calserviced` inotify →
`processZippedModFile` → `CalSets.db` (T1 §97-101).

**Troubleshooting (Step 5A):**
- `7F 34 70/72` on `$34` → wrong session (must be `$10 02` programming) or `$27` not actually unlocked.
- `7F 37 24` at exit or a checksum/digest DTC → recompute is wrong; iterate the checksum endianness/span
  and SHA span (Step 4 caveats).
- `7F 27 35` on the key → the programming level is enforcing; capture the real key (Step 6) or use Path B.

---

## 5B. FALLBACK — `calserviced` `OVERRIDE_BACKDOOR` (Path B, no `$27`)

If the programming `$27` won't bypass and you have a **privileged on-device foothold** (root or a
`vendor_cald`-context write), drop a `*.calovride` file — `calserviced` applies it **skipping `$27`
entirely** (T1 §113-117, provenance #37-38). Caveat: this backdoor carries a `!!!DISABLE BEFORE RELEASE!!!`
string; whether it is compiled into your release is undetermined from strings alone — checkable in
`scratchpad/diagx/bin__calserviced` `main()`.

The `.calovride` format is XML per `reference/.../schema/calovride_1.7.xsd` (`CalOvrideFile` →
`OverrideValue` → `CalID` + `Version` + one typed value; for an enum use `<Enumeration><Value>`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CalOvrideFile xmlns="http://caltools.gm.com/calovride"
               Description="SCREEN_RESOLUTION 2->4 native panel">
  <OverrideValue>
    <CalID>GIS738_RVCVIDEOROBUSTNESSREQUIREMENT</CalID>   <!-- match the CalDef ID -->
    <Version>7</Version>
    <Enumeration><Value>4</Value></Enumeration>            <!-- 4 = 2400x960 native -->
  </OverrideValue>
</CalOvrideFile>
```

```bash
# On-device, with vendor_cald / root context (dir is mode 770 vendor_cald:system):
cp screen_res.calovride /mnt/vendor/calibration/overrides/
# calserviced inotify watch -> apply_overrides -> CalSets.db  (no $27, no reboot needed for apply,
# but reboot to force the display stack to re-read; see Step 6)
```

**Expected outcome:** `calserviced` log shows it picked up the file (`processZippedModFile` /
`apply_overrides`) and merged the value into `CalSets.db`. No security handshake involved.

---

## 6. BOOT AND VERIFY

1. **Reboot the radio** (the `$11 01` ECUReset in Step 5A already does this; for Path B, power-cycle or
   `reboot` so the display stack re-reads the cal).
2. **Confirm the stored value changed** — re-pull `CalSets.db` and re-run `read_cal.py`:

```bash
python3 read_cal.py        # AllCalSets CalType 4 row should now show CalValue = 4 (was 2)
```

3. **Observe the display** — the screen should render at the new resolution
   (2400×960 native for value 4, or 1920×1080 for value 3) instead of 1280×768. Look for a visibly
   different pixel density / aspect handling on boot animation and the home screen.

**If you captured the real programming key instead of relying on the bypass (Step 2 fallback):**
one-time, run a legitimate DPS/SPS unlock of your *own* radio and Frida-hook `S84.dll!generateMAC` to
capture the 16-byte per-ECUID AES-CMAC key as it passes through (`dps_seed_fable_B.md` Q2;
`security_dlls/scripts/`, `HOOKING_AND_TESTING_GUIDE.md`). GM's model is a per-ECUID *static* key, so once
captured it is reusable offline forever (Python AES-CMAC, no GM server). Your radio's ECUID
`004B41DC…0114AC` is **not** yet in `ecuid_key_map.json` — it's a placeholder — so this capture has not
been done and is the clean, bypass-free way to satisfy `$27 03/04`.

---

## SUCCESS CRITERIA

- ✅ **Seed test (Step 2):** `$27 03` at the programming level returns an all-`0xFF` seed and accepts the
  dummy key — OR you have the captured real key. Without one of these, Path A cannot proceed.
- ✅ **Recompute (Step 4):** the edited blob/DB carries a self-consistent 16-bit checksum + SHA-256; `$37`
  RequestTransferExit returns positive with no `CAL_CHECKSUM_FAILURE` / `CAL_MESSAGE_DIGEST_FAILURE` DTC.
- ✅ **Persisted value (Step 6):** `CalSets.db` `AllCalSets` `CalType 4` row reads `CalValue = 4` (or 3)
  after reboot.
- ✅ **THE GOAL:** the radio display renders at the chosen resolution (2400×960 or 1920×1080) instead of
  the stock 1280×768.

---

## CONSOLIDATED TROUBLESHOOTING MATRIX

| Symptom | Likely cause | Fix |
|---|---|---|
| DoIP won't connect | wrong tester SA / DoIP version / target addr | send Vehicle Identification first; use `0x0E80` (v3) or `0x0EF5` (v2); confirm `CSM_ADDR` |
| L1 seed all-FF but L3 real challenge | SBI covers ADB/diag, not programming (the unproven link) | capture real programming key (Step 6) **or** switch to Path B `calovride` |
| `7F 27 35` (invalid key) | programming level enforcing; bypass not honored | Step 6 real key, or Path B |
| `7F 34 70/72` on RequestDownload | not in `$10 02` programming session, or `$27` not unlocked | enter programming session; re-run `$27` |
| `CAL_CHECKSUM_FAILURE` at `$37` | wrong checksum endianness/span | try big vs little-endian 16-bit word; include/exclude header in span |
| `CAL_MESSAGE_DIGEST_FAILURE` | SHA span wrong | hash full blob excluding the 32-byte digest field; try including/excluding checksum field |
| Value persists but display unchanged | display stack didn't re-read, or panel can't show that mode | full power-cycle; pick native `4` (2400×960) which the panel supports; avoid modes the panel can't render |
| `calovride` ignored (Path B) | backdoor compiled out, or wrong FS context | verify `OVERRIDE_BACKDOOR` active in `bin__calserviced main()`; write must be `vendor_cald`/mode-770 dir |

---

## SOURCE FINDINGS INDEX (this session's scratchpad + repo)

- `eeprom_security_opus_B.md` — VIP `$27`/SBI disassembly: SBI flip → all-0xFF seed on both ADB and DCM
  `$27` validators; DCM twin never part of Y181 fix; SoC-honoring is the one inferred link.
- `dps_seed_fable_B.md` — full DPS/UDS workflow, `$27` seed/key (AES-128-CMAC, per-ECUID static key not in
  DLL), CalSets.db surface is unsigned (checksum+SHA-256), EEPROM lever scope.
- `mdi2_j2534_compat_opus.md` — MDI2 is an unrestricted J2534/DoIP pass-thru; raw `$27` goes through;
  tester-SA/DoIP-version caveat.
- `provenance_audit.md` — ground-truth verification: SCREEN_RESOLUTION CalType/value/enum exact (#39),
  cal unsigned (#34), `$27` single gate (#35), `calovride` backdoor verbatim (#37-38), SBI bytes (#2-4).
- `research/MDI2_RAW_UDS_BYPASS_GUIDE.md` — runnable DoIP seed-test + `$34/$36/$37` templates.
- `research/T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md` — self-write path
  diagnosticsd→overrides→calserviced→CalSets.db; integrity fields; backdoor gating.
- `reference/.../schema/calovride_1.7.xsd` — `.calovride` XML format for Path B.
- `eeprom_map_opus_A.md` — VIP cal NvM/Ea-Fee indirection (context for why the *VIP* cal path is harder
  than the SoC `CalSets.db` path chosen here).
```
