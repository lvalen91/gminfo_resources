# MDI2 Manager — Identification Service, WiFi Pairing, and Device Log-Pull Protocol

**Scope:** the Windows "MDI2 Manager" / "GM MDI Identification Service" stack — `GM_MDI_Ident.exe`,
the 14-port device-facing transport (900x bank), and the *Get Log Files* pull protocol — as distinct
from DPS/SPS diagnostic sessions over the 10123 D-PDU tunnel (owned by
`MDI2_DPDU_API_PROTOCOL_AUG2026.md`, abbreviated MDP below). **Does not cover:** the raw UDS bypass
chain (`MDI2_RAW_UDS_BYPASS_GUIDE.md`, carried unchanged — cite by name only), the Aug-24 pcap
provenance record (`AUG24_SESSION_FULL_PCAP_TIMELINE.md`), or seed/key/SecurityAccess crypto beyond
this stack's own Blowfish layer (`GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md`).

**Evidence tags:** `[C]` confirmed live on hardware, `[FW]`/`[S]` static disassembly, `[inferred]`
reasoned but untested, `[U]` unverified/open. Dated per-claim notes override surrounding prose.

**Related:** `MDI2_DPDU_API_PROTOCOL_AUG2026.md` (D-PDU/10123 path, §2 correction below applies
there too), `AUG24_SESSION_FULL_PCAP_TIMELINE.md` (capture provenance), `mdi2_client/` (this repo —
the native macOS implementation this doc documents), `gm_dps/docs/GM_MDI_IDENT_EVIDENCE_protocol.txt`
and `mdi2_client/docs/PROTOCOL.md` (operator-facing duplicates of §0/§4 below).

---

## 0. Current state — authoritative summary

**Status: SOLVED, live-validated end to end `[C]`.** A native macOS MDI2 client
(`mdi2_client/`, pkg `mdi2`, deps pycryptodome + construct) pulls device logs over USB with no
Windows, repeatably. Final facts, each reconstructed from the investigation trail in §1-§4 and the
condensed appendix (§5) — read those sections only for the RE evidence behind a given line, not for
a live-current claim:

- **Transport:** each Connect opens a 14-TCP bank to device ports
  `9001/9003/9006-9014/9050-9052` (the Manager's own channel — **not** the 10123 D-PDU diagnostic
  path, **not** FTP/21). Log pull runs on **9052**. §4.1.
- **Wire frame (big-endian):** `[u32 0][u32 len][u32 counter][Blowfish-ECB body]`; the counter is
  cleartext and must have **bit31 set** (§4.10). Each channel is preceded by an 8-byte control frame
  `00 53 50 00 00 <code> 00 00` (client sends `0x30`; device replies `0x31`; port 9011 uses
  `0x21`/`0x20` instead). **Handshake direction (confirmed live 2026-11-14):** on 9001/9050/9051 and
  9011 the *device* sends its control frame first on connect; **9052 is silent on connect** and
  replies only after the client sends its own `0x30` frame first. §4.2.
- **Cipher: standard Blowfish-ECB**, big-endian, 8-byte blocks, pycryptodome-compatible — confirmed
  by construction (π-seeded P-array, standard S-box table, standard `BF_set_key`/`BF_encrypt`
  entry points), not by inference. §4.7.
- **Key (computable, no extraction needed):**
  `key[i] = base_key[MODULE_TYPE_ID_MDI_2][i] + device_serial` (14 dwords, 32-bit add mod 2³²,
  per-device, deterministic). `base_key` is a static constant in `bvtx_vci_rt.dll` table
  `DAT_10309d60` (entry id `0x1c`, +0xC4); `device_serial` is the `uint32` read from the
  `225.1.1.1:8194` discovery beacon (LE u32 at payload offset 9) or from the pulled logs. Formula in
  `FUN_10268960` (RVA `0x268960`). §4.8.
- **App layer = JSON** (`common_service::generic_client<PORT>`): `session_open`, `poll`, a binary
  get-logs trigger; body framing inside the Blowfish payload is `content + zero-pad + u32be(len)`
  (padded to a multiple of 8; the trailing u32be is the content length — zero-padding without
  this length suffix caused the device's `error 0x50000006` rejection, the diagnostic that led to
  finding the correct framing).
  The decrypted log body is a SID-tagged container (`0x8a9` meta / `0x8a8` data, e.g.
  `name="messages"` → category Varlog). §4.9.
