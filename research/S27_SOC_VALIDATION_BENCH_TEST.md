# Ethernet SecurityAccess bench validation

**Corrected 2026-11-14.** The original question is answered for the owner's
SBI-modified Y175 bench radio: the direct T1 `diagnosticsd` endpoint returned
31 all-FF seed bytes and accepted the documented 12-zero-byte response with
`67 02` after extended-session entry. Programming writes were not attempted.

The [owning diagnostic reference](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14)
contains the live target/build scope, Y181B static addresses, negative controls,
and limits. Keep that reference authoritative rather than inferring further
privileges from this procedure.

## Correct transport and addressing

This endpoint speaks custom GM Ethernet diagnostics over TCP port 49156,
not DoIP and not CAN ISO-TP:

```
[SRC : 2 bytes BE][TGT : 2 bytes BE][LEN : 4 bytes BE][UDS payload LEN bytes]
```

Use tester `0x00F4`, target `0x0084`. Tester `0x00F5` also passed basic live
reads and TesterPresent, but the complete grant below was tested with F4.
The old `0x0FA0` tester was wrong for this endpoint and produced NRC `0x10`.
The Y181B address handler checks tester/target fields; target validation is
not universally absent.

Connect to `<RADIO_VLAN4_IP>:49156` from a permitted `<TESTER_VLAN4_IP>` on a
T1-connected VLAN 4 interface. These placeholders mean the radio's VLAN 4
address and one source identity admitted by its shipped firewall. Do not
substitute the radio's VLAN 5 address or an assumed GHS peer: the external
listener and admission policy were verified on VLAN 4. There is no evidence
that a historical GHS candidate is an interchangeable diagnostic server.

## Validated sequence

Serialize requests on one connection and keep the same logical tester ID:

| Step | Request | Expected result observed on the SBI-modified bench |
|---|---|---|
| Optional software read | `22 F1 81` | `62 F1 81 <software data>` |
| Optional liveness check | `3E 00` | `7E 00` |
| Extended session | `10 03` | `50 03 00 64 01 F2` |
| Level-1 seed | `27 01` | `67 01` + exactly 31 bytes of `FF` |
| Documented degenerate response | `27 02` + exactly 12 zero bytes | `67 02` |
| Restore default session | `10 01` | `50 01 00 64 01 F2` |

For example, the extended-session request frame is:

```
00 F4 00 84 00 00 00 02 10 03
```

The key request's UDS length is **14**, not 33: two service/subfunction bytes
plus twelve zero bytes. The seed and submitted response have different
lengths. The obsolete equal-to-seed-length dummy-key script has been removed.
Do not use it against a non-degenerate seed. No alternative key content or
length was tested by this Ethernet validation.

Read exactly eight header bytes, parse the declared length, then read the
entire response payload. `7F <SID> 78` means response pending: continue waiting
for the final matching SID instead of sending the next request. Also account
for unsolicited notifications. Advancing after a pending frame misaligns the
request/response interpretation. Bound response lengths and overall wait time
in a client implementation.

Keep the connection for the exchange, but do not infer that session state is
purely per connection: the static service tracks a shared active tester and
session. Explicitly restore default session even if a later operation fails;
connection closure alone was not validated as restoration.

## Interpret failures at the correct layer

- `7F <SID> 10`: generic rejection. The invalid `0x0FA0` tester caused this
  response; it does not by itself prove SBI is inactive, require a controlling
  app, identify a missing registration step, or establish a universal lock.
- `7F 27 7F`: SecurityAccess is not supported in the active session. This was
  observed with a valid tester in default session; the tested successful
  predecessor is extended-session entry `10 03`.
- `7F 22 31`: the requested DID is out of range. Observed for F186, while F181
  returned software data. Do not treat it as denial of all DID reads.
- A seed of a different length or content is outside this validated degenerate
  exchange. No real seed-to-key derivation or arbitrary-key acceptance was
  demonstrated.

## What the result proves

It proves a level-1 SecurityAccess grant over the direct T1 custom-TCP path
for this exact tester, session and response. The MDI2/CAN evidence independently
records the same 31-FF/12-zero exchange. The service IDs overlap because both
carry UDS; their transport headers and gateway routing are different.

