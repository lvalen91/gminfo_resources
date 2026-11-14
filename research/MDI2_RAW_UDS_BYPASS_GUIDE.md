# MDI2 Raw UDS/J2534 Bypass — Sending Arbitrary Diagnostic Commands Outside DPS

**Date:** 2026-08-17
**Context:** The owner has a legitimate Bosch GM MDI2 + GM DPS tools, but needs to send raw UDS services (e.g. `$27` SecurityAccess, `$34/$36/$37` calibration transfer) for bench testing, outside the constrained SPS/DPS workflow.
**Summary:** DPS wraps its transport with SPS policy; the MDI2 itself is a raw UDS/CAN/DoIP
transport with no hardware-level lock, and **can carry arbitrary UDS commands** when driven
directly, via open-source libraries.

> **CORRECTION (superseded by the 2026-08-24+ D-PDU capture work in
> `MDI2_DPDU_API_PROTOCOL_AUG2026.md` and the AUG24-25 disassembly review):** the specific
> mechanism claimed below in Route A — sending raw UDS through the J2534 `PassThruWriteMsgs()` /
> `PassThruReadMsgs()` read/write API — is **not** how UDS actually reaches the wire on this
> stack. In the full DPS/Manager disassembly and live captures, only
> `PassThruOpen`/`ReadVersion`/`Connect`/`Ioctl`/`Disconnect`/`Close` are ever observed on the
> J2534 layer (`bvtx4j32.dll`); the `PassThru*Msgs` read/write pair is never used to move
> diagnostic payload. Real UDS is tunnelled underneath, over the MDI2's **proprietary
> ISO-22900-2 D-PDU API channel on TCP/10123** (`PDUStartComPrimitive`, fully documented in
> `MDI2_DPDU_API_PROTOCOL_AUG2026.md`), or — when a DPS session is configured with the
> `DoIP (Optimal)` subtype — over **raw ISO-13400 DoIP via `GM_DOIP_32.dll`**. Route B (DoIP +
> open-source `udsoncan`) below therefore remains a viable raw-UDS path; **Route A's
> "PassThruWriteMsgs/PassThruReadMsgs" framing does not, and its "confirmed J2534 exports" claim
> is withdrawn.** The hardware-has-no-lock thesis stands; the transport used is D-PDU/DoIP, not
> J2534 PassThru message read/write.

---

## 1. Architecture: MDI2, DPS, and J2534

```
┌─────────────────────────────────────────────────────────────┐
│                    MDI2 (Bosch)                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ J2534 PassThru API (all transports)                  │   │
│  │  ├─ USB J2534 (Windows native)                       │   │
│  │  ├─ WiFi J2534 (Windows native)                      │   │
│  │  ├─ Bluetooth J2534 (Windows native)                 │   │
│  │  └─ Ethernet DoIP/UDS (any OS: Linux/macOS/Win)      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │ (J2534 API calls)           │ (DoIP Ethernet)
         │                             │
    ┌────┴────────────┐        ┌──────┴───────────────┐
    │ DPS             │        │ python-can /         │
    │ (SPS workflow   │        │ udsoncan /           │
    │  wrapper only)  │        │ doipclient (open)    │
    └─────────────────┘        └──────────────────────┘
      ✗ Raw UDS                  ✓ Raw UDS / $27 / Cal
```

**Key insight:** DPS constrains itself to SPS-signed bundles. But the **underlying MDI2 J2534 layer has no such constraint** — it's just a CAN/UDS/DoIP transport. Accessing J2534 directly or via DoIP bypasses DPS's policy.

---

## 2. Three Routes to Send Raw `$27`

### Route A: Windows J2534 Client (Direct USB/WiFi/BT)

**Capability (WITHDRAWN — see the correction in the Summary above):** this route was written on
the assumption that raw UDS could be sent via `PassThruWriteMsgs()` + `PassThruReadMsgs()`. Those
message read/write calls are **not** observed on this stack's J2534 layer (`bvtx4j32.dll` uses
only `Open`/`ReadVersion`/`Connect`/`Ioctl`/`Disconnect`/`Close`); real UDS moves over the
proprietary D-PDU API on TCP/10123 (or raw DoIP), not through `PassThru*Msgs`. Prefer Route B, or
the D-PDU flow in `MDI2_DPDU_API_PROTOCOL_AUG2026.md`. The steps below are retained only as the
original (now-refuted) framing.

**Approach:**
1. Write a Win32 C/C++ program using the J2534 API (or use an existing open-source J2534 client).
2. Call `PassThruOpen()` → `PassThruConnect()` → `PassThruWriteMsgs()` to send raw UDS.
3. Example frame for `$27 01` (request seed, level 1):
   ```c
   // CAN frame: [0x62F] = Infotainment CSM (0x7DF transmit → 0x7DE receive)
   // Payload: 02 27 01 [checksum]
   unsigned char frame[] = {0x02, 0x27, 0x01, 0xCC};  // length + service + level + CRC
   PassThruWriteMsgs(..., &frame, ...);
   ```

