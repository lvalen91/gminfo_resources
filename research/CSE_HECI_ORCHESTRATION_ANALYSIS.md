# CSE / HECI Command Protocol of the GHS `ota_update` Partition

**Target:** GM Info 3.7 (gminfo37 / A3960), Y181 `W231E-Y181.3.2-SIHM22B-499.3`, INTEGRITY IoT
2020.18.19 `MY22-026`, Intel Apollo Lake (Atom Goldmont, TXE/CSE).
**Method:** Reverse-engineering of recovered GHS `.rodata` string tables and symbol table,
cross-referenced against Intel's open-source `kernelflinger` (`celadon/s/mr0/apollo`) HECI/MKHI
protocol headers.
**Confidence key:** [C] confirmed from artifact · [I] inferred / mapped · [H] hypothesis.

## Sources

- `research/decompiled/ghs_str.txt` lines 38092–38148 — the full `ota_update` HECI/OTA error
  string block (the `.ota_update.rodata` content described in the task).
- `research/decompiled/ghs_analysis.txt` lines 302–333 (addressed strings `0x00df70xx–0x00df77xx`)
  and 696 (`OtaUpdateToHeciIod`), 264/267 (`CseSeed`, `Intel HECI`), 5384/5412
  (`cseseed_iodevice.c`, `intel_heci.c`).
- `~/Downloads/github/kernelflinger/` — Intel's ABL EFI bootloader, the authoritative public source
  for the HECI/MKHI message layer:
  - `libkernelflinger/protocol/MkhiMsgs.h` — MKHI header + group/command opcodes.
  - `libheci/hecisupport.c`, `include/hecisupport.h` — HECI transaction flow (EOP example).
  - `libkernelflinger/protocol/BootloaderSeedProtocol.h` — ATTKB / seed structures.
  - `kf4abl.c` — ABL update / IFWI capsule path.
- `research/GORDON_PEAK_CELADON_INTELLIGENCE.md`, `research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md`,
  `research/HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` — architecture + reachability context.

---

## 1. Architecture — where this code lives

The `ota_update` logic is **not** in the Android guest. It is a native task inside the GHS
INTEGRITY hypervisor (the `iot/rtos` tree — build paths are literally
`/home/mal/gm_release/MY22-026/final/iot/rtos/libs/gm-i35/rel/work/intel_heci.c` and
`.../cseseed_iodevice.c`). The relevant GHS objects (from the symbol table):

```
OtaUpdateToHeciIod        <- the RPC->HECI translator (this protocol)
OtaUpdateBootArgsIod
OtaUpdateBootStatusIod / PassthruBootStatusIod
OTA_InitialTask           <- OTA handling task
IntelHeciInit / TheHeciDevice / IntelHeci_IORegisters   <- HECI PCI driver (intel_heci.c)
CseSeed_Init / CseSeed_CreateIODevice / CseSeed_ReadStatus  <- CSE seed client (cseseed_iodevice.c)
```

Data path (confirmed by strings + node map):

```
Android guest (OTA client)
    │  writes candidate image to inactive slot, then issues OTA RPC commands
    ▼
/dev/ghs/ota-isys   (GHS OTA broker node; DAC rw-rw-rw-, SELinux-gated)
    │  GIPC / VirtIO marshalled RPC  ── "RPC channel error: %d"
    ▼
OTA_InitialTask ──► OtaUpdateToHeciIod   (RPC opcode dispatch + length check)
    │  "Bad command length for OTA command."
    ▼
IntelHeci driver (intel_heci.c)  ── PCI HECI/MEI MMIO doorbell registers
    ▼
Intel CSE / TXE  (Converged Security Engine — the firmware trust anchor)
```

Key architectural fact: **the guest never speaks HECI.** It speaks a small GM RPC verb set to
`ota-isys`; `OtaUpdateToHeciIod` is the *only* thing that builds HECI/MKHI frames and touches the
CSE MMIO. That indirection is the whole security boundary and the crux of the reachability question
(§6).

---

## 2. (a) HECI command opcodes

There are **two layers**. GM's error strings expose both.

### 2.1 HECI Bus-Message (HBM) transport layer — MEI client management

Before any CSE command, `OtaUpdateToHeciIod` runs the standard Intel MEI/HECI connection dance
against a fixed CSE client (address 7 = `PREBOOT_FIXED_SEC_ADDR`, host address 0 =
`BIOS_FIXED_HOST_ADDR`; see `MkhiMsgs.h:27–39`). The error strings map 1:1 onto the MEI HBM opcodes:

