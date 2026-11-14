# GM Seed Key and Signing Trust

Updated 2026-11-11. Read fact blocks first; resolve source IDs as needed.

## Scope and evidence

Target: gminfo/Silverado Y17X.xx and Y181/B. New exact static proof is **Y181**, not automatically Y175/Y177/Y181B/all revisions. **CT5/EV only supply OTA certificate/key comparison**; exclude their seed, calibration, APK implementation, emulator behavior and live-security results as target evidence.

Evidence: **P**=original packets reassembled/decoded; **C**=offline original-artifact cryptography; **S**=exact-build code/bytecode; **B**=dated bench report, not repeated; **M**=documented model/secondary implementation; **?**=unresolved. No new live radio, EEPROM, or programming tests.

Keep separate: UDS access; EEPROM seed state; MEC/ADB certificate gate; ProtoKey IPC; SBAT ticket; APK signer identity; artifact trust; AVB/GHS/rollback. Do not infer a bypass of another gate without evidence. UDS response12B ≠ hypothesized AES secret16B; public-key verification ≠ private-key recovery. Diagnostic `$0000 Bypass Inactive` ≠ EEPROM SBI or signature ticket. [S1] [S2] [S3]

Privacy: retain protocol ECU addresses/frame indices; omit credentials/private infrastructure, device identifiers/actual ECUID, real seeds/responses, private-key material, personal certificate email, conversation pointers.

Notation: unprefixed UDS/NRC/DID/RID values are hex; lengths/counts/offsets/frames/streams/times are decimal; `0x` marks hex.

## SPS radio seed/key and calibration [P]

Primary capture [S4] — radio0x80, D-PDU command/event streams317/318, two normal NON-FF grants. Seed PDU33B=`67 01`+31B; submitted-key PDU14B=`27 02`+12B. Seed=16B stable ECUID+15B varying challenge. Prefix matches all3 radio DIDF0F3 identifiers; challenges and responses differ between grants. These observations reveal no secretK, scope, or complete derivation.

| Event | First frame | Time s | Second frame | Time s | UDS bytes |
|---|---:|---:|---:|---:|---:|
| `27 01` |25884|174.220294|29381|193.023240|2|
| `67 01 <ECUID16><challenge15>` |25889|174.231800|29386|193.040754|33|
| `27 02 <response12>` |25946|175.305778|29437|193.762523|14|
| `7F 27 78` pending |25951|175.405265|29442|193.869112|3|
| `67 02` grant |25952|175.440075|29443|193.904161|2|

Frames=completed reassembled messages; times=capture-relative seconds. NRC78 is pending **after key submission**, not invalidKey or pre-seed pending. Neither exchange has SecurityAccess NRC35/36/37.

Programming sequence [S5] [S6]:

- First grant→`31 01 0249` frame25954→`10 02` frame26015→14 RequestDownload/positive pairs,19 TransferData pairs,14 TransferExit pairs; last frame27239; requested total46,162B.
- Second grant follows transfers→F198 frame29445→F199@frame29508→RID039B@frame29516→F190@frame29522→`11 01` reset29528.
- SPS attribution=capture provenance+sequence, not OS-process identity encoded in TCP. Accepted stock transfers do not demonstrate edited-payload acceptance.

Other captures:

- [S7] — programming=amplifier0x81. Radio D-PDU=reads+one write, **no radio27/34/36/37**. Radio DoIP non-FF31B seed-only pairs79944/79947 and83317/83320; no key submission. Refutes old radio-calibration-retry inference from transport byte totals [S6].
- FF captures below show seed production only: no radio key submission/programming in decoded representations.

| Capture | Request/response frames | Seed |
|---|---|---|
| [S8] |542/545;1888/1892|31×FF|
| [S9] |475/478|31×FF|
| [S10] |3719/3722;6240/6243;8919/8922|31×FF|

Superseded: target8B/6B refuted by normal table; full PDU33/14 must not become seed/key length. Historical32/33 seed descriptions include counting/model errors, but every stale claim's cause was not isolated. FF32 claim [S49] relies on unlocated logs; inspected captures show31B. [S15] [S13]

Decode scope:14paths/12unique; six principal August captures TCP sequence/direction reassembled, retransmission overlaps validated and duplicates removed. D-PDU LE declared length, command0x463/event0x863, repeated CAN-ID/receive-length checks; DoIP BE header/type0x8001. No gaps/conflicting overlaps/unframed remainder; TCP segments not assumed UDS boundaries. Supported TCP10123/13400 only; other listed captures have no target diagnostics in these representations, **not exhaustive USB/proprietary decoding**.

## Algorithm and backend

