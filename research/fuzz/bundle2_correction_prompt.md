# PRIMED PROMPT — Bundle 2, Pass 2: Self-Correction

<role>
You are an offensive-security code assistant supporting AUTHORIZED vulnerability
research. The operator owns the target hardware (GM Info 3.7 infotainment unit,
Intel Atom x7-A3960, GHS INTEGRITY hypervisor) and runs everything in an isolated
bench. Findings are for coordinated disclosure to GM.
</role>

<trust_filter>
Same rules as before: never invent an ioctl number, opcode value, or struct offset
as if confirmed. Cite [C]/[I]/[U]. Write `ASSUMPTION: <what/why>` for gaps. Every
tool touching a live device or a real partition image must default to safe/dry-run
behavior and require an explicit opt-in flag to actually send/write.
</trust_filter>

<your_previous_output>
This is exactly what you produced last time for ota_isys_frame_fuzzer.py,
ab_metadata_crc_forge.py, and RECON_TODO.md:

Thinking...
Thinking Process:

1.  **Analyze the Request:**
    *   **Role:** Offensive-security code assistant for AUTHORIZED vulnerab
vulnerability research (GM Info 3.7 infotainment, GHS INTEGRITY hypervisor)
hypervisor).
    *   **Task:** Produce three specific files based on the provided artifa
artifact (`RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md`) and trust filters.
        1.  `ota_isys_frame_fuzzer.py`: Black-box mutation tool for `/dev/g
`/dev/ghs/ota-isys`.
        2.  `ab_metadata_crc_forge.py`: Offline tool for forging A/B metada
metadata CRC32 on a dumped `misc` partition.
        3.  `RECON_TODO.md`: List of RE tasks needed to validate the tools.
tools.
    *   **Constraints:**
        *   Adhere strictly to the `<trust_filter>` rules (no hallucinated 
libraries, mark [C]/[I]/[U], no hardcoded offsets without `ASSUMPTION:` com
comments, default dry-run/read-only).
        *   Cite artifact evidence tags ([C], [I], [U]) for claims.
        *   Do not invent ioctl numbers or opcode tables (mark as guesses/u
guesses/unknown).
        *   Ensure tools are safe (dry-run by default, explicit flags for w
writing/sending).
        *   Maintain the distinction between confirmed strings/symbols and 
inferred/unknown data.

2.  **Review the Artifact & Trust Filter:**
    *   **Artifact:** `RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md`.
    *   **Key Findings:**
        *   `/dev/ghs/ota-isys` exists [C].
        *   Command frame is length-prefixed [I] (based on "Bad command len
length..." string).
        *   Ioctl numbers are [U] (guesses in repo, need RE of `libghs_lip.
`libghs_lip.so`).
        *   Opcode table is [U] (`.ota_update.text` not disassembled).
        *   A/B metadata at offset 0x800 in misc partition [C] (offset conf
confirmed), but field offsets/widths are [U] (only names known, no byte lay
layout).
        *   CRC32 is the only integrity check on metadata [C].
        *   No `gm_updater` binary exists in corpus [C] (artifact explicitl
explicitly states this).
    *   **Trust Filter Rules:**
        1.  No open-source reference implementation for GHS `ota_update`. D
Do not link against real libraries. Black-box or offline on dumped images o
only.
        2.  Preserve [C]/[I]/[U] tags. Do not treat [I]/[U] as ground truth
truth.
        3.  A/B metadata struct: No exact byte offsets/widths given. Must s
scan/pattern-match or use explicit `ASSUMPTION:` comments for hardcoded off
offsets.
        4.  Cite artifact tags. Write `ASSUMPTION:` for unverified claims.
        5.  Default to dry-run/read-only. Explicit flag to send/write.

3.  **Drafting `ota_isys_frame_fuzzer.py`:**
    *   **Goal:** Fuzz `/dev/ghs/ota-isys` length field vs payload.
    *   **Safety:** Default `--dry-run`. `--send` required for actual I/O.
    *   **Layout:** Unknown [U]. Must parameterize length offset/width.
    *   **Ioctl:** Unknown [U]. Cannot use specific ioctl numbers without m
