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