- **Session:** the device holds exactly ONE session; release it with
  `{"data":<session_id>,"has_data":true,"id":2,"target":"session"}` or it dangles. A few dangled
  sessions exhaust the session table — after which 9052 stops answering and `session_open` returns
  no id. This is **session-table exhaustion, not a hardware wedge**; recovery is to stop connect
  loops and let the table drain (USB power-cycle is the last resort, not the first).
  *(History: originally documented 2026-08-26 as "→ USB power-cycle"; corrected 2026-11-14 once the
  drain behavior was observed.)* §4.10.
- **No device-side activation/arming step exists.** A cold-boot USB+network capture on the real
  Bosch Manager (§5, "cold-arming") proved macOS's generic RNDIS gadget is sufficient; the earlier
  "dormant device" readings were connection-pool/session exhaustion from rapid test connects, not a
  missing Bosch-specific control transfer.
- **Confirmed live end-to-end, 2026-11-14:** discovery → key derivation → 9052 handshake →
  `session_open` returns a session id → `pull_logs` returns the `messages` stream, byte-exact
  against the Manager's own saved plaintext. Bench: MDI2 on a direct USB RNDIS link reaching radio
  ECU 0x80 over the D-PDU CAN tunnel, **not** connected to a vehicle OBD2 port. The RNDIS link
  enumerates as `en17` with a `/32` mask that must be reset to `/24` after every USB replug;
  discovery keys off the subnet, not the interface name.

**Date:** investigation ran 2026-08-25/26, corrected inline 2026-11-12 and 2026-11-14 (folded above,
not left as separate strikethrough/banner pairs). Source material: full Ghidra disassembly
(`gm_dps/disassembly/pseudocode_mdi2mgr/`), prior binary analysis at
`gm_dps/docs/GM_MDI_IDENT_EVIDENCE_protocol.txt`, and live testing against real MDI2 hardware
(bench-local `192.168.171.2`) on a Win11 Surface Pro host (`192.168.171.30`) running the real Bosch
VCI Manager 9.1.2752.177. A separate, concurrent session installed the actual MDI2 Manager under
Wine; that installation work is not duplicated here.

---

## 1. `GM_MDI_Ident.exe` — the Identification Service

Two instances of one binary run concurrently:
- `8098` — "GM MDI Software\GM MDI Identification Service" instance
- `8125` — "Bosch\VTX-VCI\VCI Software (GM)\VCI Identification Service" instance

**Bind address (corrected in place 2026-08-25, same live-capture session as the original claim —
do not use the superseded reading below):** both instances bind **`0.0.0.0`**, confirmed via
`Get-NetTCPConnection -State Listen` on the running Surface (`LocalAddress 0.0.0.0`, ports
8098/8125) — they are reachable from the host's other subnets, though the Manager itself still
dials them via `127.0.0.1`. *(History: first read as "127.0.0.1 only, confirmed unreachable from
the device side and from macOS by direct live probe"; that reading does not hold — same-session
`Get-NetTCPConnection` capture showed `0.0.0.0`. Superseded reading not carried forward.)*

No TLS — plain custom binary protocol over raw `WS2_32` sockets (also a named pipe,
`\\.\pipe\VTX_Identification_Service`). Wire framing: length-prefixed segments
(`[u32 LE total_len][u32 LE opcode/SID][payload]`), dispatched in
`CClientConnectionMgr::OnDataReceived` via a long SID compare-chain. Confirmed SIDs `[FW]`:

| SID (hex/dec) | Name | Direction |
|---|---|---|
| 0x7f2 / 2034 | SID_IDENT_CONNECT_SEND | client→ident |
| 0x8a9 / 2217 | (unnamed in evidence doc; response vtable `CLogFiles_Recv`) | client→ident, log-pull trigger — see §2/§5 |
| 0x8b9-0x8bc | WIFI_CONNECT/DISCONNECT/REQ | — |
| 0x8bf / 0x8c0 | SID_WIFI_ENABLE_SEND / WifiEnable_Recv | — |
| 0x8c1-0x8c4 | WIFI_ADAPTER_INFO / WIFI_ADAPTER_IF_INFO / WifiList | — |
| 0x8d1 / 0x8d2 | SID_WIFI_CREDENTIALS_SEND / WifiCredentials_Recv | client→ident (§2) |
| 0x902 / 2306 | SID_USB_GET_STATUS_SEND | — |