| GM error string (`ghs_str.txt`) | MEI HBM operation | HBM opcode [I] |
|---|---|---|
| `HECI enumeration response failed` | HOST_ENUM_REQ | `0x04` |
| `Failed to get HECI client properties` / `Failed to issue read property command for HECI client` | HOST_CLIENT_PROPERTIES_REQ | `0x05` |
| `Failed to send connect message to HECI client` / `Invalid HECI connect status: %d` | CLIENT_CONNECT_REQ | `0x01` |
| `Failed to send disconnect message to HECI client` / `Invalid HECI disconnect status: %d` | CLIENT_DISCONNECT_REQ | `0x02` |
| `HECI read/write timed out waiting for H_IG` / `CSE ready after write` / `IS to be signaled` | doorbell flow-control (`H_CSR`/`SEC_CSR` H_IG/H_RDY/IS bits) | n/a (register bits) |
| `CSE timed out waiting for ready bit after reset` / `Timed out waiting for HECI reset` | HECI reset / SEC_RDY poll | n/a |

The transport frame is the classic HECI packet: **`[HECI header: 32-bit] + payload`**, where the
header is `{ MeAddress:8, HostAddress:8, Length:9, Reserved:6, MsgComplete:1 }`. [I, standard MEI]

### 2.2 MKHI application layer — the message inside the HECI packet

Every CSE command payload begins with a 4-byte **MKHI header** (`MkhiMsgs.h:135–148`, confirmed):

```c
union MKHI_MESSAGE_HEADER {          // 4 bytes total
    uint32_t Data;
    struct {
        uint32_t GroupId    : 8;     // which subsystem
        uint32_t Command    : 7;     // opcode within the group
        uint32_t IsResponse : 1;     // 0 = request, 1 = ACK
        uint32_t Reserved   : 8;
        uint32_t Result     : 8;     // status in the ACK  <-- the "%d" in GM errors
    } Fields;
};
```

Request format: `MKHI_MESSAGE_HEADER + command-specific body`.
Response format: same header with `IsResponse=1` and `Result` set, followed by the ACK body.
The `Result` field is exactly the value GM prints in
`...HECI command failed: %d` / `Get attkb from CSE failed with result=%d`. **A non-zero `Result`
is the CSE rejecting the command** (see §4).

### 2.3 The four `ota_update` CSE opcodes (semantic command set)

From the `.ota_update.rodata` string block, `OtaUpdateToHeciIod` issues exactly **four** distinct
CSE/ABL HECI commands plus the two ATTKB reads. Numeric Group/Command IDs for these are **ABL-BUP
proprietary** and are *not* present in public kernelflinger (kernelflinger only ships the EOP
command, group `0xFF`/cmd `0x0C`, and the MKHI GEN/FWCAPS groups). What is confirmed is the command
*set*, its ordering, and its length-checked request/response shape:

| # | Command (from strings) | Purpose | Confirmed error/success strings |
|---|---|---|---|
| 1 | **ABL update** | Program the Intel ABL bootloader region via CSE-mediated write | `Failed to send ABL update command`; `ABL update command returned invalid length: %d`; `ABL update command failed: %d` |
| 2 | **CSE prepare update** | Put CSE into "prepare update" mode (unlock/stage the firmware region for writing) | `Failed to send HECI command to prepare CSE update`; `CSE prepare update HECI command failed: %d`; `CSE did not enter prepare update mode`; `Invalid response length to CSE prepare update command: %d` |
| 3 | **CSE clear data** | Erase/clear the staged CSE data region | `Failed to send HECI command to clear CSE data`; `CSE clear data HECI command failed: %d`; `CSE clear data HECI command accepted`; `Invalid response length to CSE clear data command: %d` |
| 4 | **GET ATTKB SIZE** → **GET ATTKB** | Retrieve the Attestation Key Box (size query, then bulk read) | `Failed to send GET ATTKB SIZE HECI command`; `Failed to send GET ATTKB HECI command`; `Get attkb from CSE failed with result=%d`; `ATTKB is larger (%d bytes) than data buffer (%ld bytes)`; `Read more attkb bytes (%d) than expected (%d)`; `Read incorrect number of bytes (%d)` |

ATTKB context (`BootloaderSeedProtocol.h`): the ATTKB is the CSE-held attestation keybox, decrypted
with a 32-byte `attkb_enc_key` derived from the SVN-bound bootloader seed
(`BOOTLOADER_SEED_INFO`, `cse_svn`/`bios_svn` fields). The `GET ATTKB` pair is the two-phase
"ask size, then read N bytes" pattern — the classic overflow-prone HECI idiom (§5).

