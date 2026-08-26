# MDI2 Manager — Identification Service, WiFi pairing, and device log-pull protocol

**Date:** 2026-08-25. Scope: the Windows "MDI2 Manager" / "GM MDI Identification Service"
stack, as distinct from DPS/SPS diagnostic sessions (already covered in
`MDI2_DPDU_API_PROTOCOL_AUG2026.md`). Source material: full Ghidra disassembly
(`gm_dps/disassembly/pseudocode_mdi2mgr/`), prior binary analysis at
`gm_dps/docs/GM_MDI_IDENT_EVIDENCE_protocol.txt`, and live testing against real MDI2 hardware
(192.168.171.2) on 2026-08-25.

**Note:** a separate, concurrent session is actively working on installing the real MDI2
Manager under Wine. This doc is the static/protocol-analysis half of that effort — do not
duplicate the Wine installation work itself here.

## 1. `GM_MDI_Ident.exe` — the Identification Service

Two instances of one binary run concurrently, each bound to a different Windows-loopback-only
port (127.0.0.1 only — confirmed unreachable from the device side and from macOS by direct
live probe):
- `127.0.0.1:8098` — "GM MDI Software\GM MDI Identification Service" instance
- `127.0.0.1:8125` — "Bosch\VTX-VCI\VCI Software (GM)\VCI Identification Service" instance

> **CORRECTION (2026-08-25, live capture):** both instances now bind **`0.0.0.0`**, not
> `127.0.0.1` — verified with `Get-NetTCPConnection -State Listen` on the running Surface
> (LocalAddress `0.0.0.0`, ports 8098/8125). They are reachable from the host's other subnets,
> though the Manager still dials them via `127.0.0.1`. The "loopback-only" claim above is stale.

No TLS on either — plain custom binary protocol over raw `WS2_32` sockets (also a named pipe,
`\\.\pipe\VTX_Identification_Service`). Wire framing: length-prefixed segments
(`[u32 LE total_len][u32 LE opcode/SID][payload]`), dispatched in
`CClientConnectionMgr::OnDataReceived` via a long SID compare-chain. Confirmed SIDs:

| SID (hex/dec) | Name | Direction |
|---|---|---|
| 0x7f2 / 2034 | SID_IDENT_CONNECT_SEND | client→ident |
| 0x8a9 / 2217 | (unnamed in evidence doc; response vtable = `CLogFiles_Recv`) | client→ident, log-pull trigger — see §3 |
| 0x8b9-0x8bc | WIFI_CONNECT/DISCONNECT/REQ | — |
| 0x8bf / 0x8c0 | SID_WIFI_ENABLE_SEND / WifiEnable_Recv | — |
| 0x8c1-0x8c4 | WIFI_ADAPTER_INFO / WIFI_ADAPTER_IF_INFO / WifiList | — |
| 0x8d1 / 0x8d2 | SID_WIFI_CREDENTIALS_SEND / WifiCredentials_Recv | client→ident (see §2) |
| 0x902 / 2306 | SID_USB_GET_STATUS_SEND | — |

Everything outside the IDENT/WIFI/USB block is **relayed to "the VCI/protocol_stack"** rather
than handled locally — i.e. the ident service is a thin local multiplexer in front of the real
device-facing protocol stack (`bvtx_vci_rt*.dll`).

## 2. CORRECTION (superseding an earlier finding in `MDI2_DPDU_API_PROTOCOL_AUG2026.md` §12):
opcode 0x8d1/0x8d2 is WiFi AP pairing, not a port-10123 credential