Everything outside the IDENT/WIFI/USB block is relayed to "the VCI/protocol_stack" rather than
handled locally — the ident service is a thin local multiplexer in front of the real device-facing
protocol stack (`bvtx_vci_rt*.dll`).

## 2. Correction propagated to MDP: 0x8d1/0x8d2 is VCI WiFi AP pairing, not a 10123 credential

This section **supersedes** an earlier finding in `MDI2_DPDU_API_PROTOCOL_AUG2026.md` §12 (that
doc has been corrected to point here; this is the owning account — do not restate it there).

Traced end-to-end `[FW]`: `GM_MDI_Ident.exe`'s `CClientConnectionMgr::OnDataReceived` 0x8d1 branch
logs `"SID_WIFI_CREDENTIALS_SEND"`, deserializes a `CWifiCredentials_Send` object, and routes to
`CIdentWifi::SetWifiCredentials` (log format `"%s ssid = %s serial_number = %s ... version = %s"`),
which builds a Windows WLAN profile (`CreateProfile`, auth `"AES-CCMP"`). The sender,
`bvtx_vci_rt_j.dll`'s `CDeviceMgr::SetConfigItems`, pulls the SSID/passphrase pair from config
items literally named `"SSID"`/`"Passphrase"` (config IDs `0x12`/`0x13`, via
`VtxRtGetConfigItems`/`SetConfigItems`, opcodes `0x7e3`/`0x7e4`), format-validated only
(`ifm::ValidateWifiConfig`), never generated or looked up from any registry/DPAPI/backend store.

**This is the VCI's own WiFi access-point passphrase, unrelated to TCP/10123 authorization.** The
real capture that originally motivated the 10123-credential theory used the same Ethernet-gadget
transport replayed from macOS (`capinfos` → `"Ethernet 2"` on Windows), not WiFi, ruling out a
WiFi-vs-USB transport mismatch as the explanation too. **Net effect, still open `[U]`: the actual
port-10123 gate remains unexplained** — this is tracked in MDP, not resolved here.

## 3. The FTPS log path — a real but separate route, not the *Get Log Files* button

**This whole section documents a path that is superseded for the general Dmesg/Varlog/VCIHistory
pull** (the live capture in §4 is the authoritative account of that button) **but remains valid for
a different route** — the AAOS/Android head-unit reprogramming-log flow (`DevMgr::RunAndroidDevice
Update`/`DevMgr::end_reprogramming`), which really does use it.

Motivation for the original theory: three real pulled log files existed on disk with no
corresponding network capture (the pull happened before any of six known Aug-24 pcaps start, and a
content search for distinctive strings was a confirmed zero-hit across all six).

**FTP facts (live-confirmed, independent of the port-10123 problem) `[C]`:** the device runs a real
FTP server on port 21 (`220 Global VCI FTP Server`, vsftpd 3.0.3, `UNIX Type: L8`). Credentials are
hardcoded in `bvtx_vci_rt_j.dll`: **`firmware`/`vtx`**, via libcurl `CURLOPT_USERPWD`. Plain FTP
login is refused (`530 Non-anonymous sessions must use encryption`); explicit FTPS (`AUTH TLS`)
login with `firmware:vtx` succeeds. Real client options (`FUN_100cdcb0`): `CURLOPT_USE_SSL=3`
(`CURLUSESSL_ALL`), `CURLOPT_FTPSSLAUTH=1` (sends `AUTH SSL`, not `AUTH TLS` — untested whether the
server cares), `SSL_VERIFYPEER=0`/`SSL_VERIFYHOST=0` (self-signed, unvalidated),
`CURLOPT_INTERFACE` bound to the caller's own source IP, and 4 retries with a 500 ms backoff on
connect failure.