---

## 3. (b) State machine

Reconstructed from the command ordering and the mode strings (`prepare update mode`,
`clear data ... accepted`). This is the ABL-update flow the task's "CSE prepare update → clear data
→ ABL update" string sequence encodes:

```
        ┌──────────────────────────────────────────────────────────────┐
        │  IDLE                                                          │
        │   guest issues OTA RPC over /dev/ghs/ota-isys                  │
        └───────────────┬──────────────────────────────────────────────┘
                        │ RPC dispatch: "Bad command length for OTA command." gate
                        ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  HECI CONNECT   (enumerate → get-props → connect to CSE fixed  │
        │  client 7)      fails: enumeration/props/connect status errors │
        └───────────────┬──────────────────────────────────────────────┘
                        ▼
   (1)  ┌──────────────────────────────────────────────────────────────┐
        │  PREPARE UPDATE   send "CSE prepare update"                    │
        │  verify: Result==0 AND response length valid AND CSE reports   │
        │          it entered prepare-update mode                        │
        │  fail → "CSE did not enter prepare update mode" → ABORT        │
        └───────────────┬──────────────────────────────────────────────┘
                        ▼
   (2)  ┌──────────────────────────────────────────────────────────────┐
        │  CLEAR DATA       send "CSE clear data"                        │
        │  verify: Result==0 AND response length valid                   │
        │  success → "CSE clear data HECI command accepted"              │
        └───────────────┬──────────────────────────────────────────────┘
                        ▼
   (3)  ┌──────────────────────────────────────────────────────────────┐
        │  PROGRAM (ABL update)   send "ABL update" command(s)          │
        │  verify: Result==0 AND returned length valid                  │
        │  fail → "ABL update command failed: %d" → ABORT               │
        └───────────────┬──────────────────────────────────────────────┘
                        ▼
   (4)  ┌──────────────────────────────────────────────────────────────┐
        │  ATTKB REFRESH / VERIFY   GET ATTKB SIZE → GET ATTKB          │
        │  (re-fetch attestation keybox bound to new SVN; bounds-check) │
        └───────────────┬──────────────────────────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  DISCONNECT + A/B metadata write                              │
        │  "VMM: A/B boot metadta write failed."  → then EOP + reboot   │
        │  (ABL recovery variant: EFI IfwiCapsuleUpdate + capsule_name) │
        └──────────────────────────────────────────────────────────────┘
```

