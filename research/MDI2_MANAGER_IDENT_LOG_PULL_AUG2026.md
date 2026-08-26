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

### 4.10 SOLVED (2026-08-26) — standard Blowfish-ECB + live per-session key = 100% decrypt

The 9052 log stream is now decrypted end-to-end and byte-validated. Two facts closed it:

1. **It is *standard* Blowfish-ECB, big-endian — stock-library compatible.** The
   `ctx[0x412..0x415]` byte-order table holds the standard `{3,2,1,0}`; the block words are
   big-endian (`>II`), key packed big-endian. My earlier miss was purely the little-endian block
   assumption *plus* the wrong key. `Crypto.Cipher.Blowfish` (pycryptodome) `MODE_ECB` reproduces
   it exactly — no custom variant needed.
2. **The 56-byte key is per-session and was extracted live.** A Frida hook on
   `bvtx_vci_rt.dll` `BF_set_key` (RVA `0x1dce80`, live `base+0x1dce80`) reading its 56-byte key
   argument yielded (this session) `fde7ccb213c2b103c29a617520a9785bbf76df196dcc893412a009bbd199c34bdad67312d5909463130f6169d588af7bbd26641b01f8fd0c`.
   It is stable for the Manager-process lifetime but changes across sessions (an *earlier* capture
   would not decrypt with a *later* session's key — which is why the static keyring keys of §4.9,
   and any cross-session key, all failed).

**Validation:** capturing a fresh 9052 pull *and* the live key from the **same** session, stock
pycryptodome Blowfish-ECB decrypts the big frame to **100.00% byte-match (59497/59497)** against
the Manager's own saved plaintext `GM Varlog …txt`.

**Decoded frame + container:** on 9052, an 8-byte plaintext control frame `00 53 50 00 00 XX 00
00` precedes the messages; each message is `[u32be 0][u32be len][u32 counter][Blowfish-ECB body]`
(counter increments per message: `c583adc1…c5`). The decrypted big-frame body is an inner file
container — little-endian `[size][id][namelen][name]` entries (e.g. name `"messages"` = the
Varlog category) — followed by the raw log text.

**Tooling (working):** `GM_research/mdi2_macos/mdi2_9052_decrypt.py` (pcap + key → plaintext) and
`ps/frida_bf.py` (attaches to the live Manager, dumps the session key from `BF_set_key`).

**Remaining for a *fully native* macOS client (no Windows/Frida in the loop):** recover how the
56-byte session key is **derived/negotiated at Connect** (device-side vs client-side, and from
what — the 16-byte session GUID, the 900x handshake exchange, or the device serial). Everything
else — discovery (§4.6), the 14-socket transport (§4.1), framing/counter (§4.2), the cipher
(§4.10), and the container format — is reimplementable today. Key *derivation* is the sole open
item; live key extraction is a working stopgap in the meantime.

### 4.11 CORRECTION (2026-08-26): the key is DETERMINISTIC/stable, not per-session

§4.10 called the key "per-session" — that was wrong, an artifact of the still-buggy decryptor at
the time it was tested. With the corrected stock-Blowfish decryptor, the key
`fde7ccb213c2b103…01f8fd0c` decrypts **every** capture from this unit, across:
- two different Manager processes (pid 7064 and a later pid 8704),
- multiple Disconnect→Connect cycles,
- the original 22:59 capture *and* the later one — 100% both.

`BCryptGenRandom` never fires for it (hooked live), and the 56 key bytes appear **nowhere** as a
literal in `bvtx_vci_rt*.dll` / `bvtx4j32.dll` / `device_res.dll` / the Manager exe. So the key
is **computed deterministically at runtime from a stable input** (device serial `D88985275` /
the keyring key / a fixed constant via a KDF — derivation still being traced). It is **not** one
of the static `MODULE_TYPE_ID_*` keyring keys.

**Practical upshot for macOS:** the operative key is *fixed for a given unit*. Extract it once
per device via the Frida `BF_set_key` hook and hard-use it — no per-session/ per-pull extraction
needed. Whether it is global (same for all MDI2 units) or per-device (serial-derived) is the open
question; the derivation trace (below/next) resolves it.