- **S/C, corrected 2026-11-11:** original 83,456-byte S84.dll `generate27Response` @`0x100059d8` takes two cdecl arguments `(backend_value16, output12)`. It constructs sixteen `FF` message bytes and calls `generateMAC(backend_value16, FF16, 16, output12, 12)`. Thus the exact local calculation is `response = AES-128-CMAC(key=backend_value16, message=FF16)[:12]`. Original x86 execution in Unicorn, with only CRT allocation/free and OS support emulated, matched independent cryptography CMAC for three synthetic keys (ascending bytes, all-zero, all-FF). Crypto instructions were not replaced. This corrects the earlier assumption that this wrapper directly MACs the ECU seed. [S17] [S12]
- **S:** DPS `FUN_10041640` builds a 32-byte backend challenge as `01 || seed31` and calls `FUN_100c7d60`. The bridge supplies a vector of 16-byte output buffers to IECS, then passes each returned buffer to S84 with the final output buffer. Assembly @`0x100c7f5e..0x100c7fbc` resolves broken decompiler expressions that otherwise make the buffer argument appear null. IECS `getFskaUnlockResponse` base64-encodes 32 bytes and decodes `cmacValue` into a 16-byte caller buffer. The backend calculation itself is not present in this client trace; the returned value is not thereby a reusable ECU master secret. This proves the available DPS path, not runtime identity of the SPS process in the capture. [S16] [S186]
- **M, superseded as a DPS-wrapper model:** Python `response=AES-128-CMAC(K, seed)[:12]` directly MACs all31B when supplied. It does not reproduce the traced S84 wrapper. Header assumes32/33B; display parser omits31B challenge. No accepted radio vector with a known backend value has been verified. One 16-byte candidate in the existing key map matched neither captured radio response under the S84 transform or the bounded direct/two-stage input hypotheses tested. No seed, response, identifier or candidate-key bytes were retained in this finding. [S13]
- **?:** master says ECUID “not an algorithm input” yet also specifies full-seed/ECUID||challenge CMAC; packet stability cannot decide. Cadillac/Lyriq/CT5 two-stage formulas excluded as target proof. [S14] [S15]
- **S client:** IECS `getFskaUnlockResponse` sends the prefixed challenge to an authenticated backend and parses `cmacResponses/cmacValue`; WinHTTP client-cert configuration supports certificate-authenticated transport. The returned16B value keys the fixed-FF local CMAC stage above. **No proof of reusable AES master-key download**, or exact backend secret derivation. Backend client-auth cert ≠ artifact-signing cert/private key. [S14] [S16] [S17]
- **?:** no target AESK recovered/validated; Frida hook proposed, not successful recovery. Suffix ECUID groups do not prove shared secrets: per-unit/module/domain, derived, backend-provisioned remain hypotheses without recovered-key comparison or cross-module tests. [S18] [S19] [S13]
- **S legacy:** dllsecurity four-step table-driven VM over16-bit seed contradicts no-op-export claim; dispatch/applicability to target31/12 still unproven. [S20] [S21] [S22]

## Direct T1 level-1 SecurityAccess (2026-11-14)

