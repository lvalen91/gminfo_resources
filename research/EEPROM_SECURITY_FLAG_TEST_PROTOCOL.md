# EEPROM Security-Flag Test Protocol — `$27` Cal/Diag Gate

**Target flags:** `0x04A0`, `0x04C0`, `0x0A40`, `0x0BE0`
**Objective:** identify which flag (if any) governs the UDS `$27` SecurityAccess gate for
calibration/diagnostic mode, or enables hidden features — at minimum physical cost.
**Author context:** `$27` = ISO 14229 SecurityAccess (seed/key). Treat this as an automotive /
RF-module EEPROM where the flag block is read at boot and shadowed to RAM.

---

## 0. Governing principle: do NOT desolder first

Each physical reprogram cycle is expensive and adds bricking risk. The protocol is tiered so
that **most of the answer is obtained with zero destructive actions**, and physical flips are
ordered lowest-risk-first and stopped the moment the gate opens.

**Cost/risk ladder (always climb from the top):**

| Tier | Action | Cost | Reversible? |
|------|--------|------|-------------|
| T0 | Static analysis: xref each address in the firmware image | free | yes |
| T1 | Dynamic: read live EEPROM + patch the **RAM shadow** via debugger | low | yes (reboot) |
| T2 | In-circuit reprogram (I2C/SPI clip, no desolder) | medium | yes (rewrite) |
| T3 | Desolder / socket / reprogram / resolder | high | yes but risky |

Only escalate a given flag to T2/T3 if T0–T1 are inconclusive **and** that flag is still a live
hypothesis. In practice T0 often answers question (a) outright.

---

## 1. Hypothesis per flag

These are priors from address placement and typical EEPROM layout; **confirm each in T0 before
trusting it.** Rationale: `0x04A0`/`0x04C0` sit adjacent in an early, tightly-packed config block
(classic security/config descriptor region); `0x0A40` and `0x0BE0` sit in later, sparser regions
more typical of feature/calibration tables.

| Flag | Region | Likely role | Confidence | Bricking vector if wrong |
|------|--------|-------------|-----------|--------------------------|
| **0x04A0** | early config block | **Primary suspect for the `$27` security-level / seed-key algorithm selector or "security disabled" flag.** Adjacent to 0x04C0 suggests a paired {mode, level} descriptor. | Medium-High | May gate the diagnostic session itself — low brick risk, high info value |
| **0x04C0** | early config block, paired with 0x04A0 | Likely the **companion**: access-level mask, or the "unlock persists / dealer mode" bit. Could also be the seed-key **variant index**. | Medium | Low brick risk |
| **0x0A40** | mid/feature region | **Hidden-feature enable bitfield** (cal menu, extended diag PIDs, engineering mode) — *not* the security gate itself, but what the gate protects. | Medium | Could enable an unstable feature path; recoverable |
| **0x0BE0** | late region, near typical checksum/lock tail | **Highest danger.** Late-region flags are often the **manufacturing lock / debug-interface disable / EEPROM-write-protect** bit. Flipping this could lock JTAG/SWD or set OTP-like protection. | Low that it's the `$27` gate; High that it's dangerous | **CATASTROPHIC** — may disable the very interface you use to recover |

**Answer to (a) — most likely to govern cal-security: `0x04A0`**, with `0x04C0` as its paired
companion. `0x0A40` most likely *enables* hidden features rather than gating them. `0x0BE0` is
the least likely gate and the most likely brick — test it last or never.

---

## 2. Tier 0 — Static analysis (do this first, it may finish the job)

For each of the four addresses, in the extracted firmware / bootloader image:

1. **Find cross-references (xrefs)** to each EEPROM offset (or its RAM-shadow address).
   - Locate the boot-time EEPROM read/copy routine; map EEPROM offset → RAM shadow address.
   - Search the disassembly for loads from that shadow address.
2. **Classify each xref site:**
   - Compared inside the **`$27` handler** (seed/key, `requestSeed`/`sendKey`, `0x27` case in the
     UDS service dispatcher) → **strong evidence this flag is the gate.**
   - Read by a **feature/menu dispatcher** → hidden-feature enable.
   - Read by the **boot/checksum/lock** routine → dangerous lock bit; do not flip casually.
   - No xref at all → inert / mirror; deprioritize.
3. **Record the tested polarity:** what value does the code branch on (`== 0`, `!= 0xFF`, bit
   mask)? This tells you *which way* to flip and avoids a wasted cycle.