### 4.12 Key derivation trace (2026-08-26) — deterministic, computed at init, not at Connect

Live tracing (Frida on a fresh Manager, attached *before* Connect) of how the 56-byte
`fde7ccb2…` key comes to exist:

- **Ruled out at Connect:** the keyring function `FUN_10246d40` (`+0x246d40`) is **never called**,
  `BCryptGenRandom` **never fires**, `BCryptHashData` **never fires**, and **no `memcpy`/`memmove`
  of the key bytes** occurs. Hooked all of these across a full Disconnect→Connect + Get Log Files.
- At the first `BF_set_key`, the key `fde7ccb2…` is **already present** in the `TrnPrt` object,
  even though we attached before Connect. Backtrace (raw RVAs → functions) of the *use* path:
  `FUN_10268b90`(enc)→`BF_set_key` ← `FUN_1026b270` ← `FUN_10269ab0` ← `FUN_1026afd0`(TrnPrt) ←
  `FUN_100aeff0` ← `FUN_100af180` ← `FUN_100b1ec0` ← `FUN_1007b0b0` ← `FUN_1009bdb0` ←
  `FUN_100591f0` ← `FUN_10040f80`. This is the log-pull path; it *reads* the key, doesn't derive it.
- The live **keyring in memory still holds the on-disk defaults** (`43297fad…`/`34921fad…`,
  confirmed by ReadProcessMemory), so `fde7ccb2…` is derived and stored **only in the TrnPrt
  object**, by **direct stores** (not a CRT copy), and — since attaching post-launch already
  finds it present — **most likely at process/DLL init**, before any Connect.

**Conclusion:** the key is a **deterministic function of stable input, computed once at init via
inline stores** — not negotiated with the device at Connect and not randomly generated. Whether
the input is the device serial (`D88985275`), a fixed constant, or a transform of the keyring
default is still open.

**Next step to pin it (either):** (a) `frida.spawn` the Manager suspended, install the
keyring/RNG/hash/memcpy + a broad store-tracer, then resume — captures the **init-time**
derivation the post-attach hook misses; or (b) hardware write-watchpoint on the key address
(captured at the first `BF_set_key`) across a reconnect that reuses the object. 

**Practical status unchanged:** the key is fixed per unit, so extract-once via the `BF_set_key`
hook + reuse fully enables the macOS decryptor today (validated 100%). Native key *derivation* is
the only remaining item, and it is an init-time deterministic computation, not a Connect-time
exchange.

### 4.13 Spawn capture result (2026-08-26) — derivation is Connect-time and inline (no lib calls)

`frida.spawn` of the Manager with init-time hooks (keyring, `BCryptGenRandom`, `BCryptHashData`,
key-content `memcpy`/`memmove`, `BF_set_key`) + a memory scan for the key, all armed on
module-load before `resume`:

- **12 s after spawn, with no device Connect, the key `fde7ccb2…` is NOT present in process
  memory** (`Memory.scan` of all `rw-` ranges → 0 hits), and none of the hooks fired.

This **refutes the "derived at init" hypothesis** (§4.12): the key is **not** computed at
startup. Combined with §4.12 (attaching *before* Connect, then connecting, still caught no
keyring/RNG/hash/memcpy yet the key was present at first `BF_set_key`), the derivation is:

- **Connect-time** (only exists after a device Connect), and
- **inline** — pure in-DLL arithmetic/stores, using **no** keyring lookup, no `BCrypt*`, no CRT
  copy. Deterministic (same value every time) from stable input.

**Definitive next technique (the only ones that can catch inline stores):** (a) hardware
write-watchpoint on the key address — capture it at the first `BF_set_key`, set the watchpoint,
then Disconnect→Connect so the derivation re-writes it; or (b) `Stalker` trace of the Connect
path, filtering for the instruction that first writes `fde7ccb2`. Both require a GUI Connect on
the live rig. Static alternative: locate the `TrnPrt` constructor (vtable holding
`FUN_10268a40`/`FUN_10268b90`) and read its key-init.

