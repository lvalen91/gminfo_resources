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
> | `0x14A1` | VIN-tail residual (`XXXXXXXX` = last 8 of a VIN) | 8 |
>
> **Refined 2026-10-15:** `0x14A1` is not a live "mirror" of the current VIN — it holds whichever
> VIN was active the last time its NvM block was written, and can lag behind `0x05C1` after a
> re-VIN/reprogram event (confirmed on a separate unit where this field retained a *previous*
> vehicle's VIN tail after the module was reprogrammed onto a new one). In the dumps redacted here
> it happens to equal the current VIN's tail, which is why the placeholder substitution above still
> works, but don't assume it always matches `0x05C1` on an arbitrary dump.
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

**Corrected 2026-11-11:** the owner-corroborated minimal EEPROM recipe changes only
**data bytes `0x0441` and `0x0A81` to `0xFF`**. Pre-Y181 stock reportedly already has
`0x0A81=FF`; Y181 requires both. Leave framing bytes unchanged. The successful minimal
edit needed no CRC recomputation; this does not establish that every EEPROM region lacks
integrity checks. `0x1A01` is not an established second SBI mirror, and `0x0B41` changes
were not required and produced no observed ADB/SELinux effect.

Separate effects must remain separate:

- **ADB:** [Certificate and privilege behavior](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#237-mec-adb-certificate-authentication-root-and-registration) is maintained in the consolidated source.
- **UDS SecurityAccess:** the tested radio returns 31 all-FF seed bytes, and the client
  sends exactly 12 zero bytes and receives `67 02`. Arbitrary-key acceptance is unproven.
- **Programming:** on 2026-11-10 the client wrote 14 stock GM-signed radio calibration
  containers, finalized/reset, and verified High Country→LTZ readback with ADB retained.
  Edited containers have failed; their format is signed, while the active UDS signature
  enforcement path remains unresolved. This does not establish arbitrary custom-calibration access.
- **ProtoKey and Signature Bypass Tickets:** these are separate mechanisms from the
  UDS seed and the EEPROM SBI; do not use the shared terminology as proof of a shared gate.

See [the EEPROM audit](../research/EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md),
[the client bench report](../mdi2_client/README.md), and
[the central evidence guide](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
The candidate cells `0x04A0`, `0x04C0`, `0x0A40`, and `0x0BE0` are unwritten in the compared
dumps; their existence is not a demonstrated calibration-unlock lever. Actual Android
`SCREEN_RESOLUTION` is a `CalSets.db` value, not a proven EEPROM display-width field.

IC in question is an ST M24C64 TSSOP8, using a Tool like XGecu Programmer. The framing byte appears to change depending on Firmware Version (Android OTA). Some owner-reported updates reset the bypass, but this is not universal: the November 10 stock calibration write retained ADB. The reset trigger remains unidentified.

Last Known modifiable Build was Y181 for RPO: IOK identified radios.
I have had issues with HexEdit on macOS not saving changes to the file. So double check any modifications to the file have been saved properly before writing back to IC.
