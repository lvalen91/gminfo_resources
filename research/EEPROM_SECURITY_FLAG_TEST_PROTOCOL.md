# EEPROM Security-Flag Test Protocol — `$27` Cal/Diag Gate

**Target flags:** `0x04A0`, `0x04C0`, `0x0A40`, `0x0BE0`
**Objective:** identify which flag (if any) governs the UDS `$27` SecurityAccess gate for
calibration/diagnostic mode, or enables hidden features — at minimum physical cost.
**Author context:** `$27` = ISO 14229 SecurityAccess (seed/key). Treat this as an automotive /
RF-module EEPROM where the flag block is read at boot and shadowed to RAM.

---

## ⚠ UPDATE 2026-08-26 — RETARGETED after full-coverage RE + owner witness

The original target flags (`0x04A0/0x04C0/0x0A40/0x0BE0`) are **REFUTED** as security flags: full-coverage
RH850 disassembly (VIP_APP + VIP_BOOT) found **no code evidence** for them — their "xref counts" were grep
noise and the "IPC Security" naming was a misread of the `[IPC_S]` *serial-transport* log tag (see
`EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md` §0–§0.8). **Do not spend physical cycles on those four.** Confirmed /
high-value bench targets instead:

| Target | Bytes | Effect (evidence) |
|---|---|---|
| **ADB (SBI)** | `0x0441=FF` **AND** `0x0A80=FF` | **Owner-confirmed, 3-yr reproducible.** Both `00→FF` enables ADB; revert disables. Pre-Y181 stock ships `0x0A80` already `FF` (flip only `0x0441`); **Y181 needs both.** Framing `0x0440/0x0442` NOT required; no CRC recompute needed (the 1-byte `stock_modified` edit worked). |
| **Trim/theme** | `0x0AA0` / `0x0AE5` (candidate, UNCONFIRMED) | trim cal → boot animation + AAOS theme (HC=`0xF0`, LTZ=`0xC3`, stock=`0x69`; not the raw enum — VIP-translated). |

**Static RE is exhausted** (VIP_APP + VIP_BOOT + GHS HOSTOS all at high coverage): the EEPROM read, the SBI
consumer, and the trim translation live behind computed-jump dispatch + an externally-triggered CAN/DoIP `$27`
diagnostic + guest `/data` runtime state — none statically followable. **The bench is now the arbiter;** this
protocol is the path.

### ADB test (validate the minimal set + scope the effect)
1. Golden-dump the full 8 KB (×2, sha256) per §6.
2. Set `0x0441=0xFF` (and `0x0A80=0xFF` on Y181). Reboot.
3. Observe: `adb devices` (authorizes without the GM key?), shell context (`id`, `getenforce` — expect
   `u:r:shell:s0`, enforcing), whether `$27` SecurityAccess over CAN/DoIP now succeeds, and diff
   `/data/gm_adb/{policy,password}` before/after. **Likely mechanism:** SBI → trivial `$27` seed → `$27`
   passes → a diagnostic enables adb (runtime, `/data`).
4. **Isolate:** flip `0x0441` alone vs. `0x0441`+`0x0A80` — confirm the minimal set on THIS build.
5. **Scope:** does anything **beyond** ADB change? (the original open question).

### Trim test (find the real trim byte)
1. From a stock dump set `0x0AA0` (then `0x0AE5`) to HC `0xF0`. Reboot.
2. Observe the host-verified pipeline: `adb shell getprop persist.sys.anim.flavor` (index changes?),
   `adb logcat | grep -i AnimFlavor` (the live `GMTrim: %d, GMModel: %d, GMBrand: %d -> AnimFlavor:%d` line —
   does GMTrim flip?), and the actual boot animation/theme.
3. If neither moves it, bisect the **LTZ-vs-stock 110-byte diff** (the clean pair) watching that same
   `AnimFlavor` log line — it's the direct probe for any trim/model/brand byte.

### Observation harness (extends §5)
- **ADB:** `adb devices`, `id`, `getenforce`, `/data/gm_adb/{policy,password}` diff, `$27` seed result.
- **Trim:** `getprop persist.sys.anim.flavor`, `logcat | grep AnimFlavor`, `cmd overlay list`, the animation.
- Existing §5 `$27`/UDS probes remain valid — the `$27` seed result is the shared signal for the SBI hypothesis.

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

---

## UDS FRAME LIST — the 5 SBI/`$27`/DID bench tests (2026-08-26)

Target ECU = **`0x80`** (CSM). Portable part = the **UDS PDU**; the `gm_dps/misc/Aug24_session/ecu80_READ.Txt`
on-wire form wraps it as `0E F5 0A 80 <UDS>` (request) / `25 80 0E F5 <UDS>` (response) — DPS/MDI2 GCI framing.
Send the UDS PDU; the tool (DPS or `mdi2_client`) adds the wrapper. Keep `3E 80` (TesterPresent, suppressed)
flowing every ~2 s or the session/unlock drops.

**Preamble**
```
10 03        → 50 03 00 64 01 F4     extendedDiagnosticSession
3E 80                                 TesterPresent (suppressResponse) — keep-alive
```

### Test 1 — MEC read, SBI set vs cleared (live re-confirm of §0.14)
```
10 03
22 F1 A0   → 62 F1 A0 FF   SBI-set (MEC=255 → adb cert bypassed)
           → 62 F1 A0 00   stock   (MEC=0   → adb cert required)
22 F1 90   → 62 F1 90 <17 ASCII VIN>   (sanity)
NRC: 7F 22 31 requestOutOfRange · 7F 22 33 securityAccessDenied
```

### Test 2 — `$27` L01 key-accept ("any/stub key?")
```
10 03
27 01      → 67 01 FF FF … FF   seed (all-FF expected; COUNT bytes = seed length, ~31 in sample)
27 02 <key>                     sendKey L01; key LENGTH = seed length; try (a) all-FF then (b) all-00
           → 67 02              KEY ACCEPTED ⇒ stub/any-key unlock proven ✅
           → 7F 27 35           invalidKey ⇒ real key required
NRC: 7F 27 36 exceededAttempts · 7F 27 37 timeDelayNotExpired · 7F 27 24 sequenceError
```

### Test 3 — higher levels all-FF? (SecurityLevel value = `$27` requestSeed subfunction; sendKey = +1)
```
27 01 Service(1)            27 03 AssemblyPlant(3)      27 05 OTA(5)
27 09 Engineering(9)        27 0B RemoteDiagnostics(11) 27 0D SupplierSecAccess(13)
27 11 ExtendedReflash(17)   27 13 ExtendedAssembly(19)  27 15 ExtendedOTA(21)   27 5F EndOfLife(95)
Each → 67 <sf> <seed>. all-FF seed ⇒ level trivialized (run Test-2 sendKey on it).
NRC 7F 27 12 subFunctionNotSupported = level absent.
```

### Test 4 — `SECURE_UNLOCK_LEVEL` over DoIP (CAN↔Ethernet state-sharing) — with DID sweep
Transport = **DoIP (ISO 13400) over T1 (100BASE-T1)**. DoIP header = `02 FD <ptype:2> <len:4> <payload>`.
```
# 4a. Discover the CSM DoIP logical address (LA)  — UDP 13400
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

**Sweep note (for `mdi2_client`, Python):** iterate single DIDs (`for lo in range(0x100): send(bytes([0x22,0xF1,lo]))`,
then `hi in (0x00,0x01,0x02)`); many ECUs reject multi-DID `$22`, so one DID per request, read response, compare
SBI-set vs cleared. Space `$27` retries — attempt limit + lockout (`7F 27 37`).