**Deliverable status:** unchanged and complete — deterministic per-unit key, extract-once via the
`BF_set_key` hook, 100%-validated decrypt. Only the exact inline derivation formula (→ global vs
serial-derived) remains open.

### 4.14 Static derivation trace (2026-08-26) — architecture mapped; exact formula still buried

Pursued the derivation via static RE (safe/offline) + confirmed dynamic facts. Mapped the
transport/crypto class structure in `bvtx_vci_rt.dll`:

- The cipher `this` is a **key-holder object** (56-byte key at **offset 0**; enc `FUN_10268b90`,
  dec `FUN_10268a40` re-key from it each call). It is **distinct** from `CTransport`
  (`TrnPrt`/`CTransport::vftable`, ctor `FUN_1025cd30`, offset 0 = vtable).
- Connect wiring: `CClientTransport::InitializeClientStart` (`FUN_1025dc70`) allocates each
  0xA0-byte `CTransportServer` (`FUN_1025cd30`); connect handlers `FUN_1005f5f0` / (line 175781)
  drive the SID handshake (`0x7f5/0x849/0x874`) over a 0x2000 buffer (`FUN_10246990`).
- The key-holder class methods cluster at `FUN_10268040`–`FUN_10269620` (mostly
  serialize/enc/dec). `FUN_102682e0` is a deserializer, not SetKey.

**Dynamic facts that constrain the derivation (from §4.11–4.13 + this session):**
- Deterministic; **one master** key-holder persists across Disconnect (heap ~`0xd2dxxx`), copied
  by inline stores into ~13 per-channel holders on Connect (freed on Disconnect).
- Computed **once at first Connect** (absent before Connect; not re-derived on reconnect — a
  `MemoryAccessMonitor` write-watch on the master pages caught **no** write during reconnect).
- Uses **no** keyring lookup, `BCryptGenRandom`, `BCryptHashData`, or CRT `memcpy` — pure inline
  arithmetic. No device-serial reference seen on the traced connect/crypto path so far.

**Precise remaining lead:** the key-holder's `SetKey` (writes 56 bytes to holder+0) inside the
`FUN_10268xxx` cluster, and its single caller on the first-Connect path — that caller holds the
seed. Finding it pins global-vs-per-device. This is a bounded but non-trivial RE dig (several more
functions), not answerable from the traces alone.

