# M24C64 EEPROM Reference

Scope: the ST M24C64 I2C EEPROM on the VIP MCU bus — physical package/markings, the on-chip
record-framing protocol, and the full 8KB structured memory map (regions outside the SBI
security-flag pair). SBI flag offsets, the ADB/MEC bypass mechanism, and their consequences are
intentionally **not** reproduced here — see §5.

Related: [`identity_bom.md`](identity_bom.md) (BOM entry, board architecture),
[`vip_mcu.md`](vip_mcu.md) (RH850 VIP MCU that owns the I2C bus to this chip),
[`../../platform/eeprom_i2c_security.md`](../../platform/eeprom_i2c_security.md) (SBI flag pair,
CRC posture, I2C DAC permissions), [`../../platform/security.md`](../../platform/security.md)
(ProtoKey/ADB authentication, MEC consumption), [`../teardown.md`](../teardown.md) (index; source
of the map below).

Confidence tags: **[C]** confirmed · **[FW]** firmware evidence · **[?]** open question.

## 1. Physical Device

| Field | Value |
|-------|-------|
| Part | ST M24C64 |
| Markings | `464RQ`, `K228` |
| Package | TSSOP-8 |
| Capacity | 8 KB (64 Kbit), byte-addressable |
| Bus | I2C, slave address `0x50` |
| Bus master | RH850 VIP MCU (R7F7015873AFP) — see [`vip_mcu.md`](vip_mcu.md) |