**The path is a magic streaming token, not a real filename.** The URL is built as
`"ftp://firmware@" + host + "/" + path` with no directory prefix; `path` is never one of the four
real log names — it's a magic token: `RETR any-file` pulls the next staged log in a queue (a curl
code-78 `"any-file"` 404 is treated as benign end-of-stream), and `RETR end-file` finalizes the
pull. The four real names (`messages`→Varlog, `messages.driver`→Dmesg, `vci-history.xml`→
VCIHistory, `VTX_RT_Server.log`→Runtime) are matched by a separate classifier
(`FUN_10079e40`) against a name the server supplies inline during the `any-file` stream, purely to
pick the local output filename — never sent as RETR targets. This is why guessing literal filenames
always failed with `550 Failed to open file`.

**Staging trigger — found but never fully resolved `[U]`:** `FUN_10083fb0` gates the flow and sends
SID `0x8a9` (`CLogFiles_Recv`) before any FTP activity — almost certainly what populates the FTP
staging directory. `STAT /` against the FTP root showed the staging directory itself (`drwxrwxr-x`,
only `.`/`..`, mtime "Aug 24 12:28"); `RETR any-file` also returns `550 Failed to open file` cold,
with no preceding trigger. Two problems were never closed: (1) SID `0x8a9`'s handler was never located in
the disassembled scope (an apparent match was a false-positive OpenSSL constant); (2) `0x8a9` is
sent to the Windows-loopback ident service, unreachable from macOS/the device network, so even the
exact trigger bytes have no live target without the real `GM_MDI_Ident.exe` running. Whether
`any-file`/`end-file` is the general pull path or Android-update-specific was also never confirmed
either way — this entire question became moot once §4 found the real *Get Log Files* path runs over
9052, not FTP.

---

## 4. The real Manager transport — LIVE CAPTURE 2026-08-25, authoritative for *Get Log Files*

First successful end-to-end network capture of the real Bosch VCI Manager 9.1.2752.177
(`GM_MDI_Manager.exe`, not Wine) driving a live MDI2. Bench: Win11 Surface Pro (host
`192.168.171.30`) cabled USB to a Bosch VCI MDI2 (device `192.168.171.2`, MAC
`70-C6-AC-00-05-38`). Device internals from the pulled plaintext: Linux 4.14.162-gvci, ARMv7,
"Bosch LP518 Board". Capture driven remotely over SSH: `dumpcap` launched detached via WMI
`Win32_Process.Create` (a plain SSH-child dumpcap dies with the SSH session; the scheduled-task
route failed on account-SID mapping).

**Artifact paths (primary, non-dead-end evidence):**
`GM_research/mdi2_macos/captures/mdi_session_full_with_handshake.pcapng` + `markers.log` (uses an
in-band ICMP-echo-size-1337 marker technique to correlate capture timestamps), decrypted plaintext
at `captures/plaintext_logs/`, the decrypt tool `mdi2_9052_decrypt.py`, and the cold-arming capture
files `captures/cold_arming/{usb2.pcap,net.pcap}` (§5).

### 4.1 Transport: a 14-socket bank on device ports 900x

On every UI Connect, `GM_MDI_Manager.exe` (the runtime DLL is in-process, confirmed via
`Get-NetTCPConnection … OwningProcess`) opens a fresh bank of 14 parallel TCP connections:

    9001  9003  9006  9007  9008  9009  9010  9011  9012  9013  9014  9050  9051  9052

A subsequent Connect opens a new bank; the previous bank goes to `TimeWait`. **`10123`** (the DPS
D-PDU tunnel, MDP) and **`13400`** (DoIP) are **closed** during a Manager session — diagnostic-session
ports, unrelated to the Manager. Ports 21 (FTP) and 80 (HTTP) stay open on the device, but the
Manager's log button does not use them.

### 4.2 Wire framing and per-message counter

All 900x channels share one framing, **big-endian** (opposite the 10123 D-PDU path's LE):

    [u32 BE 0x00000000]              # always zero
    [u32 BE payload_len]             # bytes following the 8-byte header
    [payload]

`payload = [4-byte incrementing per-message counter][encrypted body]`. Counters step by 1 per
message per channel (observed e.g. `f8b7c055 → 56 → 57`); the response echoes the request's
counter. Each connection also carries an 8-byte plaintext control frame right after connect:
`00 53 50 00 00 30 00 00` (variant `...21 00 00` on port 9011) — the low byte (`0x30`/`0x21`)
encodes a per-port service/type; §0's handshake-direction note (device sends first on
9001/9011/9050/9051, client sends first on 9052) applies to this frame.