**New capability delivered this session:** full **headless GUI automation** of the Manager over
SSH — a `/it` scheduled task (runs in the interactive session) + `SetForegroundWindow`+mouse-click
drives open/close/**Connect** (auto-id 1121)/**Disconnect** (1122); verified Connect →
"Connected: SN 88985275". Scripts in `mdi2_macos/ps/` (`uia_drive.ps1`, launchers). This makes
future capture/experiments fully self-driving (no human clicks).

**Bottom line unchanged:** the macOS foundation is complete and validated — only the exact inline
key-derivation formula remains, now localized to the key-holder `SetKey` caller.

### 4.15 Static trace — pseudocode wall (2026-08-26)

Pushed the `SetKey`-caller trace to its pseudocode limit. Dead-end reasons (so this isn't
re-run blindly):

- The enc/dec (`FUN_10268a40`/`b90`) run as `__thiscall` with the **key-holder in ECX**, and that
  ECX is produced through **C++ move-semantics helpers** — e.g. `FUN_102113c0` is just
  `*this = *src; *src = 0` (a `std::move` of a pointer). Ghidra's decompiler **drops the ECX
  provenance** across these, so the key-holder's constructor + key-write can't be followed in the
  pseudocode.
- The `0x10268xxx` address neighborhood is **XML/istream parsing** (peek `<`/`>`, "unexpected
  EOF"), not the crypto class — adjacency is misleading.
- Connect handlers (`FUN_1005f5f0`) do the SID handshake (`0x7f5/0x849/0x874`) over a 0x2000
  buffer; no inline key computation visible there.

**To actually pin the formula, the remaining options are heavier:**
1. **Assembly-level RE** — re-decompile the enc/dec + their callers in a live Ghidra session
   with manual `__thiscall`/ECX typing (or read the raw x86) to recover the key-holder ctor and
   its `SetKey` source. The pseudocode dump alone is insufficient.
2. **Stalker trace** of a single automated Connect, instrumented to catch the store that first
   writes the key bytes (heavy; now feasible since Connect is fully scriptable).
3. Non-disruptive **hardware debug-register watchpoint** — but the master address isn't known
   until after the one-time write, and it isn't re-derived on reconnect, so it can't be pre-armed
   without a fresh-process race.

**Verdict:** exact derivation is **not** recoverable from the current pseudocode corpus; it needs
assembly-level ECX tracing or Stalker. Practical deliverable (deterministic per-unit key,
extract-once, validated decrypt, full automation) stands complete.

**Memory-context check (non-disruptive):** dumped ±160 bytes around all 13 live key copies. The
surrounding structure is the per-channel transport object — wide-char channel labels
(`"USB [192.168.171.2]"`, `"log_7"`), vtable/ID pointers — with **no adjacent seed, key-schedule,
or device serial**. The key is computed elsewhere; only the 56-byte result is copied in. So the
seed is not recoverable by reading around the key either. Confirms: pinning the formula needs
assembly-level ECX tracing (offline r2/Ghidra on `bvtx_vci_rt.dll`) or a Stalker trace of an
automated Connect — both substantial. Stopping the derivation hunt here.

### 4.16 Assembly-level trace (2026-08-26) — key located in object graph; compute still deeper

Offline r2 disassembly of `bvtx_vci_rt.dll` (no rig). Two solid results:

1. **Key is never on the wire → local client computation, not device-exchange.** The bytes
   `fde7ccb2…` appear in **none** of the captures (incl. the full 900x handshake), and decrypting
   the connect handshake with the static M_VCI key yields no session key. So the key is computed
   locally from a stable input (same value across all four Manager PIDs observed).

2. **Exact object-graph location of the key** (from `pdf` of the decrypt caller `FUN_100b2d30`):
   the enc/dec key-holder `this` (ECX) is loaded as `*(*(handler + 0x8c) + 8)` — i.e.
   `handler.+0x8c → cryptoCtx`, `cryptoCtx.+8 → keyholder`, `keyholder[0:0x38]` = the Blowfish
   key. The key-holder is owned by the **message-handler/dispatch** object, not the transport.

Ruled out as the key-setter (all zero-init their members): the connect handler `FUN_1005f5f0`,
the CClientTransport ctor `FUN_1025cce0`, the CTransport ctor `FUN_1025cd30`, and
`TrnClt::ConnectToServer` `FUN_1025cf40` (pure sockets). The `+0x8c` writes elsewhere are
`std::string` SSO fields (`=0xf`), unrelated.

**Precise remaining target:** who allocates the handler's `cryptoCtx` (sets `handler+0x8c`) and
writes the 56-byte key into `cryptoCtx+8`'s key-holder — this lives in the handler-registration /
connection-security setup path (the SID `0x7f5/0x849/0x874` handshake response area), a further
subsystem. Fully pinning the inline formula is a multi-subsystem RE effort; it is now localized to
the message-handler crypto-context init, with the exact field offsets known.

**Net:** derivation confirmed **local + deterministic**, key precisely located in the object
graph; the exact compute remains buried in the handler crypto-setup path. Practical deliverable
(extract-once key, validated decrypt, full automation) complete and unchanged.

### 4.17 Allocator-hook + HW watchpoint (2026-08-26) — keyholder is a 0x38 alloc; watchpoint crashes the live Manager

Pursued the definitive dynamic technique. One solid finding, one hard blocker:

- **Finding:** correlating the RT allocator `FUN_102320c3` (RVA `0x2320c3`) with `BF_set_key`
  shows the key-holder is a **dedicated `0x38` (56-byte) allocation**, key at offset 0. (The
  persistent masters predate any probe; freshly-allocated channel key-holders correlate cleanly:
  `base==keyholder, size=0x38, off=0`.)
- **Blocker:** Frida hardware watchpoints exist on this 32-bit target via the per-thread method
  `thread.setHardwareWatchpoint(id, addr, 4, 'w')` (+ `Process.setExceptionHandler`), but the
  harness (watchpoint the 4 rotating `0x38` allocs, catch the key-prefix write) **crashes the live
  Manager** — same class of disruption as the guard-page `MemoryAccessMonitor` (§4.13). Root cause:
  the `#DB` single-step storms + an exception handler that returns `true` for all exceptions
  (swallowing the app's own). Reliable per-hit identification needs `DR6`, which Frida doesn't
  cleanly expose here, so returning `false` for non-ours isn't feasible without more work.

**Net:** dynamic low-level instrumentation (guard-page or HW-watchpoint) is **not viable on the
live rig without crashing the Manager**. The derivation is now maximally localized statically —
a `0x38` key-holder from `FUN_102320c3`, key at offset 0, filled on the connect path within the
message-handler crypto context (`handler+0x8c → cryptoCtx+8 → keyholder`) — but the exact write
instruction can't be captured by the available non-destabilizing means.

**Safest remaining path to the instruction:** attach a real user-mode debugger (x64dbg/WinDbg)
and, after one connect, set a **conditional HW data breakpoint** on a known channel key-holder,
then Disconnect→Connect to catch the copy, and walk back to the master's compute; or take the DLL
into a controlled Ghidra/emulation harness (not the production Manager) for the handler
crypto-context init. Both are separate, deliberate efforts. Practical deliverable unchanged.

### 4.18 DERIVATION SOLVED (2026-08-26) — key = static base + per-device addend

Cracked via offline r2 (found the function) + one non-disruptive read-hook (confirmed live).
**Supersedes §4.12–4.17's "not recoverable" conclusions.**

The 900x channels are `common_service::generic_client<PORT, boost::mpl::map<json_format::
base_request…,base_response…>>` templates (JSON messages under the Blowfish layer; e.g. port
9001 = `speaker` service). Each generic_client's 56-byte key-holder is initialized by
**`FUN_10268960`** (RVA `0x268960`), whose x86 body is exactly:

    memmove(keyholder, base_key_table[module_type] + 0xC4, 0x38)   // static 56-byte base key
    for (i=0; i<14; i++) keyholder.dword[i] += addend              // add dword[ebp+0xc], per dword

so **`session_key[i] = base_key[module_type][i] + addend`** (per 32-bit word, mod 2³²).

**Live-confirmed values (hook on `FUN_10268960`):**
- `module_type = 0x1c` = **`MODULE_TYPE_ID_MDI_2`** (entry 27 of table `DAT_10309d60`, stride
  `0x104`, key at `+0xC4`; table is static, live == on-disk).
- `base_key[MDI_2]` = `42197fad58f363fe07cc137065da2a5604a89114b2fd3b2f57d1bbb516cb75461f08260d1ac2465e584013641aba6176025816164629b007`
- `addend = 0x054dcebb`
- `base_key + 0x054dcebb == fde7ccb2…` → **VERIFIED True** (full 56 bytes).

**Addend is per-device (not a literal — 0 occurrences in the binary; computed at connect).** It
is strikingly close to the device serial: **serial `88985275` = `0x054DD0BB`; addend `0x054DCEBB`
= serial − 512 (0x200)**. So the key is **per-device, derivable from the serial** (which a macOS
client can read from the device ident/logs) — pending confirmation of the exact serial→addend
transform (traced to `FUN_10268960 ← FUN_1006d3d0(generic_client ctor) ← FUN_1007b0b0`; the
addend flows in as `param_5`).

**macOS impact — key is now COMPUTABLE, no Windows/extraction needed:** embed the static
`base_key[MDI_2]`, compute `addend` from the unit's serial, add per-dword → the exact Blowfish
key. Confirming the serial→addend formula (one more trace, or a second unit) closes it fully;
`addend = serial − 0x200` is the working hypothesis.

### 4.19 FINAL — the addend IS the device serial (correction to §4.18's "−512")

Verified programmatically: **`0x054dcebb` = `88985275` decimal = the device serial exactly**
(§4.18's "serial − 512" was an arithmetic error — `0x054DD0BB ≠ 88985275`; `0x054DCEBB = 88985275`).

**Complete, byte-verified derivation formula:**

    blowfish_key[i] = base_key[module_type][i] + device_serial      // i = 0..13, 32-bit add mod 2^32

- `module_type` = `0x1c` = `MODULE_TYPE_ID_MDI_2` → base key `42197fad58f363fe07cc137065da2a56
  04a89114b2fd3b2f57d1bbb516cb75461f08260d1ac2465e584013641aba6176025816164629b007` (static, in
  `bvtx_vci_rt.dll` table `DAT_10309d60`, entry id 0x1c, `+0xC4`).
- `device_serial` = the unit's serial as a `uint32` (this unit `88985275`; `uiSerialNumber` /
  `VtxRtSglReadSerialNumber` / `VTX_RT_CFG_SERIAL_NUMBER`).
- Result for this unit: `fde7ccb213c2b103…01f8fd0c` — recomputed == captured, exact.

**This fully closes the macOS story.** The Blowfish key is **computable with no Windows and no
per-session extraction**: a native client reads the device serial (present in the `225.1.1.1:8194`
announce / ident / the pulled logs as `2505-88985275`), takes the static per-module base key,
adds the serial to each 32-bit word → the exact key. Per-device, deterministic, reproducible.
Nothing remains blocked on the crypto/key side for a standalone macOS MDI Manager.

### 4.20 900x application protocol DECODED — JSON messages + SID-tagged log container (2026-08-26)

Decrypting the 9052 client→server requests with the derived key reveals the application layer
(this is the `json_format::base_request/response` of the `generic_client<PORT,...>` templates):

**JSON session protocol** (one line per message, under the Blowfish frame):
```
{"data":{"date":"<DDMMYYHHMMSS+frac>","dialer":"<host ip>","interface":2,"keep_alive":false,
         "listener":"<device ip>","master":true,"name":"<user>"},"has_data":true,"id":1,"target":"session"}
{"has_data":false,"id":4,"target":"session"}        # poll
{"has_data":false,"id":9,"target":"session"}        # poll
```
Then a **binary get-logs trigger** on 9052: `a7 08 00 00 01 00 00 00 00 00 00 00 00 00 00 0c`
(→ the device streams the log container as the response).

**Decrypted log body = SID-tagged records** (SID = LE u32; confirms the prior doc's SID `0x8a9`):
```
0x8a9 meta : [sid][_r][id][kind][namelen][name]                     e.g. name="messages"
0x8a8 data : [sid][_r][id][namelen][name][datalen][data]            datalen 0xe869=59497 = Varlog
```
So a full pull = session_open → poll → get-logs → parse records; `name` selects the category
(`messages`=Varlog, etc.). Field semantics of `kind`/`_r` and the complete SID set still need more
samples, but the log path is fully reproduced.

**Working Python client:** `GM_research/mdi2_macos/client/` (package `mdi2`) — discovery, key
derivation (`base+serial`), Blowfish-ECB, `construct`-based framing + container, JSON messages,
active `pull_logs`. Verified end-to-end offline: pcap → decrypt → extract `messages` (59497 B,
byte-exact) with a stock venv (`pycryptodome` + `construct`). CLI: `python -m mdi2.cli {scan,key,connect}`.

### 4.21 Live macOS bring-up (2026-08-26) — client validated; device-activation gap found

MDI2 moved to the Mac via USB (RNDIS gadget = **en17**, MAC 70:c6:ac:00:05:39). The MDI DHCP-serves
the host **192.168.171.30** (same as Windows) but macOS assigned a **/32** — set `en17` to
`192.168.171.30/24` (`sudo ifconfig en17 inet 192.168.171.30 netmask 255.255.255.0`) so the device
subnet is on-link (a full-tunnel VPN on `utun6` had otherwise stolen the route).