**Caveats:**
- Requires reverse-engineering or modifying DPS to expose J2534 calls (DPS doesn't expose raw `PassThru*` APIs).
- Windows-only (USB/WiFi/BT J2534 drivers are Windows-native).
- **Not recommended** unless you're comfortable with Win32 API or modifying closed binaries.

### Route B: Python `udsoncan` + MDI2 DoIP (Recommended for Bench Testing)

**Capability:** The MDI2 has a **native DoIP (Ethernet) interface** that speaks UDS directly, accessible on any OS.

**Setup:**
```bash
# Install open-source UDS stack
pip3 install udsoncan doipclient python-can

# Verify MDI2 Ethernet connectivity
# MDI2 DoIP default: 192.168.x.x (check your network, or MDI2 manual)
# Standard DoIP ports: TCP/UDP 13400
```

**Bench Test: Send `$27` and Check the Seed**

```python
#!/usr/bin/env python3
"""
Bench test: send $27 SecurityAccess via MDI2 DoIP to CSM (0x745F, radio module).
Expects all-0xFF seed if EEPROM SBI is flipped to bypass.
"""

from doipclient import DoIPClient
from udsoncan.client import Client
from udsoncan import services
import struct

# Connect to MDI2 DoIP interface
# MDI2 Ethernet IP: 192.168.x.x (depends on your setup; check with ifconfig/ipconfig)
# Target: CSM (Infotainment) = 0x745F in DoIP address format
mdi2_ip = "192.168.1.100"  # ADJUST to your MDI2 Ethernet IP
csm_addr = 0x745F  # CSM DoIP target address

# Establish DoIP connection
conn = DoIPClient(mdi2_ip, 13400, None, csm_addr)

# Create UDS client
client = Client(conn)

try:
    # Connect to the ECU
    print("[*] Connecting to CSM via DoIP...")
    client.open()
    
    # Send $27 01 (request seed, level 1)
    print("[*] Sending $27 01 (SecurityAccess request)...")
    seed_response = client.send_request(services.SecurityAccess.Request(level=1))
    
    print(f"[+] Seed received: {seed_response.get_payload().hex().upper()}")
    
    # Check if it's all-0xFF (bypass indicator)
    seed_bytes = seed_response.get_payload()
    if seed_bytes == b'\xFF' * len(seed_bytes):
        print("[SUCCESS] Seed is all-0xFF → EEPROM bypass is ACTIVE")
        print("          Programming-level $27 is bypassed; key can be anything")
    else:
        print(f"[INFO] Seed is NOT all-0xFF → real challenge present")
        print(f"       Seed length: {len(seed_bytes)}, content: {seed_bytes.hex()}")
    
    # Optionally send $27 02 (submit key) — for all-0xFF bypass, any key works
    if seed_bytes == b'\xFF' * len(seed_bytes):
        print("[*] Sending $27 02 with dummy key (0x00000000)...")
        key_payload = b'\x00\x00\x00\x00'
        client.send_request(services.SecurityAccess.Request(level=2, key=key_payload))
        print("[+] Key accepted (or in bypass mode, check response)")
    
finally:
    client.close()
    print("[*] DoIP connection closed")
```

**How to run:**
```bash
python3 mdi2_seed_test.py
# Output: [SUCCESS] Seed is all-0xFF → EEPROM bypass is ACTIVE
#         OR
#         [INFO] Seed is NOT all-0xFF → real challenge present
```

**Advantages:**
- Open-source, cross-platform (Windows/Linux/macOS).
- Doesn't depend on DPS or Windows J2534 drivers.
- MDI2 DoIP is the native "all transports" interface.
- Can be scripted for batch testing.

### Route C: Pre-built J2534 GUI Client (If Available)

**Option:** Some vendors ship J2534 client GUIs (e.g. Pcan-View for CAN, or third-party UDS testers). If you have one, it can speak to the MDI2's USB J2534 interface and send raw frames.

**Status:** Unknown if GM ships such a tool; DPS itself doesn't expose raw J2534 to the user.

---

## 3. Calibration Write Flow (After `$27` Bypass)

> **Implementation correction 2026-11-07:** the current live adapter and gated CLI are in
> `mdi2_client/mdi2/live_calibration.py` and `live_programming_transport.py`; simulator-only
> status notes below describe earlier stages. A nested wire-header bug in the live one-shot
> sender has been fixed and covered by a capture-byte regression. The earlier `0x2830`
> rejection does not prove a power-mode or resource-lock cause. The live preflight now permits
> the documented High Country source profile (the radio previously matched it 14/14) or LTZ,
> without relaxing the fourteen target LTZ hashes. BCM OFF checks, an acknowledged hard reset,
> fresh identity/source verification and one post-reset voltage sample precede programming.
> These implementation checks do not establish that a live write has succeeded. The corrected
> transport still needs live revalidation; consult the client README for current behavior.
>
> **LIVE EXECUTION 2026-11-10:** this transport performed and completed a full live LTZ
> calibration write to radio `0x80` via the stock-SPS method (`write_ltz_calibration`,
> `pre_reset=False`): 14 containers transferred, finalization (`F198`/`F199`/`31 01 039B`/`F190`
> VIN/`11 01` reset) sent, and readback confirmed. Post-reset verification showed `F182` profile
> flipped High Country -> LTZ (14/14 per-slot records matching the package), `F199` programming
> date equal to the write date, all 14 `F0F0` slots present, VIN intact, and the module rebooted
> and responded. Two bugs were caught live and fixed (see the client README and
> `SPS_RECAL_UDS_SEQUENCE_AUG2026.md` [**file not found in repo, 2026-11-12** — `find`/`rg` over
> the full tree returns no match; the bug detail below is retained from this doc's own prose,
> not re-verified against that source] for specifics: a missing `0x85`/`0x28` prefix-length entry
> plus a required `28 03 01` communicationType byte, and a required `10 01` default-session
> link-bounce before `10 03` at finalization). The SecurityAccess exchange used in this write was
> the degenerate all-FF path (this module is SBI-flipped); the example below remains unverified
> as written, and the real-seed CMAC path is still unverified on any hardware.
>
> **2026-11-07 correction — example below is not a validated programming client.** The all-FF
> level-1 exchange does not establish programming-level authorization, and the example does not
> validate the negotiated maximum block size, every response, pending handling, timeouts or the
> complete pre/post-programming sequence. Signature and checksum claims below are unverified for
> the captured CSM containers. Do not execute this example as a flash procedure.
> **Update 2026-11-10:** the degenerate all-FF exchange IS now shown to grant programming-level
> authorization on this SBI-flipped module — see the live-execution note above. The example code
> itself (block size, pending handling, timeout, full sequence) remains distinct from, and less
> complete than, the client that actually performed the live write.
>
> Offline verification of the SPS capture `SPS_radioCal_and_OS_UpdateCHeck.pcapng`, D-PDU
> stream 317, reconstructed 14 RequestDownload/TransferData/TransferExit sequences. Every
> reconstructed payload matched the SHA-256 of the corresponding decompressed, unmodified cached
> LTZ CSM file, slots 02–0F in order; all declared sizes matched. In that capture the largest
> TransferData request is 4095 bytes including service and block counter (4093 data bytes), not
> 4096 data bytes. The paired event stream 318 contains 14 positive `74 20 0F FF` download
> replies, 19 positive `76` transfer replies and 14 positive `77` transfer-exit replies; it also
> contains `7F .. 78` response-pending events. This is evidence of the historical transaction,
> not acceptance by the current ECU or that replaying the complete capture is safe.
> Each cached part has an outer gzip wrapper. SPS transmitted the decompressed outer contents
> byte-for-byte: the complete CSM container, including its slot metadata and still-compressed
> inner CalOvride XML. For example, slot 04's 14,208-byte cache file becomes a 15,284-byte CSM
> container, which is exactly the captured transfer payload. No captured file required editing
> the inner XML. This byte comparison does not establish any signature verification algorithm.
> `mdi2_client/mdi2/calibration_payloads.py` now validates the 14 cached CSM/XML containers and
> builds the transfer requests offline. Its complete 47-request output was checked byte-for-byte
> against the historical LTZ capture. `mdi2/calibration_transaction.py` implements an experimental
> transaction against an injected simulated transport, with response and failure handling, a
> separately pinned LTZ reference manifest, an expected-VIN check and an adapter-size cap. It
> has no live adapter or CLI. Socket framing and response correlation, bounded sends, periodic
> TesterPresent, initial reset, recovery, finalization policy and post-reboot verification remain
> unvalidated; these components must not be treated as a working live D-PDU writer.
> The strict `mdi2/captured_events.py` parser matches the recorded receive-event layout and was
> checked against 87 captured radio responses. It is not a complete socket adapter: the captured
> receive events share a persistent receive COP, so they cannot by themselves distinguish a late
> prior response from a later same-service response. The production integration must also pin
> `LTZ_REFERENCE` independently rather than derive a manifest from the package under test.
> The experimental `mdi2/capture_read_transport.py` only accepts individual UDS DID reads on
> already configured links. It rejects programming, reset and security services and has only
> fake-socket tests; it does not start PDU, configure or prove cleanup of cyclic links. It is not
> a programming adapter or an unattended flash path. A queued matching response may be mistaken
> for a fresh response, and periodic TesterPresent lifecycle/error handling is not established.
>
> The separate cached `10017461.cfx` identifies action 2058 as `Power Mode Control Off` and
> the paired `10017550.dll` dispatches that action to `FUN_10003f40`, which reads BCM DID F085
> and contains a wait for value `00`. Its relationship to the calibration programming phase is
> not yet established. The data-wipe action's F085 `02` precondition must not be generalized to
> calibration. A verified power supply, ECU compatibility, exact state sequence and error/recovery
> handling are required before a live write.
> **Satisfied live 2026-11-10:** these preconditions were met for the live LTZ write —
> key/accessory OFF (BCM `F085`=0x00), battery alone at ~12.3-12.7 V, matching ECU/profile
> identity, and the documented state sequence; see `mdi2_client/README.md` and
> `SPS_RECAL_UDS_SEQUENCE_AUG2026.md` [**file not found in repo, 2026-11-12**] for the executed
> sequence and outcome.
> An independent offline inspection of the SPS calibration capture found BCM response
> `62 F0 85 00` in event stream 297, before the radio programming stream 317/318. This supports
> OFF as the mode observed before that run, but does not establish the value throughout every
> download or prove it alone caused the calibration to be accepted. The captured programming
> security exchanges used non-FF seeds; the separately observed all-FF exchange was a different
> state, and a key captured for another challenge must never be replayed.
> The locally saved 2024 Silverado 2500 A11 service procedure specifies starting with the vehicle
> OFF, stable programming power, PARK and the driver's door closed; SPS may change module power
> modes during its sequence. It explicitly instructs a GDS2 radio MEC reset after programming,
> unless already zero. This is a documented separate service step, not proof SPS automatically
> invokes it during every calibration or information read. The same procedure contains recovery
> instructions involving a full power removal and an SPS retry; applicability to interruption
> of this experimental Python path is unverified. See the saved A11 Radio Programming and Setup
> article in the local 2024 Silverado service-information tree.
>
> **Stock-package readback comparison:** `mdi2_client/calibration_compare.py` parses F182's
> seven-byte slot records and compares their type, CVN and revision against the metadata in
> each stock CSM container. The saved DPS read matches the High Country package in all 14
> slots and the LTZ package in 11/14; slots 02, 04 and 05 differ. A later direct F182 read
> using capture-derived link setup returned the same result on the current radio: High Country
> 14/14, LTZ 11/14. Neither read proves whole-payload identity. In the captured write, the
> RequestDownload address is zero for each block while the transferred CSM container has its
> own slot identifier; this supports file-carried targeting but the ECU-side mapping is untraced.
> The direct Python D-PDU live read attempt failed at CreateCLL with status bytes `1c280000`;
> the generated 13-byte CreateCLL payload differs from the 46-byte captured payload, so the live
> typed client and programming code must not be treated as verified. The later successful read
> used capture-derived setup; the captured CreateCLL reply is a four-byte status and the client
> supplies the CLL handle. No radio reset or programming was sent during that read.
> The captured radio request order is level-1 SecurityAccess, `31 01 02 49`, `10 02`, fourteen
> downloads, `22 F0 F0`, another level-1 SecurityAccess, writes to F198/F199, `31 01 03 9B`,
> write to F190 and `11 01`. The semantics of both RIDs and whether an additional reset is
> technically necessary are unproven. **Owner requirement for this live test:** perform a radio
> hard reset (`11 01`, positively acknowledged with `51 01`) before programming, then reconnect,
> re-establish the diagnostic session and confirm radio response and vehicle identity. If reset,
> reconnection or verification fails, do not issue any programming request. Immediately before
> calibration, take one MDI2 voltage sample and require at least 12.000 V, per owner request;
> the simulator also rejects readings over 30.000 V as invalid data, not as an approved upper
> programming-voltage limit. This threshold does not establish a reliable supply. The owner did not request in-transfer
> voltage monitoring. Keep the separately captured end-of-programming reset. A simulator models
> the pre-reset but it cannot establish a real reboot or usable live link; no live entrypoint may
> bypass it. A correct client must derive and validate the live security
> exchange, preserve the vehicle's own identifiers, wait for pending responses and handle errors;
> it must not replay stale captured keys or vehicle-specific identifier writes.
> **Resolved live 2026-11-10:** `mdi2_client`'s live transport is this correct client — it
> performed a real reboot (`11 01`/`51 01`), derived the live SecurityAccess exchange (degenerate
> all-FF, since this module is SBI-flipped), preserved the vehicle's own VIN, waited for pending
> responses, and handled errors (see the two live-caught bugs noted above and in the client
> README). It did not replay a stale captured key.
> On 2026-11-07 the owner confirmed the radio display was on with engine and accessory mode off;
> a subsequent reset attempt received extended-session and level-1 security acknowledgements,
> followed by `51 01` for `11 01`. An earlier direct reset in the active session returned
> `7F 11 7F`; the successful attempt changed the diagnostic session and completed security
> access. The observed power and display state is the owner's test prerequisite, but this
> observation alone does not establish which condition caused the difference or prove that it
> is sufficient for calibration programming.
> Capture detail: after F0F0 the SPS client destroyed its tester-present CLL and disconnected
> and destroyed the radio CLL, then created new radio and tester-present CLLs before the second
> security exchange and finalization. The simulator now requires a finalization-reconnection
> callback, rejects reuse of the same transport object and reads F190 again to check target
> identity before finalization. This extra F190 read is not established as part of the captured
> sequence, and object identity cannot verify that real CLL teardown/setup occurred. The simulator
> releases the finalization link on success or failure; its reconnect callback owns cleanup of
> partially opened or invalid links. Static callbacks and request-size limits are checked before
> the initial reset. Its integrated LTZ workflow verifies the 14 pinned stock container hashes,
> checks the observed OFF power-mode value before reset, takes one voltage sample after reconnect,
> and models post-reboot identity and calibration metadata reads. These are simulated checks;
> they do not establish actual mode freshness, reboot, link cleanup or vehicle compatibility.
> The simulated adapter demonstrates that a late duplicate response can match a subsequent
> request with the same positive response. One request at a time therefore does not prove response
> freshness. Physical response correlation and tester-present teardown remain unverified, and the
> live programming opener deliberately remains disabled.
> A live read-only F190 probe on 2026-11-07 received one matching positive response and observed
> both D-PDU event types 1 and 2; the simulated programming adapter currently treats unclassified
> events as fatal, so it cannot simply be enabled against this traffic. Tester-present CLL
> destruction was acknowledged and no events arrived during a subsequent two-second observation;
> this is not direct bus-level proof that periodic traffic ceased. Response correlation and the
> live adapter's event classification remain unresolved.
> `mdi2/calibration_readback.py` provides an offline comparison of post-reboot F182 metadata and
> F0F1/F0F2 status; matching metadata does not prove payload bytes, theme, or ADB availability.
>
> **External references:** [GM bulletin 18-NA-325](https://static.nhtsa.gov/odi/tsbs/2020/MC-10183159-9999.pdf)
> says VIP module programming requires ignition off, immediately before describing an A11 radio
> software and calibration procedure. It does not prove every requirement on this particular
> vehicle. [PCM Hammer](https://github.com/PcmHammer/PcmHammer/) supports GM powertrain
> programming but does not claim this A11; [DME Flasher](https://github.com/dmeinnovationgmbh-code/Flasher)
> provides a virtual ECU and J2534 infrastructure for a different ECU family. Neither is a
> proven drop-in A11 calibration writer. [IntellilinkMods](https://intellilinkmods.co.uk/customcalibrations)
> advertises A11 calibration services without identifying a compatible Global B tool or protocol.
>
> **Windows DPS programming research:** `dps.exe!FUN_0040bb20` resolves
> `DpsVcs.dll!fnProgrammingEvent`, which builds a protocol-dependent programming object.
> `dpsvcs.dll!FUN_10060320` dispatches utility-script operations 31/34/36/37 and its
> `FUN_10061120` opens a selected calibration and handles the negotiated transfer limit.
> A separate DPS path resolves `Prog`/`Call` from `pp.dll`, whose interpreter implements the
> same service classes. The cached LTZ utility 85577468 uses that interpreter's record and
> routine structure: its routine table contains 0249, the 14-slot F0F0 list and 039B, matching
> the SPS capture. This is strong structural compatibility evidence; a DPS execution of this
> exact LTZ package and exact protocol-object selection are not yet demonstrated. The cached
> A11_calibration.zip is an SPS cache, not proof of a directly importable DPS archive.
>
> An installed generic DPS archive `UDS_SetMecToZero_Radio.zip` separately contains a 143-byte
> utility script and a `.tbl` describing conditional radio MEC zeroing. The script selects
> ECU 80, reads F1A0, compares against a one-byte routine value 00, and has a 2E/F1A0 write
> record. Static tracing of `pp.dll` supports a conditional `2E F1 A0 00`; no such request was
> sent or captured on this ECU, and a nonzero inverse, EEPROM effect, ADB effect, session and
> authorization requirements remain unknown. This generic `.bin`/`.tbl` archive is distinct
> from the Type4 `.dll`/`.cfx` workflow.
> With accessory on and AAOS booted, a direct read returned `62 F1 A0 EF` (239), and a USB
> ADB shell was independently available; a repeat F1A0 read with the shell connected returned
> the same value. This is a paired observation, not a causal test and not a direct EEPROM read.
> The earlier off-state read failed with `ConnectionError: closed mid-frame`; it cannot be
> interpreted as a zero MEC or loss of ADB authorization.

Once you confirm the seed is all-0xFF and the key is accepted:

```python
# Continuing from the test above, after $27 02 succeeds...

# 1. Request download (ISO 14229-1 $34)
#    Tell the ECU you're about to send calibration data
print("[*] Sending $34 (RequestDownload)...")
dl_request = services.RequestDownload.Request(
    data_format_identifier=0x00,
    address_and_length_format_identifier=0x44,
    memory_address=0x00000000,  # CAL doesn't use real addr, just a placeholder
    memory_size=len(cal_blob),
)
client.send_request(dl_request)

# 2. Transfer data ($36)
#    Send the actual calibration blob in chunks (typically 4KB per frame)
print(f"[*] Sending $36 (TransferData) for {len(cal_blob)} bytes...")
chunk_size = 4096
for i in range(0, len(cal_blob), chunk_size):
    chunk = cal_blob[i:i+chunk_size]
    transfer_request = services.TransferData.Request(
        sequence_counter=i // chunk_size + 1,
        transfer_request_parameter_record=chunk
    )
    client.send_request(transfer_request)
    print(f"  [{i}/{len(cal_blob)}] sent")

# 3. Request transfer exit ($37)
#    Signal completion; VIP/SoC verifies checksum
print("[*] Sending $37 (RequestTransferExit)...")
client.send_request(services.RequestTransferExit.Request())
print("[+] Calibration write sequence complete")

# 4. Tester present ($3E) every 5 seconds (keep session alive during flash)
#    While calserviced processes the override
```

**Checksum/SHA-256 note:** **CORRECTED 2026-11-10:** the cal container is in fact RSA-2048 **signed** (SHA256withRSA over a `CalSignedHeader` that holds the SHA-256 payload digest, with an embedded GM-rooted cert chain). The 16-bit checksum + SHA-256 are genuine but are *lower-layer* integrity beneath the signature; the authenticity gate IS an RSA signature verified against a GM public key. The blob structure is `[header + checksum + data + SHA256]`. If you're hand-editing a cal, recompute both after the edit. **Live test 2026-11-10: a hand-edited cal with *both* fields recomputed correctly was STILL rejected — at the TransferData (`0x36`) stage, NRC `0x72`, before the SoC cal service even processed it. So recomputing checksum + SHA-256 is NOT sufficient; an additional UDS/bridge-layer gate blocks modified containers. Treat this hand-edit recipe as UNPROVEN until that gate is reverse-engineered.**

---

## 4. Documentation of MDI2 Capabilities (Correcting Prior Statements)

| Claim | Prior | Corrected | Evidence |
|---|---|---|---|
| "MDI2 is locked to DPS/SPS" | ✗ | MDI2 is a full J2534 device; **DPS constrains itself to SPS policy, not the hardware** | `GM_DOIP_32.dll` disasm, `MDI2_LINUX_MACOS_ANALYSIS.md` |
| "Can only send signed SPS bundles via MDI2" | ✗ | Via the D-PDU API (TCP/10123) or DoIP you can move raw UDS frames outside DPS's SPS policy | `MDI2_DPDU_API_PROTOCOL_AUG2026.md`, `udsoncan` proof-of-concept |
| "Raw `$27` requires a different adapter" | ✗ | Your MDI2 carries raw UDS over its D-PDU/DoIP transport — no extra adapter | D-PDU capture; **NOT** via `PassThru*Msgs` (only `Open`/`ReadVersion`/`Connect`/`Ioctl`/`Disconnect`/`Close` observed on `bvtx4j32.dll`) |
| "Linux/macOS users cannot use MDI2" | ✗ | DoIP (Ethernet) interface works on any OS; Python `udsoncan` client is cross-platform | `MDI2_LINUX_MACOS_ANALYSIS.md` |

---

## 5. Bench Test Checklist for Your `SCREEN_RESOLUTION` Goal

- [ ] **MDI2 DoIP connectivity:** ping the MDI2's Ethernet IP, verify `DoIPClient()` connects to 13400.
- [ ] **Seed test:** run the Python script above, confirm seed is all-0xFF (if SBI is flipped).
- [ ] **Key acceptance:** send `$27 02` with any 4-byte key, confirm no security reject.
- [ ] **Cal blob structure:** extract a real SCREEN_RESOLUTION cal from `CalSets.db`, hand-edit the enum (e.g. 2→3), recompute checksum + SHA-256.
- [ ] **Download + transfer:** use `$34/$36/$37` to send the blob to the CSM on `eth0:49156` (via `diagnosticsd`), or to the SoC on a CAN interface if you have one.
- [ ] **Boot and verify:** reboot the radio, check `CalSets.db` for the new value or observe display behavior change.

---

## 6. Open-Source UDS Libraries (Already in Your Research Tree)

From `OPENSOURCE_ECU_RESET_ANALYSIS.md`:

```bash
# Python UDS stack (all necessary)
pip3 install python-can          # CAN hardware abstraction
pip3 install can-isotp           # ISO 15765-2 (CAN transport layer)
pip3 install udsoncan            # ISO 14229-1 UDS services
pip3 install doipclient          # DoIP (ISO 13400) transport

# Example imports (from existing templates)
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection  # For CAN ISO-TP
from doipclient import DoIPClient  # For Ethernet DoIP
```

All are on PyPI, stable, and used in the existing research corpus for bench testing.

---

## 7. GM ADB Escape Hatch via `$31` RoutineControl (2026-09-10)

**Source:** Snipesy / Surreal Development, "The ABCs of Global B", 2026-06-16, **CC0 1.0**
(`https://surrealdev.com/the-abcs-of-global-b/`; canonical bibliography:
[`../platform/qualcomm_cadillac_platform.md`](../platform/qualcomm_cadillac_platform.md) → Sources).
Describes a UDS `RoutineControl` request claimed to toggle Android ADB, distinct from the
`$27`/SBI seed bypass above. The author proposes **UDS over DoIP or CAN** and interprets it as
an escape hatch for bench or in-vehicle testing, while stating the SDGM or radio blocks it.
**Correction 2026-11-07:** The article does not supply the domain byte or show a successful
request/response; this is a reported mechanism, not an independently verified live result. Note the
platform split: the article discusses both an Intel Colorado and a Qualcomm Cadillac but does not
identify which head unit, ECU address, build or transport produced this particular routine
description. **Correction 2026-11-07:** Calling it a Cadillac-only path was unsupported. On this
Intel gminfo37/A11 Silverado, EEPROM security state and the Android USB-debugging toggle affect
different parts of ADB access; the UDS routine remains unconfirmed here.

**Frame:**
```
31 01 03 32 DD 42 10 EE
```
| Byte(s) | Meaning |
|---|---|
| `31` | Service: RoutineControl |
| `01` | Sub-function: startRoutine |
| `03 32` | Routine ID `0x0332` |
| `DD` | Domain byte |
| `42` | COMPID `0x42` (66) |
| `10` | DATAID `0x10` (16) |
| `EE` | Value: `01` = enable ADB, `00` = disable ADB |

**Live CAN attempt 2026-11-07:** With the radio rebooted and USB debugging reported off,
native Python through the MDI2 addressed ECU 0x80. Extended session `10 03` returned `50 03`;
level-1 SecurityAccess succeeded (`27 01` returned a 31-byte all-FF seed; a 12-byte zero key
returned `67 02`). A single provisional request `31 01 03 32 00 42 10 01` returned
`7F 31 31` (request out of range). Domain `00` was a guess, not a documented mapping. The
response does not distinguish unsupported routine from invalid domain or other parameters;
it does not establish that this mechanism is incompatible with the radio. ADB was absent from
the host before the request; post-request UI state was not independently checked.

**Additional domain attempts, 2026-11-07:** In a fresh extended session after confirmed level-1
SecurityAccess, provisional domain values `01`, `02`, and `FF` each returned `7F 31 31` for
`31 01 03 32 DD 42 10 01`. The host still listed no authorized ADB device afterward. Together
with `00`, these are four rejected candidate values, not a complete domain enumeration. They
do not distinguish an unsupported RID from an invalid domain or another invalid parameter.

**Complete domain sweep, 2026-11-07:** After renewed extended session and level-1 SecurityAccess,
all remaining values `03`–`FE` were sent sequentially for `31 01 03 32 DD 42 10 01`; each of
the 252 requests returned `7F 31 31`. Together with the earlier `00`, `01`, `02`, and `FF` tests,
all 256 byte values were rejected. The host listed no authorized ADB device afterward. Security
access was confirmed at the start of the sweep, not checked after each request. This rules out
a successful response under the observed test sequence for every domain value, but does not
isolate the rejection to the routine ID, another parameter, session state, or platform differences.

**Post-hard-reset full sweep, 2026-11-07:** Repeated `PDU START`, obtained `51 01` for an
authenticated `11 01` hard reset, and waited approximately 20 seconds. The display was observed
off; this does not establish the Android guest's state. Radio ECU 0x80 still answered `22 F1 A0`
with `62 F1 A0 F1`, accepted `10 03` and level-1 SecurityAccess, and returned `7F 31 31` for
all 256 domain values of `31 01 03 32 DD 42 10 01`. Security access was confirmed at the start
but not after every request. This repeats the negative result after reset with the display off;
it does not prove that every SPS/DPS interaction occurs with the display or AAOS off.

**Post-reset CAN retry, 2026-11-07:** ECU 0x80 answered `22 F1 A0` with `62 F1 A0 F1`
(an earlier read returned `F2`). The radio then accepted extended session and level-1
SecurityAccess, but `31 01 03 32 00 42 10 01` again returned `7F 31 31`. The change in
`F1A0` is an observation only; it does not establish the ADB toggle, EEPROM bytes or cause.

**Read-only follow-up:** In extended session, `31 03 03 32` (request results for RID 0x0332)
returned `7F 31 31`; the same request for previously observed RID 0xFF01 returned `7F 31 12`.
This comparison is consistent with different routine handling, but request-results support and
start-routine support may differ. Neither result proves whether RID 0x0332 can be started or
identifies the missing domain; this follow-up did not repeat SecurityAccess.

**Target and local ADB path:** The source does not publish a target ECU address, CAN IDs, a
successful exchange, or a domain value. The complete domain sweep targeted the A11 radio's
ECU 0x80 over CAN; it does not test another controller or transport. Separately, decompiled
Y175/Y181-family SystemUI `GMKeyguardProtoKeyView` calls `RDMSADBEnable(boolean)` and, on a
successful result, writes the Android `adb_enabled` setting. This is evidence of a local Android
control path, not a mapping from RID 0x0332 to that method or proof of remote reachability.

**A11 data-wipe and calibration review (2026-11-07):** The saved SPS data-wipe package contains
the gzip-wrapped Type 4 application `10017908.dll` and a CFX action labelled `Reset ECU`. The
saved data-wipe CAN log reports security-validation failure and does not show a completed wipe
or establish a wipe RID. The older claim that `0x3208` is the wipe routine is unverified; do not
conflate that destructive data wipe with the confirmed `11 01` hard reboot. Separately, all 14
available A11 calibration payloads contain decompressible CalOvride XML. An in-memory search of
those 14 XML streams found no literal `ADB`, `debug`, `developer`, domain-ID, COMPID, DATAID or
`0332` strings. CalIDs are opaque, so this is not proof that no calibration affects ADB. No
calibration was flashed, and these artifacts do not provide a domain mapping for RID 0x0332.
Owner clarification: a calibration/programming operation can restore a secured MEC/SBI state
and thereby prevent access by a non-GM Secure ADB client; it need not contain an ADB-labelled
field. The exact reset trigger and mechanism are not established by this search. This
authorization state is distinct from the Android USB-debugging toggle and USB enumeration.
The observed `F1A0=F2` and all-FF `$27` seed are separate observations and do not by
themselves prove the EEPROM state or current ADB certificate policy.

**Data-wipe DLL trace, 2026-11-07:** In the decompiled `10017908.dll`, CFX action 2068 (`0x814`,
`Reset ECU`) dispatches via `FUN_100042a0` to `FUN_10003760` after confirmation. The latter reads
the power-mode DID `F085` through its current diagnostic interface and checks its data byte for
`02`; the action path has previously selected ECU `0x40`. Once the check passes, the code selects
ECU `0x80`, performs its security helper, then calls an `ISerUdsExp2` virtual method at offset
`0x44` with arguments `(1, 0x0247, buffer, 0)`. This suggested a start-routine call with no
option bytes; the subsequent live test below confirms the radio accepted `31 01 02 47` and
the owner confirmed the reset. The virtual method itself was not independently named. A live
read on ECU `0x40` returned `62 F0 85 00`, so the observed data byte did not satisfy this code's
`02` check. No data-wipe request was sent during that initial read.

**Live data-reset attempt, 2026-11-07:** With Service Mode confirmed by BCM response
`62 F0 85 02`, ECU 0x80 accepted extended session (`50 03`) and level-1 SecurityAccess
(`67 02`, using the observed all-FF seed). One `31 01 02 47` request returned
`7F 31 78` (pending), then `71 01 02 47` (positive start-routine response). This confirms
that the candidate is implemented and accepted under these conditions. The radio restarted,
displayed wipe activity, booted AAOS, and the owner confirmed its user data was wiped and it was
in the default post-reset state. No calibration transfer was performed.

**Read-only follow-up during apparent wipe:** Two samples returned `F1A0=F0`,
`F081=00 00 00 00 00 00`, `F0F1=00 00`, and `F0F2=00 00`. The earlier `F1A0` sample
before the wipe was `F1`; no causal interpretation is established. A routine-results query
`31 03 02 47` without a new SecurityAccess exchange returned `7F 31 31`. These identifiers
have not been established as wipe-progress indicators; neither the zero values nor the rejected
results query establishes completion or failure of the wipe.

**Post-wipe ADB and power-mode checks:** The owner confirmed a factory-default radio state and
manually re-enabled developer options and USB debugging. The Mac then obtained an authorized
ADB shell (`uid=2000`); it remained available after Service Mode was turned off. This confirms
access for the existing host after this wipe, not whether EEPROM SBI bytes or the GM certificate
policy changed. `F1A0` read `F1` before the wipe, `F0` during and after boot, and `EF` after
Service Mode was turned off; the cause and relation to SBI or authentication are unproven.
`F081` remained six zero bytes; `F0F1` and `F0F2` remained two zero bytes each. BCM `F085`
read `00` after Service Mode was turned off. Earlier observed values were `01` with accessory
mode reported, `04` with the engine running, and `02` with Service Mode reported. These are
observations on this vehicle, not a complete or independently validated enumeration.

**Prior Y175 test, found 2026-11-07:** The 2026-11-02 Bus 2 direct-T1 bench report says
the ADB routine was sent to the Android `diagnosticsd` custom UDS-over-TCP endpoint and returned
`7F 31 10` (generalReject); other diagnostic services were also rejected. Its summary omits the
domain byte and complete request, and the underlying exchange has not been located. This is a
reported rejection on the Android diagnostics path, not a test of ECU 0x80 via MDI2 DoIP/CAN;
it does not establish routine support, the correct domain, or the reason for rejection.
**Correction 2026-11-14:** the old blanket T1 rejections used an invalid
logical tester. F4 plus extended session now completes level-1 SecurityAccess
(31-FF seed, 12-zero response, `67 02`); see [validated T1 sequence](../diagnostics/ethernet_uds_diagnosticsd.md#live-t1-securityaccess-correction-2026-11-14). The ADB routine itself was not rerun, so its behavior remains unproven.

**What this does and does not prove:**
- It identifies a **candidate external UDS `RoutineControl` request** for a privileged action.
  The domain byte, ECU support, authorization requirements and effect have not been confirmed
  on this repo's A11/CSM. A blocked request would not establish that the routine is absent.
- It does **not** hand you authorized root `adb`. SDGM/the radio module normally **blocks this
  routine** (session/security gating on `$31` calls of this class), and even when it's not
  blocked, this Global-B `adbd` is **GM-custom and trusts only GM-provisioned keys** — enabling
  usb-debug via this route gets you a debug-enabled daemon that still refuses an unauthorized
  host's adb key. It is a togglable primitive, not a bypass of adb's own authentication.
- Note the broader authentication model this sits inside: Global-B `$27` SecurityAccess is
  ultimately authenticated against **GM's SDGM/Azure back office via SPS2/3 credentials** for
  the tiers that matter (calibration/programming) — but see
  [`../platform/ota_programming_roles.md`](../platform/ota_programming_roles.md) § Global B
  provisioning for the canonical model *and its caveat* that this repo's own DPS captures show
  `$27` as a **per-ECU** exchange, so the "against the SDGM" framing is Cadillac-specific/
  unconfirmed here; GM has deliberately left some diagnostic
  *routines* (not full security levels) unauthenticated by design. The ADB routine's authorization
  requirements remain unverified; the source explicitly says the SDGM or radio blocks it.

**How this fits the existing routes above:** send it the same way as any other raw UDS frame
in §2/§3 (Route B, `udsoncan`/DoIP, is the simplest) — it is a `RoutineControl` call like the
`31 01 02 0E FF FF FF` wakeUpNetworks routine already used elsewhere in this repo's captures,
not a new transport or session requirement.

**App-install paths on the same head unit (same article, [X] Cadillac/Qualcomm):** the UDS routine
enables `adb`, but the article also notes two *app*-install avenues distinct from it. (1) **Normal
Android side-loading is disabled** — GM removes the underlying install permission — though on *some*
software versions it reportedly still worked ("maybe you should decline those OTAs"). (2) **Google
Play is a trusted installer**: an account enrolled in a build's **internal test track (ITT)** can
push an APK straight to the head unit; a long-standing dev workaround. Both are Cadillac/Qualcomm
observations, unconfirmed on this Intel unit, and — like the UDS route — do not by themselves grant
authenticated root `adb`.

## 8. References

> **Broken-link note (2026-11-12):** none of the five filenames below (also cited inline at
> lines ~197, ~255, ~416, ~419, ~436) exist anywhere in this repo (`find`/`rg` over the full
> tree returns no match) and none are listed in `INVENTORY.md`. Treat the specific claims
> these citations were meant to back (D-PDU prefix-length/`28 03 01` fix detail, cross-platform
> DoIP usage, the `udsoncan` template source, the ADB/SBI scope claim) as uncited pending
> relocation or recreation of the source doc, not as independently false.

- `DPS_MASTER_REFERENCE.md` — J2534 architecture and DPS layers. **[file not found in repo, 2026-11-12]**
- `MDI2_LINUX_MACOS_ANALYSIS.md` — DoIP interface and cross-platform usage. **[file not found in repo, 2026-11-12]**
- `OPENSOURCE_ECU_RESET_ANALYSIS.md` — `udsoncan` Python templates (already proven working). **[file not found in repo, 2026-11-12]**
- `EEPROM_CALIBRATION_MAPPING.md` — UDS seed bypass scope (ADB + programming `$27` both use SBI). **[file not found in repo, 2026-11-12]**
- `SBI_SECURITY_SCOPE_ANALYSIS.md` — Confirms SBI affects UDS `$27` responses. **[file not found in repo, 2026-11-12]**

---

## Summary

**Your MDI2 is NOT locked to DPS.** You can send raw `$27` SecurityAccess commands via:
1. **The MDI2 D-PDU API on TCP/10123** (the transport DPS itself uses for UDS; see
   `MDI2_DPDU_API_PROTOCOL_AUG2026.md`) — **not** the J2534 `PassThru*Msgs` read/write API, which
   this stack never uses for diagnostic payload.
2. **DoIP + Python `udsoncan`** (any OS, open-source, recommended)

The bench test for your `SCREEN_RESOLUTION` goal is now **entirely within your existing hardware and open-source tools**. No new adapters needed.
