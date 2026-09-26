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

**Checksum/SHA-256 note:** As confirmed by the firmware analysis, the cal blob must carry the correct checksum (16-bit) and SHA-256; the SoC/VIP verifies but does *not* check an RSA signature. The blob structure is `[header + checksum + data + SHA256]`. If you're hand-editing a cal, recompute both after the edit.

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
Independently confirms that
Global-B head units expose a fully-decoded UDS `RoutineControl` request that toggles Android
`adb` (usb-debug) on the SoC — a *different* route from the `$27`/SBI seed bypass documented
above, and worth distinguishing from it. The author sends it **over UDS over DoIP or CAN** and
reads it as an **escape hatch left in for bench (and possibly in-vehicle) testing**. Note the
platform split: on the Cadillac/Qualcomm units the article describes this UDS routine; on **this
Intel gminfo37/A11 Silverado the confirmed adb-enable is an EEPROM byte-flip** (offsets
`0x0440`/`0x0A80` → `0xFF`), so treat the UDS routine as the Cadillac path, unconfirmed here.

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

**What this does and does not prove:**
- It proves an **external UDS `RoutineControl` request can drive a privileged internal action**
  (flipping a SoC-side Android debug flag) on Global-B hardware — the same class of head unit
  as gminfo37/CSM, though the routine ID/COMPID/DATAID triple above has not been re-confirmed
  against this repo's own captures.
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
  *routines* (not full security levels) unauthenticated by design, of which the ADB-enable
  routine above appears to be one — consistent with, and a second independent example of, the
  general pattern this doc's §1-2 already documents (MDI2/J2534 has no hardware-level lock;
  policy lives in the tooling/routine gating, not universally in the transport).

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

- `DPS_MASTER_REFERENCE.md` — J2534 architecture and DPS layers.
- `MDI2_LINUX_MACOS_ANALYSIS.md` — DoIP interface and cross-platform usage.
- `OPENSOURCE_ECU_RESET_ANALYSIS.md` — `udsoncan` Python templates (already proven working).
- `EEPROM_CALIBRATION_MAPPING.md` — UDS seed bypass scope (ADB + programming `$27` both use SBI).
- `SBI_SECURITY_SCOPE_ANALYSIS.md` — Confirms SBI affects UDS `$27` responses.

---

## Summary

**Your MDI2 is NOT locked to DPS.** You can send raw `$27` SecurityAccess commands via:
1. **The MDI2 D-PDU API on TCP/10123** (the transport DPS itself uses for UDS; see
   `MDI2_DPDU_API_PROTOCOL_AUG2026.md`) — **not** the J2534 `PassThru*Msgs` read/write API, which
   this stack never uses for diagnostic payload.
2. **DoIP + Python `udsoncan`** (any OS, open-source, recommended)

The bench test for your `SCREEN_RESOLUTION` goal is now **entirely within your existing hardware and open-source tools**. No new adapters needed.
