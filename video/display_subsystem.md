# GM Infotainment Display Subsystem Specifications

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton)
**Android Version:** 12 (API 32)
**Research Date:** December 7, 2025

---

## Y175 panel ownership and initialization — verified 2026-11-17, extended 2026-11-17

Static analysis of the mounted Y175 cleanroom and OTA GHS image establishes two
separate paths: Android composes/selects video, while GHS controls the display
I2C link and brightness in the virtualized configuration. A running i915
framebuffer does not establish a working serializer link, panel power, or light.

**2026-11-17 update:** cross-checked against (a) a second independent static pass
over the GHS `display_i2c`/`vip_server`/`lifecycle`/`vmm1` servers and (b) a live
probe of the native-Linux init running on the bench radio (`<RADIO_T1_IP>`, read-only
except for one GPIO toggle, see "Live bench confirmation" below). All three lines of
evidence agree. Findings below are tagged VERIFIED (code/binary or live measurement),
INFERRED, or UNKNOWN; items marked VERIFIED supersede earlier "remains untraced"
language in this section.

### Evidence and address conventions

Sources: cleanroom `vendor/bin/remote_display`, `vendor/lib64/hw/lvds_input.default.so`,
`vendor/calibrations/CalSets.db`, stock recovery `recovery_panel`, stock
`ti949_serdes.ko`, and Y175 OTA part `85098662`. The GHS display server was
reconstructed from `.display_i2c.text/.rodata/.data`, using its own address-space
bases `0x200000/0x400000/0x600000`; addresses below are **server-local**, not raw
OTA offsets or VIP RAM addresses. Source hashes:

| Source | SHA-256 |
|---|---|
| GHS OTA 85098662 | `317ae85ccf759476755411e66593dde9f879a43732cd342b4e101e4026535ed3` |
| remote_display | `51e50927ed5bd216bdd43e012ceb4bb0376d09b7a1ce077f1c8726547f323e9a` |
| lvds_input.default.so | `003f377c840a4ad96fae97b8d96713eb15c0576c839829ea3889eb0c56d7e014` |
| Cleanroom base CalSets.db | `15d22e32b6a7efd55ead4441c54fc42bb32c8855ae1abdde78cf121235822737` |

### Video, resolution and early configuration