4. **Check for checksum coverage:** determine whether each address falls inside a
   checksummed/CRC'd region. If yes, any flip must be followed by **recomputing and rewriting the
   checksum**, or the module will reject the image at boot. This is the #1 cause of self-inflicted
   bricks.

**Exit criteria for T0:** if exactly one flag is read inside the `$27` handler, you have your
answer for (a) with high confidence and can go straight to T1 to validate it — skip the others.

---

## 3. Tier 1 — Dynamic RAM-shadow patch (reversible, no reprogram)

Most modules copy the EEPROM config block into RAM at boot and read from RAM thereafter. If so,
you can test a flag **without touching the EEPROM at all**:

1. Attach debugger (JTAG/SWD/BDM). Confirm you have halt + memory-write.
2. Dump the live RAM shadow; confirm it matches the EEPROM offsets (byte-for-byte).
3. **Patch the shadow byte** for the candidate flag in RAM, resume, and exercise the gate (below).
4. If behavior changes → you have functional proof with a fully reversible action (power-cycle
   restores the original EEPROM value). Only then consider making it persistent via T2.

This tier lets you test **all four flags and both polarities in one sitting** with zero
destructive cost. **Do as much of the matrix here as the hardware allows.**

> Note: RAM-shadow patching bypasses EEPROM checksums, so it validates *function* but not
> *persistence*. A flag that works in RAM but is protected by a boot checksum in EEPROM will need
> the checksum recomputed when you make it persistent — flag this now.

---

## 4. Physical test order (T2/T3) — lowest risk first

Only for flags still ambiguous after T0/T1, and only if persistence must be proven. **Prefer
in-circuit (T2) over desolder (T3) always.**

**Order:**

1. **`0x04A0`** — highest info-per-risk. Primary gate suspect, early region, low brick vector.
2. **`0x04C0`** — its companion; test only if 0x04A0 alone doesn't open the gate (may need both).
3. **`0x0A40`** — feature-enable; test after the gate question is settled, to enumerate what
   opens up. Moderate risk (may boot into an unstable feature path).
4. **`0x0BE0`** — **LAST, and only with a proven recovery path.** Assume it can disable your
   debug/programming interface. Before flipping: verify you can reflash via an *independent*
   channel (external programmer on a desoldered/socketed chip), and have a known-good full image
   staged. If T0 shows it's a lock/write-protect bit, **do not flip it at all** — it answers
   nothing about `$27` and can permanently lock the part.

**One variable per cycle.** Never flip two flags in the same reprogram unless T0 proved they are
a required pair (0x04A0 + 0x04C0). Flip → observe → decide → revert-or-keep before touching the
next.

---

## 5. What to observe after each flip

Capture a **baseline** of all of these *before* the first change, so every observation is a diff.

**A. Diagnostic / `$27` gate status (the primary signal):**
- Send UDS `$10 03` (extended diagnostic session), then `$27 01` (requestSeed).
- Baseline (secured): non-zero seed returned, or `$27` returns NRC `0x33` (securityAccessDenied)
  / requires a valid key.
- **Gate opened** = one of: seed returns all-zero (security effectively disabled), `$27 02`
  (sendKey) accepted with a null/trivial key, session escalates without a key, or the calibration
  service (`$2E`/`$3D`/routine `$31`) becomes accessible without prior unlock.
- Also probe cal-adjacent services: `$22`/`$2E` on protected DIDs, `$31` cal routines.

