# Gated live calibration write

`mdi2.cli write` programs the stock GM-signed LTZ package into the bench radio (ECU `0x80`) over
the MDI2 D-PDU tunnel. Placeholders: `<LTZ_FOLDER>`, `<EXPECTED_VIN>`, `<MDI2_SERIAL>`,
`<MDI2_IP>`. Access and recovery of the adapter itself: [ACCESS.md](ACCESS.md).

## Status

**Validated on the bench.** Multiple stock LTZ writes (High Country -> LTZ) have been completed
with this tool. The first documented run (2026-11-10) wrote 14 containers, finalized, reset once,
and post-reset per-slot metadata readback matched the package (F182 profile flipped, F199 date,
all 14 F0F0 slots present, VIN intact). Validation is still scoped:

- Stock GM-signed packages only. Modified packages returned `7F 36 72`, a general programming
  failure that does not isolate its cause. Keep the hash gate intact.
- SecurityAccess used the SBI-flipped module's all-FF seed path. A real-seed AES-CMAC handshake
  is unverified on hardware; the CLI has no CMAC key option.
- Metadata readback is not a full payload readback, and success does not establish arbitrary
  radio compatibility.
- Every write needs explicit authorization for that radio, package, and VIN. Access and
  `identify` do not authorize a write.

**Recovery validated 2026-11-14:** the owner's A11, previously cleared by UDS
0249 and booting into `NoCalibration`, was restored with the same pinned stock
LTZ package. All 14 slots and the supplied VIN matched post-reset reads; the
owner confirmed normal radio/display operation. This used a narrowly scoped
in-memory cleared-profile exception and VIN restoration, described below;
the ordinary CLI source gate remains unchanged.

## Gates (all must pass, fail-closed)

1. All 14 containers (slots 02-0F) match the pinned SHA-256 hashes in
   `mdi2/ltz_reference_manifest.py`.
2. Source F182 metadata is a complete, documented **LTZ** or **High Country** profile. Unknown,
   mixed, or incomplete profiles are rejected (`mdi2/ltz_preflight.py`).
3. `<EXPECTED_VIN>` is exactly 17 characters and matches the radio's VIN.
4. BCM (ECU `0x40`) DID F085 reads the documented OFF value `00`. A lit display or service mode
   `02` does not substitute.
5. One battery-voltage sample within **12.000-30.000 V**. 30 V is a rejection boundary, not a
   recommendation, and one sample does not prove stable programming power; use stable power.

## Plan vs confirm

Argument order is **FOLDER, EXPECTED_VIN, optional SERIAL**. Older examples reversing VIN and
serial are wrong. The serial identifies the MDI2, not the radio or vehicle.

```
# dry run: reads hardware, validates gates, no programming, no reset
./.venv/bin/python -B -m mdi2.cli write "<LTZ_FOLDER>" "<EXPECTED_VIN>"
./.venv/bin/python -B -m mdi2.cli write "<LTZ_FOLDER>" "<EXPECTED_VIN>" <MDI2_SERIAL> --host <MDI2_IP>

# real programming, only when intentionally authorized
./.venv/bin/python -B -m mdi2.cli write "<LTZ_FOLDER>" "<EXPECTED_VIN>" --confirm
```

The dry run prints `PLAN: 14 pinned LTZ slots validated; module VIN matches; source <profile>;
BCM power mode OFF; battery <V>` and may sample voltage but never resets or programs. Run it and
read the plan before `--confirm`.

## Sequence with `--confirm`

Matches the decoded stock SPS transcript:

1. Fresh acknowledged PDU START; check BCM F085 and VIN; one voltage sample.
2. Extended session, DTC logging off (`85 02`), normal comms off (`28 03`), SecurityAccess,
   pre-programming routine `31 01 0249`, programming session.
3. Transfer the 14 containers; `22 F0F0` status readback.
4. Fresh finalization link (`22 F1B0`, `10 03`, SecurityAccess): `2E F198` fixed repair-shop id,
   `2E F199` current date, `31 01 039B` finalize, `2E F190 <VIN>`.
5. **One** hard reset `11 01` at finalization, then metadata readback (matching slots printed).

Stock SPS does **no** pre-reset. `--pre-reset` adds an extra `10 03`/SecurityAccess/`11 01` before
the write and is an **opt-in recovery fallback** for retrying a failed SPS-method write; do not
include it in routine instructions.

## Cleared A11 recovery 2026-11-14

The complete [A11 recovery record](../../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14)
owns the failure history, workarounds and UART boot evidence. Differences from
the normal CLI flow:

- UDS 0249 had left all 14 F182 calibration slots at base part **70008 / DLS
  00**. Each record was its slot byte followed by `00 01 11 78 30 30`.
  The standard LTZ/High Country source gate correctly rejected this profile.
  With explicit recovery authorization, a process-local classifier accepted
  only that exact complete cleared profile alongside the existing profiles.
  No client source or CLI option was changed; arbitrary mismatches were not
  accepted. The 14 pinned target hashes remained mandatory.
- F190 was **17 bytes of FF**, not a printable VIN. The first programming
  attempt stopped at `read identifiers`, with `transferred=0`; F198/F199 had
  valid lengths. After read-only diagnosis and an owner-supplied VIN, the
  recovery checked the erased/current VIN, source, BCM OFF and voltage,
  entered extended session, used the existing SecurityAccess helper, wrote
  `2E F190 <EXPECTED_VIN>` and verified F190 before planning again. A different
  existing VIN would have stopped this recovery.
- The fresh plan passed at **12.359 V**. The main
  `write_ltz_calibration(..., confirmed=True, pre_reset=False)` then ran the
  existing SPS transfer/finalization sequence with the narrow source
  classifier and all other checks intact. No pre-reset or blind retry was
  used. This recovery is not provided by `scripts/calibrate_ltz.sh` or by an
  additional `--confirm` flag.

Post-reset slots **02–0F** and the supplied VIN matched; F0F1 and F0F2 were
`0000`. The transaction's `RESET_ACCEPTED_NOT_VERIFIED` label preceded the
live writer's successful post-reset readback. Later RH850 boots reported
calibration state `2`, reached HMI ready / Accessory, and contained no
`NoCalibration` in those boot sections; the owner confirmed the radio was
operational. ADB and final MEC were not rechecked.

## Failure handling

Do not blindly retry. On a partial write run `recover` (without `--force-default-session` first),
inspect the failure phase, and see ACCESS.md section 8 for NRC 35 / `7F 36 72` and gate errors.
A malformed frame or ambiguous response poisons the session and closes the tunnel; rearm only
after 9052 health is confirmed. Do not create durable raw logs of write runs; the bench wrapper
`run_cal_write.py` (`--go --log`) can capture private infrastructure, so prefer this CLI.
