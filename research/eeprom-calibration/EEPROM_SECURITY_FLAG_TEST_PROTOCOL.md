# EEPROM Security-Flag Test Protocol

**Scope:** this doc owns bench-test *methodology* for probing CSM (`0x80`) EEPROM
security/config flags and UDS `$27` SecurityAccess gating — the T0→T3 cost/risk ladder,
static/RAM-shadow/physical test procedures, backup/rollback/recovery, and the 5 live
UDS/DID bench-test recipes (frame-level bytes).

**Explicitly NOT here:** which EEPROM byte is the real `$27` gate, the EEPROM memory map,
and the SBI/ADB-bypass mechanism — all owned by
[`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md) (ELA), the
canonical, continuously-corrected source for flag identity. Do not re-derive or restate
that debate here; this doc only supplies the *procedure* to test whatever byte ELA names.

Evidence tags: `[C]` confirmed live, `[V]` verified, `[FW]`/`[S]` static firmware,
`[inferred]`, `[U]` unverified, `[X]` external.

**Related:** [`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)
(flag identity, canonical), [`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
(UDS `27`/`67` seed-key algorithm detail),
[`../diagnostics/diagnosticsd_security_access.md`](../diagnostics/diagnosticsd_security_access.md)
and [`../diagnostics/diagnosticsd_dids_and_dtc.md`](../diagnostics/diagnosticsd_dids_and_dtc.md)
(live T1 SecurityAccess/DID-sweep detail the UDS tests below defer to).

---

## History

This doc originally targeted four hypothesized flags (`0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0`)
as the `$27` gate. A 2026-08-26 full-coverage RH850 disassembly (VIP_APP + VIP_BOOT) plus
owner bench witness **refuted all four** — their xref counts were grep noise and the
"IPC Security" naming was a misread of the `[IPC_S]` serial-transport log tag. **Superseded,
see ELA §0–§0.8** for the refutation and ELA's current flag-identity findings (confirmed
ADB/SBI bytes, trim/theme candidates, the 0x0A80-vs-0x0A81 marker/data correction, etc.).
The sections below that named those four flags by number (former §1 Hypothesis, §4
Physical test order, §7 Decision tree, §8 Summary answers) have been reduced to one line
each; the generic methodology they wrapped (T0–T3 ladder, static/RAM-shadow procedure,
observation checklist, backup/rollback) is unaffected by which byte turns out to be the
gate and is kept in full below.

---

## 0. Governing principle: do NOT desolder first

Each physical reprogram cycle is expensive and adds bricking risk. The protocol is tiered
so that **most of the answer is obtained with zero destructive actions**, and physical
flips are ordered lowest-risk-first and stopped the moment the gate opens.

**Cost/risk ladder (always climb from the top):**

| Tier | Action | Cost | Reversible? |
|------|--------|------|--------------|
| T0 | Static analysis: xref each candidate EEPROM address in the firmware image | free | yes |
| T1 | Dynamic: read live EEPROM + patch the **RAM shadow** via debugger | low | yes (reboot) |
| T2 | In-circuit reprogram (I2C/SPI clip, no desolder) | medium | yes (rewrite) |
| T3 | Desolder / socket / reprogram / resolder | high | yes but risky |

Only escalate a given candidate byte to T2/T3 if T0–T1 are inconclusive **and** that byte
is still a live hypothesis per ELA. In practice T0 often answers the gate question
outright.

---

## 1. Flag hypothesis — superseded

The original per-flag hypothesis table (region/role/confidence/brick-risk for
`0x04A0`/`0x04C0`/`0x0A40`/`0x0BE0`) is **superseded, see
[`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`](EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md)**. Byte
identity and current-best gate candidate are tracked there, not here.

---

## 2. Tier 0 — Static analysis (do this first, it may finish the job)

For each candidate byte named by ELA, in the extracted firmware/bootloader image:

1. **Find cross-references (xrefs)** to the EEPROM offset (or its RAM-shadow address).
   - Locate the boot-time EEPROM read/copy routine; map EEPROM offset → RAM shadow
     address.
   - Search the disassembly for loads from that shadow address.
2. **Classify each xref site:**
   - Compared inside the **`$27` handler** (seed/key, `requestSeed`/`sendKey`, the `0x27`
     case in the UDS service dispatcher) → **strong evidence this byte is the gate.**
   - Read by a **feature/menu dispatcher** → hidden-feature enable, not the gate itself.
   - Read by the **boot/checksum/lock** routine → dangerous lock bit; do not flip casually.
   - No xref at all → inert/mirror; deprioritize.
3. **Record the tested polarity:** what value does the code branch on (`== 0`, `!= 0xFF`,
   bit mask)? This tells you *which way* to flip and avoids a wasted cycle.
4. **Check for checksum coverage:** determine whether the address falls inside a
   checksummed/CRC'd region. If yes, any flip must be followed by **recomputing and
   rewriting the checksum**, or the module will reject the image at boot. This is the #1
   cause of self-inflicted bricks.

**Exit criteria for T0:** if exactly one candidate byte is read inside the `$27` handler,
you have your answer with high confidence — go straight to T1 to validate it, skip the
rest of the physical ladder.

---

## 3. Tier 1 — Dynamic RAM-shadow patch (reversible, no reprogram)

Most modules copy the EEPROM config block into RAM at boot and read from RAM thereafter.
If so, you can test a candidate byte **without touching the EEPROM at all**:

1. Attach debugger (JTAG/SWD/BDM). Confirm you have halt + memory-write.
2. Dump the live RAM shadow; confirm it matches the EEPROM offsets (byte-for-byte).
3. **Patch the shadow byte** for the candidate flag in RAM, resume, and exercise the gate
   (§5 below).
4. If behavior changes → you have functional proof with a fully reversible action
   (power-cycle restores the original EEPROM value). Only then consider making it
   persistent via T2.

This tier lets you test **every remaining candidate and both polarities in one sitting**
with zero destructive cost. **Do as much of the matrix here as the hardware allows.**

> Note: RAM-shadow patching bypasses EEPROM checksums, so it validates *function* but not
> *persistence*. A byte that works in RAM but is protected by a boot checksum in EEPROM
> will need the checksum recomputed when made persistent — flag this now.

---

## 4. Physical test order (T2/T3) — superseded

The original fixed physical-test ordering (`0x04A0` → `0x04C0` → `0x0A40` → `0x0BE0`) is
**superseded, see ELA**. The *rule* survives independent of which bytes it applies to:
order remaining candidates lowest-info-risk first, test late-region/checksum/lock-tail
bytes last and only with a proven independent recovery path staged (per §6), and never
flip two bytes in the same reprogram cycle unless T0 proved they are a required pair.
One variable per cycle — flip → observe (§5) → decide → revert-or-keep before the next.

---

## 5. What to observe after each flip

Capture a **baseline** of all of these *before* the first change, so every observation is
a diff.

**A. Diagnostic / `$27` gate status (the primary signal):**
- Send UDS `$10 03` (extended diagnostic session), then `$27 01` (requestSeed).
- Baseline (secured): non-zero seed returned, or `$27` returns NRC `0x33`
  (securityAccessDenied) / requires a valid key.
- **Gate opened** = one of: seed returns all-zero (security effectively disabled), `$27 02`
  (sendKey) accepted with a null/trivial key, session escalates without a key, or the
  calibration service (`$2E`/`$3D`/routine `$31`) becomes accessible without prior unlock.
- Also probe cal-adjacent services: `$22`/`$2E` on protected DIDs, `$31` cal routines.

**B. Boot / log output:**
- Serial/UART boot log, debug console, or diagnostic trouble codes (`$19` readDTC).
- Watch for: new "engineering mode"/"dealer mode"/"cal enabled" banners; **or**
  checksum/config-error messages (means the flip landed inside a checksummed region and
  the CRC wasn't fixed).
- Confirm the module still completes boot to normal operation (no boot loop).

**C. Behavior / feature changes:**
- New menu items, unlocked PIDs/DIDs, cal screens, RF/TX test modes, hidden UDS routines.
- Regression check: verify **normal function is unimpaired** (the byte may enable a
  feature *and* break something else).

**D. Interface health:**
- Immediately re-verify debugger attach and EEPROM read-back still work after flipping any
  late-region/checksum-tail/lock-bit candidate. If the programming interface is gone,
  execute rollback (§6) before anything else.

**Log every cycle** in a table: `byte | old→new value | checksum fixed? | seed result |
boot log delta | features | interface OK?`.

---

## 6. Backup / rollback procedure

**Before the first physical change:**
1. **Full-image golden backup:** read the *entire* EEPROM (not just the candidate bytes)
   at least **twice**, and verify the two dumps are byte-identical. Store off-device with
   a checksum (sha256) recorded. This is your ground truth.
2. Photograph the board (component orientation, pin 1, decoupling caps) before any
   desolder.
3. Record the exact programmer settings (chip model, voltage, I2C/SPI address, page size)
   that produced a verified read — you'll need identical settings to write back.
4. If the chip is soldered and you must desolder, **install a socket** (or use an
   in-circuit clip) so subsequent cycles don't require reflow.

**After each flip:**
- Read back the whole chip and diff against the intended image (confirm *only* the target
  byte(s) changed and the write didn't corrupt neighbors or the checksum).

**Rollback (revert a change):**
1. Re-flash the **golden full-image backup** (not a byte patch — the whole image, so any
   checksum/wear-leveling side effects are also reverted).
2. Verify read-back == golden sha256.
3. Power-cycle; confirm boot log + normal function + `$27` back to baseline (secured)
   behavior.

**If the interface is bricked** (e.g., a lock/write-protect candidate disabled
debug/write access):
1. Desolder the chip and program it on a **standalone external programmer** with the
   golden image (this is why the golden image and a socket matter).
2. If an OTP/permanent-lock bit was set and cannot be cleared, the chip is scrap — replace
   with a blank flashed to the golden image. (This is the scenario the ordering in §4 is
   designed to avoid.)

---

## 7. Decision tree — superseded

The original decision tree was keyed to the four refuted flags by number
(`0x04A0`/`0x0BE0` branch labels, etc.). **Superseded, see ELA** for current flag
identity. The flow itself is unchanged and byte-agnostic:

```
START
 └─ T0 static xref analysis
     ├─ Exactly one candidate byte read inside the $27 handler?
     │     └─ YES → that is the gate. Go to T1 to confirm, then STOP.
     ├─ A byte read only by boot/checksum/lock routine?
     │     └─ Mark DANGEROUS. Exclude from casual testing.
     └─ Ambiguous / multiple candidates → continue to T1.

 T1 RAM-shadow patch (reversible, test the whole matrix here)
     ├─ Patching byte X opens the $27 gate?
     │     └─ YES → functional answer found.
     │            ├─ Persistence needed? → escalate ONLY byte X to T2. Else STOP.
     │            └─ If X worked only paired with byte Y, treat {X,Y} as the pair.
     ├─ A byte toggles hidden features but not the gate?
     │     └─ Record as feature-enable, not the $27 answer.
     └─ No byte changes anything in RAM → gate is not a simple EEPROM flag
           (may be code/OTP/fuse-based). STOP escalation; re-scope.

 T2 in-circuit reprogram (only surviving candidates, lowest-risk first per §4)
     ├─ After each single flip: run §5 observations.
     ├─ Gate opens AND interface healthy AND normal function intact?
     │     └─ SUCCESS. Rollback all other experiments to golden. STOP.
     ├─ Gate opens but something broke → note trade-off; rollback; STOP or refine.
     └─ No effect → rollback, advance to next candidate.

 Late-region/lock-bit candidate (before ever flipping it)
     ├─ Independent recovery path proven (external programmer + golden image staged)?
     │     ├─ NO  → DO NOT FLIP. Stop.
     │     └─ YES → flip as a final experiment only; re-verify interface immediately after.

 GLOBAL STOP CONDITIONS
     • The $27 gate opened and the module still boots/functions → done; revert everything else.
     • All candidates exhausted with no gate effect → conclude the $27 gate is not EEPROM-flag
       governed; pivot to firmware/OTP/fuse investigation.
     • Any unrecoverable interface loss → stop, execute external-programmer recovery (§6).
```

---

## 8. Summary — superseded

The original (a)-(d) summary answers named the four refuted flags directly. **Superseded,
see ELA** for the current answer to "which byte is the gate." The methodology-level
answers survive unchanged:
- **Order:** T0 static → T1 RAM-shadow (all candidates, reversible) → physical,
  lowest-risk-first, late-region/lock-tail bytes last and gated on a proven recovery path.
- **Observe:** `$27` seed/key response and cal-service access; boot/UART log deltas and
  checksum errors; new features + regression check; interface health after each flip.
- **Rollback:** verified full-image golden backup (×2, sha256), socket the chip, revert by
  re-flashing the whole golden image; external-programmer recovery if the interface is
  lost.
- **Biggest self-brick risk:** flipping a byte inside a checksummed region without
  recomputing the checksum — always resolve checksum coverage in T0.

---

## UDS FRAME LIST — the 5 SBI/`$27`/DID bench tests (2026-08-26)

Target ECU = **`0x80`** (CSM). Portable part is the **UDS PDU**; the
`gm_dps/misc/Aug24_session/ecu80_READ.Txt` on-wire form wraps it as `0E F5 0A 80 <UDS>`
(request) / `25 80 0E F5 <UDS>` (response) — DPS/MDI2 GCI framing. Send the UDS PDU; the
tool (DPS or `mdi2_client`) adds the wrapper. Keep `3E 80` (TesterPresent, suppressed)
flowing every ~2 s or the session/unlock drops.

**Preamble**
```
10 03        → 50 03 00 64 01 F4     extendedDiagnosticSession
3E 80                                 TesterPresent (suppressResponse) — keep-alive
```

### Test 1 — MEC read, SBI set vs cleared
```
10 03
22 F1 A0   → 62 F1 A0 FF   SBI-set (MEC=255 → adb cert bypassed)
           → 62 F1 A0 00   stock   (MEC=0   → adb cert required)
22 F1 90   → 62 F1 90 <17 ASCII VIN>   (sanity)
NRC: 7F 22 31 requestOutOfRange · 7F 22 33 securityAccessDenied
```
MEC value semantics (whether nonzero means bypassed vs. production) is an open
corpus-wide conflict — see `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md` and ELA's Open
Conflicts sections, not restated here.

### Test 2 — level-1 response format (corrected 2026-11-14)

The verified degenerate exchange has a **31-byte seed and a 12-byte submitted response**.
A prior equal-length/all-FF-key recipe was incorrect and is not reproduced here. On direct
T1 use logical tester F4, target `0x0084`, and the exact custom framing in the
[owning diagnostic reference](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).

```
10 03                 -> 50 03 ...       extended session
27 01                 -> 67 01 + FF x31  seed
27 02 + 00 x12        -> 67 02           exact tested response accepted
10 01                 -> 50 01 ...       restore default session
```

The earlier invalid-tester NRC `0x10` did not establish SBI-inactive state. One accepted
zero response does not prove arbitrary-key acceptance, all-FF key acceptance, any other
security level, programming writes, or root access. Do not send a fabricated key for a
real/non-degenerate seed.

### Test 3 — higher levels, all-FF seed? (SecurityLevel = `$27` requestSeed subfunction; sendKey = +1)
```
27 01 Service(1)            27 03 AssemblyPlant(3)      27 05 OTA(5)
27 09 Engineering(9)        27 0B RemoteDiagnostics(11) 27 0D SupplierSecAccess(13)
27 11 ExtendedReflash(17)   27 13 ExtendedAssembly(19)  27 15 ExtendedOTA(21)   27 5F EndOfLife(95)
```
Each supported level may return `67 <sf> <seed>`. An all-FF seed alone does not prove a
grant or establish its key format. A later 2026-11-14 T1 read sweep validated 09/0A and
0B/0C using the 31-FF/12-zero format from Test 2; other higher levels remain untested. See
the [read-sweep results](../diagnostics/diagnosticsd_dids_and_dtc.md#bounded-read-only-sweep-and-uart-reset-follow-up-2026-11-14).
Do not extrapolate to every level or arbitrary key content. NRC `7F 27 12`
subFunctionNotSupported = level absent.

### Test 4 — `SECURE_UNLOCK_LEVEL` over DoIP (CAN↔Ethernet state-sharing) — with DID sweep
Transport = **DoIP (ISO 13400) over T1 (100BASE-T1)**. DoIP header = `02 FD <ptype:2>
<len:4> <payload>`. (DoIP wire-protocol detail beyond this probe is owned by
`platform/ethernet_networking.md`; not restated here.)
```
# 4a. Discover the CSM DoIP logical address (LA) — UDP 13400
Vehicle Identification Request:  02 FD 00 01 00 00 00 00
   → 02 FD 00 04 <len> <VIN:17> <LA:2> <EID:6> <GID:6> …    LA = ECU logical addr → Target Address (TA)

# 4b. TCP 13400 → Routing Activation (tester source e.g. 0E00)
   02 FD 00 05 00 00 00 07  0E 00  00  00 00 00 00
   → 02 FD 00 06 … code 0x10 = success

# 4c. First raise level on CAN (Test 2/3), THEN read over DoIP:
   Diag message (ptype 0x8001):  02 FD 80 01 00 00 00 07  0E 00  <TA_hi TA_lo>  22 <DID_hi DID_lo>
   → 62 <DID> <level>   level matches the CAN-set level ⇒ shared state; 0 ⇒ per-transport (separate)

# 4d. DID sweep (SECURE_UNLOCK_LEVEL wire-DID unknown — enum "CUSTOM id 17" ≠ a DID). Prioritized:
   candidates:  22 00 11 · 22 00 17 · 22 11 17 · 22 00 05
   Eth block:   22 F1 00 … 22 F1 FF
   GM custom:   22 01 00 … 22 02 FF
   HIT = 62 <DID> <n> where n ∈ {0,1,3,5,9,11,13,17,19,21,95} (a SecurityLevel value).
```
The DoIP-responder topology/ownership question (which side originates vs. echoes) is an
open cross-tree conflict — see `AUG24_SESSION_FULL_PCAP_TIMELINE.md`'s Open Conflicts, not
resolved here.

### Test 5 — DID-18 Signature-Bypass Ticket (real DID unknown; "18" = service-manual, enum `mGBMessageId=2`)
```
# 5A (preferred) CAPTURE during an OTA poll:
  Trigger a dev-signed VIP package install (or a programming session) → DelayedWKSApp calls isSBISet()
  → VIPRequestManager emits the ticket request on CAN toward the VIP. Sniff CAN for the req/resp pair,
  once with SBI set and once cleared → payload>0 vs 0 identifies the message + its bus ID.

# 5B (fallback) $22 sweep to ECU 0x80 AND the VIP target:
  candidates:  22 00 12 · 22 00 18 · 22 F1 18 · 22 F1 12 · 22 00 02
  block:       22 F1 00 … 22 F1 FF     (the ticket DID = the one whose payload flips 0↔nonzero with SBI)
```

**Sweep note** (for `mdi2_client`, Python): iterate single DIDs (`for lo in range(0x100):
send(bytes([0x22,0xF1,lo]))`, then `hi in (0x00,0x01,0x02)`); many ECUs reject multi-DID
`$22`, so one DID per request, read response, compare SBI-set vs cleared. Space `$27`
retries — attempt limit + lockout (`7F 27 37`).
