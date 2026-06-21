# gminfo-3.7-3.8-ADB-EEPROM
EEPROM Modification to Enable ADB Access, Disables Authorized Secure ADB Client requirment.

> **⚠️ Redaction notice — the `.bin` dumps here are sanitized.** Vehicle/unit
> identifiers (VIN, unit serial, repair-shop SN) have been overwritten **in
> place with the valid VIN character `X`**, preserving exact byte length so no
> field shifts. Only the device-ID block is touched:
>
> | Offset | Field | Length |
> |--------|-------|--------|
> | `0x0501` | Unit serial | 9 |
> | `0x05C1` | VIN (`XXXXXXXXXXXXXXXXX`) | 17 |
> | `0x0681` | Repair-shop SN | 10 |
> | `0x14A1` | VIN-suffix mirror (`XXXXXXXX` = last 8 of the VIN) | 8 |
>
> These fields lie **outside the CRC-checked regions** — the stored CRC words at
> `0x16E0 / 0x19E0 / 0x1A80 / 0x1B40 / 0x1B60 / 0x1B80` are byte-identical to the
> originals, so the dumps stay internally consistent and offset-faithful for
> structural reference. In text/docs the same placeholders are used, so the VIN
> suffix `XXXXXXXX` is recognizably the tail of the full VIN `XXXXXXXXXXXXXXXXX`.
> Re-image your own unit's real dump before any write-back.

Using a dump tool/software, extract the firmware from the indentified IC. Using any Hex editor, flip the following. Then write back to IC, tripple check your work.

For example using minipro on macOS with an XGecu Programmer
<pre>
minipro -p "M24C64" -r dump.bin
minipro -p "M24C64" -w modified.bin
minipro -p "M24C64" -r verify.bin
</pre>

===============================================

  - Byte 0x440: 0x5A (framing byte)
  - Byte 0x441: 0x00 ← Security flag = ENABLED
  - Byte 0x442: 0x5A (framing byte)

  - Byte 0xa80: 0x5A (framing byte)
  - Byte 0xa81: 0x00 ← Security flag = ENABLED
  - Byte 0xa82: 0x5A (framing byte)

===============================================

  - Byte 0x440: 0x5A (framing byte)
  - Byte 0x441: 0xFF ← Security flag = DISABLED
  - Byte 0x442: 0x5A (framing byte)

  - Byte 0xa80: 0x5A (framing byte)
  - Byte 0xa81: 0xFF ← Security flag = DISABLED
  - Byte 0xa82: 0x5A (framing byte)

  - Byte 0x1A01: 0xFF ← second SBI mirror = DISABLED  (stock 0x00)
  - Byte 0x0B41: 0x01 ← debug-mode flag = ENABLED     (stock 0x00)

> NOTE: the Y181 stock→modified diff toggles **all four** bytes — 0x441→0xFF,
> 0xa81→0xFF, 0x1A01→0xFF, 0x0B41→0x01 (verified by byte-diff of the shipped
> Y181_stock.bin vs Y181_modified.bin). The 0x5A shown above is one firmware's
> framing marker; the shipped Y181 bins actually use F0 @0x440 and C3 @0xa80 —
> locate each security byte by **offset**, not by the framing value.

IC in question is an ST M24C64 TSSOP8, using a Tool like XGecu Programmer. The framing byte appears to change depending on Firmware Version (Android OTA). Each update will reset back to 0x00 and lock ADB access.

Last Known modifiable Build was Y181 for RPO: IOK identified radios.
I have had issues with HexEdit on macOS not saving changes to the file. So double check any modifications to the file have been saved properly before writing back to IC.
