# Ethernet SecurityAccess bench validation

**Corrected 2026-11-14.** The original question is answered for the owner's
SBI-modified Y175 bench radio: the direct T1 `diagnosticsd` endpoint returned
31 all-FF seed bytes and accepted the documented 12-zero-byte response with
`67 02` after extended-session entry. Programming writes were not attempted.

The [owning diagnostic reference](../diagnostics/ethernet_uds_diagnosticsd.md#live-t1-securityaccess-correction-2026-11-14)
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
See the [ECUReset follow-up](../diagnostics/ethernet_uds_diagnosticsd.md#live-t1-ecureset-validation-2026-11-14).
The SecurityAccess result is therefore not evidence of a working ECUReset.


## Later read-sweep follow-up (2026-11-14)

The separate [bounded read sweep](../diagnostics/ethernet_uds_diagnosticsd.md#bounded-read-only-sweep-and-uart-reset-follow-up-2026-11-14)
also validated seed/key pairs 09/0A and 0B/0C with the same 31-FF/12-zero
format. F0A7 became readable, but a one-byte service-23 memory request still
ended with NRC 25 after passing the earlier level-1 security denial. Service-38
ReadDir and ReadFile probes gave NRC 11. A UART-instrumented reset repeat again
gave NRC 25 without an observed Android reboot or selected reset event on UART.
These are per-service outcomes, not a universal authorization or memory-access
grant. The original level-1 recipe above remains the validated basic sequence.