**Ordering rationale [I]:** prepare-update *unlocks/stages* the region (must succeed and be
confirmed via a mode read-back before anything is touched), clear-data *erases* the staged region
(idempotent, ACK'd), ABL-update *writes* the new image, ATTKB read *re-binds* attestation to the new
SVN. Each stage is gated on the previous stage's `Result==0` and a response-length check — the state
machine will not advance on a short/oversized response. This is a **fail-closed** design at every
edge.

The EFI-variable path (`IfwiCapsuleUpdate` / `/sys/kernel/capsule/capsule_name m1:@0`, from
`kf4abl.c` + init.rc) is the **alternate/recovery** programming route used when the live HECI path
is unavailable — the same firmware region, reached at next boot via ABL capsule instead of runtime
HECI.

---

## 4. (c) CSE validation gates

CSE validation happens at three tiers; the `ota_update` task only sees the *results* of the CSE-side
checks (via the MKHI `Result` byte) plus its own client-side sanity checks.

**Tier 1 — GM `ota_update` RPC guard (in `OtaUpdateToHeciIod`), before any HECI:**
- **Command length check:** `Bad command length for OTA command.` — the RPC verb + its argument
  length are validated before dispatch. First and cheapest gate.
- **RPC channel integrity:** `RPC channel error: %d`.

**Tier 2 — HECI/MKHI response validation (client-side, in GHS):**
- **`Result` field must be 0** (`SEC_SUCCESS`, `MkhiMsgs.h:65`). Non-zero → the `...failed: %d`
  strings. The CSE-side reasons enumerated in the header: `SEC_INVALID_MESSAGE (0x02)`,
  `SEC_M1_DATA_OLDER_VER (0x03)`, `SEC_M1_DATA_INVALID_VER (0x04)`, `SEC_INVALID_M1_DATA (0x05)`,
  `SEC_ERROR_ALIAS_CHECK_FAILED (0x01)`.
- **Response-length validation** on *every* CSE reply: `Invalid response length to CSE prepare
  update command`, `Invalid response length to CSE clear data command`, `ABL update command
  returned invalid length`. The state machine treats a wrong-length ACK as failure.
- **Mode read-back:** prepare-update is only accepted if CSE actively confirms it entered
  prepare-update mode (`CSE did not enter prepare update mode`) — not merely a success code.
- **ATTKB bounds check:** `ATTKB is larger than data buffer`, `Read more attkb bytes than
  expected`, `Read incorrect number of bytes` — explicit size gate before/after the bulk read.

**Tier 3 — CSE firmware-internal validation (inferred from Intel CSE semantics + the `Result`
codes above):**
- **Signature / manifest:** the ABL/IFWI image programmed through the CSE update path is validated
  against the CSE's firmware manifest chain. `SEC_INVALID_M1_DATA` / `SEC_M1_DATA_INVALID_VER` are
  M1-manifest validation results — the CSE checks the update payload's signed manifest. This is the
  **Boot Guard / CSE-anchored signature gate**; the private key is not in any extracted artifact.
- **Anti-rollback (SVN):** `SEC_M1_DATA_OLDER_VER (0x03)` is the CSE refusing a *downgrade* — the
  update's Security Version Number is compared against the CSE-fused minimum SVN. This is the
  firmware-level enforcement that blocks Y181→Y177 (`GORDON_PEAK_CELADON_INTELLIGENCE.md`: "anti-
  rollback version enforcement" in the HECI/CSE layer). The seed/ATTKB are **SVN-bound**
  (`BOOTLOADER_SEED_INFO.cse_svn`), so a successful rollback would also break attestation — a second
  interlock.
- **Length/format:** CSE validates payload length and message structure server-side, surfacing as
  `SEC_INVALID_MESSAGE`.

**Net:** signature (M1 manifest), version/rollback (SVN vs fuse), and length/format are all checked
*inside* CSE; GHS adds independent length + mode-confirmation checks on top. Every gate is
fail-closed.

---

## 5. (d) Fuzz targets — malformed HECI/RPC that could break it

Ranked by attack surface reachable and by the client-side handling that the strings reveal:

1. **`OtaUpdateToHeciIod` RPC length dispatcher (highest value).** The `Bad command length for OTA
   command.` gate is the first parser on untrusted guest input. Fuzz: RPC verb ID sweep (find
   undocumented opcodes beyond the 4 known), argument length = {0, 1, MAX-1, MAX, MAX+1, 2³²-1},
   and length-field vs actual-payload mismatch. Goal: reach a HECI-frame builder with attacker-
   controlled length that skips the guard.

2. **ATTKB two-phase read (GET ATTKB SIZE → GET ATTKB).** Classic size-then-read TOCTOU / integer
   handling. The three distinct guard strings (`larger than data buffer`, `more bytes than
   expected`, `incorrect number of bytes`) prove the developers were worried here — fuzz a CSE (or
   a MITM on the HECI response) that returns: size=0, size > buffer, size that passes the first
   check but streams more bytes, and off-by-one byte counts. Target: heap/stack overflow in the
   ATTKB copy, or a `%ld`/`%d` size confusion (note the format string mixes `%d` and `%ld` — signed
   32/64 mismatch is a real risk).

3. **HECI response-length parser for prepare/clear/ABL.** Each command has an `Invalid response
   length` path — fuzz truncated, oversized, and fragmented multi-packet HECI responses
   (`MsgComplete` bit toggling; `Attempting to read too much data from HECI` string shows a read-
   sizing path). Target: the reassembly buffer.

4. **MEI HBM state confusion.** Send connect/disconnect/enumerate out of order or with bogus
   status codes (`Invalid HECI connect status: %d`, `Invalid HECI client property status: %d`) to
   desync the client state machine, especially around the reset/timeout paths
   (`Timed out waiting for HECI reset`) — a use-after-reset of the client structure.

5. **State-machine edge skipping.** Try to drive ABL-update (program) without a preceding accepted
   prepare/clear, or replay `clear data` mid-program, to test whether the sequencing gate is truly
   enforced server-side or only advisory in GHS.

6. **Format-string / textlog sink.** The audit/textlog path (`%s: Dropped textlog message`, adjacent
   in the same string table) is a downstream sink for these `%d`/`%s` error prints — worth checking
   whether any attacker-influenced field reaches a format string.

The **CSE itself** (Tier 3) is the hardened target: fuzzing the M1 manifest, SVN field, and payload
length via crafted ABL-update bodies tests the signature/rollback gates — but requires already being
able to emit arbitrary HECI frames (i.e., you must win #1 first, or have hypervisor-level access).

---

## 6. (e) Reachability — can a guest IPC message hit CSE directly?

**Short answer: not directly, and not today from the shell.** The design interposes
`OtaUpdateToHeciIod` between the guest and the CSE MMIO precisely so the guest cannot form HECI
frames. A guest RPC to `/dev/ghs/ota-isys` reaches CSE only *through* the four validated verbs.

**The gates between a guest and CSE:**

1. **SELinux on `/dev/ghs/ota-isys`.** DAC is `rw-rw-rw-`, but the shell domain is denied. Reaching
   the node needs a less-restricted domain (a compromised system/vendor service) or a policy
   escalation. This is the primary barrier from an unprivileged guest.
   (`HARDWARE_HYPERVISOR_ATTACK_VECTORS.md` §"/dev/ghs/* IOCTL Interface".)
2. **Unknown ioctl/RPC framing.** The `ota-isys` dispatch table is not recovered — the `ghs_probe`
   tool exists but was never built, and the ioctl values are guesses pending
   `/system/lib64/libghs_lip.so` RE. So even with node access, the RPC verb encoding must be
   reversed first.
3. **The `Bad command length` RPC guard** (§4 Tier 1) — first parser on guest bytes.
4. **CSE-internal signature + SVN validation** (§4 Tier 3) — even a perfectly-formed ABL-update
   command cannot flash unsigned or downgraded firmware; CSE rejects with `SEC_INVALID_M1_DATA` /
   `SEC_M1_DATA_OLDER_VER`. The signing key is absent from all artifacts.

**Where a guest *can* get leverage:**
- **The RPC→HECI translator is the real target.** If `OtaUpdateToHeciIod` mis-handles a crafted
  length/opcode (§5 #1–#3) *before* CSE validation, a guest could corrupt GHS hypervisor memory —
  which is far more valuable than flashing (GHS is the trust root above CSE for the rollback
  counter). This is a memory-safety attack on the *broker*, not a protocol attack on CSE.
- **Rollback-counter angle.** The documented interest in `ota-isys` is that it "owns the misc/vda9
  rollback counter." A native rollback verb likely exists (legitimate downgrade support). If that
  verb is reachable and under-validated, it is a downgrade primitive that sidesteps the *GHS*
  counter — but the *CSE* SVN fuse still independently blocks a firmware rollback, so this would
  weaken AVB/GHS rollback protection, not CSE's.
- **No-IOMMU DMA bypass (out of band).** `intel_iommu=off` is confirmed. A DMA-capable device could
  in principle write GHS/TXE-managed RAM directly, bypassing the RPC path entirely — but that is a
  hardware/DMA attack, not "a guest IPC message."

**Conclusion:** A guest IPC message **cannot be crafted to command CSE directly** — it is always
mediated and validated by `OtaUpdateToHeciIod`, and CSE independently enforces signature + rollback.
The realistic exploit target is a **memory-safety bug in the GHS RPC→HECI broker** (ATTKB size
handling and the RPC length dispatcher are the standout candidates), reached only after clearing the
SELinux gate on `/dev/ghs/ota-isys` and reversing the `ota-isys` RPC framing (needs `libghs_lip.so`
RE). Compromising the broker yields hypervisor-memory corruption; it does **not** yield arbitrary
firmware flashing, which stays behind the CSE M1-manifest + SVN fuses.

---

## 7. Open items / next RE steps

- **Recover the numeric Group/Command IDs** for prepare-update / clear-data / ABL-update / GET-ATTKB.
  They are ABL-BUP messages not in public kernelflinger. Best sources: disassemble the code around
  `OtaUpdateToHeciIod` (`ghs_analysis.txt` symbol `010d98d8`) to read the MKHI header immediates, or
  diff against Intel Slim Bootloader / ABL BUP HECI client sources.
- **Reverse `/system/lib64/libghs_lip.so`** to get the real `ota-isys` ioctl/RPC dispatch table
  (unblocks fuzz target #1 and the reachability question).
- **Build `ghs_probe`** (`research/tools/ghs_probe/`, NDK r25+) and deploy in an automotive-permitted
  domain to enumerate the `ota-isys` verb space empirically.
- **Confirm ATTKB `%d` vs `%ld` size types** in the disassembly — signed/width confusion is the
  highest-probability memory-safety bug from the string evidence.
