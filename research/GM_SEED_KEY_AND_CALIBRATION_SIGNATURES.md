# GM Seed-Key and Calibration Signatures

Updated 2026-11-18 (this consolidation pass; prior content dated 2026-11-16). The Nov-11
static/packet audit made no new live changes; the separately dated Nov-16 CANable follow-up
includes live programming/control tests.

**Scope:** the canonical seed-key/SecurityAccess doc for gminfo/Silverado Y17X.xx and
Y181/B: the UDS `27`/`67` exchange, the S84.dll/DPS CMAC algorithm (including
`tisvcsv4.dll`'s multi-OEM dispatch architecture), the ProtoKey VIP↔SoC IPC chain, the
EEPROM/ADB/ProtoKey/SBAT gate-independence table, the CSM calibration-container
signature format + Python verifier, and the APK/OTA signing trust chain. New exact
static proof in this doc is **Y181**, not automatically Y175/Y177/Y181B/all revisions;
**CT5/EV supply OTA-certificate comparison only** — their seed, calibration, APK
implementation, emulator behavior and live-security results are explicitly excluded as
evidence for this platform.

**Does NOT live here** (pointer only, never restated): EEPROM byte-level map and
SBI/marker-byte mechanism → `../eeprom/` / `eeprom_i2c_security.md`; VIP control-scope,
CRC boundaries, I2C-access table → `VIP_CONTROL_ANALYSIS.txt`; CalDef record structure
and VIP calibration-index tables → `CALDEF_VIP_CALIBRATION_ANALYSIS.txt`; the live
CAN613/614 custom-calibration-write bench record → `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md`;
CalSets.db checksum/container RE → `CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md`;
SELinux/CIL write-path reachability → `SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md`;
general SELinux/FBE/CVE/ADB security posture → `../platform/security.md`; raw UDS
bypass mechanics over MDI2 → `MDI2_RAW_UDS_BYPASS_GUIDE.md` (carried unchanged, cite
only).

**Evidence tags** (this doc's own convention, distinct from platform/'s `[C]/[V]/[FW]/
[S]/[inferred]/[U]/[X]` shorthand — kept as originally authored rather than
retro-tagged): **P** = original packets reassembled/decoded; **C** = offline
original-artifact cryptography; **S** = exact-build code/bytecode; **B** = dated bench
evidence; **M** = documented model/secondary implementation; **?** = unresolved.

Keep separate: UDS access; EEPROM seed state; MEC/ADB certificate gate; ProtoKey IPC;
SBAT ticket; APK signer identity; artifact trust; AVB/GHS/rollback. Do not infer a
bypass of one gate from evidence about another. UDS response (12B) ≠ hypothesized
AES secret (16B); public-key verification ≠ private-key recovery. Diagnostic
`$0000 Bypass Inactive` ≠ EEPROM SBI or a signature ticket.

Privacy: retain protocol ECU addresses/frame indices; omit credentials/private
infrastructure, device identifiers/actual ECUID, real seeds/responses, private-key
material, personal certificate email, conversation pointers.

Notation: unprefixed UDS/NRC/DID/RID values are hex; lengths/counts/offsets/frames/
streams/times are decimal; `0x` marks hex.

## 1. SPS radio seed/key and calibration [P]

Primary capture — radio 0x80, D-PDU command/event streams 317/318, two normal non-FF
grants. Seed PDU (33B) = `67 01` + 31B; submitted-key PDU (14B) = `27 02` + 12B.
Seed = 16B stable ECUID + 15B varying challenge. The prefix matches all 3 radio DID
`F0F3` identifiers; challenges and responses differ between grants. These observations
reveal no secret key, scope, or complete derivation.

| Event | First frame | Time (s) | Second frame | Time (s) | UDS bytes |
|---|---:|---:|---:|---:|---:|
| `27 01` | 25884 | 174.220294 | 29381 | 193.023240 | 2 |
| `67 01 <ECUID16><challenge15>` | 25889 | 174.231800 | 29386 | 193.040754 | 33 |
| `27 02 <response12>` | 25946 | 175.305778 | 29437 | 193.762523 | 14 |
| `7F 27 78` pending | 25951 | 175.405265 | 29442 | 193.869112 | 3 |
| `67 02` grant | 25952 | 175.440075 | 29443 | 193.904161 | 2 |

Frames = completed, reassembled messages; times = capture-relative seconds. NRC `78` is
pending **after key submission**, not invalid-key or pre-seed pending. Neither exchange
carries SecurityAccess NRC `35`/`36`/`37`.

Programming sequence:

- First grant → `31 01 02 49` frame 25954 → `10 02` frame 26015 → 14 RequestDownload/
  positive pairs, 19 TransferData pairs, 14 TransferExit pairs; last frame 27239;
  requested total 46,162B.
- Second grant follows the transfers → F198 frame 29445 → F199 @ frame 29508 → RID
  `039B` @ frame 29516 → F190 @ frame 29522 → `11 01` reset frame 29528.
- SPS attribution = capture provenance + sequence, not OS-process identity encoded in
  TCP. Accepted stock transfers do not demonstrate edited-payload acceptance.

Other captures:

- Programming = amplifier 0x81. Radio D-PDU = reads + one write, **no radio 27/34/36/37**.
  Radio DoIP non-FF 31B seed-only pairs 79944/79947 and 83317/83320; no key submission.
  Refutes the older radio-calibration-retry inference from transport byte totals.
- FF captures below show seed production only: no radio key submission/programming in
  decoded representations.

| Capture | Request/response frames | Seed |
|---|---|---|
| capture_attempt1.pcapng | 542/545; 1888/1892 | 31×FF |
| capture_attempt2.pcapng | 475/478 | 31×FF |
| multiple_intefaces_attempt1.pcapng | 3719/3722; 6240/6243; 8919/8922 | 31×FF |

Superseded: target 8B/6B figures are refuted by the normal-grant table above; the full
33B/14B PDU length must not become the seed/key length. Historical "32/33-byte seed"
descriptions include counting/model errors, but every stale claim's cause was not
isolated. An "FF32" claim relying on an unlocated log is not supported — inspected
captures show 31B. See [Open Conflicts](#open-conflicts) for the still-unresolved
31-vs-32-byte question traced to a different source chain.

Decode scope: 14 paths / 12 unique; six principal August captures TCP sequence/
direction reassembled, retransmission overlaps validated, duplicates removed. D-PDU LE
declared length, command 0x463/event 0x863, repeated CAN-ID/receive-length checks;
DoIP BE header/type 0x8001. No gaps, no conflicting overlaps, no unframed remainder; TCP
segments are not assumed to be UDS boundaries. Supported transports: TCP 10123/13400
only; other listed captures have no target diagnostics in these representations —
**not an exhaustive USB/proprietary decode.**

### Footnote — Type4-VCAP legacy 2-byte seed table (legacy, NOT this CSM's scheme)

Absorbed from the retired `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt` §15.9. Type4 VCAP
is a *data-capture* tool, not a programming tool, and its XML capture format (`<Capture
… ><Dlc Protocol="gmlan" …><Device …><Service Id="27">…`) comes from an **older (2018)
vehicle**, unrelated to the gminfo3.7 CSM covered by §1 above:

| ECU ID | RxCanId | Seed (hex) |
|---|---|---|
| 0x58 | 647 | 3630 |
| 0x60 | 64C | 9D53 |
| 0x51 | 651 | E20B |
| 0x7E8 | HS-CAN | EDB3 |
| 0x7EA | HS-CAN | 52BB |

These are legacy **2-byte** GMLAN seeds from a 2018-era vehicle/tool package
(`CameraLoops_com_0..4`, `Type4_VCAP_*.tbl`) — they are **not** evidence about this
CSM's seed length or algorithm and must not be cited for either. The compendium's own
accompanying claim that "the CSM (gminfo3.7) uses 32-byte seeds (ECUID + Challenge)" is
itself one of the superseded 32-byte figures tracked under
[Open Conflicts](#open-conflicts) item 2 below — do not treat it as corroboration.

## 2. Algorithm and backend

- **S/C, corrected 2026-11-11:** the original 83,456-byte `S84.dll::generate27Response`
  @ `0x100059d8` takes two cdecl arguments `(backend_value16, output12)`. It constructs
  sixteen `FF` message bytes and calls `generateMAC(backend_value16, FF16, 16, output12,
  12)`. The exact local calculation is therefore `response = AES-128-CMAC(key=
  backend_value16, message=FF16)[:12]`. Original x86 execution in Unicorn, with only CRT
  allocation/free and OS support emulated, matched independent CMAC cryptography for
  three synthetic keys (ascending bytes, all-zero, all-FF). Crypto instructions were not
  replaced. This corrects the earlier assumption that this wrapper directly MACs the ECU
  seed.
- **S:** DPS `FUN_10041640` builds a 32-byte backend challenge as `01 || seed31` and
  calls `FUN_100c7d60`. The bridge supplies a vector of 16-byte output buffers to IECS,
  then passes each returned buffer to S84 with the final output buffer. Assembly @
  `0x100c7f5e..0x100c7fbc` resolves broken decompiler expressions that otherwise make the
  buffer argument appear null. IECS `getFskaUnlockResponse` base64-encodes 32 bytes and
  decodes `cmacValue` into a 16-byte caller buffer. The backend calculation itself is not
  present in this client trace; the returned value is not thereby a reusable ECU master
  secret. This proves the available DPS path, not runtime identity of the SPS process in
  the capture.
- **M, superseded as a DPS-wrapper model:** a Python model of `response =
  AES-128-CMAC(K, seed)[:12]`, directly MACing all 31B when supplied, does not reproduce
  the traced S84 wrapper above. The header assumed 32/33B; the display parser omits the
  31B challenge. No accepted radio vector with a known backend value has been verified.
  One 16-byte candidate in the existing key map matched neither captured radio response
  under the S84 transform nor the bounded direct/two-stage input hypotheses tested. No
  seed, response, identifier, or candidate-key bytes were retained in this finding.
- **?:** the master reference says ECUID is "not an algorithm input," yet also specifies
  a full-seed/ECUID||challenge CMAC; packet stability alone cannot decide between them.
  Cadillac/Lyriq/CT5 two-stage formulas are excluded as target proof.
- **S client:** IECS `getFskaUnlockResponse` sends the prefixed challenge to an
  authenticated backend and parses `cmacResponses/cmacValue`; WinHTTP client-cert
  configuration supports certificate-authenticated transport. The returned 16B value
  keys the fixed-FF local CMAC stage above. **No proof of a reusable AES master-key
  download, or of the exact backend secret derivation.** A backend client-auth cert ≠
  an artifact-signing cert/private key.
- **?:** no target AES key recovered or validated; a Frida hook was proposed, not
  successfully run to recovery. Suffix-matching ECUID groups do not prove shared
  secrets: per-unit, per-module, per-domain, derived, or backend-provisioned sourcing
  all remain hypotheses without a recovered-key comparison or cross-module test.
- **S legacy:** `dllsecurity.dll`'s four-step table-driven VM over a 16-bit seed
  contradicts an earlier no-op-export claim; its dispatch/applicability to this target's
  31B/12B exchange is still unproven. See the multi-OEM dispatch architecture below,
  which independently confirms `dllsecurity.dll::CSecurity::SetSeedAndGetKey` as
  `tisvcsv4.dll`'s default/GM-standard path.

### 2.1 `tisvcsv4.dll` — multi-OEM SecurityAccess dispatch architecture

Absorbed from the retired `TISVCSV4_MULTI_OEM_KEYSERVER_AUG2026.md` (2026-08-25
session). Source: a full-function Ghidra disassembly of `tisvcsv4.dll` (25,809
functions total; DPS's UDS `$27` protocol engine), scoped to a 30-function
security-relevant subset (keyword match + one-hop call-graph proximity to known
SecurityAccess functions + hand-rolled-crypto signal detection), independently
annotated by 6 parallel passes that converged on near-identical architecture. Full
merged annotations: `gm_dps/disassembly/annotations/
tisvcsv4.dll.SECURITY_CANDIDATES.annotations.md` (subdirectory link, not resolved per
this reorg's rules).

**Headline finding:** `tisvcsv4.dll` is **not GM-only** — it is a shared multi-brand
diagnostic-protocol engine that dispatches UDS `$27` SecurityAccess key computation to
one of several **externally-loaded, per-OEM key-server DLLs**, chosen upstream (by
vehicle architecture / ECU config), not by a single visible switch statement.

**Layer 1 — GM-internal algorithm-class selector**, `FUN_10086bb0` (top-level
dispatcher), keyed on a method byte (`param_4 & 0xff`) combined with a 16-bit algorithm
ID (`uVar6`, built from a config byte + the request param):
- `2`/`3` → hand-rolled inline algorithm bank (via `FUN_10087420` → `FUN_10002c50`)
- `4`/`5` → `FUN_10001670` (outside the scoped candidate set, not yet analyzed)
- `6`/`7` → `GetTickCount()`-seeded random challenge, mixed via byteswap / `+0x6187` /
  rotate / `+0x6f19` / rotate, then routed to standard `CSecurity::SetSeedAndGetKey`
- `0x10` → `CSecurity::SetSeedAndGetKey(uVar6 | 0x1000)`
- **default** → `CSecurity::SetSeedAndGetKey(uVar6)` — the standard GM path, confirmed
  imported from `dllsecurity.dll`, not locally implemented (`FUN_100873b0` is a thin
  bridge; only one call site to the real method exists in the whole 25,809-function
  file, with no definition in-module)

**Layer 2 — hand-rolled algorithm table**, `FUN_10002c50`, keyed on a 16-bit algorithm
ID read from `*(ushort*)(in_ECX+2)` (sourced from the `CVIT1` seed table): IDs
`0x201`–`0x305` are bespoke inline transforms (LFSR bit-permutation, iterated
LCG multiply-add loops, S-box/table lookups, embedded key constants) — genuinely
hand-rolled crypto, not library calls. IDs `0x3f6`/`0x4f6`/`0x4fe` escape to a different
external DLL: `DllTzSale.dll::fnRequestOperation` (not yet analyzed).

**Layer 3 — per-OEM external key-server DLLs**, each reached through its own dedicated
leaf function (which function gets called — the "brand switch" — is decided by the
caller above this file, most plausibly by vehicle architecture/`CVIT1` id, not
confirmed from this candidate set alone):

| OEM / purpose | DLL | Export | Caller in `tisvcsv4.dll` | Entry |
|---|---|---|---|---|
| GM (standard) | `dllsecurity.dll` | `CSecurity::SetSeedAndGetKey` | `FUN_100873b0` (bridge only) | `0x100873b0` |
| SAIC | `Seed2Key.dll` | `SAIC_ComputeKeyFromSeed` | `FUN_1006bb50` (lazy loader) | `0x1006bb50` |
| GM 5-byte MAC | `IVCS5B.dll` (config-driven name, not literal) | `RequestOperation` | `FUN_10086d50`, logged by `FUN_1006bbd0` | `0x10086d50` |
| (unclear OEM) | `IECS.dll` (config-driven name) | `getUnlockResponse` | `FUN_10086f90` | `0x10086f90` |
| (unclear OEM) | `IECS.dll` | `getKeyProvResponse` | `FUN_10087140` | `0x10087140` |
| PSA / Stellantis (Opel/Vauxhall) | `ivcspsa.dll` (hardcoded) | `GetPsaKey` | `FUN_10087530` (also branches on host exe being `dps.exe`) | `0x10087530` |
| Shanghai-GM | `ivcssgm.dll` (hardcoded) | `RequestOperation` | `FUN_10087cc0` | `0x10087cc0` |
| Nissan (reflash) | `sesame_GM.dll` → decrypts → `simsim_GM.dll` | `ExtractEncryptedDLL` → `GetKey` (class `CNissanKey`) | `FUN_10049ab0` — a full KWP2000 unlock+reprogram state machine, `'GMPS'`-tagged download block | `0x10049ab0` |
| Legacy algorithm escape | `DllTzSale.dll` | `fnRequestOperation` | inline in `FUN_10002c50` for IDs `0x3f6`/`0x4f6`/`0x4fe` | (inline) |

Two of the loaders (`IVCS5B.dll`, `IECS.dll`) pull their actual module name from a
runtime config/singleton object (`FUN_101bd974` → vtable+0xc) rather than a hardcoded
string — a configurable plugin architecture, meaning the literal DLL name seen in this
binary's import table may not be the only one ever loaded at that call site.

**What this means for research scope:** `Seed2Key.dll`, `sesame_GM.dll`,
`simsim_GM.dll`, `ivcspsa.dll`, `ivcssgm.dll`, `IVCS5B.dll`, and `DllTzSale.dll` are all
real, load-bearing DLLs in the actual key-computation supply chain for one brand or
another. Only `dllsecurity.dll`, `S84.dll`, and `IECS.dll` (already in the current
13-binary disassembly scope) have been located and disassembled; the rest, including
`IVCS5B.dll`, have not been located on disk and are outside the 64,105-function
disassembly as of the 2026-08-25 session. `S84.dll`'s AES-CMAC (§2 above) is one option among several the platform
supports, not necessarily the one used for this specific vehicle/ECU — this file alone
does not resolve which path a 2024/2025 Chevrolet Silverado uses, only that it is almost
certainly `dllsecurity.dll` or `S84.dll`, not the SAIC/PSA/Nissan branches.
`FUN_10001670`, `FUN_10002a90`, `FUN_100031c0` (called by algorithm IDs `0x206`/`0x207`/
`0x20a` with embedded key constants) are flagged as follow-up candidates just outside
the scoped 30 functions.

This section is coarser than, and defers to, §2's resolved `S84.dll` CMAC detail for
that specific DLL; it is kept because it is the only existing treatment of the other
six OEM dispatch branches and the Layer-1/Layer-2 selector architecture around them.

## 3. Direct T1 level-1 SecurityAccess (2026-11-14)

Live Y175, using Y181B static address-check analysis: logical tester F4, target 0x0084,
custom TCP framing, extended session `10 03`, then `27 01` yielded 31 all-FF bytes;
`27 02` plus 12 zero bytes yielded `67 02`. Default session was restored. See the
[validated T1 sequence](../diagnostics/diagnosticsd_security_access.md#live-t1-securityaccess-correction-2026-11-14).
Earlier NRC `0x10` tests used invalid tester `0x0FA0`. This matches the degenerate MDI2
exchange at the UDS level, but does not prove the exact OBD/gateway/A11 forwarding
chain, arbitrary keys, calibration-write authorization, signature bypass, or root. No
programming write was attempted.

## 4. EEPROM, ADB, ProtoKey, tickets — gate-independence table

| Evidence | Fact and limit | Sources |
|---|---|---|
| Degenerate B+ code | Requires 31×FF seed → 12-zero response → `67 02`. A reported 31B submitted key → `7F 27 13` incorrect length. Not arbitrary content/length/level. | `LIVE_DPS_CAPTURE_ECU80_AUG2026.md` |
| EEPROM B | Minimal data edits `0x0441`/`0x0A81` = FF; framing/markers unchanged. Earlier stock reportedly already has the latter FF; Y181 needs the pair. Successful minimal edit reported without CRC recomputation. Old four-byte recipe/`0x0B41`/marker-gate claims not established as extra gates. Byte-level detail and the marker-vs-data correction owned by `eeprom_i2c_security.md`/`../eeprom/` — not restated here. | `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`, `../eeprom/VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md` |
| VIP S/M | Shared parameterized subsystem; 19-bit accumulation (2–20) ≠ 19 EEPROM flags, universal wire-level behavior, or a direct slot/subfunction map. Full body across Y175/Y177/Y181 refutes the Y177 four-byte-stub theory; 906B size does not identify all wire inputs/secret sourcing. | `../eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md`, `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` |
| ADB S/M | Separate MEC → SoC secure-mode/cert gate: 1–255 reads as bypass; zero/invalid/query failure reads as retained. `persist.gm.adb.secure=1` forces enforcement. UDS seed ≠ ADB auth message. **This row's "1–255 = bypass" reading is one side of the unresolved MEC-semantics question — see [Open Conflicts](#open-conflicts) item 1.** | `../eeprom/EEPROM_Analysis_Report.md` |
| ProtoKey S | 1B request; 17B response = status + 16B key. Full IPC chain traced below in [§5 ProtoKey](#5-protokey--gm_protokey--libpal_securityso-ipc-chain). No key-content crypto found anywhere in the chain; upstream VIP-side producer not thereby characterized. Lifecycle states ≠ UDS levels. | `ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md` (absorbed, see §5) |
| SBAT manual | Rev 1.12 p17: ECU Bypass Ticket for GMLAN/GMUDS; selected deviceID + binary SBAT from the GM Cyber ticket server, independently of DPS. Target eligibility, disabled checks, lifetime, vehicle binding, and edited-cal acceptance unknown. SBAT bypass indicator values cited by one DPS source: `$4444` = bypass inactive (production), `$0080` = bypass active (authorized) `[U]` — unconfirmed against this doc's own live evidence, kept here only as a cited value pair, not a verified gate reading. | `DPS_User_Guide.pdf#page=17` |
| Other manual functions | p27 Vehicle Key Provisioning = vehicle/gateway message-auth keys; p32 Theft Deterrent Security Code = a separate legacy 4B code; pp34–37 CLI `BYPASS_TKT`/server-results support ≠ ticket/secret recovery. | `DPS_User_Guide.pdf` |
| Development/ticket M | `AllowDevSignedVIP`, development-signed `VIP_APP`/`VIP_BOOT`, and the Signature Bypass Ticket ≠ universal unsigned-cal acceptance. Service names/Android enum IDs/EEPROM SBI are not an interchangeable control mapping. | `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`, `../platform/ota_update_stack.md` |

## 5. ProtoKey — `gm_protokey` ↔ `libpal_security.so` IPC chain

Absorbed from the retired `ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md` (2026-08-25
session). This is the headline finding of that doc and the canonical ProtoKey record
for this corpus; the gate-independence table's ProtoKey row above points here rather
than restating it.

**Provenance:** the real raw `SOC_SYSTEM` (3.2GB, `firmware/update_packages/Y181/
86331654`) and `SOC_VENDOR` (466MB, `.../86331650`) partition images were recovered and
read directly with `debugfs` (no mount needed — confirmed real ext4 via superblock +
`AVBf` AVB footer), closing a blocker that had left `gm_protokey` and `diagnosticsd`
"permission denied" on every prior live-device attempt. `/vendor/bin/gm_protokey`
(21,720B, x86-64 PIE ELF, stripped, 160 functions) and `/vendor/lib64/
libpal_security.so` (135,600B, x86-64 ELF, source path embedded:
`/gmplatform/gm/gmsecurity/vip/private/pal_security.cpp`, 509 functions) were both
extracted from `SOC_VENDOR` and fully decompiled.

**`gm_protokey`'s property-write call** (`FUN_001045c0 @ 001045c0`):

```c
void FUN_001045c0(char *param_1)
{
  ...
  iVar1 = property_get("vendor.gm.security.state", local_78, ...);
  if (0 < iVar1) {
    iVar1 = strncmp(param_1, local_78, 0x5c);
    if (iVar1 != 0) {
      property_set("vendor.gm.security.state", param_1);
      __android_log_buf_print(3, 4, "GM_PROTO_KEY",
        "Current security state : %s => %s", local_78, param_1);
    }
  }
}
```

The entire binary contains exactly **four** distinct state-name strings ever passed to
this setter: `"data_locked"`, `"initializing"`, `"warm_reboot"`, `"stopped"`. There is
**no** `"bypassed"`/`"secured"`/`"enforced"`/`"permissive"` string anywhere in the
binary. `vendor.gm.security.state` is a lifecycle/boot-state indicator (has protokey
processing completed, or is data-decryption still gated) — not a direct bypass/
security-outcome flag.

**Full request→response→consumption chain** (`gm_protokey` ↔ `libpal_security.so`'s
`NVipPal`/`CommIPC` transport):

```
gm_protokey main()
  → protokey_pal_register_callback(&FUN_00103a50)   [gm_protokey's callback,
                                                        aka "protokey_pal_set_key"]
    → DAT_00123508 = callback_ptr
    → pal_security_init()                            [libpal_security.so @ 0010f000]
        loops pal_sec_open_ipc_channel() until connected
        → spawns background thread: pal_sec_do_work  [@ 0010d6e0]

pal_sec_do_work()  (background thread loop, while DAT_00123508 != 0)
  → pal_sec_send_protokey_request()  [@ 0010e320]
      CommIPC::writeMessage(ipc_handle, protokey_request_byte, 1)   // 1-byte req to VIP
  → CommIPC::readMessage(ipc_handle, buf, 0x200)                    // blocking read
  → pal_sec_parse_message(buf, len)  [@ 0010e850]
      GATE 1: len == 0x11 (17 bytes: 1 status byte + 16 key bytes) else reject
              ("Wrong protokey size. Expected: %u. Actual: %zu.")
      → pal_sec_check_protokey_status(buf[0])  [@ 0010f4b0]
          GATE 2: switch on VIP's self-reported status byte —
            1 = success (only case returning 0/pass)
            2 = ICUSB not enabled   5 = invalid parameters
            3 = BIS key not valid   6 = ICUSB busy
            4 = protokey gen fail   7 = ICUS key program failed
                                    8 = secret key load failure
            default = "wrong status message"
          any non-1 value → 0xffffffff (fail), loop retries
      if GATE 1 and GATE 2 both pass:
          local_48/uStack_40 = buf[1..16]     // 16 key bytes copied VERBATIM,
                                               // no transform, no check
          (*DAT_00123508)(&local_48, 0x10)    // → calls gm_protokey's FUN_00103a50
          DAT_00123510 = 1                    // "key received" flag

gm_protokey :: FUN_00103a50(key_ptr, key_len)   ["protokey_pal_set_key"]
  __android_log_buf_print(..., "Protokey callback invoked by PAL")
  GATE 3: key_ptr != 0 && key_len != 0   (pointer/length sanity only)
  __android_log_buf_print(..., "Received valid ProtoKey from PAL.")
  → dispatches key via C++ vtable call on a singleton object (DAT_00107d68+0x30)
    (downstream consumer not further resolved — no vold/keystore/fscrypt strings
    found anywhere in gm_protokey, so it is either an internal class or reached
    via a library not covered by the string search)
```

**Headline finding: there is no cryptographic or content validation of the 16-byte key
material anywhere in this chain**, on either the transport library
(`libpal_security.so`) or the consuming daemon (`gm_protokey`). The three gates that
exist are: (1) exact message length, (2) the VIP's own self-reported one-byte status
code, (3) a non-null pointer/length check. None inspects the key bytes themselves — no
entropy check, no known-bad-value check, no signature/MAC. **The entire trust boundary
between the VIP and Android collapses to a single byte: the VIP's self-reported status
code.** If the VIP reports `status = 1`, Android accepts whatever 16 bytes follow,
unconditionally.

This does not by itself prove the EEPROM/SBI bypass forces `status = 1` from the VIP
(that mechanism is VIP-side, in the still-unresolved `FUN_ram_000b67d0` seed/key state
machine — see `../eeprom/VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md`), but it does prove
that **if** the VIP can be made to report success for a degenerate/non-genuine key
(exactly what the SBI-driven CAN `$27` seed evidence in §3/§4 above already suggests),
**there is no independent SoC-side check that would catch or reject it.** The Android
side is a pure length/status gate with no cryptographic verification of its own.

> **Correction to `../platform/security.md`:** that doc's historical "`gm_protokey`
> detects bypass → SELinux PERMISSIVE" framing is doubly wrong per this trace: (1) no
> state string in the binary encodes a bypass/permissive outcome at all — the four
> states are lifecycle-only (`initializing`/`data_locked`/`warm_reboot`/`stopped`); (2)
> nothing in this 160-function binary, nor in `libpal_security.so`, flips SELinux
> enforcement — the trace instead finds a *different*, more specific headline fact (zero
> crypto validation of the 16-byte key, trust collapsing to the VIP's 1-byte status).
> `security.md`'s current text (`security.md` §"ProtoKey / ADB Authentication," dated
> 2026-11-16) already retracts the general "→ SELinux ENFORCING/PERMISSIVE" framing, but
> does not yet carry this specific IPC-chain/zero-validation finding — **that
> propagation is still open; flagged here and in this doc's ledger, not applied, since
> this consolidation pass does not edit `platform/` files.**

Supporting evidence from the same source doc, not previously carried: the ramdisk
sepolicy grep that motivated this trace found `vendor.gm.security.state` read by four
domains (`gm_authManager`, `gmConnectionService`, `platform_app`, `system_app`), backed
by two on-disk paths — `/data/vendor/gm/security/` (labeled `gm_protokey_valid_file`)
and `/data/gmprotokey/` (labeled `gm_protokey_system_file`). Separately (and
unconnected to the ProtoKey chain itself), the same pull also recovered
`/vendor/bin/diagnosticsd` (426,824 B, byte-size-matched to prior live enumeration) from
`SOC_VENDOR`, closing a binary-availability gap for the DoS finding in
`DIAGNOSTICSD_UDS_WORKER_STARVATION_DOS_AUG2026.md`; and separately again, the source
doc's own ramdisk is `ramdisk.cpio.gz` but is actually LZ4-compressed, not gzip (a
provenance-drift note of the same kind flagged elsewhere in this corpus — not to be
confused with `GM_INFO37_BOOT_CHAIN_ANALYSIS.md`'s LZ4 note, which is about the boot
kernel image, a different artifact).

Two ranges of the source doc are **not** carried into this section and are flagged as
unassigned in this doc's ledger rather than restated here without an owner: its §3
(`GMAuthManagerService`/`GMAuthTokenService` decompile — real dealer/Techline ADB-grant
mechanism, confirmed *not* to read `vendor.gm.security.state` and therefore ruled out as
the bypass consumer; class names `GMAdbAuth.java`, `GMAdbPolicy.java`,
`GMAdbAuthService.java`, `GMAdbSocketServer.java`, `GMUpdateCertificate.java`,
`GMOcspCheckFrequencyHandler.java`, `ClientCertificateRevokedReceiver.java`; mechanism is
AES-encrypted policy + VIN/CSM-ID match + X.509 chain + OCSP revocation check) belongs
with a USB-ADB/dealer-cert-auth doc
(`USB_ADB_SESSION_FINDINGS_2026-10-10.md` or `../platform/security.md`), not here; this
is a real, as-yet-unplaced gap this consolidation pass could not close (no target doc in
`/tmp/research_reorg/new/` charters this content), flagged for a future pass. Its own §5
(a correction to `MASTER_REFERENCE.md`'s Y175/Y177/Y181 permissive-behavior table)
is itself superseded — the source doc's own banner says the three-way Y175/Y177/Y181
`VIP_APP` diff found a full ~906-byte validator in **all** builds, no stub in any —
see `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` §2 (carried unchanged; cited, not restated).

## 6. Original Y181 provenance [S/C]

ZIP single member, ext4 image, 3,228,360,704B. Build
`W231E-Y181.3.2-SIHM22B-499.3`, Android 12 / API 32, incremental 231. Read-only
selective extraction. Original `DelayedWKSApp.apk`, 21,185,914B: ZIP CRC pass,
byte-identical to the target development copy. Code is therefore exact stock Y181, not
inference from directory name or CT5. Originals are immutable; temp extracts/decompiles
are supplementary, regenerable, not independent samples.

| Image path | Role |
|---|---|
| `/system/priv-app/DelayedWKSApp/DelayedWKSApp.apk` | Update code; CRC/equality checked |
| `/system/framework/framework-res.apk` | APK platform signer anchor |
| `/system/etc/security/production/signingCA.cer` | Production X.509 CA |
| `/system/etc/security/updatekey/platform.pub` | Separate update public key |
| `/system/etc/security/otacerts.zip` | Recovery/update cert bundle |

Regeneration: extract the original ZIP into isolated temp storage, validate ext4/build/
CRC/byte equality, read listed files using `debugfs` without mounting/modifying the
image.

## 7. CSM calibration format [C]

All 14 stock containers — payload digest, header RSA, signer-record CA signature — each
pass 14/14; RSA-2048/e=65537/PKCS#1v1.5/SHA-256. All 14 share one calibration signer
modulus.

| Half-open bytes | Length | Role |
|---|---:|---|
| [30:62], 0x1E | 32 | SHA256(container[858:]) |
| [62:344] | 282 | Custom signer record authenticated by production CA |
| [88:344], 0x58 | 256 | Big-endian signer modulus |
| [344:600], 0x158 | 256 | CA signature over [62:344] |
| [2:600] | 598 | Signed calibration header |
| [600:856], 0x258 | 256 | Calibration signature over [2:600] |
| [858:end], 0x35A | variable | Digest-covered payload |
| 0x368 | — | Inner gzip begins |

Signer record = subject/certificateID/key-not-beforeID/modulus/root signature; **custom
fixed layout, not X.509**. The external CA is X.509. This refutes a "package format: no
RSA, only hashes" claim; it does not prove verifier invocation on every route.

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

| Mutation | Payload digest | Header RSA | Record CA signature |
|---|---|---|---|
| Stock | Pass | Pass | Pass |
| Payload byte only | Fail | Pass | Unchanged |
| Payload byte + recomputed digest | Pass | Fail | Unchanged |
| Signed-header byte | Unchanged where applicable | Fail | Unchanged where applicable |
| Embedded-modulus byte | Unchanged | Invalidated | Fail |

## 8. Active calibration path and bench results

Exact stock Y181:

| Method | Observation |
|---|---|
| `SignerInfo.verify()` | Complete 282B read → true; no root-signature verification call |
| `CalSignedHeader.verify()` | `SHA256withRSA`, embedded signer modulus |
| `SignedCalibration.verify()` | Calls signer-record/header/digest operations |
| `DiagnosticInstaller.attach(boolean sbi)` | Package attachment gets literal `false`, not the supplied `sbi` |
| `UpdatePackage.attach()` | Handles manifest/signature/module-part; `Envelop` → `false` |
| Original attach bytecode | Packed-switch `Envelop` → default `false`, not merely a JADX decompile omission |

Parsing/primitive byte order inspected. The Java `Envelop` route is still not shown
accepting a live stream. `integrityonly=true` skips a Java verifier, but the inspected
target call passes `false`: **no operational Java signature/root bypass established.**
These Java observations are distinct from the confirmed VIP CAN header-verification
path below.

- **B, Nov 10:** stale-digest modified write → TransferExit NRC 72; digest-correct
  modified write → TransferData block 01 NRC 72; cal slots lost after failed attempts,
  restored with stock LTZ. NRC 72 = general programming failure, not signature-specific.
  Competing explanations (stale per-chunk checksum vs RSA-header gate vs native
  checksum/digest-only) were not isolated by these tests; neither format proof nor a
  failed write identifies the rejecting method.
- **C/S/B, Nov 16:** direct CAN5/CANable stock LTZ and HC writes completed and passed
  restart/readback checks; the HC welcome video was visually confirmed. A stock slot 0C
  container with only one header-signature bit changed, leaving XML/digest/length/
  signed fields intact, was rejected at block 01 with NRC 72; genuine data passed in the
  same session. Repeating the original SXM-disable edit and reading F0F1 before recovery
  yielded **PEC0015**. The matching `VIP_APP` 85759599 reference's header parser at file
  offset 56D50 passes bytes [2:599], signature [600:855], and the signer key to the
  crypto wrapper; its failed-verification branch sets PEC0015, returns zero, and caller
  4F1D0 converts that failure to NRC 72 before SoC calibration init. This confirms the
  tested level-01 CAN5 rejection as a signed-header verification failure. Additional
  Nov 16 SXM-disable trials under session 03/05 reproduced NRC 72 with immediate PEC0015
  and successful genuine slot 0C restoration. Engineering-09 was granted but 021E was
  denied before download. These results do not generalize to every build, transport, or
  security profile. The
  [owning verification record](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-direct-can5-repeat-and-header-signature-rejection-confirmed)
  records hashes, addresses, controls, stock restoration, and limits.
- **S/B, Nov 16, custom acceptance:** separate CAN613/614 development-memory commands
  allowed temporary writes to the two VIP parser marker words. With those words set
  after profile-01 programming entry, the modified SXM-disable slot 0C returned
  `76 01`/`76 02`/`77` and PEC0000. Both RAM words were restored to zero with readback.
  The owner confirmed SXM disappeared from AAOS Radio. This is **not** valid-ticket
  provisioning, key recovery, or an Engineering-09 exemption. A 10.505-second physical
  supply-off cycle then retained SXM disablement, confirmed by the owner with clean
  post-cycle CAN status. See the
  [success record](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-successful-custom-sxm-calibration-through-can613614).
- **B, Nov 16, projection follow-up:** the same temporary-RAM route accepted a slot 0C
  payload retaining SXM-false and adding CarPlay/Android-Auto feature-enable-false
  overrides. Both blocks/exit were positive, PEC0000, verifier words restored; the owner
  confirmed both projection entries disappeared. This candidate has no cold-cycle or
  attached-phone verification yet. See the
  [projection record](DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md#2026-11-16-carplay-and-android-auto-custom-calibration-accepted).
- **S, Nov 16:** the same parser has an exception for a validated SBA-ticket marker, set
  by signed-ticket validation; it is separate from UDS `27` grants. No valid ticket or
  operational CAN/T1 activation has been demonstrated. Signer-record validation precedes
  this header-signature exception.
- **M, native integrity:** per-message additive checksum, XOR `0xA55A`,
  `(sum(body)&0xffff)^0xa55a`; finalization payload SHA-256. Recomputing lower layers ≠
  authenticity bypass.
- **B, Nov 10, stock:** HighCountry → LTZ, 14 containers, finalize/reset/readback, all-FF
  auth, ADB uid 2000 retained, no MEC action. Refutes a universal ADB/programming
  catch-22 for this configuration; not edited-cal acceptance.
- **Conditional format validity:** payload-consistent digest + valid header RSA +
  root-authenticated signer record, plus separate transport/diagnostic-state/framing/
  module/install policies. Modified payload + fixed digest breaks header RSA; the
  matching signer private key could re-sign **if this path enforced it**; an applicable
  exception could change the requirement. Neither the private key nor an applicable
  custom-cal ticket has been demonstrated. Stock signed alternatives are proven; edited
  acceptance is not.

## 9. APK/OTA signing and shared authority

- **C, APK:** original `framework-res`/`DelayedWKSApp` both pass `apksigner verify`,
  Scheme v3, byte-identical DER cert/equal RSA-2048 SPKI; subject CN = `GM Code
  Signature Server`, issuer CN = `GPD`; cert signatures verify under the production CA.
  Only these two anchors were compared, not all GM apps. APK leaf ≠ cal leaf ≠ target OTA
  leaf; also differs from CA/`platform.pub`.
- APK updates/signature privileges require a recognized signer identity/lineage + package
  policy; another CA-issued cert ≠ platform signer. Signature/privileged permissions and
  SELinux/Binder access remain separate concerns.
- **C/S, OTA:** stored SHA-256 matches the manifest; RSA-2048/PKCS1v1.5/SHA-256 manifest
  signature verifies under the SMD leaf; the leaf cert verifies under the production CA.
  The exact Y181 `Signature.java` selects production/development CA and calls
  `untrusted.verify(trusted.getPublicKey())`: a normal manifest route, established —
  unlike the cal `Envelop` route.
- **B, Y175 harness:** stock cert accepted; a replacement self-signed cert →
  `Err_PublicSigningCert`; manifest probe, not a custom CSM test. `Sign Type=NONE` per
  module ≠ a whole update unverified; manifest/hashes/signer/module/boot policy remain.
  `Bypass P/N & Module ID Check` changes identity matching, not a proven signing
  exception. Production USB-notifier/development-cal-override (type 2) selection has
  build/path restrictions; existence ≠ normal production selection.

OTA-only comparison:

| Cohort | Same complete DER certificate/SPKI within cohort | Artifacts |
|---|---|---|
| gminfo Y181/Y181B | Yes | [S42] [S45] |
| CT5/Silverado EV | Yes | [S46] [S47] |

Cohort leaf certs/keys **differ**; all 4 cert signatures verify under the original Y181
production CA. Actual DER/SPKI/signatures were compared, not names alone: this refutes
a universal "`GM Code Signature Server`" leaf-key claim. APK certs and all 14 CSM
signer records also verify under that CA, with distinct leaf keys.

Other anchors: `updatekey/platform.pub` is a separate RSA-2048, not the APK/platform/cal
CA; the "platform" filename does not establish APK identity. `otacerts.zip` /
`releasekey_secure_boot.x509.pem`: a recovery cert, separate RSA-2048, distinct from the
CA/`platform.pub`. Shared root = issuing authority; the corresponding private key could
affect verifiers honoring it **conditional on actual trust/policy**. No root/leaf
private key recovered; no universal private leaf, cross-platform package acceptance, or
Android signer equality follows. Hardware/module/manifest/AVB/GHS/rollback remain out of
scope here.

RSA-1024 hypervisor candidate: parsing/matching public key/function/code use is
pending; not a validated, observed RSA-2048 cal-signer recovery.

## 10. Open questions and historical claims

- Known-secret target vector: resolve normal construction/input mapping, Kscope,
  backend secret boundary.
- The tested Y175 CAN caller/header failure is now identified above (§8). Remaining:
  other transports/builds/profiles, full downstream/root enforcement, and the
  validated-ticket activation path; no custom acceptance has been demonstrated there.
- SBAT: establish target issuance/eligibility/binding/disabled checks.
- A matching Y181B OTA leaf does not establish identical native cal code.
  Cross-platform package acceptance/trust policy is untested; these unknowns do not
  authorize new live actions.
- Older compendia: physical secret storage remains a hypothesis; an encrypted-EEPROM
  reset-payload interpretation is rejected (see `eeprom_i2c_security.md`); a
  bridge-symbol forwarding attribution is retracted (see
  `../diagnostics/ethernet_uds_diagnosticsd.md`); owner downgrade retests refine the
  observed rejection stage without proving the exact rollback-counter layout (see
  `GHS_DOWNGRADE_PROTECTION_ANALYSIS.txt`). Indexed sources are not blanket
  endorsements.

## Open conflicts

1. **SecurityAccess seed length, 31 vs 32 bytes.** This doc's own §1/§2 above (L17-70 of
   the prior revision) treat **31 bytes** (16B ECUID + 15B challenge) as settled, based
   on the normal-grant capture table. `MDI2_DPDU_API_PROTOCOL_AUG2026.md` §6 (L247-260)
   explicitly flags this **UNRESOLVED**: that doc's own earlier text stated a 32-byte
   total (16B ECUID + 16B random), attributed to a live capture, while a second,
   independently and programmatically re-parsed capture from a different physical unit
   shows 31 bytes (16B ECUID + 15B random) — "double-counted by hand and by script," per
   its own words — and notes SecurityAccess seed length should be an ECU firmware
   property, not per-unit-variable, so the two captures disagreeing is itself unexplained.
   The 32-byte figure also traces back further to the retired `DPS_SECURITY_ANALYSIS.txt`
   §4.3.1 ("SEED FORMAT DISCOVERY, December 2025"), which documents a `67 01` response of
   32 bytes total (16B ECUID + 16B "Random Challenge") from `Y177update_CSM.Txt`, plus an
   all-`FF` 32-byte bypassed-state response from `A11_CSM_x80.Txt`. MDP's own report could
   not confirm this doc's 31-byte number closes MDP's doubt, since the two capture sets
   differ. **Not silently resolved here** — carried as open, citing both `MDI2_DPDU_API_
   PROTOCOL_AUG2026.md` §6 and `DPS_SECURITY_ANALYSIS.txt` §4.3.1 (retired, migrated
   verbatim into `DPS_AND_MODIFICATION_LANDSCAPE.txt`, carried unchanged — cited by name/
   section only, not restated at length here).

2. **MEC value semantics.** Whether a nonzero/244-style Manufacturer Enable Counter
   reading means "bypassed/unlocked" or "production/locked" is unresolved across the
   corpus. This doc's own §4 ADB row above states "1–255 = bypass; zero/invalid/query
   failure = retained," consistent with `VIP_CONTROL_ANALYSIS.txt` §5.2 and
   `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`'s convention (nonzero MEC = unlocked/bypass) and
   with `GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md` §2.3.6-7's live per-unit MEC table (MEC
   207/227/241/244/0 observed across Y175/Y181/Y181B) — but that table documents values,
   not the semantic rule. The retired `DPS_SECURITY_ANALYSIS.txt` (§"MEC COUNTER
   OBSERVATIONS"), the retired `GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt`, and the retired
   `PROJECT_MASTER_CHECKLIST.txt` instead read a nonzero/244 MEC as "production/locked" —
   and `DPS_SECURITY_ANALYSIS.txt`'s own 2026-11-12 inline note already flags that its
   "production/locked" label for MEC 244 contradicts its own capture data (the same
   bypassed-state capture that reads MEC 244 also reports "ADB accessible with standard
   platform-tools"). No single doc has closed this across all sources. Per
   `GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`'s own routing and
   `EEPROM_LAYOUT_COMPREHENSIVE_AUDIT.md`'s routing (both named for this item), the
   semantic question stays open in both docs rather than being picked here.

## Related

- `../eeprom/README.md`, `../eeprom/VIP_SBI_WRITE_MECHANISM_TRACE_AUG2026.md`,
  `../eeprom/VIP_SEED_SCOPE_ANALYSIS_AUG2026.md` — EEPROM SBI mechanism (byte-level map
  owner).
- `eeprom_i2c_security.md` (`../platform/`) — EEPROM map/I2C permission owner.
- `VIP_CONTROL_ANALYSIS.txt` — VIP control-scope/CRC/I2C-access owner.
- `CALDEF_VIP_CALIBRATION_ANALYSIS.txt` — CalDef/VIP calibration-index table owner.
- `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` — live CAN613/614 custom-write bench-record
  owner; this doc's Ghidra signature-verification trace is deferred there/here
  reciprocally, not duplicated.
- `CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md` — CalSets.db checksum/container RE owner.
- `SELINUX_VENDOR_CALD_ESCALATION_ANALYSIS.md` — `calserviced`/vendor_cald SELinux
  reachability owner.
- `../platform/security.md` — general SELinux/FBE/CVE/ADB posture owner; carries this
  doc's ProtoKey correction as an outstanding propagation item (see §5 above and this
  doc's ledger).
- `../platform/ota_update_stack.md`, `../platform/ota_programming_roles.md` — OTA
  Binder/state-machine and module-role owners; this doc's §9 is signature/trust-specific,
  not restated there.
- `../diagnostics/diagnosticsd_security_access.md` — live T1 SecurityAccess bench-test
  record owner (§3 above).
- `MDI2_RAW_UDS_BYPASS_GUIDE.md`, `VIP_FIRMWARE_Y177_Y181_COMPARISON.md` — carried
  unchanged; cited by name/section only (§5, §Open conflicts above).

## Sources and coverage

133 text paths = 129 direct full reads + 4 full-content comparisons: fully read external
counterpart plus every differing/added block independently read; not hash-identical
duplicates. Corpus is relevant research, not every file in both trees. Excluded as
proof: conversation/transcripts, raw enumeration/UART catalogs, third-party source
bundles, unrelated vehicle manuals, model/fuzz output; incidental video `RDSEED`.
Relative links are portable; absolute links require a mounted source volume. Source IDs
below are defined once, never reconstructed from aliases.

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

### PDFs: 13 paths / 10 unique

Nine text-bearing unique files: all extracted text/all pages read; embedded screenshots
not all OCRed. One image-only hardware-label PDF: OCR relevance inspection. Duplicate
pairs explicit below.

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

### Captures: 14 paths / 12 unique

Six principal August captures reassembled in supported TCP representations; two
duplicate paths counted once. Remaining six unique/absence scope below.

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
[S2]: <ANDROID_SIDE_PROTOKEY_TRACE_AUG2026.md> — retired; absorbed into this doc's §5 above.
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
[S22]: <TISVCSV4_MULTI_OEM_KEYSERVER_AUG2026.md> — retired; absorbed into this doc's §2.1 above.
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
[S38]: <SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md> — retired; see its own pointer.
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
[S71]: <DPS_SECURITY_ANALYSIS.txt> — retired; verbatim-migrated into [S70], carried unchanged. See [Open conflicts](#open-conflicts) item 1 for the one still-live citation (§4.3.1).
[S72]: <EEPROM_MAPPING_FABLE_REPORT.md>
[S73]: <EEPROM_SECURITY_FLAG_TEST_PROTOCOL.md>
[S74]: <GHS_FILE_MAP_85098662.md>
[S75]: <GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md>
[S76]: <GHS_PRIVACY_CAPABILITY_ANALYSIS.md>
[S77]: <GM_AAOS_SECURITY_RESEARCH_COMPENDIUM.txt> — retired; its §15.9 absorbed into this doc's §1 footnote above.
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
