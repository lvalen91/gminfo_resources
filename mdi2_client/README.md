# macOS MDI2 client

Native, Windows-free client for the GM/Bosch **MDI2** device-facing protocol, implementing the RE
in `../research/MDI2_MANAGER_IDENT_LOG_PULL_AUG2026.md` (see that doc's §0 summary). **Live-validated
end-to-end** over USB: discover → derive key → control handshake → session_open → get-logs →
Blowfish-ECB decrypt → SID container → Varlog → session_close, repeatable back-to-back.

## Status
| piece | module | state |
|---|---|---|
| Discovery (`225.1.1.1:8194` beacon receive/multicast join) | `discovery.py` | partial — beacon field/serial decode still TODO |
| Key derivation (`base_key[MDI_2] + serial`, byte-verified) | `crypto.py` | done |
| Blowfish-ECB (big-endian, stock pycryptodome) | `crypto.py` | done |
| Wire frame + 8-byte control frame (construct) | `framing.py` | done |
| 900x session, control handshake, patient recv | `transport.py` | done |
| JSON app messages + body length-suffix framing + get-logs + session-close | `messages.py` | done |
| SID log container decode (`0x8a9` meta / `0x8a8` data) | `container.py` | done |
| Log pull, back-to-back | `logs.py` | **done, live-validated** |
| Non-log 900x services (device info, network settings) | — | not yet mapped (needs a WiFi capture) |
| D-PDU tunnel re-arm (management `session_open` → 9050 `PDU START`) | `live_calibration.rearm_dpdu_tunnel` | **done, live-validated** (re-opens TCP/10123) |
| Live D-PDU radio link (resource-0x2A bring-up, persistent RX cop, cyclic TesterPresent) | `live_programming_transport.py` | **live-verified end-to-end 2026-11-10** carrying the full LTZ calibration write (14 containers + finalization + reset + readback) |
| Read-only identify / cal readback | `live_calibration.identify` | implemented; reports adapter rejection separately from ECU responses |
| ECU reset (`11 01` -> `51 01`; stock SPS does exactly one, at finalization; an opt-in `--pre-reset` fallback can add one before the write) | `live_calibration.py` | **live-verified** |
| Factory data-wipe (Service Mode `02` procedure) | — (no wipe routine in this client's code; see `live_calibration.py` note) | **live-verified** on the bench procedure; not exposed as a CLI command here |
| Gated LTZ calibration **write** | `live_calibration.write_ltz_calibration`, `cli write` | **live-verified 2026-11-10** — full write performed on radio `0x80` via the stock-SPS method (`pre_reset=False`), 14 containers + finalization + reset; post-reset readback confirmed profile High Country -> LTZ. SecurityAccess used the degenerate all-FF path (module is SBI-flipped); the real-seed CMAC path remains unverified (see `security_cmac.py`) |
| D-PDU channel marker `0x463` (`(channel << 8) \| 0x10`) | `live_programming_transport._cop_marker` | channel `0x25` capture-verified on a vehicle; **live 2026-11-10 generalized to channels 0x02-0x30** (observed during the LTZ write, reads/writes succeeded on all of them); channels outside that range remain unverified |
| GM SecurityAccess AES-128-CMAC | `security_cmac.py`, `cli security` | math proven offline (RFC 4493); **the real-seed CMAC key handshake has still never been run on a vehicle** (the live write used the degenerate all-FF path instead, confirmed live 2026-11-07/2026-11-10) |
| ECU/DID catalog, generic UDS client | `ecu_catalog.py` + `data/*.json`, `uds_generic.py` | offline-tested; static protocol IDs only |
| Multi-ECU "Read All" over SocketCAN/ISO-TP | `module_reader.py`, `can_transport.py`, `cli read-all` | **offline-only**; bench fallback, never run against a live bus |

## Live D-PDU programming (calibration write) — `live_programming_transport.py` / `live_calibration.py`

**Live-verified 2026-11-10:** a full LTZ calibration was written to the CSM radio (ECU `0x80`)
via the stock-SPS method (`write_ltz_calibration`, `pre_reset=False`) — 14 containers (slots
02-0F) transferred, then finalization (`2E F198`="9999988888", `2E F199`=run-date, `31 01 039B`
finalize routine, `2E F190 <VIN>`, `11 01` reset), then readback. Post-reset verification: `F182`
profile flipped High Country -> LTZ (14/14 per-slot records match the package); `F199`
programming date = the write date; all 14 `F0F0` slots present; VIN intact; module rebooted and
responded. SecurityAccess used the **degenerate all-FF** path because this module is SBI-flipped;
key/accessory were OFF (BCM `F085`=0x00) with the radio held awake by the sustained D-PDU session,
on battery alone (~12.3-12.7 V). ADB `uid 2000` access on the radio was retained through the write
and reset. No MEC (`F1A0`) action was taken or needed. The real-seed AES-128-CMAC SecurityAccess
path (non-SBI-flipped module) remains **unverified** — see `security_cmac.py`.

> **Scope, corrected 2026-11-11:** this client has demonstrated writes of **stock GM-signed
> calibration packages**. Independent offline checks verified all 14 CSM header signatures and
> production-CA signer-record signatures (RSA-2048 PKCS#1 v1.5/SHA-256). Editing the payload and
> recomputing its digest invalidates the existing header signature. Modified-package attempts
> returned `7F 36 72`; that general programming failure does not isolate the cause to a signature
> check. The active target UDS signature/root verifier and a usable bypass remain unresolved.
> No signing private key was recovered. See the
> [seed key and signing reference](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).

The MDI2's diagnostic transport is the ISO-22900-2 **D-PDU API tunnelled over TCP/10123**
(`research/MDI2_DPDU_API_PROTOCOL_AUG2026.md`). This client now drives it natively:

- **Tunnel re-arm.** 10123 is not always listening and is **not idempotent** — one malformed
  frame closes it and it does not self-rearm. `rearm_dpdu_tunnel(serial, host)` re-opens it by
  the management flow (`session_open` on 9052 → three polls + `APP_NAME=PDU/COMMAND=START` on
  9050, ending in the live session id as a LE u32). Live-verified it reopens 10123. If the
  device's **session service is wedged** (symptom: 9052 stops answering its control handshake,
  from dangling sessions), only a **USB power-cycle** recovers it.
- **Response filtering and serialization.** ECU responses arrive on the MDI's
  *persistent receive COP*, never the request COP, so responses cannot be attributed by COP.
  Attribution is therefore **strict serialization**: one request in flight; `parse_radio_rx` is a
  strict allow-filter (radio handle + event type 1 + persistent RX COP + response CAN id);
  non-matching events (TX-confirms, keepalive, D-PDU type-2) are skipped; any timeout/ambiguity
  poisons the session and tears the tunnel down. A well-formed `7F <sid> <nrc>` echoing the
  in-flight service is a correlated terminal answer, not an ambiguity: it surfaces as
  `TransactionError("service XX NRC xx")` and the link stays up (2026-11-10; previously it
  poisoned, forcing a re-open per unsupported DID, which wedged the MDI). Serialization and
  prefix checks alone do not prove freshness against late duplicates with the same response;
  see the simulator's caveat.
- **TesterPresent** is a cyclic `3E 80` offloaded to a separate CLL (`create_keepalive_cll`).
- **SecurityAccess** probes the `27 01` seed and branches (`unlock_security_access`): a 31×`0xFF`
  seed takes the degenerate all-FF → 12 zero-byte key path (byte-identical to `unlock_all_ff_seed`,
  confirmed live 2026-11-07); a real non-degenerate seed uses AES-128-CMAC via a caller-supplied
  key (`GMSecurityAccess`); a real seed with no key **aborts** (no key is fabricated). This
  (SBI-flipped) module currently returns the all-FF seed, so the degenerate path triggers. The
  decoded stock SPS session caught the module in its *normal* state (real 12-byte CMAC key) — the
  branch covers both.
- **Framing correction (2026-11-07).** `build_one_shot` returns a complete frame; the live sender
  incorrectly added a second header. It now sends exactly one header, covered by a byte-for-byte
  regression against the captured seed request. ComParam `0x19=0x22` and the shorter UPDATEPARAM
  trailer also match the capture. The earlier `0x2830` rejection does not establish ECU power
  mode or a leaked CLL: malformed frames reached the adapter before ECU transmission.
- **Calibration power mode.** Read BCM ECU `0x40`, DID `F085`, and require the documented OFF
  value `00` before the initial reset and after reconnect. Service Mode `02` belongs to the
  separate data-wipe procedure. A lit display does not establish BCM power mode.
- **CLL hygiene.** Each CLL holds the ECU/CAN resource; `LiveDpduSession.close` destroys its CLLs
  and closes partially opened sockets/links on failure. No status-to-lock inference is made.

CLI:
```
./.venv/bin/python -m mdi2.cli rearm    <SERIAL>                       # re-open 10123
./.venv/bin/python -m mdi2.cli identify <SERIAL>                       # read-only VIN/MEC/cal meta
./.venv/bin/python -m mdi2.cli recover  <SERIAL>                       # diagnose module left in programming mode
./.venv/bin/python -m mdi2.cli write <LTZ_FOLDER> <SERIAL> <VIN>       # dry-run plan (gates only)
./.venv/bin/python -m mdi2.cli write <LTZ_FOLDER> <SERIAL> <VIN> --confirm   # the ONE live write (stock SPS)
./.venv/bin/python -m mdi2.cli write <LTZ_FOLDER> <SERIAL> <VIN> --confirm --pre-reset  # opt-in: hard-reset first (NOT stock SPS; retry fallback)
```
The `write` command requires the 14 LTZ containers to match the pinned `ltz_reference_manifest`
hashes and the connected VIN to match `<VIN>`. The source F182 metadata must match the documented
LTZ or High Country profile; unknown, mixed or incomplete source profiles are rejected. Source
metadata is not proof of arbitrary vehicle compatibility. The target remains the unchanged LTZ
containers, regardless of the supported source profile.

With `--confirm`, the writer performs a fresh acknowledged PDU START, checks BCM OFF and VIN,
and takes one voltage sample (at least 12.000 V; readings above 30.000 V are rejected as
implausible, not approved as safe). Only then does it run the programming state machine, which
matches the decoded stock SPS transcript: extended session, DTC logging off (`85 02`) and normal
comms off (`28 03`), SecurityAccess, pre-programming routine `31 01 0249`, programming session,
the 14-container transfer, `22 F0F0` status readback, a fresh finalization link
(`22 F1B0`/`10 03`, SecurityAccess, fixed repair-shop id `2E F198 "9999988888"`, **current-date**
`2E F199`, finalize routine `31 01 039B`, `2E F190 <VIN>`), and the single radio hard reset
`11 01` at finalization. Stock SPS performs **no** radio pre-reset; the `--pre-reset` flag is an
opt-in fallback (an extra `10 03`/SecurityAccess/`11 01` before the write) for retrying a failed
SPS-method write, and is **not** part of the stock sequence. The dry-run plan may sample voltage
but never resets or programs. Matching metadata does not verify the entire flashed payload.

## Install / run
```
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m mdi2.cli key <SERIAL>   # serial -> 56-byte Blowfish key
./.venv/bin/python -m mdi2.cli scan           # listen for the device beacon
```
Pull logs (requires the MDI2 on this machine's `192.168.171.0/24` link):
```python
from mdi2 import crypto
from mdi2.transport import Session
from mdi2.logs import pull_logs
key = crypto.derive_key(<SERIAL>)                     # or read serial from discovery.discover()
s = Session(key, "192.168.171.2").connect(ports=[9052])
print([(n, len(d)) for n, d in pull_logs(s)])         # [('messages', ~56900)]  = Varlog
s.close()
```
Offline: `mdi2_key.py <serial>` (→ key) and `mdi2_9052_decrypt.py <pcap> <key_hex>` (→ plaintext logs).

## Operational notes
- The MDI2 must be on this machine's network (direct USB gadget, or a tunnel). macOS gives the
  gadget iface (`en17`) a `/32` and a VPN can steal the route — fix per re-plug:
  `sudo ifconfig en17 inet 192.168.171.30 netmask 255.255.255.0`.
- **No Bosch/Windows activation is needed** — macOS generic RNDIS is sufficient.
- The device holds **one session**; `pull_logs` sends the session-close so back-to-back pulls work.
  If it stops responding (dangling sessions from crashed/aborted runs), USB power-cycle it.
- The 900x channels are `common_service::generic_client<PORT>` JSON services (9001=speaker,
  9052=logs, …); only the log path is implemented so far.

## Generic UDS capabilities (additive, bench/diagnostic; separate from the live radio path)
These modules are generic and do **not** touch the vehicle-tested MDI2 live write/identify path:
- `mdi2/security_cmac.py` — offline AES-128-CMAC implementation using an assumed
  `ECUID(16)‖Challenge(16)[‖checksum]` input and 12-byte truncation. The captured level-1 seed
  is 31 bytes, so this helper's 32/33-byte model needs reconciliation before real-seed use.
  Domain-suffix fallback (`DOMAIN_SUFFIXES`) is implemented, not established as universal key
  sharing. The GM response shape lacks a hardware-verified known-answer vector; RFC CMAC tests
  establish the primitive only. See the [central reference](../research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md).
- `mdi2/ecu_catalog.py` + `mdi2/data/*.json` — 24-ECU / 28-DID / 4-RID static catalog (protocol IDs only).
- `mdi2/uds_generic.py` — transport-agnostic UDS client (`GenericUdsClient`).
- `mdi2/module_reader.py` — DPS-style multi-ECU "Read All" (bus wake, F1B0 discovery, per-ECU read).
- `mdi2/can_transport.py` — optional SocketCAN + ISO-TP transport (`python-can`/`can-isotp`, lazy).

New CLI subcommands (existing `scan/key/connect/rearm/identify/recover/write` are unchanged;
`security` is pure computation, `read-all` needs a SocketCAN interface and is offline-verified only):
```
python -m mdi2.cli security <seed_hex> [--key <hex> | --key-map <path>]   # DRY-RUN CMAC compute
python -m mdi2.cli read-all --transport can --interface can0 [--security --key-map <path>]
```

### SecurityAccess key map (NEVER commit real keys)
Keys live in a JSON map `{ecuid_hex: aes128_key_hex}`. The only tracked map is
`keys.example.json` (PLACEHOLDER keys). Put the real map at a **git-ignored** path and pass it
via `--key-map` (or `GMSecurityAccess(key_map_path=...)`). `.gitignore` already excludes
`keys.json`, `*.keys.json`, `keymap.json`, and `secrets/`. Suggested location:
`~/.config/mdi2/keys.json`. With no `--key-map`, **no keys are loaded** (`GMSecurityAccess()` starts
empty), so `security` needs `--key` or `--key-map`; the shipped example is not auto-loaded.

**Live-revalidation still required** (offline-verified only here): `read-all` discovery/wake
(`WAKE_NM_CAN_ID=0x10400000`, F1B0 probe), the CAN/ISO-TP transport, the `0x463` marker outside
the now live-verified 0x02-0x30 channel range (see the D-PDU channel marker row above), and any
real-seed (non-degenerate) SecurityAccess key response against a real ECU. The CMAC math is
proven against RFC 4493 vectors offline; the real-seed CMAC key handshake has never been run on a
vehicle — the live 2026-11-10 write used the degenerate all-FF path instead.
