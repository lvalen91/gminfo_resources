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

## Failure handling

Do not blindly retry. On a partial write run `recover` (without `--force-default-session` first),
inspect the failure phase, and see ACCESS.md section 8 for NRC 35 / `7F 36 72` and gate errors.
A malformed frame or ambiguous response poisons the session and closes the tunnel; rearm only
after 9052 health is confirmed. Do not create durable raw logs of write runs; the bench wrapper
`run_cal_write.py` (`--go --log`) can capture private infrastructure, so prefer this CLI.