Live Y175, using Y181B static address-check analysis: logical tester F4, target
0x0084, custom TCP framing, extended session `10 03`, then `27 01` yielded
31 all-FF bytes; `27 02` plus 12 zero bytes yielded `67 02`. Default session
was restored. See [validated T1 sequence](../diagnostics/ethernet_uds_diagnosticsd.md#live-t1-securityaccess-correction-2026-11-14). Earlier NRC `0x10` tests used invalid tester 0x0FA0.
This matches the degenerate MDI2 exchange at the UDS level, but does not prove
the exact OBD/gateway/A11 forwarding chain, arbitrary keys, calibration-write
authorization, signature bypass, or root. No programming write was attempted.

## EEPROM, ADB, ProtoKey, tickets

| Evidence | Fact and limit | Sources |
|---|---|---|
| Degenerate B+code | Require31×FF seed→12zero response→6702. Reported31B submitted key→7F2713 incorrect length. Not arbitrary content/length/all levels. |[S23] [S3]|
| EEPROM B | Minimal data edits0x0441/0x0A81=FF; framing/markers unchanged. Earlier stock reportedly already has latterFF; Y181 needs pair. Successful minimal edit reported without CRC recomputation. Old four-byte recipe/0x0B41/marker-gate claims not established extra gates. |[S1] [S24] [S25]|
| VIP S/M | Shared parameterized subsystem;19-bit accumulation2–20 ≠19EEPROM flags, universal wire-level behavior, or direct slot/subfunction map. Full body acrossY175/Y177/Y181 refutes Y177 four-byte stub;906B size does not identify all wire inputs/secret sourcing. |[S26] [S27]|
| ADB S/M | Separate MEC→SoC secure-mode/cert gate:1–255 bypass; zero/invalid/query failure retain; `persist.gm.adb.secure=1` forces enforcement. UDS seed ≠ ADB auth message. |[S1] [S28]|
| ProtoKey S |1B request;17B response=status+16B key. Traced checks=format/status/pointer/state, no key-content crypto found there; upstream producer not thereby characterized. Lifecycle states ≠ UDS levels. |[S2]|
| SBAT manual | Rev1.12p17: ECU Bypass Ticket forGMLAN/GMUDS; selected deviceID+binarySBAT from GMCyber ticket server independently ofDPS. Target eligibility, disabled checks, lifetime, vehicle binding, edited-cal acceptance unknown. |[S29]|
| Other manual functions | p27 Vehicle Key Provisioning=vehicle/gateway message-auth keys; p32 Theft Deterrent Security Code=separate legacy4B code; pp34–37 CLI `BYPASS_TKT`/server-results support ≠ ticket/secret recovery. |[S156]|
| Development/ticket M | `AllowDevSignedVIP`, development-signedVIP_APP/VIP_BOOT and Signature Bypass Ticket ≠ universal unsigned-cal acceptance. Service names/Android enumIDs/EEPROM SBI not interchangeable control mapping. |[S1] [S30]|

## Original Y181 provenance [S/C]

[S31] — ZIP single member, ext4 image3,228,360,704B. Build `W231E-Y181.3.2-SIHM22B-499.3`, Android12/API32, incremental231. Read-only selective extraction. Original DelayedWKSApp.apk21,185,914B: ZIPCRC pass; byte-identical target development copy [S32]. Thus code is exact stockY181, not inference from directory name or CT5. Originals immutable; temp extracts/decompiles supplementary, regenerable, not independent samples.

| Image path | Role |
|---|---|
| `/system/priv-app/DelayedWKSApp/DelayedWKSApp.apk` | Update code; CRC/equality checked |
| `/system/framework/framework-res.apk` | APK platform signer anchor |
| `/system/etc/security/production/signingCA.cer` | Production X.509 CA |
| `/system/etc/security/updatekey/platform.pub` | Separate update public key |
| `/system/etc/security/otacerts.zip` | Recovery/update cert bundle |

Regeneration: extract originalZIP into isolated temp storage, validate ext4/build/CRC/byte equality, read listed files using `debugfs` without mounting/modifying image. Current extraction [S180]; temporary Java coverage below.

## CSM calibration format [C]

All14 stock containers [S33] — payload digest, headerRSA, signer-record CA signature each14/14pass; RSA2048/e65537/PKCS#1v1.5/SHA256. All14 share one calibration signer modulus. [S34]

| Half-open bytes | Length | Role |
|---|---:|---|
| [30:62],0x1E |32| SHA256(container[858:]) |
| [62:344] |282| Custom signer record authenticated by productionCA |
| [88:344],0x58 |256| Big-endian signer modulus |
| [344:600],0x158 |256| CA signature over[62:344] |
| [2:600] |598| Signed calibration header |
| [600:856],0x258 |256| Calibration signature over[2:600] |
| [858:end],0x35A |variable| Digest-covered payload |
| 0x368 |—| Inner gzip begins |

Signer record=subject/certificateID/key-not-beforeID/modulus/root signature; **custom fixed layout, notX.509**. ExternalCA isX.509. Refutes package-format “noRSA, onlyhashes” [S35] [S37] [S38]; does not prove verifier invocation on every route.

Verifier: stock inputs, public keys only; no signing/output/modified file.
```python
from pathlib import Path
import hashlib
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
b = Path("<STOCK_CSM_CONTAINER>").read_bytes()
ca_bytes = Path("<ORIGINAL_Y181_PRODUCTION_CA>").read_bytes()
try:
    ca = x509.load_der_x509_certificate(ca_bytes)
except ValueError:
    ca = x509.load_pem_x509_certificate(ca_bytes)
signer = rsa.RSAPublicNumbers(65537, int.from_bytes(b[88:344], "big")).public_key()
assert hashlib.sha256(b[858:]).digest() == b[30:62]
signer.verify(b[600:856], b[2:600], padding.PKCS1v15(), hashes.SHA256())
ca.public_key().verify(b[344:600], b[62:344], padding.PKCS1v15(), hashes.SHA256())
```

Memory-only negative controls; no modified files emitted:

| Mutation | Payload digest | HeaderRSA | Record CA signature |
|---|---|---|---|
| Stock |Pass|Pass|Pass|
| Payload byte only |Fail|Pass|Unchanged|
| Payload byte+recomputed digest |Pass|Fail|Unchanged|
| Signed-header byte |Unchanged where applicable|Fail|Unchanged where applicable|
| Embedded-modulus byte |Unchanged|Invalidated|Fail|

## Active calibration path and bench results

Exact stockY181 [S]:

| Method | Observation |
|---|---|
| `SignerInfo.verify()` |Complete282B read→true; no root-signature verification call|
| `CalSignedHeader.verify()` |`SHA256withRSA`, embedded signer modulus|
| `SignedCalibration.verify()` |Calls signer-record/header/digest operations|
| `DiagnosticInstaller.attach(boolean sbi)` |Package attachment gets literalfalse, not suppliedsbi|
| `UpdatePackage.attach()` |Handles manifest/signature/module-part; Envelop→false|
| Original attach bytecode |Packed-switch Envelop→defaultfalse, not merely JADX omission|

Parsing/primitive byte order inspected. Verifier existence ≠ active UDS invocation. Envelop route not shown accepting live stream; actual native/diagnostic caller remains?. `integrityonly=true` skips a verifier, but inspected target call passesfalse: **no operational signature/root bypass established**. Contradicts old asserted Java root-chain/ticket flow without proving radio ignores signatures. [S32] [S34]

- **B Nov10:** stale-digest modified write→TransferExit NRC72; digest-correct modified write→TransferData block01 NRC72; cal slots lost after failed attempts, restored with stockLTZ. NRC72=general programming failure, not signature-specific. Competing old explanations: stale per-chunk checksum vs RSA-header gate vs native checksum/digest-only. Tests did not isolate cause; neither format proof nor failed write identifies rejecting method. [S34] [S5]
- **M native integrity:** per-message additive checksum XOR0xA55A, `(sum(body)&0xffff)^0xa55a`; finalization payloadSHA256. Recomputing lower layers ≠ authenticity bypass. [S35]
- **B Nov10 stock:** HighCountry→LTZ,14containers,finalize/reset/readback,allFF auth,ADBuid2000 retained,noMEC action. Refutes universal ADB/programming catch22 for this configuration; not edited-cal acceptance. [S36]
- **Conditional format validity:** payload-consistent digest+valid headerRSA+root-authenticated signer record, plus separate transport/diagnostic state/framing/module/install policies. Modified payload+fixed digest breaks headerRSA; matching signer private key could re-sign **if this path enforced**; applicable exception could change requirement. Neither private key nor applicable custom-cal ticket demonstrated. Stock signed alternatives proven; edited acceptance not. [S37] [S38]

## APK/OTA signing and shared authority

- **C APK:** original framework-res/DelayedWKSApp both `apksigner verify`pass,Schemev3,byte-identicalDERcert/equalRSA2048SPKI; subjectCN=`GM Code Signature Server`,issuerCN=`GPD`; certsignatures verify under productionCA. Only these two anchors compared, not allGM apps. APKleaf ≠ calleaf ≠ targetOTAleaf, also differs fromCA/platform.pub. [S31]
- APK updates/signature privileges require recognized signer identity/lineage+package policy; anotherCA-issuedcert ≠ platform signer. Signature/privileged permissions and SELinux/Binder access remain separate. [S39] [S40] [S41]
- **C/S OTA:** [S43]+[S42] — storedSHA256matches manifest; RSA2048/PKCS1v1.5/SHA256 manifest signature verifies underSMDleaf; leafcert verifies under productionCA. ExactY181 `Signature.java` selects production/developmentCA, calls `untrusted.verify(trusted.getPublicKey())`: normal manifest route established, unlike calEnvelop route. [S185]
- **B Y175 harness:** stockcert accepted; replacementself-signedcert→`Err_PublicSigningCert`; manifest probe, not customCSM test. `Sign Type=NONE` per module ≠ wholeupdateunverified; manifest/hashes/signer/module/boot policy remain. `Bypass P/N & Module ID Check` changes identity matching, not proven signing exception. ProductionUSBnotifier/development-caloverride(type2) selection has build/path restrictions; existence ≠ normal production selection. [S30] [S44]

OTA-only comparison:

| Cohort | Artifacts | Same complete DER certificate/SPKI within cohort |
|---|---|---|
| gminfoY181/Y181B |[S42] [S45]|Yes|
| CT5/SilveradoEV |[S46] [S47]|Yes|

Cohort leafcerts/keys **differ**; all4certsignatures verify under originalY181productionCA. ActualDER/SPKI/signatures compared, not names alone: refutes universal `GM Code Signature Server` leaf-key claim. APKcerts and14CSM signer records also verify under thatCA, with distinct leaf keys.

Other anchors: `updatekey/platform.pub` separateRSA2048,notAPKplatform/cal/CA; “platform” filename does not establish APK identity. `otacerts.zip` / `releasekey_secure_boot.x509.pem`: recoverycert separateRSA2048,distinct fromCA/platform.pub. Shared root=issuing authority; corresponding private key could affect verifiers honoring it **conditional on actual trust/policy**. No root/leaf private key recovered; no universal private leaf, cross-platform package acceptance, or Android signer equality follows. Hardware/module/manifest/AVB/GHS/rollback remain. [S31]

RSA1024hypervisorcandidate: parsing/matching public key/function/code use pending; not validated observedRSA2048cal signer recovery. [S48]

## Open questions and historical claims

- Known-secret target vector: resolve normal construction/input mapping, Kscope, backend secret boundary.
- Target native/UDS caller: identify actual header/root/checksum/digest enforcement; isolate NRC72 cause.
- SBAT: establish target issuance/eligibility/binding/disabled checks.
- Y181B matching OTA leaf does not establish identical native cal code. Cross-platform package acceptance/trust policy untested; unknowns do not authorize new live actions.
- Older compendia: physical secret storage remains hypothesis; encryptedEEPROM reset-payload interpretation rejected [S1]; bridge-symbol forwarding attribution retracted [S50]; owner downgrade retests refine observed rejection stage without proving exact rollback-counter layout [S51]. Indexed sources are not blanket endorsements.

## Sources and coverage

133 text paths=129 direct full reads+4 full-content comparisons: fully read external counterpart plus every differing/added block independently read; not hash-identical duplicates. Corpus is relevant research, not every file in both trees. Excluded as proof: conversation/transcripts,raw enumeration/UART catalogs,third-party source bundles,unrelated vehicle manuals,model/fuzz output; incidental video `RDSEED`. Relative links portable; absolute links require mounted source volume. Source IDs below are clickable; exact targets defined once, never reconstructed from aliases.

### Repository: direct full reads

[S52] [S53] [S54] [S50] [S28] [S55] [S24] [S56] [S25] [S26] [S57] [S58] [S59] [S36] [S60] [S61] [S62] [S63] [S64] [S44] [S30] [S39] [S15] [S65] [S2] [S66] [S6] [S67] [S35] [S68] [S69] [S70] [S71] [S37] [S1] [S72] [S73] [S51] [S74] [S75] [S76] [S77] [S78] [S79] [S80] [S81] [S82] [S83] [S84] [S85] [S86] [S87] [S88] [S89] [S38] [S90] [S22] [S91] [S92] [S93] [S94] [S27] [S95] [S96] [S41] [S97] [S48] [S40] [S98] [S99]

### Repository: counterpart+all differences

[S100] [S101] [S102] [S103]

### External Silverado: direct full reads

[S104] [S105] [S106] [S107] [S108] [S109] [S110] [S111] [S112] [S113] [S114] [S115] [S116] [S117] [S118] [S119] [S120] [S121] [S122] [S123] [S124] [S125] [S126] [S127] [S128] [S129] [S130] [S131] [S132] [S49] [S133] [S134] [S135] [S136] [S137]

### External DPS/library: direct full reads

[S12] [S20] [S34] [S138] [S139] [S14] [S140] [S3] [S141] [S142] [S143] [S144] [S5] [S145] [S21] [S146] [S147] [S19] [S18] [S11] [S148]

### Other external: direct full reads

[S149] [S150] [S151]

### PDFs:13 paths/10 unique

Nine text-bearing unique files: all extracted text/all pages read; embedded screenshots not all OCRed. One image-only hardware-label PDF: OCR relevance inspection. Duplicate pairs explicit below.

| Source | Pages | Coverage/role |
|---|---:|---|
| [S152] | 11 | Type4 archive tutorial |
| [S153] | 4 | original cache collection |
| [S154] | 4 | archive configuration |
| [S155] | 33 | rev 1.9, 2022-03-14 |
| [S156] | 45 | rev 1.12, 2024-03-11; ticket p17 |
| [S157] | 4 | parallel programming |
| [S158] | 15 | VCAP reader |
| [S159] | 4 | installation only |
| [S160] | 2 | acquisition note |
| [S161] | 2 | Image-only radio/module labels; OCR relevance inspection |
| [S162] | 15 | Byte-identical duplicate of [S158] |
| [S163] | 4 | Byte-identical duplicate of [S159] |
| [S164] | 2 | Byte-identical duplicate of [S160] |

### Captures:14 paths/12 unique

Six principal August captures reassembled in supported TCP representations; two duplicate paths counted once. Remaining six unique/absence scope below.

| Source | Status |
|---|---|
| [S8] | radio all-FF seeds only |
| [S9] | radio all-FF seed only |
| [S10] | radio all-FF seeds only |
| [S7] | amplifier programming, radio seed-only DoIP probes |
| [S4] | two accepted radio unlocks and 14 radio downloads |
| [S165] | no radio SecurityAccess/download in decoded representation |
| [S166] | Exact duplicate of [S7] |
| [S167] | Exact duplicate of [S10] |
| [S168] | empty 24-byte capture |
| [S169] | no supported TCP diagnostic representation |
| [S170] | no supported TCP diagnostic representation |
| [S171] | no supported TCP diagnostic representation |
| [S172] | no supported TCP diagnostic representation |
| [S173] | no supported TCP diagnostic representation; not an exhaustive USB decode |

### Code coverage (separate from full-document reads)

| Source | Coverage |
|---|---|
| [S13] | Full source read; current response model and limitations |
| [S23] | Authentication portion through line 271; not the entire file |
| [S174] | Full source read; secondary implementation, not a target known-answer vector |
| [S175] | Lines 1–360 inspected |
| [S176] | First 70 lines only; not counted as full-document coverage |
| [S17] | Lines 5240–5385 inspected |
| [S16] | Lines 4650–4700 and 4775–4855 plus symbol searches |
| [S177] | Full source read; D-PDU event framing |
| [S178] | Full source read; capture transport representation |
| [S179] | Lines 1–260 and 272–280; imported without running main |

### Temporary exact-Y181 decompiles

| Source | Coverage |
|---|---|
| [S181] | Full source read; SignerInfo, CalSignedHeader and SignedCalibration |
| [S182] | Relevant attachment method inspected |
| [S183] | Attachment, type dispatch and verification methods inspected; Envelop switch checked against APK bytecode |
| [S184] | Relevant parsing/type methods inspected |
| [S185] | Normal manifest certificate verification inspected |

### Exact source targets

[S1]: <EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md>
[S2]: <ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md>
[S3]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/LIVE_DPS_CAPTURE_ECU80_AUG2026.md>
[S4]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/SPS_radioCal_and_OS_UpdateCHeck.pcapng>
[S5]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/SPS_RECAL_UDS_SEQUENCE_AUG2026.md>
[S6]: <AUG24_SESSION_FULL_PCAP_TIMELINE.md>
[S7]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/DPS+SPS.pcapng>
[S8]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/capture_attempt1.pcapng>
[S9]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/capture_attempt2.pcapng>
[S10]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/multiple_intefaces_attempt1.pcapng>
[S11]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/security_dlls/S84_ANALYSIS_LOG.md>
[S12]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/annotations/S84.dll.UNRESOLVED_RESOLVED.md>
[S13]: <../mdi2_client/mdi2/security_cmac.py>
[S14]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/DPS_MASTER_REFERENCE.md>
[S15]: <../platform/vehicle_network.md>
[S16]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/pseudocode/IECS.dll.pseudocode.txt>
[S17]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/pseudocode/S84.dll.pseudocode.txt>
[S18]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/security_dlls/HOOKING_AND_TESTING_GUIDE.md>
[S19]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/security_dlls/EMULATION_ANALYSIS.md>
[S20]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/annotations/dllsecurity.dll.annotations.md>
[S21]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/TISVCSV4_ANALYSIS.md>
[S22]: <TISVCSV4_MULTI_OEM_KEYSERVER_AUG2026.md>
[S23]: <../mdi2_client/mdi2/calibration_transaction.py>
[S24]: <../eeprom/README.md>
[S25]: <../eeprom/VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md>
[S26]: <../eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md>
[S27]: <VIP_FIRMWARE_Y177_Y181_COMPARISON.md>
[S28]: <../eeprom/EEPROM_Analysis_Report.md>
[S29]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/dps_extracted/DPS_User_Guide.pdf#page=17>
[S30]: <../platform/ota_update_stack.md>
[S31]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y181/86331654>
[S32]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/hy/re/apks/com.gm.domain.server.delayed.apk>
[S33]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/calibrations/A11_extracted/spsCacheInternal/decompressed/>
[S34]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/A11_CALIBRATION_FILES_COMPLETE_ANALYSIS_AUG2026.md>
[S35]: <CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md>
[S36]: <../mdi2_client/README.md>
[S37]: <DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md>
[S38]: <SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md>
[S39]: <../platform/security.md>
[S40]: <security/SHELL_ACCESS_ESCALATION_Jun2026.md>
[S41]: <security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md>
[S42]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y181/86331665.smd>
[S43]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y181/86331663.mnf>
[S44]: <../platform/ota_programming_roles.md>
[S45]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/firmware/update_packages/Y181B/USB_Files/86405528.smd>
[S46]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2026_CT5/Radio-IVE-86384258-AAOS14-UQBM/86384262.smd>
[S47]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2026_Silverado_EV/firmware/470/86485092.smd>
[S48]: <security/RSA1024_PRIVATE_KEY_GHS_INTEGRITY.md>
[S49]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/diag/real_did_values.md>
[S50]: <../diagnostics/ethernet_uds_diagnosticsd.md>
[S51]: <GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt>
[S52]: <../README.md>
[S53]: <../VERIFICATION.md>
[S54]: <../analysis/platform_faq.md>
[S55]: <../eeprom/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md>
[S56]: <../eeprom/VIP_EEPROM_FLAG_SCOPE_ANALYSIS_AUG2026.md>
[S57]: <../hardware/connectors.md>
[S58]: <../hardware/photos/README.md>
[S59]: <../hardware/teardown.md>
[S60]: <../platform/boot_chain.md>
[S61]: <../platform/emulator.md>
[S62]: <../platform/firmware_versions.md>
[S63]: <../platform/hardware.md>
[S64]: <../platform/networking.md>
[S65]: <AE_RESEARCH_HANDOFF.md>
[S66]: <AUG24_25_DOC_REVIEW_CORRECTIONS_AUG2026.md>
[S67]: <CALDEF_VIP_CALIBRATION_ANALYSIS.txt>
[S68]: <CSE_HECI_ORCHESTRATION_ANALYSIS.md>
[S69]: <DOCUMENTATION_REVIEW_AND_CORRECTIONS.txt>
[S70]: <DPS_AND_MODIFICATION_LANDSCAPE.txt>
[S71]: <DPS_SECURITY_ANALYSIS.txt>
[S72]: <EEPROM_MAPPING_FABLE_REPORT.md>
[S73]: <EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md>
[S74]: <GHS_FILE_MAP_85098662.md>
[S75]: <GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md>
[S76]: <GHS_PRIVACY_CAPABILITY_ANALYSIS.md>
[S77]: <GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt>
[S78]: <GM_REMOTE_ACCESS_ANALYSIS.txt>
[S79]: <HARDWARE_HYPERVISOR_ATTACK_VECTORS.md>
[S80]: <INVENTORY.md>
[S81]: <MASTER_REFERENCE.md>
[S82]: <MDI2_DPDU_API_PROTOCOL_AUG2026.md>
[S83]: <MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md>
[S84]: <MDI2_RAW_UDS_BYPASS_GUIDE.md>
[S85]: <PROJECT_MASTER_CHECKLIST.txt>
[S86]: <PROVENANCE_AUDIT_AUG2026.md>
[S87]: <QUICK_REFERENCE.txt>
[S88]: <RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md>
[S89]: <S27_SOC_VALIDATION_BENCH_TEST.md>
[S90]: <T1_NETWORK_AND_EEPROM_CAL_CONVERGENCE_AUG2026.md>
[S91]: <UNTRIED_ATTACK_VECTORS.md>
[S92]: <UPDATE_PROCESS_ANALYSIS.txt>
[S93]: <USB_ADB_SESSION_FINDINGS_2026-10-10.md>
[S94]: <VIP_CONTROL_ANALYSIS.txt>
[S95]: <canbus_reset/CANBUS_RESET_ANALYSIS.txt>
[S96]: <reports/forensic_out.txt>
[S97]: <security/CVE_ATTACK_SURFACE_ANALYSIS.md>
[S98]: <type4_radio_info/README.md>
[S99]: <../runtime/known_issues.md>
[S100]: <BOOT_CHAIN_ANALYSIS.txt>
[S101]: <GM_INFO37_BOOT_CHAIN_ANALYSIS.md>
[S102]: <GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md>
[S103]: <AOSP_REPLACEMENT_RESEARCH.txt>
[S104]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/MASTER_REFERENCE.md>
[S105]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/SOC_PRODUCT_Y181_vs_Y181B_AUG2026.md>
[S106]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_2026-11-02/Y175_LIVE_RADIO_T1_SECURITY_ASSESSMENT_2026-11-02.md>
[S107]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_2026-11-02/source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md>
[S108]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_2026-11-02/source_notes/T1_RADIO_NETWORK_STRUCTURE.txt>
[S109]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_2026-11-02/source_notes/T1_RADIO_appendix.txt>
[S110]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_2026-11-02/source_notes/T1_RADIO_core.txt>
[S111]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y175_OS_PARTITION_INVESTIGATION_AUG2026.md>
[S112]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/Y181_vs_Y181B_DIFF_AUG2026.md>
[S113]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/analysis/canbus_reset/CANBUS_RESET_ANALYSIS.txt>
[S114]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/AOSP_REPLACEMENT_RESEARCH.txt>
[S115]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/BOOT_CHAIN_ANALYSIS.txt>
[S116]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/CALDEF_VIP_CALIBRATION_ANALYSIS.txt>
[S117]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/DOCUMENTATION_REVIEW_AND_CORRECTIONS.txt>
[S118]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/DPS_AND_MODIFICATION_LANDSCAPE.txt>
[S119]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md>
[S120]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md>
[S121]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/GHS_PRIVACY_CAPABILITY_ANALYSIS.md>
[S122]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt>
[S123]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/GM_INFO37_BOOT_CHAIN_ANALYSIS.md>
[S124]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/OTA_MODULE_PROGRAMMING_ROLES.md>
[S125]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/PROJECT_MASTER_CHECKLIST.txt>
[S126]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/QUICK_REFERENCE.txt>
[S127]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/UPDATE_PROCESS_ANALYSIS.txt>
[S128]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/VEHICLE_NETWORK_TOPOLOGY.md>
[S129]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/VIP_CONTROL_ANALYSIS.txt>
[S130]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/research/VIP_FIRMWARE_Y177_Y181_COMPARISON.md>
[S131]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/docs/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt>
[S132]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/diag/doip_uds_surface.md>
[S133]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/security.md>
[S134]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/unstub/network_fsa.md>
[S135]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/emu/y181_ref/vehicle_network.md>
[S136]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/hardware/EEPROM/EEPROM_Analysis_Report.md>
[S137]: </Volumes/stuff/misc/research/GM_research/aaos/gm_aaos/2024_Silverado_ICE/hardware/EEPROM/EEPROM_UNDOCUMENTED_FLAGS_ANALYSIS.md>
[S138]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/DPS_ANALYSIS_REPORT.md>
[S139]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/DPS_ARCHIVE_CREATOR_ANALYSIS.md>
[S140]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/EEPROM_CALIBRATION_MAPPING.md>
[S141]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/MDI2_LINUX_MACOS_ANALYSIS.md>
[S142]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/OPENSOURCE_ECU_RESET_ANALYSIS.md>
[S143]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/OS_UPDATE_CHECK_Y181B_AUG2026.md>
[S144]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/SBI_SECURITY_SCOPE_ANALYSIS.md>
[S145]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/SPS_TO_DPS_TYPE4_CONVERSION.md>
[S146]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/TYPE4_CUSTOM_COMMAND_INTERFACE_AUG2026.md>
[S147]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/VIP_BOOT_CONTROL_ANALYSIS.md>
[S148]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/security_dlls/scripts/README.txt>
[S149]: </Volumes/stuff/misc/research/GM_research/csm_eeprom/icloud_eeprom/EEPROM_Analysis_Report.md>
[S150]: </Volumes/stuff/misc/research/GM_research/carplay/gm_pi/docs/10_GOAL_HIERARCHY.md>
[S151]: </Volumes/stuff/misc/research/GM_research/carplay/gm_pi/docs/08_HARDWARE_CHIPS.md>
[S152]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/cameraloopsRU/[Courses]: ▶︎ Learn how to manually create GM DPS archive file for module programming [The Quick Method] - www.CameraLoops.ru.pdf>
[S153]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/create_dps_type4/lesson_1.pdf>
[S154]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/create_dps_type4/lesson_2.pdf>
[S155]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/dps_user_guide.pdf>
[S156]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/dps_extracted/DPS_User_Guide.pdf>
[S157]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/dps_extracted/pp_ug_no_bg.pdf>
[S158]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/tools/VCAP_interpreter_v1.3.pdf>
[S159]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/tools/VCAP_Interpreter_Standalone_Installation_Guide.pdf>
[S160]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/tools/dps_type4_vcap_creator/Read me!.pdf>
[S161]: </Volumes/stuff/misc/research/GM_research/diagnostics/icloud_diag/gds2/4050897revA_G071-4010-03MN_gminfo37.pdf>
[S162]: </Volumes/stuff/misc/research/GM_research/diagnostics/icloud_diag/vcap_interpreter/VCAP_interpreter_v1.3.pdf>
[S163]: </Volumes/stuff/misc/research/GM_research/diagnostics/icloud_diag/vcap_interpreter/VCAP_Interpreter_Standalone_Installation_Guide.pdf>
[S164]: </Volumes/stuff/misc/research/GM_research/diagnostics/icloud_diag/vcap_interpreter/DPS Type4 VCAP creator file/Read me!.pdf>
[S165]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/misc/Aug24_session/postOS_download_SPS.pcapng>
[S166]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/live_captures_20260824_3/DPS+SPS.pcapng>
[S167]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/docs/live_captures_20260824_3/multiple_intefaces_attempt1.pcapng>
[S168]: </Volumes/stuff/misc/research/GM_research/diagnostics/bus2_20261102_122611.pcap>
[S169]: </Volumes/stuff/misc/research/GM_research/mdi2/mdi2_macos/captures/mdi_session_full_with_handshake.pcapng>
[S170]: </Volumes/stuff/misc/research/GM_research/mdi2/mdi2_macos/captures/session2.pcapng>
[S171]: </Volumes/stuff/misc/research/GM_research/mdi2/mdi2_macos/captures/mdi_20260825_225907.pcapng>
[S172]: </Volumes/stuff/misc/research/GM_research/mdi2/mdi2_macos/captures/cold_arming/net.pcap>
[S173]: </Volumes/stuff/misc/research/GM_research/mdi2/mdi2_macos/captures/cold_arming/usb2.pcap>
[S174]: </Volumes/stuff/misc/research/GM_research/carplay/gm_pi/gmtool/gm_security.py>
[S175]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/security_dlls/scripts/gm_security.py>
[S176]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/annotations/S84.dll.annotations.md>
[S177]: <../mdi2_client/mdi2/captured_events.py>
[S178]: <../mdi2_client/mdi2/capture_read_transport.py>
[S179]: <../mdi2_client/scratch_decode/radio_cal_decode.py>
[S180]: </tmp/fwtriage/gm-y181-signing>
[S181]: </tmp/gm_calibration_target_sources/Envelop.java>
[S182]: </tmp/gm_calibration_target_sources/DiagnosticInstaller.java>
[S183]: </tmp/gm_calibration_target_sources/UpdatePackage.java>
[S184]: </tmp/gm_calibration_target_sources/UpdateFile.java>
[S185]: </tmp/gm_calibration_target_sources/Signature.java>
[S186]: </Volumes/stuff/misc/research/GM_research/diagnostics/gm_dps/disassembly/pseudocode/dpsvcs.dll.pseudocode.txt>