**Working live from macOS:** ping .2 (~1 ms); ports 21/80/9000/9002/9004/9005/9001/9052 open;
**discovery beacon** received on `225.1.1.1:8194` — 41 bytes, decodes to `[len][0x86d][serial
uint32][…][module_type 0x1c=MDI_2][…]`, so the client **auto-derives the key from the beacon**.
All 14 channels TCP-connect; key derivation, Blowfish, framing, control-frame format, JSON
messages, and container parsing are all validated against captures.

**Blocker — 900x services are dormant on the Mac.** The device ACKs the control frame + session_open
but sends **no data on any channel**; the identical bytes got a 1 ms reply on the Surface. So the
device needs a **device-level activation** that the Bosch Windows stack performs (USB
driver control step and/or an ident handshake) and the generic macOS RNDIS gadget does not. The
900x app protocol is fully reproduced; only *arming* the device from a cold, non-Bosch host remains.

**Next:** capture a **cold first-connect** on the Surface (device power-cycled, then Bosch Manager's
very first connect) incl. USB-control + ident traffic, to find the activation step; or inspect the
Bosch USB driver's enumeration/control sequence. Client code: `GM_research/mdi2_macos/client/`.

### 4.22 LIVE macOS client WORKS (2026-08-26) — device dormancy was connection-pool exhaustion