The encrypted body shows repeating 16-byte ciphertext blocks across repeated identical pulls — a
block cipher in ECB mode, 16-byte block granularity (**ciphertext shape only**; §4.7 identifies the
actual algorithm). *(History: an early pass over this same evidence guessed "AES-ECB, 16-byte
block" from the 16-byte ciphertext repeat alone; §4.7's construction-level trace of
`bvtx_vci_rt_j.dll` found the real primitive is Blowfish-ECB with an 8-byte block — the 16-byte
repeat is just two concatenated Blowfish blocks, not an AES block. The AES guess never held and is
not carried forward as a live claim.)*

### 4.3 *Get Log Files* button → port 9052, encrypted stream

Click → 28-byte request on 9052:

    00000000 00000014            # hdr, payload_len = 0x14 (20)
    8aa81d35                     # 4-byte counter (increments per click)
    1c2faed2 8c01416a a6c46ff4 f64834b0   # 16-byte session token, constant within a session

Server replies with the log payload as a stream of 1460-byte (MSS) segments, Blowfish-ECB
encrypted, ~81 KB per pull. The 16-byte token is constant across pulls in one session and changes
across sessions — it functioned as the de facto session/auth handle during this investigation
(before the JSON `session_open` layer in §4.9 was decoded). The Manager writes the decrypted result
to `C:\ProgramData\Bosch\VTX-VCI\VCI Software (GM)\Logs\Categories\` as
`GM {Dmesg,Varlog,VCIHistory} <ISO-ts>-D<serial>.txt` — this captured ciphertext↔plaintext pair is
the known-plaintext oracle the rest of the derivation (§4.7-§4.8, §5) was validated against.

### 4.4 UI-button → function map

- **Get Log Files** button handler = `FUN_00437700` in `gm_mdi_manager.exe` (branches on the
  worker's return: `0` → "Log Files retrieved", nonzero → "Failed"; save path from registry value
  `LogFileLocation`).
- Worker = `FUN_0044f0a0` → `FUN_00460da0()` then a virtual call through the in-process runtime
  session object `DAT_004c5554`. The exe is a thin MFC shell; the 9052 socket, framing, counter,
  token, and decryption all live in the runtime DLL (`bvtx_vci_rt*.dll`/`bvtx4j32.dll`).

### 4.5 UI Connect/Disconnect is loopback IPC only

A deliberate Disconnect → Connect cycle produced **no** device-facing TCP for the logical toggle —
only loopback IPC to the ident service `127.0.0.1:8125` (Manager→ident: 106-byte request/16-byte
ack; ident→Manager: ~16.6 KB device-identification/config blob). The device's 900x bank is managed
separately (it re-banks on Connect, §4.1) — this is why the UI never visibly "disconnects" the
device link; the multicast beacon (§4.6) is independent of the UI's logical connect state.

### 4.6 Device discovery beacon

The MDI2 continuously multicasts `192.168.171.2:42178 → 225.1.1.1:8194`, ~1/s. *(History: original
reading called this a 106-byte payload; corrected 2026-11-12: 106 is the **UDP length field**
including the 8-byte header, so the real payload is 98 bytes — first u32 `0x62`, then `0x86d`,
serial as LE u32 at payload offset 9. A shorter 41-byte-payload/49-byte-UDP-length variant also
appears in the same captures — not a contradiction of the 98-byte reading, just a second observed
beacon size; `mdi2_client/mdi2/const.py`'s "observed 41-byte beacon" comment refers to that
variant. That 41-byte variant's payload carries `module_type 0x1c = MDI_2` inline, not just the
serial.)* A client can passively discover the device and confirm liveness by joining
`225.1.1.1:8194` — no handshake, no auth required. This beacon is the idle keepalive/"watchdog"
mechanism — there is no separate TCP-level watchdog.

### 4.7 Crypto of the 900x/9052 bodies — Blowfish-ECB, confirmed by construction

Traced from the *Get Log Files* vcall into `bvtx_vci_rt_j.dll` (image base `0x10000000`; regional
twins `bvtx_vci_rt.dll`/`_p` are byte-for-byte equivalent here). The transport class is `TrnPrt`
(log strings `TrnPrt::Run … Encrypting/Decrypt`, `TrnPrt::SendRecv_ArchiveBuffer`).

- Key schedule `FUN_101dce80` (= `BF_set_key`) seeds the P-array with the standard π-digit
  constants (`0x243f6a88 0x85a308d3 0x13198a2e …`) and copies the 1024-dword S-box table from
  `DAT_102fa138` — the **standard Blowfish** S-box (confirmed byte-for-byte), so any stock Blowfish
  implementation (pycryptodome, big-endian block convention) is byte-compatible.
- Block routine `FUN_101dc790` (= `BF_encrypt`); buffer enc/dec `FUN_101dd350`/`FUN_101dcfe0`.
- Encrypt `FUN_10268b90` pads the post-counter region to a multiple of 8; decrypt `FUN_10268a40`
  rejects non-multiples with `"Invalid message size, encrypted message must be multiple of 8"` →
  8-byte block (Blowfish/DES family; the S-box + π seed pin it to Blowfish, not DES, and rule out
  the earlier AES-ECB guess at §4.2).
- Key length passed to `BF_set_key` is `0x38` = 56 bytes — Blowfish's maximum (448-bit) key.
- The cipher wrapper is a named-dispatch layer (`FUN_101dd350`/`FUN_101dcfe0` string-compare their
  mode arg against `DAT_102f9c20 = "ecb"`, confirmed live), but the real block routine is textbook
  big-endian Blowfish — `Crypto.Cipher.Blowfish` (pycryptodome) `MODE_ECB` reproduces it exactly, no
  custom byte-order variant needed. (An early reading suspected a non-standard F-function byte-order
  table at `ctx[0x412..0x415]`; that table holds the standard `{3,2,1,0}` ordering — the apparent
  non-standard-ness was an artifact of testing against the wrong key, not the wrong algorithm; see
  §5.)

### 4.8 Key derivation — SOLVED: static per-module base key + device-serial addend

**Formula, byte-verified:**

    session_key[i] = base_key[module_type][i] + device_serial     // i = 0..13, 32-bit add mod 2^32

The 900x channels are `common_service::generic_client<PORT, boost::mpl::map<json_format::
base_request…,base_response…>>` templates. Each generic_client's 56-byte key-holder is initialized
by `FUN_10268960` (RVA `0x268960`), whose x86 body is exactly:

    memmove(keyholder, base_key_table[module_type] + 0xC4, 0x38)   // static 56-byte base key
    for (i=0; i<14; i++) keyholder.dword[i] += addend              // per 32-bit word

**Live-confirmed values** (hook on `FUN_10268960`): `module_type = 0x1c` =
`MODULE_TYPE_ID_MDI_2` (entry 27 of table `DAT_10309d60`, stride `0x104`, key at `+0xC4`; table is
static, live == on-disk); `base_key[MDI_2]` =
`42197fad58f363fe07cc137065da2a5604a89114b2fd3b2f57d1bbb516cb75461f08260d1ac2465e584013641aba6176025816164629b007`.
The addend is **not** a literal in the binary (0 occurrences); it is computed at connect and is the
device's serial number as a raw `uint32` — `blowfish_key[i] = base_key[module_type][i] +
device_serial`, confirmed by recomputing and matching the live-extracted session key exactly for
the test unit (full 56 bytes, 100% match). *(History: §5's derivation hunt first produced
`addend = serial − 0x200` from an off-by-one reading of the test unit's serial digits; recomputing
with the correct serial value showed the addend **is** the raw serial, no offset — the "−512"
reading was an arithmetic slip, not a second valid formula, and is not carried forward.)*

**Result:** the Blowfish key is computable with no Windows and no live extraction — a native
client reads the device serial (from the beacon, §4.6, or from ident/logs), takes the static
per-module base key, and adds the serial to each 32-bit word.

### 4.9 Application layer — JSON session protocol + SID-tagged log container

Decrypting the 9052 client→server requests with the derived key reveals the application layer
(`json_format::base_request/response` of `generic_client<PORT,...>`):

```
{"data":{"date":"<DDMMYYHHMMSS+frac>","dialer":"<host ip>","interface":2,"keep_alive":false,
         "listener":"<device ip>","master":true,"name":"<user>"},"has_data":true,"id":1,"target":"session"}
{"has_data":false,"id":4,"target":"session"}        # poll
{"has_data":false,"id":9,"target":"session"}        # poll
```

Then a binary get-logs trigger on 9052: `a7 08 00 00 01 00 00 00 00 00 00 00 00 00 00 0c` → the
device streams the log container as the response.

Decrypted log body = SID-tagged records (SID as LE u32; confirms §1/§3's SID `0x8a9`):

```
0x8a9 meta : [sid][_r][id][kind][namelen][name]                     e.g. name="messages"
0x8a8 data : [sid][_r][id][namelen][name][datalen][data]            datalen 0xe869=59497 = Varlog
```

Full pull sequence: `session_open` → `poll` → get-logs → parse records; `name` selects the category
(`messages`=Varlog, etc.). `kind`/`_r` field semantics and the complete SID set were never fully
enumerated (only enough samples to drive the client) — the log path itself is fully reproduced
regardless.

### 4.10 Session lifecycle and the robustness fixes that made repeated pulls work

Four facts closed the client's reliability, folded together here (originally found and corrected
across several passes — see §5 for the dead ends that preceded each):

1. **Counter must have bit31 set.** The `[u32be 0][u32be len][u32 counter][body]` counter is not a
   plain 1..N sequence — values with bit31 clear make the device abort the response after
   `{"data":`; values with bit31 set (`0xc583adc1`, `0x8aa81d35`, `0xcc666310`, all captured live)
   are processed normally. Fix: `Channel.counter` starts at `random.getrandbits(31) |
   0x80000000` and increments mod 2³².
2. **Session-close required.** The device holds exactly one session; send
   `{"data":<session_id>,"has_data":true,"id":2,"target":"session"}` after each pull or the
   session dangles (repeated dangles exhaust the session table — recoverable by draining, not a
   hardware fault; see §0).
3. **Patient recv.** `recv_frames` must accumulate until idle-after-data; a frame-by-frame reader
   misread replies and left sessions dangling.
4. **Control frame must be the full 8 bytes** `00 53 50 00 00 <code> 00 00` — a 7-byte version
   stole a byte from the next frame and misaligned `session_open`.

With all four fixed, a client-constructed `session_open` is byte-identical to the real one, and the
device returns full success: `{"data":{"port":9011,"session":<id>},"error":0,"has_data":true,
"id":1}`, confirmed on the real MDI2 over macOS USB. A full pull then runs:
`discover → derive key → control handshake → session_open → poll → get-logs → Blowfish-ECB decrypt
→ SID container → "messages" (Varlog, byte-exact against the Manager's own saved plaintext)`. The
first full live pull returned 56811 bytes of live Varlog, decoding to a plausible boot log
("Aug 26 00:31:46 <MDI_HOSTNAME> syslog-ng... Booting Linux... 4.14.162-gvci"). Three consecutive
back-to-back pulls with no power-cycle between them each returned the full Varlog live, confirming
robustness.

### 4.11 macOS interface setup

MDI DHCP-serves the host `192.168.171.30` over the USB RNDIS gadget (enumerates as `en17`, MAC
`70:c6:ac:00:05:39`), but macOS assigns a `/32` mask — set it to `/24` after every USB replug:

    sudo ifconfig en17 inet 192.168.171.30 netmask 255.255.255.0

(a full-tunnel VPN on another interface can otherwise steal the route). Discovery keys off the
subnet, not the interface name — `en17` is only what this gadget happened to enumerate as.

---

## 5. Appendix: dead ends ruled out during the key-derivation hunt

The live key-derivation trace (now solved, §4.8) took nine dated passes (2026-08-25/26) across
static RE, live Frida hooks, and one cold-capture session before landing on the final formula. None
of the intermediate conclusions below are current; they are kept only as a short record of what was
tried and why each route failed, so the same dead ends are not re-run.

- **Static keyring lookup (ruled out).** Six `MODULE_TYPE_ID_*` keys were pulled live from the
  keyring table (`DAT_10302ac8`, stride `0x104`, key at `+0xC4`) via read-only
  `ReadProcessMemory`. None decrypted the captured 9052 stream against the known-plaintext oracle,
  under any of the 24 byte-order permutations tested against a from-scratch Blowfish
  reimplementation. Conclusion: these are defaults/fallbacks, not the operative key.
- **"Per-session" key (ruled out).** A Frida hook on `BF_set_key` first yielded a key that appeared
  to change across what were actually separate Manager process instances; re-testing against a
  corrected decryptor showed the same key (`fde7ccb2…`, withheld) decrypts every capture from the
  same unit across different Manager PIDs and reconnects — the key is deterministic per device, not
  per session.
- **"Derived at process init" (ruled out).** `frida.spawn` with hooks armed before `resume` showed
  no keyring/RNG/hash/memcpy calls and no key present in memory until after a device Connect — the
  derivation is Connect-time, not init-time, and uses no library-level crypto/RNG calls (pure inline
  arithmetic).
- **Assembly/object-graph tracing (dead end, but located the key precisely).** Static `pdf`
  tracing found the key-holder is a dedicated `0x38`-byte allocation (`FUN_102320c3`) owned by the
  message-handler object (`handler+0x8c → cryptoCtx`, `cryptoCtx+8 → keyholder[0:0x38]`), ruling out
  the connect handler, the transport ctor, and `TrnClt::ConnectToServer` as the key-setter. The
  exact write instruction inside the handler's crypto-context init was never pinned from pseudocode
  alone (Ghidra drops ECX provenance across `std::move`-style helpers used here).
- **Dynamic instrumentation of the write (dead end — method note, not a finding).** Frida
  hardware watchpoints on the rotating key-holder allocations **crashed the live Manager** (the
  `#DB` single-step storm plus an exception handler that swallows all exceptions made per-hit
  identification infeasible without further work) — not viable on the production rig without
  destabilizing it. Headless GUI automation of the Manager (SSH + `SetForegroundWindow` + scripted
  Connect/Disconnect) was built as a side effect of this effort and remained useful for later,
  non-destructive capture work.
- **"Addend = serial − 512" (arithmetic slip, corrected same investigation).** The first successful
  decode of the derivation formula (`FUN_10268960`: base key + per-dword addend) misread the test
  unit's serial digits, producing an addend that looked like `serial − 0x200`. Recomputing with the
  correct serial value showed the addend **is** the raw serial — see §4.8's final formula.
- **"Device needs Bosch-specific activation/arming" (ruled out by a cold-capture test).** Moving the
  MDI2 to macOS produced an apparently dormant device (control frames ACKed, no data on any
  channel) that was first read as a missing USB-driver/ident "arming" step the generic macOS RNDIS
  gadget doesn't perform. A full cold-boot USB (USBPcap) + network capture on the Surface showed
  standard RNDIS enumeration (VID `0x0ca0`/PID `0x1301`: `GET_DESCRIPTOR` x3 + `SET_CONFIGURATION`,
  `OID_GEN_CURRENT_PACKET_FILTER`, `SET 802_3_MULTICAST_LIST`; no `OID_GEN_RNDIS_CONFIG_PARAMETER`)
  and initialization with **no vendor control transfers, no vendor OID, no
  arming message** — the device gets zero host→device packets until the 900x TCP connect itself.
  The dormancy was connection-pool/session exhaustion from rapid repeated test connects (§0, §4.10),
  not a missing activation step; this is the current, correct account.

---

## Open conflicts

- **Keyring table identity mismatch (unresolved in source, not closed by a later dated
  correction).** Two different tables are used to classify this same MDI2 unit's module type: the
  six-entry static keyring (`DAT_10302ac8`, §5) classes the hardware as `MODULE_TYPE_ID_M_VCI`
  (id `2`), while the final, live-confirmed derivation formula (`FUN_10268960`, §4.8) reads
  `module_type = 0x1c` (`MODULE_TYPE_ID_MDI_2`) out of a *different*, larger table
  (`DAT_10309d60`). The source material never reconciles why the same physical unit maps to two
  different ids in two different tables, or how the two tables relate to each other — it simply
  moves on once the `DAT_10309d60`/`0x1c` path is confirmed to produce the byte-exact key. Kept open
  here rather than silently assumed to be "two unrelated lookup tables that happen to both apply."