Traced end-to-end: `gm_mdi_ident.exe`'s `CClientConnectionMgr::OnDataReceived` 0x8d1 branch logs
`"SID_WIFI_CREDENTIALS_SEND"`, deserializes a `CWifiCredentials_Send` object, and routes to
`CIdentWifi::SetWifiCredentials` (log format `"%s ssid = %s serial_number = %s ... version =
%s"`), which builds a Windows WLAN profile (`CreateProfile`, auth `"AES-CCMP"`). The sender,
`bvtx_vci_rt_j.dll`'s `CDeviceMgr::SetConfigItems`, pulls the pair from config items literally
named `"SSID"` / `"Passphrase"` (config IDs `0x12`/`0x13`, via `VtxRtGetConfigItems`/
`SetConfigItems`, opcodes `0x7e3`/`0x7e4`), only format-validated
(`ifm::ValidateWifiConfig`), never generated or looked up from any registry/DPAPI/backend store.
**This is the VCI's own WiFi access-point passphrase, unrelated to TCP/10123 authorization** —
the earlier doc's causal claim (that this credential explains the 10123 `ECONNREFUSED`) is
wrong and has been corrected there. Also checked: the real capture that motivated that theory
used the same Ethernet-gadget-style transport we replay from macOS (`capinfos` →
`"Ethernet 2"` on Windows), not WiFi, so a WiFi-vs-USB transport mismatch isn't the explanation
either. **Net effect: the actual port-10123 gate remains unexplained.**

## 3. Device log-pull mechanism (the actual finding this doc is mainly for)

Motivation: three real pulled log files exist on disk
(`gm_dps/docs/live_captures_20260824_2/GM {Dmesg,Varlog,VCIHistory} 2026-08-24T11-54-5{1,6}-D88985275.txt`),
confirming the MDI2 Manager can retrieve device logs — but no corresponding network capture
exists (the pull happened at 11:54, before any of the six known pcaps start at 12:03+; content
search for distinctive log strings — `"Booting Linux"`, `"Bosch LP518"`, hostname
`"2505-88985275"` — is a confirmed zero-hit across all six captures).

### 3.1 Transport: FTPS, not the SID/IPC protocol

> **CORRECTION (2026-08-25, live capture — see §4):** FTPS/21 is **not** the path the
> Manager's *Get Log Files* button actually uses. A live capture of the real Bosch VCI Manager
> 9.x pulling logs shows the pull runs over an **encrypted TCP channel on device port 9052**
> (part of the 900x port bank, §4), not vsftpd/21. The `firmware:vtx` FTPS login is real and
> still works, but it belongs to a **different** code path (the AAOS/Android reprogramming-log
> route flagged in §3.3 caveat 3), not the general Dmesg/Varlog/VCIHistory pull. Treat §3.1–3.3
> as accurate for *that* FTP path only; §4 is the authoritative account of the button.

The device runs a **real FTP server** on port 21: `220 Global VCI FTP Server`, vsftpd 3.0.3
(`STAT` confirms), `UNIX Type: L8`, FEAT lists `AUTH SSL`/`AUTH TLS`/`EPRT`/`EPSV`/`PASV`/`PBSZ`/
`PROT`/`REST STREAM`/`SIZE`/`TVFS`/`MDTM`. **Credentials are hardcoded in `bvtx_vci_rt_j.dll`:
`firmware` / `vtx`**, set via libcurl `CURLOPT_USERPWD` (opt `0x2715`). Confirmed live
(2026-08-25) against the real unit: plain FTP login is refused
(`530 Non-anonymous sessions must use encryption`); **explicit FTPS (`AUTH TLS`) login with
`firmware:vtx` succeeds** — this is a genuine, reproducible, unlock-free win, independent of the
port-10123 problem.

Exact curl options used by the real client (from `FUN_100cdcb0`, entry `0x100cdcb0` in
`bvtx_vci_rt_j.dll`, the real `curl_read` function — confirmed by reading its full body):
`CURLOPT_USE_SSL=3` (`CURLUSESSL_ALL`, both control and data channel),
`CURLOPT_FTPSSLAUTH=1` (`CURLFTPAUTH_SSL` — i.e. sends `AUTH SSL`, not `AUTH TLS`; untested
whether this distinction matters to the server), `SSL_VERIFYPEER=0`, `SSL_VERIFYHOST=0`
(self-signed cert, no validation), `CURLOPT_INTERFACE` bound to the caller's own source IP,
plus standard verbose/timeout/retry housekeeping (4 retries w/ 500ms backoff on connect
failure).