The earlier "dormant device" (§4.21) was **not** a missing Bosch activation — it was the device's
**connection-pool exhausted** by repeated test connects. After a USB power-cycle the device
responds immediately from macOS. Two more findings closed the live path:

1. **Per-channel control handshake:** each 900x channel must first exchange the 8-byte control
   frame `00 53 50 00 00 <code> 00 00` (client `0x30`, device `0x31`; port 9011 uses `0x21`/`0x20`)
   before any app message.
2. **App-body framing (inside the Blowfish body):** `content + zero-pad + u32be(len)`, padded to
   a multiple of 8 (the trailing u32be is the content length; responses use it too). My earlier
   zero-padding without the length suffix caused the device's `error 0x50000006` rejection.

With both fixed, a **client-constructed `session_open` is byte-identical to the real one** and the
**live device returns full success**: `{"data":{"port":9011,"session":<id>},"error":0,"has_data":
true,"id":1}` — confirmed on the real MDI2 over macOS USB. Discovery works too: the
`225.1.1.1:8194` beacon carries the serial (`0x054dcebb`=88985275) and module type `0x1c`, so the
client auto-derives the key.

**Net: the macOS client is validated end-to-end live** — discover → derive key → control
handshake → session_open (accepted) — with all layers (Blowfish, framing, app-body length suffix,
JSON, container) byte-exact against both captures and the live device. Operational caveat: the
device holds **one session** and a pool of a few connections; leftover sessions/leaked connections
from rapid testing make it respond inconsistently until a USB power-cycle. A production client
should open only the channels it needs (9052 for logs) and close cleanly.