The supported physical topology is Intel video → HDMI → DS90UH949-Q1 → FPD-Link III
→ DS90UB948 → OpenLDI/LVDS panel. **Corrected 2026-11-17:** the part is DS90UH949-Q1,
not DS90UB949 — matches `hardware/teardown.md`'s teardown identification, and matches
the live register dump below (register `0xF0`-`0xF5` on the live chip reads ASCII
`_UH949`). TI identifies the 949 as an HDMI-input device, not an eDP/LVDS-input
serializer ([TI datasheet](https://www.ti.com/lit/ds/symlink/ds90ub949-q1.pdf)).
The historical Android compositor observations below remain separate from native
Linux connector naming. SELinux paths alone do not prove which connector is active.

`remote_display` starts at Android boot via `init.remote_display.rc`. It queries
GMCalibrationManager for `SCREEN_RESOLUTION` and compares the enum against
`/sys/module/drm/parameters/edid_firmware`: `1080p→3`, `0768p→2`, `0960p→4`.
When different, the inspected branches for 2/3/4 read and update a 512-byte
`EARLY_CALS` record in `/dev/block/by-name/ghs_storage`, including
`SCREEN_RESOLUTION` and `CAMERA_RESOLUTION`. This establishes a real bridge from
calibration to early display configuration; it is not just an icon/layout setting.
The complete GHS consumer and exact reboot/application timing remain untraced.

The verified eMMC user dump was checked read-only for this device-specific record.
GPT places `ghs_storage` at LBAs 264192–296959 (512-byte sectors); its first
512 bytes were all zero at dump time. Therefore no populated `EARLY_CALS` record
was recovered from that location. This does not negate the writer code or prove
that GHS has no other configuration/default path. No dump or live partition was modified.

Stock kernel EDID `edid/harman0960p.bin` contains 2400×960 timing with a
153.98 MHz pixel clock. Detailed timings are embedded firmware data; no matching
raw porch/sync/serializer-register calibration overrides were established by this pass.

### Link initialization and panel commands

GHS display context at `0x600000` contains 7-bit addresses: serializer `0x0c`,
deserializer `0x2c`, faceplate/panel controller `0x12`. The second context has
zero device addresses. Main `0x201189` initializes the bus/resources and starts
link setup. Serializer reinitialization `0x2009e2` toggles its configured GPIO
low then high, with delay calls, applies register tables, applies temperature
errata, initializes the deserializer, and configures interrupts.

**Resolved 2026-11-17 (VERIFIED, two independent disassemblies — GHS `display_i2c`
and the guest's `ti949_serdes.ko` kernel module — agree exactly):**
- The reset GPIO is **467** (board label `"TI949_INTB"` is actually the *interrupt*
  line's platform-data name; 467 is the separate PDB/reset line, read from the
  guest kernel's `ti949_serdes_pdata` at `vmlinux` file offset `0x2231a60`). The
  interrupt line is GPIO **449**.
- Delay units are microseconds (GHS `0x203f07` divides by 1,000,000); the kernel
  module uses `msleep(10)`/`msleep(100)` for the same two delays.
- GHS's `IOD_GPIO_33`/`IOD_GPIO_15` objects are the SoC-side names for these same
  two signals routed to the serializer (33↔467 reset path, 15↔449 interrupt path);
  the 467/449 numbering is the guest-visible GPIO-chip-relative numbers, GHS's
  33/15 are server-local object indices, not raw pad numbers — the two numbering
  schemes are not directly comparable past this correspondence.

The primary serialized register/value pairs in GHS data are:

- Serializer: `07:96 08:96 71:50 78:50 03:da 0d:0f 0e:77 72:24 79:24 c2:aa 16:02`.
- Deserializer: `1d:23 1e:33 21:11 26:20 27:20`.

**Confirmed identical** against the stock kernel module's own table at
`ti949_init_settings` (`.rodata+0x40`, 9 register pairs) and `ti948_init`'s five
writes — same registers, same values, same order. These are **not** a complete
standalone bring-up recipe by themselves; the full stock sequence (kernel-module
disassembly, VERIFIED) is: PDB low→high (10 ms low, 100 ms high) → read serializer
`0x5A`, write `0x5B` = 3 or 4 depending on `0x5A` bits [5:4] → the 9-pair serializer
table above → 10 ms → the 5-pair deserializer table above → read-modify-write
serializer `0x5B` clearing bit 5 ("errata #3") → a delayed `apply_errata1` work item
(500 jiffies later) that applies temperature-dependent values to serializer
indirect registers `0x40`/`0x41`/`0x42`. `0x20081f` (GHS) / the kernel module's
`0x5A & 0x30` check perform the equivalent link-mode readback; `0xC7` is polled
(≤5 reads) as the interrupt-status/ready check during re-enable. No chip-ID or
link-lock register is checked against an expected value anywhere in the stock path.

**Register names resolved 2026-11-17 against the public TI DS90UB949-Q1 datasheet
(SNLS452B, Nov 2014/rev Aug 2019) — this chip is register-compatible with the
DS90UH949-Q1 part actually on the board (same family, automotive-grade variant).
This replaces the earlier "unnamed"/inferred register table with the vendor's own
names, and the default value table matches: live register `0x03` read `0xD2`
before any write, and the datasheet's own default for `0x03` is `0xD2`.**

| Reg | Name | Meaning |
|---|---|---|
| `0x03` | General Configuration | bit 7 = Back Channel CRC Checker Enable (default on) |
| `0x07`/`0x08` | Slave ID[0] / Slave Alias[0] | 7-bit field at bits[7:1]: remote I2C address + its alias. `0x96` decodes to `0x4B` — **this is the touch controller slot**, alias equal to its real address (no remapping) |
| `0x71`/`0x78` | Slave ID[2] / Slave Alias[2] | `0x50` decodes to `0x28` — **a third remote device slot, not previously identified in this repo.** It does not ack on a live bus scan with the link up (see "Link bring-up" below); likely unpopulated on this board variant, or needs a separate enable not yet found |
| `0x72`/`0x79` | Slave ID[3] / Slave Alias[3] | `0x24` decodes to `0x12` — **the faceplate controller slot** |
| `0x0C` | General Status | bit4 Link Lost, bit3 BIST CRC Error, bit2 TMDS Clock Detect, bit1 DES (back-channel) CRC Error, bit0 Link Detect |
| `0x0D` | GPIO0 | bits[7:4] Revision ID (read-only) |
| `0x16` | BCC Watchdog Control | bits[7:1] timeout in 2 ms units (default `0xFE`), bit0 disables the watchdog |
| `0x1E` | Transmitter Port Select | bit2 PORT1_I2C_EN (second I2C address = DeviceID+1), bit1 PORT1_SEL, bit0 PORT0_SEL |
| `0x20` | Deserializer Capabilities 1 | bit7 FREEZE_DES_CAP (stop auto-load from the back channel), bits 6:4 link-training mode bits, auto-set by the back channel once RX lock is detected |
| **`0x5A`** | **DUAL_STS — the link-status register GHS/the driver check** | bit7 `FPD3_LINK_RDY` (valid downstream connection detected), bit6 `FPD3_TX_STS` (transmitter active + receiver locked), bits[5:4] `FPD3_PORT_STS` (00=dual, 01=single-port0, 10=single-port1, 11=replicate), bit3 `TMDS_VALID`, bit2 `HDMI_PLL_LOCK`, bit1 `NO_HDMI_CLK` (active-high = **no** clock), bit0 `FREQ_STABLE`. GHS's `0x20081f` check for bits `0x80`+`0x04` is literally `FPD3_LINK_RDY` AND `HDMI_PLL_LOCK` |
| `0x5B` | DUAL_CTL1 | bit7 FPD3_COAX_MODE (strap), bit6 DUAL_SWAP, bit5 RST_PLL_FREQ, bit4 FREQ_DET_PLL, bit3 DUAL_ALIGN_DE, bit2 DISABLE_DUAL, bit1 FORCE_DUAL, bit0 FORCE_LINK |
| `0xC6`/`0xC7` | ICR / ISR | Interrupt Control / Interrupt Status; bit7 of each is `IE_IND_ACC`/`IS_IND_ACC`, indirect-register-access-complete interrupt enable/flag |

`0xC2`/`0xC4` were not resolved against the public register table in this pass
(the datasheet's revision history lists them among registers "added to default
list" without a table entry found at their own address in this text extraction);
their function remains UNKNOWN from this source. [TI DS90UB949-Q1 datasheet
(SNLS452B)](https://www.ti.com/lit/ds/symlink/ds90ub949-q1.pdf).

**Driver defects found in passing (VERIFIED, kernel module disassembly,
`vendor/lib/modules/ti949_serdes.ko`), noted here because they bear on reset
reliability, not exploit material:**
- All three chips (serializer 0x0c, deserializer 0x2c, faceplate 0x12) share one
  `i2c_client` struct; each access overwrites `client->addr` first. Only
  `reinit_ti949_948` takes `serdes_mutex`; the IRQ handler and the errata
  delayed-work item touch the same address field without it, so a concurrent
  reinit and errata/IRQ access can interleave and misdirect a register access to
  the wrong chip.
- If probe fails after the chrdev/class/workqueue are created but before IRQ
  setup succeeds, those resources are not torn down and can outlive the
  driver's freed private struct.
- `remove()` never cancels the delayed errata work or destroys its workqueue;
  unload inside the pending 500-jiffy window risks a use-after-free.

Stock recovery's separate `panelB_init()` opens `/dev/i2c-7` and sends to slave
`0x12`: `01 01`, waits 300 ms, then `20 ff ff` for the 960p path. The latter is
brightness register `0x20` followed by a little-endian 16-bit value. **Register
`0x01`'s semantics are UNKNOWN** — GHS's own code never writes it (GHS's only
faceplate writes are to `0x20` and `0x2a`; its only read is `0x1a`), so calling
`01 01` a "faceplate reset" is an assumption this pass could not confirm either
way. The 768p branch handles older panel firmware differently; it must not be
substituted for the 960p sequence. This faceplate reset/brightness sequence does
not itself perform all serializer initialization or prove external panel supply
is enabled.

### Brightness ownership

GHS `0x200196` emits `20 <low byte> <high byte>` to address `0x12`.
Main initially writes brightness zero. IPC callback `0x20045a` accepts messages
of at least nine bytes with byte 0 equal to `0x02` or `0x11` and byte 1 equal
to `0xb1`; brightness is `(byte[5] << 8) | byte[6]`. Assembly confirms the byte
positions. It applies that value unless its special-state latch is active.
An event branch for state value 3 latches brightness `0x8fc0` and never clears
the latch. **Resolved 2026-11-17 (VERIFIED):** state value 3 is the recovery-mode
notification from `lifecycle` (published when `CheckRecoveryMode` is non-zero,
else 1 is published); when `display_i2c` sees it, it sets the latch, forces the
fixed `0x8fc0` brightness, and stops the temperature poll — this is recovery-mode
brightness override, not an unidentified state. The upstream VIP producer and
CAN-to-brightness calculation are not traced in this pass (RH850 VIP firmware was
not disassembled); what is VERIFIED is where the value originates for GHS's
purposes — see "Brightness curve location" below.

Android `LvdsDevice::init()` reads `vendor.ghs.is_virt`. Both
`setDispBrightness` and the display branch of `setBacklightLevel` skip direct
I2C writes when this property is true. In the nonvirtualized path they generate
the same `20 low high` message.

**Resolved 2026-11-17 (VERIFIED, GHS `display_i2c` guest-I2C handler disassembly)
— the guest-write block is a software message filter, not MMU/EPT page denial:**
the handler (`0x200c0d`) inspects each guest I2C request and drops it before it
reaches the bus:
- Faceplate writes touching registers `0x20`/`0x21` (brightness) or `0x2a` (RVC
  status) are silently dropped — the guest's write is logged once and the status
  returned to the guest reports **success**, so a guest can't tell its brightness
  write was discarded.
- All serializer (`0x0c`) writes and plain reads are dropped the same way.
- Deserializer (`0x2c`) writes are allowed only for registers `0x1d`–`0x21`, plus
  `0x26`/`0x27` when the recovery latch above is set.
- Write-pointer-then-read pairs are **not** filtered — a guest can still read any
  register (e.g. faceplate `0x1a` is served to the guest) even where writes are
  blocked.
- **Filter bug (VERIFIED, static only, not exploited):** the end-register bound is
  computed in 8 bits (`r15b = (len & 0xff) + reg − 2`), while the request's `len`
  field is 16-bit. A write naming `reg=0x20` with `len=0x100` computes an 8-bit
  wraparound end register and passes the brightness-register check it should
  fail. Whether the lower-level driver or the faceplate itself accepts/rejects a
  write that large is UNKNOWN — this was not sent to hardware. Flagging it here as
  a defensive-hardening item on the owner's own device, not as something acted on.

Thus the existence of Android HAL functions does not mean a virtualized Android
guest owns the physical backlight: GHS owns the I2C bus, decides per-message
whether the guest's write reaches it, and the guest is told "success" either way.

### Brightness curve location — resolved 2026-11-17

**VERIFIED (static disassembly, VIP application image `85759599`):** the
Global-B input/output curve tables (see "Actual LTZ/HC calibration overrides"
below) live in the **VIP (RH850) firmware image**, not in GHS and not in the
guest. Offsets within that image: failsoft/threshold constants at `0xf8338`
(`4587, 19068, 17039`), 21-point output tables at `0xf8342`/`0xf8386`, an
11-point control-output table at `0xf836e`, and input axes at `0xf83de`/`0xf8402`/
`0xf841a`. A `[BCTL] Failed to load calibration for calID %d` string sits at
`0x7e6e` in the same image. **No Global-B tables exist in the GHS OTA image at
all** — this pass's earlier search for the curve's consumer inside GHS was
looking in the wrong component. The RH850 VIP binary itself was not disassembled
in this pass (x86 tooling only); which VIP routine actually applies the curve to
produce the `0xb1` frame's 16-bit value, and what ambient/headlight inputs feed
it, remain UNKNOWN.

### Actual LTZ/HC calibration overrides

The gzip CSM files were decoded, their inner XML at offset `0x368` extracted,
and `CalID` values joined to the base database names. Base database values alone
must not be described as effective vehicle overrides.

| Calibration | LTZ part/slot | HC part/slot | Verified override |
|---|---|---|---|
| SCREEN_RESOLUTION | 87846432 / 08 | 87846432 / 08 | 4 = 2400×960 |
| DISPLAY_BRIGHTNESS_INPUT_TABLE_GLOBALB | 85045371 / 04 | 85045386 / 04 | Identical 21-point input curve |
| DISPLAY_BRIGHTNESS_OUTPUT_TABLE_GLOBALB | 85045371 / 04 | 85045386 / 04 | Identical 21-point output curve |

Inputs: `0,5,9,13,17,21,25,29,33,37,40,55,60,65,70,75,80,85,90,95,100`.
Outputs: `66,328,655,983,1311,1966,2621,3932,6554,9830,13107,65535,65535,65535,65535,65535,65535,65535,65535,65535,65535`.
These differ from the base database's near-linear output curve. The same parts
also contain legacy daytime/nighttime brightness overrides; their existence
does not establish that the Global-A path is active on this Global-B hardware.
The base definition includes Global-B failsoft brightness 17039, but no override
of that field was found in these two packages. **The live consumer is the VIP
firmware image, not GHS** — see "Brightness curve location" above.

The earlier CAN trial changing slot08 from 4 to 2 was accepted but produced
visible tearing; stock restoration restored normal output. See the
[trial evidence](../research/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#screen_resolution-1280768-can-trial--2026-11-17).
That proves a behavioral effect, not successful operation at the alternate timing.

### Native Linux result and live link bring-up — superseded 2026-11-17

Probe04 booted on the radio: DMC loaded, `inteldrmfb` is 2400×960, stride 9600,
32 bpp, GPU active, and framebuffer samples contain red/green/blue bands.
HDMI-A-1 is explicitly forced, so its reported connected/enabled status is not
physical link confirmation. The owner observed a blank screen. No backlight
class device exists, so no actual brightness level or panel-supply state was read.

**Corrected 2026-11-17:** the earlier claim that "native bus 7 is instead PCI
`00:17.0`" was wrong. Live enumeration on the bench radio shows `/dev/i2c-10`'s
adapter name is `i2c_designware.7`, and its PCI parent (`readlink` of the sysfs
device path) is `0000:00:17.3` — the same instance number *and* the same PCI
function the guest's SELinux genfs mapping names for bus 7. The controller
candidate from the earlier pass was correct; the bus-numbering cross-reference
was not.

**Link bring-up succeeded 2026-11-17 (live, VERIFIED on hardware), using the
exact stock sequence recovered independently from both the GHS disassembly and
the `ti949_serdes.ko` kernel-module disassembly above, replayed by hand via two
purpose-built static tools (`i2cwr` for single-register writes, `i2creg`/`i2cscan`
for read-only probing — no files were written on the radio outside `/tmp`):**

1. Drove GPIO 467 low 10 ms then high, waited 100 ms (PDB reset).
2. Wrote serializer `0x16 = 0x02`.
3. Read serializer `0x5A` → `0xCD`; `0xCD & 0x30 == 0x00`, so wrote `0x5B = 0x03`
   per the verified branch logic.
4. Applied the 9-pair serializer table and the 5-pair deserializer table listed
   above, in order, with the 10 ms gap between them.
5. Read `0x5A` again → still `0xCD`; `0xCD & 0x84 == 0x84`, satisfying the GHS
   lock-readiness check (`0x20081f`) — **this is the link-lock condition
   stated as untested in earlier drafts of this doc, now confirmed on real
   hardware.** **Decoded against the public DS90UB949-Q1 datasheet (2026-11-17):**
   `0xCD` = `1100 1101` is `FPD3_LINK_RDY=1, FPD3_TX_STS=1 (locked), FPD3_PORT_STS=00
   (dual mode), TMDS_VALID=1, HDMI_PLL_LOCK=1, NO_HDMI_CLK=0 (clock present),
   FREQ_STABLE=1`. In plain terms: the serializer reports a fully locked FPD-Link
   III connection, actively receiving and locked to valid, stable HDMI from the
   SoC's GPU. This is a real, complete link-up condition, not just a bit pattern
   match.
6. Applied the remaining stock steps not yet covered above: the errata-#3
   read-modify-write on `0x5B` (clearing bit 5; it was already clear), the
   `set_mode_ctrl` sequence (read `0x5B`, read deserializer `0x1C` → `0x3B`,
   write serializer `0x1E=0x02`, `0x20=0x8F`, `0x1E=0x01`, then `0x5B=0x03`
   because `0x1C` bit 5 was set), and `enable_intb` (`0xC4=0x00`, read `0xC7`
   → `0x60`, `0xC2=0xAA`, `0xC6=0x41`).

**Result:** a full bus scan of `/dev/i2c-10` after this sequence acks **four**
addresses that previously acked none or only the serializer: serializer `0x0c`,
**faceplate `0x12`**, deserializer `0x2c`, and **touch controller `0x4b`**. The
faceplate's register `0x0F` was observed to change value between two reads
seconds apart (`0x07` → `0x02`), which is live, non-static behavior and the
strongest evidence yet that the faceplate side of the link is functioning, not
just acking its address.

**New finding, unresolved (2026-11-17):** the serializer's register table also
configures a third remote device slot at `0x28` (Slave ID/Alias[2], decoded from
`0x71`/`0x78` against the public datasheet — see the register table above). This
address does **not** ack on the post-bring-up bus scan alongside the other three.
Not previously identified anywhere in this repo. Either this board variant doesn't
populate that device, or it needs an enable/condition this pass didn't find.
Flagging as open, not guessing what it is.

**Touch controller (Atmel maXTouch, I2C `0x4b`) — reachable but UNKNOWN whether
functional. Addressing corrected 2026-11-17:** the probe below used single-byte
(8-bit) register addressing, matching the serializer/deserializer/faceplate
convention. **maXTouch chips actually use 16-bit, LSB-first register/object
addressing** (confirmed against the mainline Linux `atmel_mxt_ts.c` driver's
`__mxt_read_reg()`), so an 8-bit-addressed probe does not reliably land on the
intended register at all. Registers `0x00`–`0x1F` all read `0x01` under 8-bit
addressing, repeatably across three probes a second apart.

**Resolved 2026-11-17 (VERIFIED, live): the touch controller is alive and
functional.** Re-probed with a second purpose-built tool, `i2creg16`, using real
16-bit LSB-first addressing (confirmed against the mainline Linux
`atmel_mxt_ts.c` driver's own `__mxt_read_reg()` byte order) and a single
burst-read transaction (tests the chip's real auto-increment behavior rather
than re-sending the address each byte). Address `0x0000`, 16 bytes:

```
a4 3e 10 aa 21 40 28 75 fa 00 f2 17 00 25 c2 17
```

This is a genuine, non-repeating Atmel maXTouch Information Block: Family ID
`0xA4`, Variant ID `0x3E`, Version `0x10`, Build `0xAA`, Matrix X-size `0x21`
(33), Matrix Y-size `0x40` (64), Object Table Element count `0x28` (40 objects).
The earlier flat `0x01` reading was an artifact of using 8-bit addressing against
a 16-bit-addressed device, not a fault, not an idle/no-touch state, and not a
missing bootloader handshake. **The flat reading was never evidence the chip was
non-functional** — it was the wrong protocol. No write was sent to the touch
controller.

**Touch confirmed live and working 2026-11-17 (VERIFIED, physical touch test).**
The full 40-entry object table was read (`0x0007`, 240 bytes) and parsed per the
public Object Based Protocol structure (7-byte info block + 6-byte table entries,
[Microchip/Atmel maXTouch Object Protocol family](https://www.mouser.lt/pdfDocs/MXTAN0213_Interfacing_with_maXTouch_Touchscreen_Controllers_00002428A.pdf)).
This is a Gen5-class part — object types include `T100` (`TOUCH_MULTITOUCHSCREEN`,
entry 31) rather than the older `T9`, consistent with 40 total objects and a
~8.6 KB internal memory map. **T5 (`GEN_MESSAGEPROCESSOR`) is entry 4: address
`0x1845`, object size 11 bytes.** Polling that address once every 200 ms for 10
seconds while physically touching the panel captured a clean idle→active→idle
transition: steady `0xFF` ("no message pending," this chip's idle sentinel) before
and after, then a run of messages with distinct report IDs each carrying a
different, non-zero payload exactly during contact, before returning to `0xFF`.

**T100 message format decoded 2026-11-17 (VERIFIED against the mainline Linux
kernel's own `drivers/input/touchscreen/atmel_mxt_ts.c`, `mxt_proc_t100_message()`
and the object-init code around `T5_msg_size` — primary source, not a datasheet
paraphrase):**

| Byte | Field |
|---|---|
| 0 | Report ID |
| 1 | Status: bit7 `DETECT`, bits[6:4] `TYPE` (1=finger, 2=passive stylus, 4=hovering finger, 5=glove, 6=large touch) |
| 2–3 | X position, 16-bit little-endian |
| 4–5 | Y position, 16-bit little-endian |
| 6+ | Optional aux fields (orientation/pressure/area), position set by the `TCHAUX` config bits (object offset 3) in the T100 instance, in the fixed order VECT→AMPL→AREA |

**The real per-message length is 10 bytes, not the object's declared 11** — the
driver explicitly drops the object's last byte as CRC/reserved padding for any
chip not matching the old mXT224-pre-V2.0 special case
(`T5_msg_size = object_size − 1`, "CRC not enabled, so skip last byte"). The
initial capture above read all 11 bytes per sample; re-parsing drops that
trailing byte.

**Report-ID ownership, computed from this chip's own object table** (sequential
allocation starting at ID 1 for T6, standard Atmel convention, matching the
Linux driver's own enumeration order): T100's real per-finger touch slots are
IDs **`0x3c`–`0x5d`**; IDs `0x3a`/`0x3b` (T100's first two IDs) are its own
reserved **SCRSTATUS** messages (global screen/calibration status, not a touch
slot, different field meaning), filtered out by the driver itself
(`id = message[0] − T100_reportid_min − 2; if (id < 0) return`). Re-examining
the earlier capture against this: the message at report ID `0x3b` was
SCRSTATUS, not a touch slot — which is why its status byte didn't decode as a
sensible per-finger message. The genuine touch-slot messages were IDs
`0x3c`–`0x3f`, decoded per the table above:

| Report ID | X | Y |
|---|---|---|
| `0x3c` | 2135 | 41 |
| `0x3d` | 2399 | 657 |
| `0x3e` | 2271 | 97 |
| `0x3f` | 2394 | 782 |

These X values cluster near the panel's native 2400-pixel width and Y stays
within its 960-pixel height — numerically consistent with real on-panel
coordinates, not garbage, which is independent supporting evidence the decode
is substantially correct.

**Open discrepancy, not resolved in this pass:** the status byte's `DETECT` bit
(bit 7) reads clear on all four touch-slot messages above, which does not match
"active touch-down" in the driver's own logic (a clear `DETECT` means "finger
up," and the driver doesn't even act on X/Y when it's clear). The most likely
explanation is that free-running 200 ms polling — not gated on the `INTB`
interrupt (GPIO 449) — missed the true press-state messages and only caught
interpolated/trailing ones, since a real touch gesture generates messages far
faster than one every 200 ms. **The X/Y values above should be read as
plausible, not confirmed** until a capture gated on the GPIO 449 falling edge
(reading exactly one message per interrupt, draining the FIFO) is done. That
capture was not attempted in this pass.

**Display content: probe04 PID1 overwrote fbdev once per second (corrected 2026-11-17).**
Writing a raw BGRA image to `/dev/fb0` showed momentarily before reverting to
RGB thirds. Inspection of the exact `display-init.c` used for probe04 resolves
this: its main loop calls `paint()` before checking the interactive-shell child,
and `paint()` opens, maps, redraws, and closes `/dev/fb0` each iteration. The
loop sleeps one second, including while the shell runs. Consequently an open-fd
snapshot could miss it. The previous FBC/PSR-cache explanation was an untested
hypothesis and is superseded by this explicit writer. It is not established
that fbdev maps the wrong GEM object. A new console revision removes `paint()`
so fbcon can retain ownership; physical console verification remains separate.
**Fix (live, VERIFIED):** a second purpose-built tool, `kmsshow`, opens
`/dev/dri/card0`, allocates its own dumb buffer via `DRM_IOCTL_MODE_CREATE_DUMB`,
fills it with the image, and issues `DRM_IOCTL_MODE_ADDFB2` +
`DRM_IOCTL_MODE_SETCRTC` directly against CRTC 50 / connector 90 (HDMI-A-1),
bypassing the fbdev path entirely. This held steady (confirmed by a second
photograph) where the `/dev/fb0` write did not. `kmsinfo`, a read-only
companion, confirmed CRTC 50's active framebuffer switched from the original
`inteldrmfb` fb (106) to the tool's own fb (105) and stayed there.

None of this proves panel brightness/backlight control from native Linux — no
write to brightness registers `0x20`/`0x2a` was attempted in this pass (the
GHS-side guest-write-block findings above explain why that write would be
pointless under GHS, but this was native Linux with GHS not in the loop, where
the restriction does not apply). None of this was built into a new boot image;
all tooling lives in `/tmp` on the bench radio and does not survive a reboot.


### Probe05 console and diagnostic tooling — 2026-11-17

The next RAM image removes PID1's periodic framebuffer painter and leaves i915
fbcon in control. Kernel options enable the standard Linux logo (including
CLUT224), SUN12x22 console font, debugfs, and verbose timestamped printk with a
4 MiB ring buffer. FBC/PSR are disabled for this diagnostic revision; they were
not established as the cause of probe04's overwritten images. PID1 mounts
devpts for SSH PTYs and debugfs for hardware inspection.

`panel-stock --init-link` now reproduces the successful stock link sequence at
startup. It locates PCI 00:17.3 / DesignWare instance 7 rather than assuming an
I2C bus number, checks the verified INT3452:00 GPIO bank before touching GPIO
467, checks transfer results/link readiness, and has a 15-second guard. It does
not issue the separate faceplate maximum-brightness command. A hardware failure
leaves USB diagnostics available. The helper is skipped in QEMU.

BusyBox 1.37.0 was rebuilt natively on the build machine from the
[official source archive](https://busybox.net/downloads/busybox-1.37.0.tar.bz2),
SHA256 `3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4`.
The image has 403 applets, including `i2cdetect`, `i2cget`, `i2cset`, `i2cdump`,
`i2ctransfer`, `devmem`, `lspci`, `lsusb`, `hexdump`, `xxd`, `timeout`, `fbset`,
`chvt`, `setfont`, `dmesg`, `blockdev`, and full modprobe/depmod. Existing custom
`i2creg16`, `i2creg`, `i2cwr`, `i2cscan`, `pcimem`, `kmsinfo`, and `kmsshow`
sources were also compiled and included. Matching igb/brcmfmac/brcmutil and
atmel_mxt_ts modules have versioned dependency metadata. Including the touch
module is not evidence of successful interrupt assignment or evdev binding;
no automatic touch-controller instantiation was added.

Final boot image: 24,244,224 bytes, SHA256
`f4a2816c5dadf91518effb2eb66320497f297157e3024034d5bf48b7ba1499cc`.
QEMU validation passed: a screenshot showed two Linux penguins above kernel
messages, a newly emitted printk was read back from the virtual console,
required applet paths and PTY support were present, and shell/hash/read-only
block/NCM/SSH-server checks passed. This verifies virtual console behavior;
the corrected helper was subsequently validated on the radio as follows.

**Physical result:** the first probe05 boot reached the USB root shell but its
panel helper aborted before GPIO initialization with
`*** buffer overflow detected ***`, exit 134 (SIGABRT). The helper had supplied
a 512-byte destination to fortified `realpath()`, which requires PATH_MAX space.
This was an implementation error, not a failure of the recovered panel sequence.
After changing the buffer to PATH_MAX and rebuilding on the native build machine,
the corrected helper was transferred over T1 SSH and executed in RAM. It returned
`PANEL: stock link initialization complete on /dev/i2c-10, status=cd; fbcon owns video`.
The owner immediately confirmed visible output. The corrected helper also replaced
the running RAM copy, and the final image hash above includes the fix. T1
key-authenticated root SSH was re-established. No persistent radio storage was
written. The complete corrected image has not yet undergone a second cold boot;
its helper has been proven live on the first probe05 kernel.


### Probe06 corrected build and firmware staging — 2026-11-17

Built natively on the designated build machine while probe05 remained running.
Kernel release is `4.19.283-elk-linux-probe-r06`; USB product is
`ELK_LINUX_PROBE_06`. The PATH_MAX panel-helper correction is included, with
fbcon/logos, no periodic RGB repaint, 403 BusyBox applets, custom diagnostic
tools, debugfs/devpts, and matching versioned modules. Stale module directories
for other kernel releases are excluded from the packaged image.

The cleanroom's `ipu4_cpd_b0.bin`, `regulatory.db`, and `regulatory.db.p7s` are
now embedded through CONFIG_EXTRA_FIRMWARE alongside DMC and the display EDID.
This addresses file availability during early kernel probing; it does **not**
yet establish IPU firmware acceptance, camera capture, or shorter physical boot
time. The panel helper still runs from PID1, not as a built-in kernel driver.

| Embedded input | Bytes | SHA256 |
|---|---:|---|
| ipu4_cpd_b0.bin | 4861952 | `120f0434d40c891be79390690f5f1d764c98c8cbdca1092f3df1c55dddcc420f` |
| regulatory.db | 1412 | `eb6f74dea3f4949b6bd29a07b769193a1bab08e6d6fd49e945fff87f238876b0` |
| regulatory.db.p7s | 1198 | `0a0351e790bf6fbaf3f5ba2ee4b7cf4b9048be16413e0f0fe94943f1df16b28c` |

Initially boot-tested probe06 image: 25,653,248 bytes, SHA256
`282944532855e71be8ea2f2b8f4f64b33541f6e0db422e84db06c5113404c4a1`.
The final image passed QEMU console/framebuffer, printk-to-VT readback, applet,
PTY, shell, SHA256, read-only block, NCM configuration and SSH-server checks.
**Hardware boot verified:** after stock HMI-ready UART events, direct CAN
ELK entry returned `7101f000818003`, temporary VIP state was restored, and USB
8087:09ef was confirmed. The RAM image booted as
`4.19.283-elk-linux-probe-r06`; USB shell and T1 root SSH both worked. The
embedded IPU firmware progressed to module/library version20181222, exposing
25 video nodes, nine V4L subdevices and one media device. Capture remains
unverified; I2C-subdevice initialization warnings remain. The regulatory
database was rejected with `loaded regulatory.db is malformed or signature is missing/invalid`;
embedding the stock files did not establish acceptance by this kernel.

`Run /init as init process` occurred at0.437303s (previous missing-IPU-firmware
path waited about62s); i915 fb0 registered at1.159639s. This exposed an early
startup ordering issue: the panel helper initially returned link status92
and failed. A later live retry returnedCD, exit0. A readiness correction now
skips mode selection while the link is unready and polls the stock0x84 status
mask for up to5s without repeated resets. The corrected helper was installed
in RAM, but this new readiness path has not yet had a fresh-boot verification.

The readiness-corrected image is also25,653,248 bytes, SHA256
`a80cf231ee30535fbe8dc70078ae0480b232aa4152559aca895ab0262be70bab`.
It replaces the local probe06 artifact; the currently running kernel came
from the initial hash above. The broad live hardware inventory was
performed on probe05 and is owned by
[hardware coverage](../platform/hardware.md#native-ram-linux-hardware-coverage--2026-11-17).


### Probe07 graphics runtime — prepared 2026-11-17

The next image retains the corrected panel helper/readiness wait and packages
Mesa EGL/OpenGL ES, Intel Vulkan and VA-API userspace, plus test/inspection
commands. Hardware shader rendering passed on the running probe06 without
changing display scanout. Probe07 itself has passed QEMU but is not yet booted
on the radio. The [owning acceleration record](hardware_rendering.md#native-linux-gpu-acceleration--verified-2026-11-17)
contains the exact tests, limits, package versions and final image hash.

---

## Display Panel Specifications

### Primary Display

| Property | Value |
|----------|-------|
| Panel Model | DD134IA-01B |
| Manufacturer | Chimei Innolux (CMN) |
| Product ID | 41268 |
| Manufacture Date | Week 36, Year 2020 |
| Display Type | Internal LCD |
| Connection Type | Direct (Port 35) |

### Resolution and Timing

| Property | Value |
|----------|-------|
| Physical Resolution | 2400 x 960 pixels |
| Aspect Ratio | 2.5:1 (25:10) |
| Refresh Rate | 60.00 Hz (60.001434 Hz actual) |
| VSYNC Period | 16.666268 ms |
| Presentation Deadline | 14.666268 ms |
| App VSYNC Offset | 2.5 ms |

### Pixel Density

| Property | Value |
|----------|-------|
| Physical DPI (X) | 192.911 |
| Physical DPI (Y) | 193.523 |
| Logical Density | 200 dpi |
| Density Scale | 1.25x (200 / 160 dpi baseline) |

### Display Metrics

| Metric | Value |
|--------|-------|
| Physical Size | 13.39 inches diagonal (confirmed: /Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/specs/gminfo3.7_tech_specs.md) |
| Usable App Area | 1416 x 960 pixels (with system UI) |
| Full Screen | 2400 x 960 pixels |

---

## Display Controller

### Hardware Composer (HWC)

| Property | Value |
|----------|-------|
| HAL Version | 2.1 / 2.2 / 2.3 (`composer.intel@2.3-service`) |
| Implementation | `iahwcomposer` (Intel Automotive HWC) |
| Display ID | 4615537251352926243 |
| HWC Display ID | 0 |

### Display Modes

```
Mode ID: 0 (Active)
  Resolution: 2400 x 960
  Refresh Rate: 60.00 fps
  DPI: 192.91 x 193.52
```

**Note:** Single display mode only - no variable refresh rate support.

---

## SurfaceFlinger Configuration

### Build Configuration

| Setting | Value |
|---------|-------|
| PRESENT_TIME_OFFSET | 0 |
| FORCE_HWC_FOR_RGB_TO_YUV | 0 |
| MAX_VIRT_DISPLAY_DIM | 0 |
| RUNNING_WITHOUT_SYNC_FRAMEWORK | 0 |
| NUM_FRAMEBUFFER_SURFACE_BUFFERS | 3 |

### Sync Configuration

- **Sync Type:** `EGL_ANDROID_native_fence_sync`
- **Wait Sync:** `EGL_KHR_wait_sync`

### Scheduler Settings

| Property | Value |
|----------|-------|
| Touch Timer | Off |
| Content Detection | Off |
| Layer History Size | 125 |
| Active Layers | Variable |
| Idle Timer | Off (platform) |
| Frame Rate Override | Not Supported |

### Phase Timing

| Phase | Duration |
|-------|----------|
| App Phase | 2.5 ms |
| SF Phase | 3.0 ms |
| App Duration | 17.17 ms |
| SF Duration | 13.67 ms |
| HWC Min Duration | 0 ns |

---

## Color Management

### Color Configuration

| Property | Value |
|----------|-------|
| Color Mode | Native (Mode 0) |
| Render Intent | Colorimetric |
| Dataspace | Unknown (0) |
| Color Management | Enabled |
| Wide Color Gamut | Not Supported |

### Supported Color Modes

| Mode ID | Mode Name |
|---------|-----------|
| 0 | ColorMode::NATIVE |

### HDR Capabilities

| HDR Type | Supported |
|----------|-----------|
| HDR10 | No |
| HDR10+ | No |
| HLG | No |
| Dolby Vision | No |

**HDR Metadata:**
- Max Luminance: 500.0 nits
- Max Average Luminance: 500.0 nits
- Min Luminance: 0.0 nits

---

## Composition Pipeline

### Layer Composition

| Composition Type | Description | Usage |
|------------------|-------------|-------|
| DEVICE (2) | Hardware overlay | Preferred |
| CLIENT (1) | GPU composition | Fallback |

### Typical Layer Stack

```
Layer Stack (129 visible layers typical):

1. Wallpaper BBQ wrapper
   - Type: DEVICE
   - Size: 2400x960
   - Blend: NONE
   - Opaque: true

2. zeno.carlink/MainActivity  *(from the February 2026 CPC200 rig; the app on the radio as of 2026-11-12 is gm_ccpa, `zeno.gmccpa.av.CarPlayActivity` in package `android.car.usb.handler`; this layer dump was not re-captured)*
   - Type: CLIENT/DEVICE
   - Size: 2400x960
   - Blend: NONE
   - Opaque: true

3. LeftBar (System UI)
   - Type: CLIENT
   - Size: 189x960
   - Blend: PREMULTIPLIED
   - Opaque: false

4. ScreenDecorOverlay (Top)
   - Type: CLIENT
   - Size: 2400x95
   - Blend: PREMULTIPLIED

5. ScreenDecorOverlayBottom
   - Type: DEVICE
   - Size: 2400x95
   - Blend: PREMULTIPLIED
```

### Composition Statistics

| Metric | Value |
|--------|-------|
| Uses Client Composition | Yes |
| Uses Device Composition | Yes |
| Flip Client Target | No |
| Reused Client Composition | Yes |

---

## Framebuffer Management

### Buffer Queue Configuration

| Property | Value |
|----------|-------|
| Max Acquired Buffers | 2 |
| Max Dequeued Buffers | 1 |
| Dequeue Cannot Block | No |
| Async Mode | No |
| Queue Buffer Can Drop | No |
| Legacy Buffer Drop | Yes |
| Buffer Format | 1 (RGBA_8888) |
| Transform Hint | 0x00 |
| Frame Counter | Continuous |

### Buffer Slots

| Slot | State | Dimensions |
|------|-------|------------|
| 0 | FREE/ACQUIRED | 2400x960 (stride 2432) |
| 1 | ACQUIRED | 2400x960 (stride 2432) |
| 2 | FREE | 2400x960 (stride 2432) |

---

## Display Power Management

### Power States

| State | Status |
|-------|--------|
| Current State | ON |
| Screen Acquired | Yes |
| HW VSYNC Enabled | No (when idle) |
| HW VSYNC Available | Yes |

### Brightness Control

| Property | Value |
|----------|-------|
| Current Brightness | 0.398 (39.8%) |
| Brightness Range | 0.0 - 1.0 |
| Default Brightness | 0.398 |
| Backlight Minimum | 0.035 |
| Backlight Maximum | 1.0 |
| VR Brightness Range | 0.307 - 1.0 |
| VR Default Brightness | 0.335 |

### Auto-Brightness

| Property | Value |
|----------|-------|
| Auto-Brightness Enabled | No |
| Light Sensor | Not Available |
| Software Auto-Brightness | Supported |
| Allow While Dozing | No |

### Brightness Curve

```
Ambient Lux → Brightness Mapping:
0 lux    → 0.232 (23.2%)
50 lux   → 0.390 (39.0%)
300 lux  → 0.547 (54.7%)
720 lux  → 0.783 (78.3%)
2000 lux → 0.980 (98.0%)
```

---

## Display Features

### Supported Features

| Feature | Status |
|---------|--------|
| Secure Display | Yes |
| Protected Buffers | Yes |
| Trusted Display | Yes |
| Rotation Support | Yes (with content) |
| Minimal Post-Processing | No |

### Display Flags

```
FLAG_DEFAULT_DISPLAY
FLAG_ROTATES_WITH_CONTENT
FLAG_SECURE
FLAG_SUPPORTS_PROTECTED_BUFFERS
FLAG_TRUSTED
```

---

## Virtual Display Support

### Display Adapters

| Adapter | Status |
|---------|--------|
| LocalDisplayAdapter | Active |
| VirtualDisplayAdapter | Available |
| OverlayDisplayAdapter | Available |

### Virtual Display Configuration

- Overlay displays not configured
- Remote display service: Stopped

---

## Performance Metrics

### Frame Statistics

| Metric | Value |
|--------|-------|
| Target Frame Rate | 60.00 fps |
| Total Missed Frames | 566 (since boot) |
| HWC Missed Frames | 566 |
| GPU Missed Frames | 536 |

### Static Screen Statistics

| Duration | Percentage | Description |
|----------|------------|-------------|
| < 1 frame | 2.9% | Very active |
| < 2 frames | 3.8% | Active |
| < 3 frames | 1.5% | Moderate |
| < 4 frames | 1.3% | Light |
| < 5 frames | 0.9% | Light |
| < 6 frames | 0.7% | Idle |
| < 7 frames | 0.6% | Idle |
| 7+ frames | 88.5% | Static |

---

## RenderEngine (GPU Fallback)

### Configuration

| Property | Value |
|----------|-------|
| EGL Version | 1.4 Android META-EGL |
| GLES Vendor | Intel |
| GLES Renderer | Mesa Intel HD Graphics 505 |
| GLES Version | OpenGL ES 3.2 Mesa 21.1.5 |
| Protected Context | Not Supported |
| Program Cache | 3 programs |
| Image Cache | 27 images |
| Framebuffer Cache | 3 buffers |

### Last Dataspace Conversion

```
Source: Default (0)
Target: Default (0)
```

---

## System UI Layout

### Screen Regions

| Region | Position | Size |
|--------|----------|------|
| Top Decor | (0, 0) | 2400 x 95 |
| Left Bar | (0, 0) | 189 x 960 |
| Bottom Decor | (0, 865) | 2400 x 95 |
| App Content | (189, 95) | 1416 x 770 |
| Full Screen | (0, 0) | 2400 x 960 |

### Insets

| Inset Type | Value |
|------------|-------|
| Top | 0 (configurable) |
| Status Bar | 95 pixels |
| Navigation Bar | 95 pixels |
| Left Bar | 189 pixels |

---

## Recommendations

### Optimal Video Surface Configuration

1. **Surface Type:** SurfaceView for video playback
2. **Layer Type:** DEVICE composition when possible
3. **Z-Order:** Below system overlays
4. **Secure Content:** Supported via FLAG_SECURE

### Performance Tips

1. Minimize layer count to reduce composition overhead
2. Use opaque layers where possible (blend=NONE)
3. Avoid transparent overlays during video playback
4. Target 60 fps for smooth automotive UI

### CarPlay/Android Auto Display

| Property | Recommended |
|----------|-------------|
| Resolution | 2400 x 960 or 1920 x 768 |
| Frame Rate | 60 fps |
| Color Format | RGBA_8888 or NV12 |
| Composition | DEVICE (overlay) |

### Linux 7.3.5 runtime panel correction — 2026-11-17

The stable Probe image boots and creates a 2400×960 i915 framebuffer, but its
packaged helper initially returns `PANEL: display I2C controller missing or
ambiguous`. Linux 7.3.5 exposes the adapters under `/sys/bus/i2c/devices/`;
this boot has no `/sys/class/i2c-adapter` class. The controller identified by
PCI `00:17.3` is bus 10, with serializer/display devices behind it. Selection
must use the bus-device path and physical PCI identity rather than a fixed bus
number or obsolete class path.

The next guard returned `PANEL: reset line 33 identity differs; refusing reset`.
GPIO-v2 did not supply the expected line name, while pinctrl explicitly reports
`pin 33 (GPIO_33)` on `INT3452:00`; gpiochip0 has 78 lines. Pinctrl ranges map
line 33 directly to pin 33. A temporary helper retained the chip-label/count
checks and verified pinctrl identity when the line-name field is empty.
It then completed link initialization on `/dev/i2c-10`, status `CD`, and the
owner confirmed visible display output. The helper remains resident holding
the GPIO-v2 request FD: closing it does not guarantee the reset output stays
high. No panel brightness write was needed in this test.

These are **RAM-only corrections** to the image with SHA-256
`34a92caf9eea8cc488531d47ecbca9f0b5fddf3eefbca663d5ae96ab14c220d6`.
The saved r01 image and shared builder were not changed during that physical
test. Corrected source/binary were prepared in temporary directories outside
the builder. These fixes were subsequently integrated into stable02 as noted
below; automatic panel initialization was subsequently verified on stable02.

Touch remains reachable: the bus-10 address-0x4b burst read using 16-bit,
LSB-first register addressing returned the same valid information block listed
above. Only the power-button input device is currently registered; maXTouch
Linux device/IRQ binding is not established by that successful read.

**Stable02 integration (2026-11-17):** the shared 7.3.5 builder now includes the
runtime-proven helper unchanged. Compiled helper SHA-256 is
`2eb7f924ffb7f88fd92fe20660b4f94cd055c59eab36d8545e8ae6f9e8432790`,
matching the helper used for the successful physical test. Final boot-image
SHA-256 is `f9977c166122b86d0839cb253779dba2eb26166938624513d34b966fc886d885`.
QEMU passed framebuffer-console text readback and matched its 1280×800
framebuffer dimensions to a screenshot showing Linux logos and kernel logs.
A subsequent physical stable02 boot reached USB shell and T1 SSH. Its packaged
helper started automatically and retained `probe-panel-reset` on GPIO-v2 line 33
at output-high. A read-only serializer check returned `0xCD`, i915 reported
2400×960, and HDMI-A-1 was enabled. No manual panel initialization was issued.
The owner confirmed the display is active on this stable02 boot. This verifies
the integrated helper starts the physical panel without a post-boot repair.
