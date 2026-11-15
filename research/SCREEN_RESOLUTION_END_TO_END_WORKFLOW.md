# Custom SCREEN_RESOLUTION calibration status and evidence requirements

**Target:** Silverado gminfo37 / Y17x / Y181/B, A11 CSM radio `0x80`.
**Corrected 2026-11-11:** the former runnable workflow assumed unsigned calibration containers,
guessed framing/offsets, a four-byte dummy key and a required level-3 unlock. It was not a
validated programming procedure. The stock write is now demonstrated, but a custom
`SCREEN_RESOLUTION` write is not. The
[central reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md) owns the reconciled seed/key,
signing and acceptance evidence.

## Calibration identity

The older recorded `CalSets.db` row is a native SQLite integer enum, not a binary calibration blob:

| Field | Value |
|---|---|
| CalName | `SCREEN_RESOLUTION` |
| CalID | `__-Jk4IQIEeWHkIX-EVZFdA` |
| CalDef | `GIS738_RVCVIDEOROBUSTNESSREQUIREMENT`, version 7 |
| CalType | 4, enumeration |
| Older recorded CalValue | 2 |
| Y181B exported CalValue, 2026-11-12 | **4 (`SIZE_2400_BY_960`), `OverRiden=8`** |
| EnumID | `_PWvKYIQHEeWHkIX-EVZFdA` |

Defined values: `0=800x480`, `1=1280x720`, `2=1280x768`, `3=1920x1080`, `4=2400x960`.
The newer value is independently read from both byte-identical recovery-export
databases; see the [Y181B baseline](../platform/vehicle_config.md#y181b-exported-calibration-baseline-2026-11-12).
It does not establish how the value changed or a successful custom write.
The enum's presence establishes an available data representation, not tested panel behavior.
Do not treat changing this cell as equivalent to selecting a physical display timing or
expanding every application. See
[`gmsystemui_app_capability_gating.md`](../platform/gmsystemui_app_capability_gating.md)
for the separate UI capability checks.

## Proven stock programming path

The documented 2026-11-10 stock LTZ write performed level-1 SecurityAccess (`27 01/02`),
pre-programming routine `0249`, programming session `10 02`, 14 container downloads,
status readback, a fresh finalization link, metadata/finalization and reset. With the SBI
bypass active, the radio returned 31 all-FF seed bytes and accepted 12 zero key bytes.
A separate level-3 unlock is not established as a requirement for this stock sequence.
The non-degenerate seed/key implementation remains unverified on hardware.

Use the evidence and implementation in the [MDI2 client](../mdi2_client/README.md) and the
[decoded SPS sequence](/Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/SPS_RECAL_UDS_SEQUENCE_AUG2026.md).
The original guessed DoIP target, four-byte dummy key, arbitrary blob offsets and incomplete
programming scripts have been removed from this page because they were not the successful
client or a validated custom-calibration method.

## The actual signed calibration container

All 14 inspected stock CSM containers have independently verified RSA-2048 PKCS#1 v1.5/SHA-256
signatures over `[2:600]`, using the signer modulus at `[88:344]` and signature at `[600:856]`.
The digest at `[30:62]` equals `SHA256(container[858:])`. A production-CA signature at
`[344:600]` authenticates the 282-byte custom signer record `[62:344]`.

Changing the payload and recomputing the digest invalidates the existing signed header.
The former recipe of recomputing a checksum and SHA-256 and then flashing was not a working
custom-package method. The exact UDS runtime signature/root verifier remains untraced;
verified package cryptography does not by itself identify the failure stage on the ECU.

The reported 2026-11-10 modified-package attempts failed with `7F 36 72` despite a recomputed
payload digest. Earlier source notes alternately blamed transport checksums and RSA; that
cause was not isolated. Failed attempts removed calibration slots and required stock LTZ
recovery. No successful custom `SCREEN_RESOLUTION` write or changed display behavior is
established by these results.

## Local overrides and acceptance criteria

A direct database edit or a local `*.calovride` application is a separate path, requiring
appropriate filesystem permissions and SELinux access. uid-2000 ADB alone does not establish
those privileges. **Updated 2026-11-15:** targeted Y175 main/parser analysis
confirms the compiled plaintext XML loader. That does not prove live shell
access, safe per-item rollback or successful deployment; see the
[owning loader trace](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#3e-standalone-xml-loader-runtime-controls-and-visual-test-limits-2026-11-15).
A custom XML file is not a signed CSM container, and the Signature-Bypass Ticket is not a
validated way to make either path accept a modified payload.

A future custom-write result needs a build-pinned source package, a verified active loader,
positive acknowledgements through finalization, post-reset calibration readback, and measured
display behavior. Stock-package metadata matching does not prove every payload byte or the
intended visual result. No further hardware operation is implied by this documentation.

## Source documents

- [Seed key and signing reference](GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- [Type4 workflow and calibration glossary](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md).
- [Checksum/database details](CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md).
- [CSM container structural analysis](/Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/A11_CALIBRATION_FILES_COMPLETE_ANALYSIS_AUG2026.md).
- [MDI2 transport and stock write](../mdi2_client/README.md).

**Correction reason/date (2026-11-11):** independent signature checks falsified the unsigned-
container premise; reported stock success does not validate modified content, and NRC `0x72`
does not isolate the rejection cause. This replaces the unverified executable recipe in place.