**B. Boot / log output:**
- Serial/UART boot log, debug console, or diagnostic trouble codes (`$19` readDTC).
- Watch for: new "engineering mode" / "dealer mode" / "cal enabled" banners; **or** checksum/
  config-error messages (means you flipped inside a checksummed region and didn't fix the CRC).
- Confirm the module still completes boot to normal operation (no boot loop).

**C. Behavior / feature changes:**
- New menu items, unlocked PIDs/DIDs, cal screens, RF/TX test modes, hidden UDS routines.
- Regression check: verify **normal function is unimpaired** (the flag may enable a feature *and*
  break something else).

**D. Interface health (critical after 0x0BE0):**
- Immediately re-verify debugger attach and EEPROM read-back still work. If the programming
  interface is gone, execute rollback (Section 6) before anything else.

**Log every cycle** in a table: `flag | old→new byte | checksum fixed? | seed result | boot log
delta | features | interface OK?`.

---

## 6. Backup / rollback procedure

**Before the first physical change:**
1. **Full-image golden backup:** read the *entire* EEPROM (not just the four bytes) at least
   **twice**, and verify the two dumps are byte-identical. Store off-device with a checksum
   (sha256) recorded. This is your ground truth.
2. Photograph the board (component orientation, pin 1, decoupling caps) before any desolder.
3. Record the exact programmer settings (chip model, voltage, I2C/SPI address, page size) that
   produced a verified read — you'll need identical settings to write back.
4. If the chip is soldered and you must desolder, **install a socket** (or use an in-circuit
   clip) so subsequent cycles don't require reflow.

**After each flip:**
- Read back the whole chip and diff against the intended image (confirm *only* the target byte(s)
  changed and the write didn't corrupt neighbors or the checksum).

**Rollback (revert a change):**
1. Re-flash the **golden full-image backup** (not a byte patch — the whole image, so any
   checksum/wear-leveling side effects are also reverted).
2. Verify read-back == golden sha256.
3. Power-cycle; confirm boot log + normal function + `$27` back to baseline (secured) behavior.

**If the interface is bricked** (e.g., after 0x0BE0 disabled debug/write-protect):
1. Desolder the chip and program it on a **standalone external programmer** with the golden image
   (this is why the golden image and a socket matter).
2. If an OTP/permanent-lock bit was set and cannot be cleared, the chip is scrap — replace with a
   blank flashed to the golden image. (This is the scenario the ordering is designed to avoid.)

---

## 7. Decision tree — when to stop

```
START
 └─ T0 static xref analysis
     ├─ Exactly one flag read inside the $27 handler?
     │     └─ YES → that is the gate (answer a). Go to T1 to confirm, then STOP.
     ├─ A flag read only by boot/checksum/lock routine (esp. 0x0BE0)?
     │     └─ Mark DANGEROUS. Exclude from casual testing. Do NOT flip to chase $27.
     └─ Ambiguous / multiple candidates → continue to T1.

 T1 RAM-shadow patch (reversible, test the whole matrix here)
     ├─ Patching flag X opens the $27 gate?
     │     └─ YES → functional answer found.
     │            ├─ Persistence needed? → escalate ONLY flag X to T2. Else STOP.
     │            └─ If X worked only paired with 0x04C0, treat {0x04A0,0x04C0} as the pair.
     ├─ A flag toggles hidden features but not the gate?
     │     └─ Record as feature-enable (likely 0x0A40). Not the answer to (a).
     └─ No flag changes anything in RAM → gate is not a simple EEPROM flag
           (may be code/OTP/fuse-based). STOP escalation; re-scope.

 T2 in-circuit reprogram (only surviving candidates, order: 04A0 → 04C0 → 0A40 → 0BE0)
     ├─ After each single flip: run Section-5 observations.
     ├─ Gate opens AND interface healthy AND normal function intact?
     │     └─ SUCCESS. Rollback all other experiments to golden. STOP.
     ├─ Gate opens but something broke → note trade-off; rollback; STOP or refine.
     └─ No effect → rollback, advance to next flag.

 0x0BE0 gate (before ever flipping it)
     ├─ Independent recovery path proven (external programmer + golden image staged)? 
     │     ├─ NO  → DO NOT FLIP. Stop.
     │     └─ YES → flip as the final experiment only; re-verify interface immediately after.

 GLOBAL STOP CONDITIONS
     • The $27 gate opened and the module still boots/functions → done; revert everything else.
     • All four flags exhausted with no gate effect → conclude the $27 gate is not EEPROM-flag
       governed; pivot to firmware/OTP/fuse investigation.
     • Any unrecoverable interface loss → stop, execute external-programmer recovery.
```

---

## 8. Summary answers

- **(a) Most likely gate:** `0x04A0` (early config block, adjacent to its companion `0x04C0`);
  confirm by static xref into the `$27` handler. `0x0A40` = hidden-feature enable, not the gate.
  `0x0BE0` = probable lock/write-protect, the dangerous outlier.
- **(b) Order:** T0 static → T1 RAM-shadow (all flags, reversible) → physical
  `0x04A0` → `0x04C0` → `0x0A40` → `0x0BE0` (last, gated on a proven recovery path).
- **(c) Observe:** `$27` seed/key response and cal-service access; boot/UART log deltas and
  checksum errors; new features + regression check; **interface health** after each flip.
- **(d) Rollback:** verified full-image golden backup (x2, sha256), socket the chip, revert by
  re-flashing the whole golden image; external-programmer recovery if the interface is lost.
- **Biggest self-brick risk:** flipping a byte inside a checksummed region without recomputing the
  checksum — always resolve checksum coverage in T0.
```