### 3.2 The path is a magic token, not a real filename

URL is built as `"ftp://firmware@" + host + "/" + path`, **no directory prefix ever added** —
confirmed by reading `FUN_100cdcb0` in full. The `path` argument passed in by the only caller,
`CDeviceMgr::get_file_from_device` (`FUN_100c63a0`), is **not** one of the four real log names —
it's a magic streaming token:
- **`RETR any-file`** — pulls the next staged log file in a queue (repeated in a loop; a
  `CURLE_REMOTE_FILE_NOT_FOUND` (curl code 78 / `0x4e`) response containing `"any-file"` is
  treated as benign end-of-stream, not an error — confirmed via the exact NRC-check logic at
  line 186196 of that function).
- **`RETR end-file`** — sent once after the loop to finalize/signal completion.

The four real names (`"messages"` → category "Varlog", `"messages.driver"` → "Dmesg",
`"vci-history.xml"` → "VCIHistory", `"VTX_RT_Server.log"` → "Categories"/"Runtime") are matched
by a separate classifier (`FUN_10079e40`, called from `` `anonymous-namespace'::ArchiveLogFile ``)
against a name **the server supplies inline during the any-file stream**, purely to decide the
local output filename — they are never sent as RETR targets themselves. This is why guessing
literal filenames (`RETR messages`, `RETR /var/log/messages`, etc.) correctly failed with
`550 Failed to open file` in every live test.

**Live-tested (2026-08-25) and still unresolved**: `RETR any-file` also returns
`550 Failed to open file` cold, with no preceding trigger. `STAT /` on the real device shows
the FTP root is a **genuinely empty staging directory** (`drwxrwxr-x`, only `.`/`..`, mtime
`Aug 24 12:28` — i.e. last touched during a real session yesterday, untouched since), confirming
files are staged transiently during an active pull, not persistently present.

### 3.3 The staging trigger: SID 0x8a9 (`CLogFiles_Recv`) — found but not fully resolved

`FUN_10083fb0` in `bvtx_vci_rt_j.dll` — the function that gates the whole get-logs flow (checks
two state flags at `in_ECX+0x59c`/`+0x59d` before proceeding) — constructs and sends **SID
`0x8a9`** (`FUN_10246240(0x8a9)`) with response type `CLogFiles_Recv::vftable` before any FTP
activity. This is almost certainly what causes the device to populate the FTP staging directory.

**Two open problems, not yet resolved:**
1. SID `0x8a9`'s handler wasn't found in the disassembled scope — an apparent match at line
   406212 of the same file turned out to be a false positive (a statically-linked OpenSSL
   `s3_srvr.c` internal state constant, unrelated). The evidence doc's known ident-service SID
   table doesn't cover `0x8a9` either.
2. Whatever it does, `0x8a9` is sent to the **Windows-loopback ident service**
   (127.0.0.1:8098/8125) — confirmed unreachable from macOS or from the device network. Even
   with the exact trigger bytes, there's no live target to send them to without the real
   `GM_MDI_Ident.exe` process running (natively or under Wine).
3. Weaker caveat: the `any-file`/`end-file` FTP mechanism was found specifically under
   `DevMgr::RunAndroidDeviceUpdate` / `DevMgr::end_reprogramming` in the call graph — it may be
   the Android/AAOS head-unit programming-log path rather than the general
   dmesg/varlog/vci-history pull that produced the files in `live_captures_20260824_2/`. Not
   confirmed either way.

### 3.4 Recommended next step

Get the real `GM_MDI_Ident.exe`/Manager stack running under Wine (tracked in a separate,
concurrent session) and capture a fresh network trace of an actual Manager-driven log pull.
That would directly answer: (a) what SID `0x8a9`'s wire effect actually is, (b) whether it's
relayed to the device over the already-documented low-port channel (`gm_dps` §11) or something
else, and (c) whether `any-file`/`end-file` is really the general log-pull path or Android-update
-specific. Once the trigger is known, the FTPS side is already proven working
(`firmware:vtx` auth confirmed live) — only the staging trigger is missing.

---

## 4. LIVE CAPTURE 2026-08-25 (late) — the real Manager transport (authoritative; supersedes the FTPS assumption in §3.1 for the *Get Log Files* button)

First successful end-to-end network capture of the **real Bosch VCI Manager 9.1.2752.177**
(`GM_MDI_Manager.exe`, not Wine) driving a live MDI2. Bench: Win11 Surface Pro (host
`192.168.171.30`) cabled USB to a Bosch VCI MDI2 (device `192.168.171.2`, MAC `70-C6-AC-00-05-38`;
host-side NIC MAC `...39` — paired). Device internals (from the pulled plaintext): **Linux
4.14.162-gvci, ARMv7, "Bosch LP518 Board", hostname `2505-88985275`, serial `D88985275`**.
Capture driven remotely over SSH: `dumpcap -i <MDI2> -i <loopback>`, launched **detached via
WMI `Win32_Process.Create`** (a plain `Start-Process`/SSH-child dumpcap is killed when the SSH
session closes; the scheduled-task route failed on account-SID mapping). Artifacts (working tree,
not this repo): `GM_research/mdi2_macos/captures/mdi_session_full_with_handshake.pcapng` (+
`markers.log`, wall-clock phase markers; in-band markers = ICMP echo payload size 1337), and the
matching **decrypted plaintext** logs under `captures/plaintext_logs/`.

### 4.1 Transport: a 14-socket bank on device ports 900x — NOT 10123, NOT FTP

On every UI **Connect**, `GM_MDI_Manager.exe` (the runtime DLL is in-process — it owns the
sockets directly, confirmed via `Get-NetTCPConnection … OwningProcess`) opens a **fresh bank of
14 parallel TCP connections** to the device:

    9001  9003  9006  9007  9008  9009  9010  9011  9012  9013  9014  9050  9051  9052

A subsequent Connect opens a new bank; the previous bank goes to `TimeWait`. `10123` (the DPS
D-PDU tunnel, `MDI2_DPDU_API_PROTOCOL_AUG2026.md`) and `13400` (DoIP) are **closed** during a
Manager session — those are diagnostic-session ports, unrelated to the Manager. Ports **21 (FTP)
and 80 (HTTP) are open** on the device but the Manager's log button does not use them (§4.3).

### 4.2 Wire framing (big-endian) and per-message counter

All 900x channels share one framing — note **big-endian**, opposite the 10123 D-PDU path's LE:

    [u32 BE  0x00000000]              # always zero
    [u32 BE  payload_len]            # bytes following the 8-byte header
    [payload]

`payload = [4-byte incrementing per-message counter][encrypted body]`. Counters step by 1 per
message per channel — observed live: `f8b7c055 → f8b7c056 → f8b7c057`, `be53536c → 6d → 6e`,
`d5a2f0c1 → c2`, and the log channel's `8aa81d35 → 36 → 37 → 38` (one step per *Get Log Files*
click). Encrypted bodies show **repeating 16-byte ciphertext blocks** across messages and across
repeated identical pulls → a **block cipher in ECB mode, 16-byte block** (AES-ECB shape; key/
derivation not yet recovered). Each connection also carries an 8-byte **plaintext control frame**
right after connect: `00 53 50 00 00 30 00 00` (variant `00 53 50 00 00 21 00 00` on port 9011 —
the low byte, `0x30`/`0x21`, appears to encode a per-port service/type).

### 4.3 *Get Log Files* button → port 9052, encrypted stream

Click → 28-byte request on **9052**:

    00000000 00000014            # hdr, payload_len = 0x14 (20)
    8aa81d35                     # 4-byte counter (increments per click)
    1c2faed2 8c01416a a6c46ff4 f64834b0   # 16-byte session token, CONSTANT within a session

Server replies with the log payload as a stream of 1460-byte (MSS) segments, **encrypted**
(same ECB signature), ~81 KB per pull. The **16-byte token is constant across pulls in one
session and changes across sessions** — a session/auth handle, and the leading candidate for the
long-unexplained port-auth gate (§2/§3.3). The Manager writes the **decrypted** result to
`C:\ProgramData\Bosch\VTX-VCI\VCI Software (GM)\Logs\Categories\` as
`GM {Dmesg,Varlog,VCIHistory} <ISO-ts>-D<serial>.txt`. **We captured the 9052 ciphertext and the
matching plaintext file for the same pull** → a known-plaintext pair to attack the cipher.

### 4.4 UI-button → function map (answers "buttons should map to functions")

- **Get Log Files** button handler = `FUN_00437700` in `gm_mdi_manager.exe` (branches on the
  worker's return: `0` → "Log Files retrieved", nonzero → "Failed to retrieve Log Files"; save
  path from registry value `LogFileLocation`).
- Worker = `FUN_0044f0a0` → calls `FUN_00460da0()` then a virtual call
  `(**(*DAT_004c5554 + 8))(&arg)` through the in-process **runtime session object**
  `DAT_004c5554`. The exe is a thin MFC shell; the 9052 socket, BE framing, counter, token, and
  decryption all live in the runtime DLL (`bvtx_vci_rt*.dll` / `bvtx4j32.dll`). Recovering the
  cipher/key means tracing from that vtable slot into the runtime's send/recv + crypto — that is
  the single remaining blocker for a native macOS reimplementation.

### 4.5 UI Connect/Disconnect is loopback IPC only

A deliberate **Disconnect → Connect** cycle produced **no** device-facing TCP for the *logical*
toggle — only loopback IPC to the ident service `127.0.0.1:8125` (Manager → 106-byte request /
16-byte ack; ident → **~16.6 KB** device-identification/config blob). The device 900x bank is
managed separately (it re-banks on Connect, §4.1). This is why the operator's UI never showed a
"disconnect": the device link (and the multicast beacon, §4.6) is independent of the UI's logical
connect state.

### 4.6 Device discovery beacon (free win for a macOS client)

The MDI2 continuously multicasts `192.168.171.2:42178 → 225.1.1.1:8194`, 106-byte UDP payload
(~1/s). A native macOS tool can **passively discover the device and confirm liveness by joining
`225.1.1.1:8194`** — no handshake, no auth. The idle keepalive/"watchdog" the operator asked
about is this UDP beacon, not TCP.

### 4.7 macOS reimplementation foundation — what is now known vs blocking

Known & reproducible from macOS today: device discovery (§4.6), the 900x connect topology
(§4.1), the BE framing + counter + 8-byte control frame (§4.2), the 9052 request layout (§4.3),
and the exact plaintext the pull yields (ground-truth files). **Blocking:** the ECB block-cipher
key/derivation for the 900x/9052 bodies, and the origin/lifecycle of the 16-byte session token.
Next step is code-side, not capture-side: trace `DAT_004c5554`'s vtable into the runtime crypto,
and/or exploit the captured known-plaintext↔ciphertext pair.

### 4.8 Crypto of the 900x/9052 bodies — Blowfish-ECB (runtime-DLL trace, 2026-08-25)

Traced from the *Get Log Files* vcall into `bvtx_vci_rt_j.dll` (image base `0x10000000`;
regional twins `bvtx_vci_rt.dll`/`_p` are byte-for-byte equivalent here). The transport class
is **`TrnPrt`** (log strings `TrnPrt::Run … Encrypting/Decrypt`, `TrnPrt::SendRecv_ArchiveBuffer`).

**Algorithm = Blowfish in ECB, confirmed by construction, not inference:**
- Key schedule `FUN_101dce80` (= `BF_set_key`) seeds the P-array with the π-digit constants
  `0x243f6a88 0x85a308d3 0x13198a2e …` and copies the 1024-dword S-box table from `DAT_102fa138`.
  That S-box is the **standard Blowfish** table (`DAT_102fa138` little-endian = `0xd1310ba6
  0x98dfb5ac 0x2ffd72db 0xd01adfb7 …`) — so any stock Blowfish (e.g. pycryptodome, big-endian
  block convention) is byte-compatible.
- Block routine `FUN_101dc790` (= `BF_encrypt`), buffer enc/dec `FUN_101dd350` / `FUN_101dcfe0`.
- Encrypt `FUN_10268b90` pads the post-counter region to a multiple of 8; decrypt `FUN_10268a40`
  rejects non-multiples with **`"Invalid message size, encrypted message must be multiple of 8"`**
  → **8-byte block** (Blowfish/DES family; the S-box + π seed pin it to Blowfish, not DES).
- Key length passed to `BF_set_key` is **`0x38` = 56 bytes** — Blowfish's maximum (448-bit) key.

**On-wire layout of every 900x/9052 message (all 14 channels share it):**

    [u32 BE 0x00000000][u32 BE payload_len][u32 counter (CLEARTEXT)][Blowfish-ECB(body)]

The 4-byte counter is *not* encrypted (encrypt pads `payload_len-4` to a multiple of 8); it
increments per message and the **response echoes the request's counter** (live: request on 9052
`…00000014 | 8aa81d35 | <token>`; response `…0000e474 | 8aa81d35 | <58480-byte BF-ECB blob>`,
matching the ~57 KB Varlog it decodes to). No per-message IV (pure ECB — confirmed by repeating
16-byte ciphertext runs on the wire and repeating block runs after trial-decrypt).

**Key source `FUN_10246d40`** — a mutex-guarded keyring indexed by module-type id (table at
`DAT_10302ac8`, entries strided `0x104` bytes: `[u32 id]["MODULE_TYPE_ID_MDI"…][key @ +0xC4]`;
`param_1==0` → default key at `DAT_10302a90`). The default/`MODULE_TYPE_ID_MDI` blob extracted
statically is
`43297fad38e373fe07a7137045da2a16 04689104c2fd3b2f37d06bb516cb7546 1f08260d1ac2465e58402364 1aba6176 02581616 4629b007` (56 B) — **but it does NOT decrypt the captured 9052
stream** (tried both key- and block-word orders against the known Varlog plaintext; ECB structure
appears, plaintext does not). So the operative key is the one `BF_set_key`'s `this`/context holds
at encrypt time, set by the `TrnPrt` constructor (or a different keyring entry), **not** this
static default.

**Two routes to the operative key (either finishes the macOS client):**
1. *Static:* trace the `TrnPrt` constructor / where `FUN_10268a40`/`b90`'s `this` gets its 56-byte
   key member, and where the keyring entries at `DAT_10302ac8+0xC4` are populated at init.
2. *Dynamic (fastest — we have a live session):* the Manager is running with an open session on
   the Surface. Attach x64dbg/WinDbg to `GM_MDI_Manager.exe`, breakpoint `BF_set_key`
   (`bvtx_vci_rt_j.dll+0x1dce80`) or dump the key-schedule buffer `DAT_102f9c20` after a
   *Get Log Files*, and read the 56-byte key directly. Then verify against the captured
   ciphertext↔`captures/plaintext_logs/` pair (harness in `mdi2_macos/`, pycryptodome
   `Blowfish.MODE_ECB`).

**Net for the macOS port:** algorithm, framing, counter, block size, and the exact validation
oracle are all locked; only the 56-byte Blowfish key remains, and it is one debugger breakpoint
away given the live rig.

### 4.9 Live key extraction + reproduction status (2026-08-25, later)

**All six keyring keys pulled from the running Manager** (pid, `bvtx_vci_rt.dll` — the *plain*
variant is what loads, base `0x731F0000`; RVAs match the `_j` pseudocode) via read-only
`ReadProcessMemory` (PowerShell P/Invoke over SSH; the 32-bit module list needs SysWOW64
PowerShell). Keyring table at DLL RVA `0x302ac8`, entries strided `0x104`: `[u32 id][name][key
@+0xC4, 56 B]`:

| id | name | 56-byte Blowfish key (hex) |
|----|------|-----|
| 1 | MODULE_TYPE_ID_MDI | `43297fad38e373fe07a7137045da2a16 04689104c2fd3b2f37d06bb516cb7546 1f08260d1ac2465e58402364 1aba6176 02581616 4629b007` |
| 2 | MODULE_TYPE_ID_M_VCI | `34921fad38e373ee37a7137035da2a16 04689104d2fd3b1f37d06bb316cb7546 1f08260d1ac2465e58402364 1aba6176 02581616 4629b007` |
| 3 | MODULE_TYPE_ID_6520_Generic | (= id 1) |
| 4 | MODULE_TYPE_ID_6515_Maserati | (= id 1) |
| 5 | MODULE_TYPE_ID_6515_SD | (= id 1) |
| 6 | MODULE_TYPE_ID_6515_TwinTec | (= id 1) |

The MDI2 hardware here (Bosch LP518, "GM branded MDI2") is classed **`MODULE_TYPE_ID_M_VCI`
(id 2)** by the 9.x stack — its key (`34921fad…`) is the only one that differs from the shared
default. (id 1 `MDI` = the original MDI generation.)

**Cipher wrapper is a named-dispatch layer, not raw Blowfish.** `FUN_101dd350`/`FUN_101dcfe0`
start by *string-comparing* their mode arg against `DAT_102f9c20 = "ecb"` (confirmed both in the
binary and by the live dump of that address returning `65 63 62 00` = "ecb"). The real block
routine is `FUN_101dc790`: textbook Blowfish rounds (`xL ^= P[i]`, `xR ^= F(xL)`, F = `((S0[a]+
S1[b])^S2[c])+S3[d]`), P at ctx+0, S-boxes at ctx+`0x12`/`0x112`/`0x212`/`0x312` (the S-box
table `DAT_102fa138` is the standard Blowfish S-box). **But the four F-function byte selectors
are read from a runtime table `ctx[0x412..0x415]`** — i.e. the byte order feeding the S-boxes is
parameterized, a non-standard variant. Stock big-endian Blowfish (pycryptodome) does **not**
reproduce the stream with either candidate key across key/block word-swap combinations, and the
known-plaintext oracle (`captures/plaintext_logs/GM Varlog …txt`) stays unmatched — the gap is
this F-byte-order table, not the key.

**Finish (one of):** (a) reimplement Blowfish per `FUN_101dce80`+`FUN_101dc790` with the S-box
table from `DAT_102fa138` and brute the small `ctx[0x412..0x415]` byte-order space against the
oracle; or (b) live-dump the *keyed* context (P+S after `BF_set_key`, incl. `ctx[0x412..0x415]`)
and run the raw Feistel — removes all endianness guessing. Key material, block routine, framing,
and oracle are all in hand; only the byte-order permutation remains.

**UPDATE (2026-08-26): static keys ruled out — key is session-derived.** A faithful from-scratch
reimplementation of the DLL's exact Blowfish (standard S-box from `DAT_102fa138`, π P-array, F =
`((S0+S1)^S2)+S3`, native little-endian block load, the `ctx[0x412..0x415]` permutation applied
to **both** key-packing and F-selection) was brute-forced over **all 24 byte-order permutations ×
both candidate keys** against the Varlog oracle. It reproduces the ECB block-repetition structure
but never the plaintext. Conclusion: `MODULE_TYPE_ID_*` keyring values are **defaults/fallbacks,
not** the operative 9052 key — the live key is established per session (the constant-per-session
16-byte handshake token, or a key negotiated over the 900x connect exchange, is the prime
suspect). Corrected finish: (a) trace the `TrnPrt` constructor to where its 56-byte key member is
written at session setup (is it copied from the keyring, or derived from the token / handshake?);
or (b) live-dump the *keyed* Blowfish context after a *Get Log Files* — this needs the per-object
context address, i.e. a debugger (none installed on the bench; x64dbg/WinDbg SDK would close it in
one breakpoint on `bvtx_vci_rt.dll` `BF_set_key`/`FUN_101dce80`, reading its key argument). The
reimplementation harness + oracle are ready to confirm the instant the real key/derivation is in
hand.