It does **not** prove programming-session entry (`10 02`), arbitrary calibration
or partition writes, acceptance of edited/signed containers, signature bypass,
Android UID 0, GHS access, the key-compare component's location, or an exact
OBD connector → gateway → A11 forwarding chain. Refer to the
[seed/key and signing reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md)
for the separate signing gates. No firmware writes, programming routines or
ECU reset was sent during the seed/key validation above. A separate subsequent
T1 hard-reset test returned pending replies followed by `7F 11 25` at about
30 seconds, without an observed Android reboot; default session was restored.
See the [ECUReset follow-up](../diagnostics/diagnosticsd_security_access.md#live-t1-ecureset-validation-2026-11-14).
The SecurityAccess result is therefore not evidence of a working ECUReset.


## Later read-sweep follow-up (2026-11-14)

The separate [bounded read sweep](../diagnostics/diagnosticsd_dids_and_dtc.md#bounded-read-only-sweep-and-uart-reset-follow-up-2026-11-14)
also validated seed/key pairs 09/0A and 0B/0C with the same 31-FF/12-zero
format. F0A7 became readable, but a one-byte service-23 memory request still
ended with NRC 25 after passing the earlier level-1 security denial. Service-38
ReadDir and ReadFile probes gave NRC 11. A UART-instrumented reset repeat again
gave NRC 25 without an observed Android reboot or selected reset event on UART.
These are per-service outcomes, not a universal authorization or memory-access
grant. The original level-1 recipe above remains the validated basic sequence.


**Extended enumeration, 2026-11-14:** the full 16-bit DID-number sweep at
level 09 returned 135 positives. Subsequent candidate-set tests validated
additional grants at levels 03, 05, 0D, 11, 13 and 15; only 09/0B/0D exposed
F0A7. Seed selector 5F ended in NRC 25. Programming session 02 returned NRC 22;
no programming transfer or calibration erase followed. The later 128-selector
DTC shape test produced indiscriminate empty/zero-filled positives, consistent
with the native stub rather than proof of an empty queried fault store. See
the [complete retained inventory](../diagnostics/diagnosticsd_dids_and_dtc.md#exhaustive-did-number-sweep-and-extended-enumeration-2026-11-14).

**Concurrent-observer correction (2026-11-14):** later USB-logcat plus UART
observations show wire SIDs 11 and 23 being converted to native
DIAG_UNKNOWN_SERVICE, followed by local request-ID-0 unsupported-response
construction and a 30-second NRC-25 timer result. The static native converter
map omits both SIDs. The earlier NRC 25 does not by itself prove an unavailable
VIP/GHS backend or that those components received the intended request. See the
[concurrent UART/logcat analysis](../diagnostics/diagnosticsd_protocol.md#concurrent-uart-and-usb-logcat-correlation-2026-11-14).

## Final controlled actions and MEC preservation (2026-11-14)

The later all-overrides clear was explicitly authorized and sent once as
31 01 02 49 after extended session / level-01 grant. It returned 71 01 02 49
at 0.126 seconds after one pending frame. Calserviced confirmed ALL OVERRIDES
CLEARED and created a persistent J5 indicator. Fourteen F182 module identities
changed to base part 70008 / DLS 00; total record count remained 28. MEC was
FF/255 before, immediately after, at three seconds and on a later read. No
MEC write/reset command was sent; no Android reboot occurred. Power-cycle
application remains for the owner's subsequent test. See the
[owning final-clear record](../diagnostics/diagnosticsd_routines_and_recovery.md#final-calibration-clear-completed-mec-preserved).

Other starts established working 03D8 control and 0248 audio reset; 0254
returned positive, including the documented empty-database success case.
Programming-session entry remained NRC 22 at levels 01/03/05 because its live
Java handler requires authenticated remote-programming-active state. The
root daemon could not be attached with LLDB (Operation not permitted), despite
a successful owned-UID-2000 control attachment. Both alternative Binder F181
reads were rejected by the protected permission gate. These are specific
limits, not failures of the validated synthetic SecurityAccess exchange.

**Post-power-cycle correction, 2026-11-14:** the owner subsequently rebooted
by removing/restoring power. RH850 entered `NoCalibration (0xe)` after the
startup fault timeout; the display reported bad/incomplete calibration.
T1 diagnostic reads still worked, MEC stayed FF, and all 14 cleared module
identities remained base 70008/00. USB ADB did not reappear. See the
[owning post-boot finding](../diagnostics/diagnosticsd_routines_and_recovery.md#owner-power-cycle-after-clear-nocalibration-fault-2026-11-14).

**Recovery completed, 2026-11-14:** the main MDI2 client restored the pinned
stock LTZ package to this cleared A11. The exact 70008/00 profile required a
one-time in-memory source exception; the erased VIN was restored from the
owner's supplied value before programming. All 14 slots and VIN matched
post-reset readback; F0F1/F0F2 were `0000`. Later UART boots reached HMI ready
with calibration state `2`, and the owner confirmed normal radio operation.
ADB and final MEC were not rechecked. See the
[completed MDI2 recovery](../diagnostics/diagnosticsd_routines_and_recovery.md#successful-mdi2-ltz-recovery-after-calibration-clear-2026-11-14).