**Interface note (macOS):** MDI DHCP-serves host `192.168.171.30`, but macOS assigns a `/32` and a
full-tunnel VPN can steal the route — set `en17` to `/24`: `sudo ifconfig en17 inet 192.168.171.30
netmask 255.255.255.0` (redo after each re-plug).

### 4.23 CORRECTION to §4.22 — device DOES need Bosch activation (arming), not just a clean pool

Further power-cycles resolve the ambiguity: a truly cold device (never armed by a Bosch Manager
this power cycle) accepts TCP on the 900x ports but **does not answer the control frame** — its
900x services are **dormant/unarmed**. The one time the client fully succeeded (§4.22), the device
was still **armed from its immediately-prior Surface Manager session** (residual state), not cold.

So both are true: (a) the macOS client protocol is complete and **proven** (byte-exact
session_open → full `{"port","session","error":0}` success against the live device when armed);
(b) but **arming the device requires the Bosch Windows stack's activation** (USB driver control
step and/or ident handshake), which the generic macOS RNDIS gadget does not perform. Cold Mac-only
bring-up is therefore not yet possible — the client works only against an already-armed device.

**The remaining blocker is the activation/arming handshake** (was §4.21, mis-attributed to
exhaustion in §4.22). Next: capture a **cold arming** on the Surface — power-cycle the MDI, then
the Bosch Manager's first connect, with a **USB-level capture** (usbmon/Wireshark USBPcap) plus the
device-network trace — to find the control transfer or ident exchange that arms the 900x services,
then replicate it on macOS (libusb/IOKit, or a network handshake). Everything above the arming
step is done and validated.