**[C]** Legible in close-up photography; cross-referenced against the board I2C enumeration in
`../../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §8 (I2C table) and the BOM entry in
[`identity_bom.md`](identity_bom.md) §4.1 ("VIP EEPROM").

## 2. Framing Protocol

Each stored record follows a fixed envelope:

```
[framing byte] [data] [framing byte] [FF padding]
```

Four framing byte values are observed across the map:

| Framing byte | Observed role |
|--------------|---------------|
| `0x69` | Configuration/state records (counters, ECUID, SBAT, calibration IDs) |
| `0xF0` | String/data records (part numbers, dates, VIN, HW part number, DTC IDs, counters) |
| `0xC3` | Calibration/numeric records (flag-adjacent values, MEC NVM, SecurityAccess bitmask) |
| `0x5A` | Short-form/placeholder records (test data, short VIN, non-zero single-byte flags) |

**[?]** No single framing byte maps to exactly one semantic category — the same byte recurs
across unrelated regions (e.g. `0x69` tags both the boot counter at `0x0040` and the
certificate/signed blob at `0x1F60`). Framing byte alone is not sufficient to classify an
unknown region; it must be combined with offset and observed data shape.

## 3. Structured Regions (Full 8KB Map, Non-SBI)

Offsets, framing bytes, and observed data below are from the stock dump analyzed in
`../teardown.md` ("Deep EEPROM Analysis — Full 8KB Map"). Values shown as `X`-redacted were
redacted for this repository; see source dump for provenance.

| Offset | Framing | Data | Region |
|--------|---------|------|--------|
| `0x0040` | `69` | `0x27E6` (10,214) | Boot/write counter **[C]** |
| `0x03A0` | `69` | `004B41DC...14AC` (16 bytes) | ECUID, matches UDS `$27` **[C]** |
| `0x0400` | `69` | `0x19`, checksum `0xE4A4` | Security level bitmask (duplicated at `0x0420`) **[FW]** |
| `0x0500` | `F0` | `<SN_REDACTED>` | GM service part number fragment **[C]** |
| `0x0580` | `F0` | `"20.02.2025"` | Last programming date **[C]** |
| `0x05A0` | `F0` | `"7310500000000X"` | Calibration file ID **[C]** |
| `0x05C0` | `F0` | `<VIN_REDACTED>` | VIN **[C]** |
| `0x0680` | `5A` | `"9999988888"` | Placeholder/test data **[?]** |
| `0x06E0` | `F0` | `0x600202B1` | HW part number, matches VIP log **[C]** |
| `0x0B60` | `C3` | `0xF70400` | Unknown flag; not altered by the SBI transition documented in `../../platform/eeprom_i2c_security.md` **[?]** |
| `0x0C01` | `5A` | `0x01` | Non-zero single-byte flag; function undetermined, value untouched across the observed revisions **[?]** |
| `0x0E00` | — | 142-byte block | VIP calibration NVM (timeout values, thresholds) **[FW]** |
| `0x0EC0` | `69` | `0x0186...` (SBAT data) | SBAT state (`keyNBID`, `appNBID`) **[FW]** |
| `0x0EE0` | `F0` | `0x7C4A`, `0x8F42` | DTC identifiers **[FW]** |
| `0x0F00`–`0x12D9` | mixed | 21-point curves | Brightness/audio calibration lookup tables **[FW]** |
| `0x14A0` | `5A` | `<SHORT_VIN+PLANT_REDACTED>` | Short VIN + plant code **[C]** |
| `0x15E0` | `69` | boot-counter area | `PLC_BootCounter` region **[FW]** |
| `0x1A80` | `C3` | `0x0167` (359?) | MEC NVM value — stored value differs from the transmitted value `0xFF`; MEC semantics owned by `../../platform/security.md` §"MEC (Manufacturer Enable Counter)" **[FW]** |
| `0x1AE0` | `C3` | `0x06` | SecurityAccess unlock bitmask (which levels have been unlocked) **[FW]** |
| `0x1B60` | `F0` | `0x92` (146), `0x035A` (858) | Two independent reflash/programming counters **[C]** |
| `0x1F60` | `69` | 97 bytes, high-entropy | Certificate/signed blob (contains `"15-47WYBN"`) **[FW]** |

**[?]** `0x1A80` is also characterized in `../../platform/eeprom_i2c_security.md` (merged I2C/EEPROM
security table) as a CRC-location offset in a separate pass over the same dump. The two
characterizations have not been reconciled; treat both as open pending a joint re-read of the
dump against both offset lists.

## 4. High-Reference / Structure-Base Regions

A VIP-firmware cross-reference pass flagged the offsets below as having many code references;
most of that framing has since been retracted. Current status:

| Offset | Status | Observed Value | Note |
|--------|--------|-----------------|------|
| `0x0A00` | Structure-base address, not an individual flag **[?]** | — | See correction below |
| `0x0B00` | Structure-base address, not an individual flag **[?]** | — | See correction below |
| `0x04A0` | No stored data | `0xFF` (unwritten) **[C]** | Earlier "firmware-ref" framing superseded; see correction |
| `0x04C0` | No stored data | `0xFF` (unwritten) **[C]** | Earlier "firmware-ref" framing superseded; see correction |
| `0x0A20` | Adjacent to `0x0A00` structure | — | No independent data |
| `0x0A40` | No stored data | `0xFF` (unwritten) **[C]** | Confirmed by direct hex read |
| `0x0A60` | Adjacent to `0x0A00` structure | — | No independent data |
| `0x0AC0` | Adjacent to `0x0A00` structure | — | No independent data |
| `0x0B20` | Adjacent to `0x0B00` structure | — | No independent data |
| `0x0BE0` | No stored data | `0xFF` (unwritten) **[C]** | Confirmed by direct hex read |

**Correction history (preserved for provenance):**

> Direct hex comparison of `gm_csm_stock.bin` and `ADB_enabled.bin` shows `0x04A0`, `0x04C0`,
> `0x0A40`, `0x0BE0` are `0xFF` (unwritten) in **both** dumps; they hold no stored data. The
> earlier "N firmware refs" framing for these four offsets, and a note associating
> `0x04C0` with a CalGroup `0x44` handler, are **superseded** by the direct hex read.
>
> The remaining "871 refs" (`0x0A00`) and "311 refs" (`0x0B00`) figures are **retracted**
> (`../../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0). They came from a radare2
> string-proximity pass that is not reproducible from this repo's artifacts and was
> inconsistent between two passes (871 vs 854 for `0x0A00`; 311 vs 305 for `0x0B00`).
> Do not treat "871" / "311" as hard counts.
>
> What still holds, via separate evidence: `0x0A00` and `0x0B00` are real structure-base
> addresses, not individual flags; see the audit doc's §2.1.

## 5. Security-Adjacent Fields — Pointer Only

Several regions above are read by the platform's authentication/security logic (security level
bitmask `0x0400`/`0x0420`, SecurityAccess unlock bitmask `0x1AE0`, MEC NVM value `0x1A80`,
reflash counters `0x1B60`). The SBI flag pair itself (`0x0440`/`0x0441` primary,
`0x0A80`/`0x0A81` backup) and the mechanism by which its state affects ADB authentication are
**out of scope for this document** — see
[`../../platform/eeprom_i2c_security.md`](../../platform/eeprom_i2c_security.md) and
[`../../platform/security.md`](../../platform/security.md) (ProtoKey / ADB Authentication, MEC)
for that analysis, and `../../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` for the primary research
trail.

## Sources

- `../teardown.md` — "Deep EEPROM Analysis (Full 8KB Map)" section (framing protocol,
  structured-region table, undocumented-flag cross-reference and its correction history).
- `../../platform/eeprom_i2c_security.md` — SBI flag pair, I2C bus permissions, CRC posture
  (cross-referenced, not duplicated).
- `../../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` — primary EEPROM layout research; authoritative
  for anything retracted or superseded above.