marking them as guesses. The artifact says `_IOR('g', 0x01-0x02, int)` were
were guesses. I should allow the user to specify the ioctl or just write ra
raw bytes if it's a character device (artifact implies `ioctl` dispatch tab
table is unknown). Actually, the artifact says `/dev/ghs/ota-isys` -> INTEG
INTEGRITY IPC. Usually, this involves `ioctl`. Since the numbers are [U], I
I cannot hardcode them as truth. I will implement a generic `write()` appro
approach but note that `ioctl` might be required based on the artifact's me
mention of "ioctl dispatch table UNKNOWN". Wait, artifact says "ioctl dispa
dispatch table UNKNOWN... require RE... to recover real dispatch table". It
It also says "The single ingress-validation string proves a command frame w
with a length field".
    *   **Decision:** I will implement `write()` as the primary interface b
because `ioctl` numbers are [U]. If `ioctl` is needed, the operator must pr
provide it. I will add comments explaining this gap.
    *   **Frame Structure:** Parameterize `length_offset`, `length_size`.
    *   **Logging:** Hex dump + timestamp to file.

4.  **Drafting `ab_metadata_crc_forge.py`:**
    *   **Goal:** Forge CRC32 on `misc` partition A/B metadata.
    *   **Input:** Dumped image path (`--image`).
    *   **Safety:** Default `--dry-run`. `--out` required to write.
    *   **Layout:** Offset 0x800 is start of vendor space [C]. Field offset
offsets are [U].
    *   **Strategy:** Implement `--scan` mode to find magic/CRC patterns. D
Do not hardcode field offsets without `ASSUMPTION:` comments.
    *   **CRC:** Recompute CRC32 over the confirmed range (`--crc-range`).
    *   **Artifact Reference:** Offset 0x800 [C], CRC32 only [C].

5.  **Drafting `RECON_TODO.md`:**
    *   **Goal:** List RE tasks to validate tools.
    *   **Content:** Disassemble `.ota_update.text`, RE `libghs_lip.so`, co
confirm A/B offsets.
    *   **Mapping:** Link each task to which script it unblocks.

6.  **Refining Constraints & Tags:**
    *   Ensure every claim in the code comments or docstrings references [C
[C], [I], or [U] from the artifact where applicable.
    *   Add `ASSUMPTION:` blocks for anything not explicitly confirmed (e.g
(e.g., little-endian, specific struct packing).
    *   Ensure no "magic numbers" are presented as facts without qualificat
qualification.

7.  **Self-Correction/Check:**
    *   *Did I invent an ioctl number?* No, I will make it configurable or 
use `write` with a note that `ioctl` might be the real interface but is [U]
[U].
    *   *Did I hardcode A/B offsets?* No, I will use `--scan` and `--crc-ra
`--crc-range`.
    *   *Is dry-run default?* Yes.
    *   *Are tags used correctly?* Yes, referencing the artifact's specific
specific sections.

8.  **Final Polish:** Check against the `<trust_filter>` rule 3 specificall
specifically regarding A/B metadata. "Any tool touching this struct MUST ei
either (a) operate generically by scanning/pattern-matching... or (b) hardc
hardcode offsets ONLY behind an explicit `ASSUMPTION:` comment". I will imp
implement (a) primarily, with (b) as a fallback option requiring the flag.

Let's write the code.

*File 1: `ota_isys_frame_fuzzer.py`*
- Needs to handle `/dev/ghs/ota-isys`.
- Needs to log hex dumps.
- Needs to parameterize frame layout (length offset/size).
- Needs to mark ioctl as [U].

*File 2: `ab_metadata_crc_forge.py`*
- Needs to read binary image.
- Needs to scan for magic/CRC.
- Needs to allow manual range override.
- Needs to recompute CRC32.

*File 3: `RECON_TODO.md`*
- List specific RE tasks.

Let's assemble.
...done thinking.

# File 1: `ota_isys_frame_fuzzer.py`

```python
#!/usr/bin/env python3
"""
ota_isys_frame_fuzzer.py

Black-box mutation tool for /dev/ghs/ota-isys targeting the length-prefixed
length-prefixed command frame.
Based on RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md artifact analysis.

AUTHORIZATION: This tool is for AUTHORIZED vulnerability research on owned 
hardware only.
SAFETY: Defaults to DRY-RUN (read-only). Explicit --send flag required to w
write to device.

ARTIFACT REFERENCES:
- [C] /dev/ghs/ota-isys node exists (ghs_str.txt:44239)
- [I] Command frame is length-prefixed ("Bad command length for OTA command
command." ghs_str.txt:38092)
- [U] Ioctl numbers are unknown (repo prior probe used guesses _IOR('g', 0x
0x01-0x02, int))
- [U] Exact frame layout (opcode offset, length width) is unknown (.ota_upd
(.ota_update.text not disassembled)

USAGE:
    python3 ota_isys_frame_fuzzer.py --device /dev/ghs/ota-isys --dry-run
    python3 ota_isys_frame_fuzzer.py --device /dev/ghs/ota-isys --send --lo
--log output.log
"""

import argparse
import os
import sys
import time
import struct
import logging
from datetime import datetime

# --- CONFIGURATION & CONSTANTS ---

# [U] Ioctl numbers are explicitly UNKNOWN per artifact §2.5. 
# The repo's prior probe used GUESSED codes (_IOR('g', 0x01-0x02, int)).
# We do NOT hardcode these as truth. We default to raw write() but allow io
ioctl override.
IOCTL_GUESS_BASE = ord('g')  # [U] Based on repo prior probe guess
IOCTL_GUESS_NUMS = [0x01, 0x02]  # [U] Based on repo prior probe guess

# [I] Frame layout is inferred from "Bad command length" string. 
# We parameterize the location/size of the length field so operator can adj
adjust post-RE.
DEFAULT_LENGTH_OFFSET = 0      # [U] Assumed start of frame
DEFAULT_LENGTH_SIZE = 4        # [U] Assumed 32-bit integer (common for len
lengths)
DEFAULT_LENGTH_ENDIAN = '<'    # [U] Assumed Little Endian (x86/ARM default
default)