### 4.24 Cold-arming capture RESOLVES it — NO special activation; macOS RNDIS is sufficient

Captured the full cold sequence on the Surface (USBPcap both buses + device-network dumpcap):
device power-cycled off, plugged in, Windows mounts it, Bosch Manager first-connect → "Connected".
Artifacts: `GM_research/mdi2_macos/captures/cold_arming/{usb2.pcap,net.pcap}`. Findings:

- **USB enumeration is standard** (dev VID `0x0ca0` PID `0x1301`, RNDIS: class 02/subclass 02/proto
  ff). The only control transfers are GET_DESCRIPTOR ×3 + SET_CONFIGURATION — **no vendor control
  requests**.
- **RNDIS init is standard**: `INITIALIZE`, then `SET OID_GEN_CURRENT_PACKET_FILTER` and
  `SET 802_3_MULTICAST_LIST` — exactly what every RNDIS host (incl. the generic macOS driver) does.
  **No vendor OID, no `OID_GEN_RNDIS_CONFIG_PARAMETER`, no arming message.**
- **No pre-900x device-facing network step:** before the 900x connect (29.6 s) the only device
  traffic is its own `225.1.1.1:8194` beacon; the 17 KB `127.0.0.1:8125` exchange is pure
  Manager↔ident **loopback**. The device gets **zero** host→device packets until the 900x TCP
  connect.
- The successful cold 900x connect uses the **identical** bytes my macOS client sends (control
  frame `00 53 50 00 00 30 00 00` → device `…31…` in ~1 ms, then the byte-exact session_open).

**Conclusion: the device requires NO Bosch-specific activation.** macOS's generic RNDIS gadget is
sufficient; the macOS client works cold (proven by the earlier full session_open success). The
intermittent "dormancy" on the Mac was **connection-pool/session exhaustion from rapid repeated
test connects** (the device holds one session + a few connections) plus device boot timing — NOT a
missing arming step. **This confirms §4.22 and supersedes §4.23/§4.21's "activation gap".**

**Practical rule for the macOS client:** power-cycle the MDI for a clean state, connect once, open
only the channels needed (9052 for logs), and **close cleanly**; don't hammer it. Under those
conditions the full loop (discover → derive key → control handshake → session_open → get-logs →
decrypt) works from macOS, USB-only, no Windows.

### 4.25 FULL LIVE LOG PULL FROM macOS — SUCCESS (2026-08-26)

The complete loop runs end-to-end against the real MDI2 over macOS USB, **no Windows**:

    discover (beacon serial) -> derive key -> per-channel control handshake ->
    session_open (device: {"port":9011,"session":<id>,"error":0}) -> poll -> get-logs ->
    Blowfish-ECB decrypt -> SID container -> "messages" = 56811 bytes of live Varlog
    ("Aug 26 00:31:46 2505-88985275 syslog-ng... Booting Linux... 4.14.162-gvci").

**The last bug — the message counter must have its HIGH BIT set.** The `[u32be 0][u32be len]
[u32 counter][body]` counter is not a plain 1..N sequence: values with bit31 clear (`1`,
`0x10000001`) make the device **choke and abort** the response after `{"data":`; values with
bit31 set (`0xc583adc1`, `0x8aa81d35`, `0xcc666310` — all captured) are processed normally. Fixed
in the client: `Channel.counter` starts at `random.getrandbits(31) | 0x80000000` and increments
mod 2^32. With that, a client-**constructed** session_open (byte-exact body) is accepted and the
full pull succeeds.

**Session semantics:** the device holds **one session**, and the first session_open on a fresh
session must be the first app message. It is released on a **clean disconnect** (the Manager sends
a session-close; the client currently just closes TCP, so a session dangles until timeout/
power-cycle — sending the close is the one remaining polish item for back-to-back pulls).

**Status: the macOS MDI2 client is done and live-validated** — discovery, key derivation
(base+serial), Blowfish-ECB, framing, control handshake, JSON session, get-logs, and container
decode, pulling real device logs from macOS with no Windows in the loop. Client:
`mdi2_client/` (repo) / `GM_research/mdi2_macos/client/` (with venv).