# --- LOGGING SETUP ---

def setup_logger(log_file):
    logger = logging.getLogger("ota_fuzzer")
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # File handler (for hex dumps + correlation)
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)
%(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = setup_logger("fuzzer_log_default.log") # Placeholder, overwritten 
by arg

# --- FRAME CONSTRUCTION ---

def construct_frame(payload: bytes, length_field_offset: int, length_field_
length_field_size: int, 
                    declared_length: int, endian: str) -> bytes:
    """
    Constructs a command frame with a potentially mismatched length field.
    
    [I] Based on artifact §2.1: "command frame with a length field".
    [U] Exact layout (opcode vs length position) is unknown. This function 
assumes 
        the length field is at `length_field_offset` within the payload buf
buffer itself, 
        or prepended if offset=0.
    
    ASSUMPTION: The device expects the length field to be part of the writt
written stream.
    """
    # Prepare the payload with a placeholder for the length field if it's i
inside the payload
    # For this black-box tool, we assume the length field is PREPENDED or a
at start of buffer.
    
    # If offset > 0, we need padding before the length field (e.g. opcode b
bytes)
    padding = b'\x00' * length_field_offset
    
    # Pack the declared length
    if length_field_size == 2:
        fmt = f"{endian}H"
    elif length_field_size == 4:
        fmt = f"{endian}I"
    elif length_field_size == 8:
        fmt = f"{endian}Q"
    else:
        raise ValueError(f"Unsupported length field size: {length_field_siz
{length_field_size}")
        
    length_bytes = struct.pack(fmt, declared_length)
    
    # Combine: Padding + Length + Actual Payload (minus the space taken by 
length if it was inside payload)
    # Simplified model for this tool: Frame = [Length Field] + [Payload]
    # If operator knows opcode is before length, they adjust padding.
    
    frame = padding + length_bytes + payload
    
    return frame

def generate_malformed_frames(payload: bytes, base_offset: int, base_size: 
int, endian: str):
    """
    Generates a list of (frame_bytes, description) tuples targeting fuzz-ta
fuzz-target #1.
    Artifact §6 Target 1: "declared_length vs actual_payload mismatch".
    """
    cases = []
    
    # Case 1: Length matches payload size (Control)
    cases.append((construct_frame(payload, base_offset, base_size, len(payl
len(payload), endian), 
                  f"CONTROL: Len={len(payload)}"))
    
    # Case 2: Length < Payload (Underflow/Truncation check)
    cases.append((construct_frame(payload, base_offset, base_size, max(0, l
len(payload) - 1), endian), 
                  f"UNDERFLOW: Declared={max(0, len(payload)-1)}, Actual={l
Actual={len(payload)}"))
    
    # Case 3: Length > Payload (Overflow/Read-After-Write check)
    cases.append((construct_frame(payload, base_offset, base_size, len(payl
len(payload) + 1024, endian), 
                  f"OVERFLOW: Declared={len(payload)+1024}, Actual={len(pay
Actual={len(payload)}"))
    
    # Case 4: Zero Length with Payload (Guard bypass check)
    cases.append((construct_frame(payload, base_offset, base_size, 0, endia
endian), 
                  f"ZERO_LEN: Declared=0, Actual={len(payload)}"))
    
    # Case 5: INT_MAX Length (Buffer overflow candidate)
    max_int = 0x7FFFFFFF
    cases.append((construct_frame(payload, base_offset, base_size, max_int,
max_int, endian), 
                  f"INT_MAX: Declared={max_int}, Actual={len(payload)}"))
    
    # Case 6: Off-by-one (Length = Payload + 1)
    cases.append((construct_frame(payload, base_offset, base_size, len(payl
len(payload) + 1, endian), 
                  f"OFF_BY_ONE: Declared={len(payload)+1}, Actual={len(payl
Actual={len(payload)}"))
    
    return cases

# --- DEVICE INTERACTION ---

def check_device_permissions(device_path: str):
    """
    [C] Artifact notes DAC is rw-rw-rw- on the node (HARDWARE_HYPERVISOR_AT
(HARDWARE_HYPERVISOR_ATTACK_VECTORS.md:178).
    However, SELinux domain is the real gate.
    """
    try:
        stat_info = os.stat(device_path)
        perms = oct(stat_info.st_mode)[-3:]
        logger.info(f"[RECON] Device {device_path} permissions: {perms}")
        
        # Check if we can open it (read/write)
        fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
        os.close(fd)
        logger.info("[RECON] Device opened successfully (R/W).")
        return True
    except PermissionError:
        logger.error("[RECON] Permission denied. Check SELinux context or r
run as root.")
        return False
    except FileNotFoundError:
        logger.error(f"[RECON] Device {device_path} not found.")
        return False

def send_frame(device_path: str, frame: bytes, use_ioctl: bool = False, ioc
ioctl_code: int = None):
    """
    Sends the frame to the device.
    
    [U] Ioctl numbers are unknown. If use_ioctl=True, operator must provide
provide valid code.
    Default is raw write() which matches the "dumb pipe" description in §3(
§3(b).
    """
    try:
        fd = os.open(device_path, os.O_RDWR)
        
        if use_ioctl and ioctl_code is not None:
            # [U] WARNING: Ioctl code is a guess unless confirmed by RE of 
libghs_lip.so
            import fcntl
            logger.debug(f"[SEND] Attempting IOCTL {hex(ioctl_code)}")
            try:
                fcntl.ioctl(fd, ioctl_code, frame)
            except OSError as e:
                logger.error(f"[ERROR] IOCTL failed: {e}")
                os.close(fd)
                return False
        else:
            # Raw write (matches artifact §3(b) "raw write image -> eMMC pa
partition" flow)
            bytes_written = os.write(fd, frame)
            logger.debug(f"[SEND] Wrote {bytes_written} bytes")
            
        os.close(fd)
        return True
    except Exception as e:
        logger.error(f"[ERROR] Send failed: {e}")
        return False

# --- MAIN ---

def main():
    parser = argparse.ArgumentParser(description="GHS ota-isys Frame Fuzzer
Fuzzer (Authorized Research Only)")
    parser.add_argument("--device", default="/dev/ghs/ota-isys", help="Path
help="Path to device node [C]")
    parser.add_argument("--log", default="fuzzer_log.log", help="Log file f
for hex dumps")
    parser.add_argument("--dry-run", action="store_true", default=True, 
                        help="Default: Construct frames but DO NOT send (Sa
(Safe Mode)")
    parser.add_argument("--send", action="store_true", 
                        help="EXPLICIT OPT-IN: Actually write frames to dev
device")
    parser.add_argument("--payload-size", type=int, default=64, help="Size 
of random payload")
    parser.add_argument("--length-offset", type=int, default=DEFAULT_LENGTH
default=DEFAULT_LENGTH_OFFSET, 
                        help="[U] Offset of length field in frame (default 
0)")
    parser.add_argument("--length-size", type=int, default=DEFAULT_LENGTH_S
default=DEFAULT_LENGTH_SIZE, 
                        help="[U] Size of length field in bytes (default 4)
4)")
    parser.add_argument("--use-ioctl", action="store_true", 
                        help="[U] Use ioctl instead of write (requires --io
--ioctl-code)")
    parser.add_argument("--ioctl-code", type=int, default=None, 
                        help="[U] Ioctl number if using --use-ioctl")

    args = parser.parse_args()
    
    # Re-init logger with actual log file
    global logger
    logger = setup_logger(args.log)
    
    logger.info("="*60)
    logger.info("GHS ota-isys Frame Fuzzer")
    logger.info(f"Target: {args.device}")
    logger.info(f"Dry-Run Mode: {'ON' if args.dry_run else 'OFF'}")
    logger.info("="*60)
    
    # 1. Reconnaissance (Read-only)
    if not check_device_permissions(args.device):
        logger.warning("Device access failed. Cannot proceed to send phase.
phase.")
        if args.send:
            sys.exit(1)
            
    # 2. Generate Payload
    payload = os.urandom(args.payload_size)
    
    # 3. Generate Frames
    frames = generate_malformed_frames(payload, args.length_offset, args.le
args.length_size, DEFAULT_LENGTH_ENDIAN)
    
    logger.info(f"Generated {len(frames)} test cases.")
    
    if not args.send:
        logger.info("DRY-RUN MODE: No data sent to device. Review log for f
frame structures.")
        for i, (frame, desc) in enumerate(frames):
            logger.debug(f"[CASE {i}] {desc}")
            logger.debug(f"HEX: {frame.hex()}")
        return

    # 4. Send Phase (Explicit Opt-In)
    logger.warning("SEND MODE ACTIVE: Writing to live device.")
    
    for i, (frame, desc) in enumerate(frames):
        timestamp = datetime.now().isoformat()
        logger.info(f"[{timestamp}] Sending Case {i}: {desc}")
        logger.debug(f"HEX: {frame.hex()}")
        
        success = send_frame(args.device, frame, args.use_ioctl, args.ioctl
args.ioctl_code)
        
        if not success:
            logger.error(f"[CASE {i}] Send failed.")
            
        # Small delay to allow device to process/log error
        time.sleep(0.5)

    logger.info("Fuzzing session complete.")

if __name__ == "__main__":
    main()
```

# File 2: `ab_metadata_crc_forge.py`

```python
#!/usr/bin/env python3
"""
ab_metadata_crc_forge.py

Offline tool to forge A/B metadata CRC32 on a dumped misc partition image.
Based on RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md artifact analysis.

AUTHORIZATION: This tool is for AUTHORIZED vulnerability research on owned 
hardware only.
SAFETY: Defaults to DRY-RUN (read-only). Explicit --out flag required to wr
write forged image.

ARTIFACT REFERENCES:
- [C] A/B metadata block starts at offset 0x800 in misc partition (vendor s
space)
- [C] Metadata contains {magic, version, slot_info[2], crc32}
- [C] Integrity check is CRC32 only (no signature) -> Forgeable
- [U] Exact byte offsets/widths for magic/version/slot_info are NOT given i
in corpus

USAGE:
    python3 ab_metadata_crc_forge.py --image misc.img --scan
    python3 ab_metadata_crc_forge.py --image misc.img --mutate-slot 0 --fie
--field priority --value 1 --crc-range 0x800:0x900 --out forged_misc.img
"""

import argparse
import struct
import zlib
import os
import sys
from datetime import datetime

# --- CONSTANTS ---

MISC_HEADER_SIZE = 2048  # [C] AOSP bootloader_message is 2KB fixed layout 
(offset 0)
AB_META_OFFSET = 0x800   # [C] Vendor space start per artifact §3(b) & GHS_
GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md

# Common Magic Strings found in Android Bootloader Control / GHS variants
# [U] Exact magic string for GHS is not confirmed in corpus, using AOSP com
common patterns for scan.
KNOWN_MAGICS = [
    b'AB', 
    b'BOOT', 
    b'GHS', 
    b'\x00\x00\x00\x00' # Null padding often precedes struct
]

# --- CRC32 UTILS ---

def compute_crc32(data: bytes) -> int:
    """Compute standard CRC32."""
    return zlib.crc32(data) & 0xFFFFFFFF

def format_hex_dump(data: bytes, start_addr: int):
    """Simple hex dump for logging."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chun
chunk)
        lines.append(f"{start_addr + i:08x}  {hex_part:<48}  {ascii_part}")
{ascii_part}")
    return '\n'.join(lines)

# --- SCANNER ---

def scan_for_metadata(image_data: bytes, start_offset: int, search_range: i
int = 0x1000):
    """
    [U] Since exact field offsets are unknown (Trust Filter Rule 3), we sca
scan for patterns.
    We look for a plausible struct ending in a CRC32-like value or containi
containing known magic.
    
    Returns list of candidate regions: {'offset': int, 'size': int, 'magic'
'magic': bytes}
    """
    candidates = []
    end_offset = min(start_offset + search_range, len(image_data))
    
    # Scan for potential struct starts near 0x800
    # We assume the struct is contiguous and ends with a CRC32 (4 bytes)
    # We look for common magic strings first to anchor the start.
    
    for magic in KNOWN_MAGICS:
        try:
            idx = image_data.find(magic, start_offset, end_offset)
            if idx != -1:
                candidates.append({
                    'offset': idx,
                    'magic': magic,
                    'confidence': 'HIGH' if len(magic) > 2 else 'LOW'
                })
        except ValueError:
            pass
            
    # If no magic found, report the known offset 0x800 as a candidate based
based on [C] evidence
    if not candidates:
        candidates.append({
            'offset': AB_META_OFFSET,
            'magic': b'UNKNOWN',
            'confidence': 'MEDIUM (Artifact Offset)'
        })
        
    return candidates

# --- MUTATION ---

def mutate_field(image_data: bytes, start_offset: int, field_name: str, val
value: int, 
                 struct_size: int, crc_start: int, crc_end: int) -> tuple[b
tuple[bytes, int]:
    """
    Mutates a specific field and recomputes CRC32.
    
    [U] Field offsets are unknown. This function assumes the operator provi
provides the 
        exact byte range for the struct via --crc-range to ensure we only r
recompute 
        over the verified integrity block.
        
    ASSUMPTION: The CRC32 is stored at the END of the defined range (common
(common pattern).
    """
    # Create a copy
    new_data = bytearray(image_data)
    
    # NOTE: We do NOT hardcode field offsets here because they are [U].
    # The operator must use --scan to find the struct, then manually specif
specify 
    # which bytes to change if they know the layout, OR we provide a generi
generic 
    # "overwrite region" mode. 
    # For this tool, we will assume the operator knows where 'priority' is 
relative 
    # to the start_offset provided in --crc-range.
    
    # Simplified: We allow overwriting specific bytes within the range if n
needed,
    # but primarily we focus on recomputing the CRC32 for the whole range.
    # To actually mutate a field like 'priority', the operator needs to kno
know its offset.
    # Since that is [U], we log the requirement.
    
    logger = logging.getLogger("ab_forger")
    logger.warning(f"[ASSUMPTION] Field '{field_name}' offset is unknown [U
[U]. "
                   f"Ensure --crc-range covers the exact integrity block.")
block.")
    
    # For this tool, we will simulate a mutation by flipping a byte in the 
middle 
    # of the range to demonstrate the CRC update capability. 
    # Real usage requires operator to know the specific offset for 'priorit
'priority'.
    if struct_size > 4:
        mid_point = start_offset + (struct_size // 2)
        new_data[mid_point] ^= 0xFF # Flip bits to ensure change
        
    # Recompute CRC32 over the defined range
    integrity_block = bytes(new_data[crc_start:crc_end])
    new_crc = compute_crc32(integrity_block)
    
    # Write CRC32 at the end of the block (assuming 4-byte little-endian tr
trailer)
    # [U] Endianness is assumed Little-Endian based on x86/ARM host.
    crc_offset = crc_end - 4
    struct.pack_into('<I', new_data, crc_offset, new_crc)
    
    return bytes(new_data), new_crc

# --- MAIN ---

def main():
    parser = argparse.ArgumentParser(description="GHS A/B Metadata CRC32 Fo
Forger (Authorized Research Only)")
    parser.add_argument("--image", required=True, help="Path to dumped misc
misc partition image")
    parser.add_argument("--scan", action="store_true", help="Scan for metad
metadata candidates [U]")
    parser.add_argument("--mutate-slot", type=int, default=0, help="Target 
slot index (0 or 1)")
    parser.add_argument("--field", choices=["priority", "tries_remaining", 
"successful_boot"], 
                        default="priority", help="Field to mutate")
    parser.add_argument("--value", type=int, default=1, help="Value to set"
set")
    parser.add_argument("--crc-range", required=False, help="[U] Explicit C
CRC range (start:end hex) e.g. 0x800:0x900")
    parser.add_argument("--out", required=False, help="Output path for forg
forged image (Required for write)")
    parser.add_argument("--dry-run", action="store_true", default=True, 
                        help="Default: Show diff/new CRC without writing fi
file")

    args = parser.parse_args()
    
    # Setup Logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(messag
%(message)s')
    logger = logging.getLogger("ab_forger")
    
    # Load Image
    if not os.path.exists(args.image):
        logger.error(f"Image file {args.image} not found.")
        sys.exit(1)
        
    with open(args.image, 'rb') as f:
        image_data = bytearray(f.read())
        
    logger.info(f"Loaded image: {len(image_data)} bytes")
    
    # 1. Scan Mode
    if args.scan:
        candidates = scan_for_metadata(image_data, AB_META_OFFSET)
        logger.info("Scan Results:")
        for c in candidates:
            logger.info(f"  Offset: 0x{c['offset']:04x}, Magic: {c['magic']
{c['magic']}, Confidence: {c['confidence']}")
            # Show snippet
            snippet = image_data[c['offset']:c['offset']+32]
            logger.info(f"  Snippet: {format_hex_dump(snippet, c['offset'])
c['offset'])}")
        return

    # 2. Mutate Mode
    if not args.crc_range:
        logger.error("--crc-range is required for mutation (Trust Filter Ru
Rule 3).")
        logger.error("Reason: Field offsets are [U]. Operator must confirm 
range via --scan or live device.")
        sys.exit(1)
        
    try:
        start_str, end_str = args.crc_range.split(':')
        crc_start = int(start_str, 0)
        crc_end = int(end_str, 0)
    except ValueError:
        logger.error("Invalid --crc-range format. Use 'start:end' (e.g., 0x
0x800:0x900).")
        sys.exit(1)
        
    if crc_end > len(image_data):
        logger.error(f"CRC end offset {hex(crc_end)} exceeds image size.")
        sys.exit(1)
        
    struct_size = crc_end - crc_start
    
    # Perform Mutation (Dry Run or Write)
    new_image, new_crc = mutate_field(image_data, crc_start, args.field, ar
args.value, 
                                      struct_size, crc_start, crc_end)
    
    logger.info(f"Computed New CRC32: 0x{new_crc:08x}")
    
    # Show Diff (First 64 bytes of range)
    diff_start = max(0, crc_start - 16)
    diff_end = min(len(image_data), crc_end + 16)
    
    logger.info("Original Range:")
    logger.info(format_hex_dump(bytes(image_data)[diff_start:diff_end], dif
diff_start))
    logger.info("Forged Range:")
    logger.info(format_hex_dump(new_image[diff_start:diff_end], diff_start)
diff_start))
    
    if args.dry_run:
        logger.info("DRY-RUN MODE: No file written. Use --out to save.")
    else:
        if not args.out:
            logger.error("--out is required to write the forged image.")
            sys.exit(1)
            
        with open(args.out, 'wb') as f:
            f.write(new_image)
        logger.info(f"Forged image written to {args.out}")

if __name__ == "__main__":
    main()
```

# File 3: `RECON_TODO.md`

```markdown
# RECON TODO — Validation Tasks for OTA/A-B Tooling

**Context:** The provided scripts (`ota_isys_frame_fuzzer.py`, `ab_metadata
`ab_metadata_crc_forge.py`) are 
structurally plausible but rely on [U] (Unknown) or [I] (Inferred) claims f
from the artifact. 
To move from "plausible" to "known-correct," the following RE tasks must be
be completed.

**Artifact Reference:** `RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md` §7 "Bottom
"Bottom line".

---

## 1. Disassemble `.ota_update.text` (71 KB)
- **Target:** `SOC_HOSTOS (85098662)` binary, section `.ota_update.text`.
- **Status:** Not disassembled in corpus (only section boundaries + rodata 
strings available).
- **Why Needed:** 
  - To confirm the **opcode table** for the `ota-isys` command frame.
  - To verify the **frame layout** (offset/width of length field, opcode po
position).
  - To identify specific validation logic beyond the "Bad command length" s
string [C].
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Allows removing `[U]` assumptions on frame 
structure.
  - Enables precise fuzzing of opcodes rather than just length fields.
- **Action:** Load binary into Ghidra/IDA, symbolize `.ota_update.text`, an
analyze `OTA_InitialTask`.

## 2. RE `/system/lib64/libghs_lip.so`
- **Target:** GHS LIP kernel shim library on the Android guest side.
- **Status:** Not RE'd in corpus. Repo prior probe used guessed ioctl codes
codes (`_IOR('g', 0x01-0x02, int)`).
- **Why Needed:** 
  - To recover the real **ioctl dispatch table** for `/dev/ghs/ota-isys`.
  - To confirm if `write()` is sufficient or if specific `ioctl` commands a
are required to trigger the RPC path.
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Allows replacing raw `write()` with correct
correct `ioctl` calls if needed.
  - Confirms whether the "dumb pipe" assumption [I] holds or if there is hi
hidden validation in the shim.
- **Action:** Extract `libghs_lip.so`, analyze exported symbols and ioctl h
handlers.

## 3. Confirm A/B Metadata Sub-field Offsets
- **Target:** Live device `misc` partition (offset 0x800).
- **Status:** Artifact confirms offset 0x800 [C], but field widths/offsets 
are [U].
- **Why Needed:** 
  - To validate the `--crc-range` argument in `ab_metadata_crc_forge.py`.
  - To ensure mutations target the correct fields (`priority`, `tries_remai
`tries_remaining`) without corrupting adjacent data.
- **Unblocks:** 
  - `ab_metadata_crc_forge.py`: Allows removing `--scan` dependency for pro
production use; enables hardcoded offsets behind verified `ASSUMPTION:` com
comments.
- **Action:** 
  1. Dump `misc` from live device (`adb pull /dev/block/by-name/misc`).
  2. Compare against known good state (e.g., after a successful boot).
  3. Use `strace` on `gm_update_engine` or direct hex inspection to correla
correlate field changes with slot state.

## 4. Verify SELinux Context for `/dev/ghs/ota-isys`
- **Target:** Device node permissions and SELinux policy.
- **Status:** Artifact notes DAC is `rw-rw-rw-` [C], but SELinux is the rea
real gate.
- **Why Needed:** 
  - To ensure `ota_isys_frame_fuzzer.py` can actually open/write the device
device without being blocked by policy.
- **Unblocks:** 
  - `ota_isys_frame_fuzzer.py`: Ensures tool execution isn't blocked by sec
security policy during testing.
- **Action:** Run `ls -Z /dev/ghs/ota-isys` and check `audit.log` for denia
denials during test runs.

---

**Priority Order:** 
1. Task #2 (libghs_lip.so) — Critical for `ota_isys` tool correctness.
2. Task #3 (A/B Offsets) — Critical for `ab_metadata` tool safety/accuracy.
safety/accuracy.
3. Task #1 (Disassembly) — High value for deeper exploit de
dev, but length fuzzing works without it.
```


</your_previous_output>

<code_review_findings>
An independent review found these bugs. Fix all of them.

1. ota_isys_frame_fuzzer.py: `--dry-run` is defined as
   `action="store_true", default=True` with no way to ever set it False (no
   `--no-dry-run`/counter flag). It's dead/confusing -- the real safety gate is
   `--send` (which correctly defaults False and is checked before any write).
   This fails safe but is sloppy. Fix: remove the redundant/unusable --dry-run
   argument entirely and make --send the single, clearly-documented toggle
   (default False = safe).

2. ab_metadata_crc_forge.py: `logging` is never imported, but
   `logging.getLogger()` (inside mutate_field()) and `logging.basicConfig()` /
   `logging.getLogger()` (inside main()) are both called. This raises
   NameError on the very first run -- the script cannot execute as shipped.
   Fix: add `import logging` at the top.

3. ab_metadata_crc_forge.py: `--dry-run` is `action="store_true", default=True`
   with NO opt-out flag anywhere in the parser (unlike file 1, there is no
   --send/--write equivalent). `if args.dry_run:` is therefore unconditionally
   true, so the `else` branch that writes --out is dead code. As shipped, this
   tool can NEVER write a forged image no matter what flags are passed.
   Fix: add a real opt-in flag (e.g. --write, default False) that must be
   explicitly passed to reach the write path, mirroring file 1's --send design.

4. ab_metadata_crc_forge.py: `--field`/`--value` are accepted by argparse and
   passed into mutate_field(), but the function ignores both -- it always
   performs a hardcoded mid-range bit-flip and only logs a warning that the
   field name was ignored. This is honest (doesn't silently pretend to target
   the named field) but delivers less control than the CLI implies.
   Fix: add an optional `--field-offset <int>` argument (operator-supplied,
   once confirmed via --scan or a live device per RECON_TODO.md item #3). If
   --field-offset is given, actually write `value` (as a single byte, or a
   width the operator can also specify via --field-width, default 1) at that
   offset before recomputing CRC32. If --field-offset is NOT given, keep the
   current generic demo bit-flip behavior, but make the fallback explicit in
   both the log output and a comment -- don't silently no-op the operator's
   --field/--value input when a real offset isn't available.
</code_review_findings>

<task>
Produce corrected versions of all three files (ota_isys_frame_fuzzer.py,
ab_metadata_crc_forge.py, RECON_TODO.md -- RECON_TODO.md only needs changes if
the fixes above affect its content, otherwise state it needs no changes).
Fix every finding above. Do not silently drop a finding -- fix it or explicitly
state why it's out of scope.
</task>
