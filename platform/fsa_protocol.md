# GM FSA (Feature Service Architecture) Protocol

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton), Android 12 guest under GHS INTEGRITY
**Research Date:** June 2026 (Y181 `W231E-Y181.3.2-SIHM22B-499.3`), with Y175 live-bench
follow-ups through 2026-11-17
**Data source:** live ADB shell (uid=2000), `enumeration/Y181/jun2026/` capture,
`DelayedWKSApp.apk` decompilation, Y175 bench port scans and Bus-2 T1 tap captures

**Scope:** FSA/NFSA wire format, service catalog (port/serviceId/partition mapping), per-service
function tables, recovered protobuf definitions, live query results, and FSA-protocol-layer
security findings (parser bugs, auth model, injection surfaces). Vehicle-telemetry content that
rides this transport (`DisplaysCoordination`) is in scope here because the transport framing,
not the signal list, is this doc's subject.

**Evidence legend:** `[C]` confirmed live (ADB/bench/tap); `[U]` update/correction superseding
earlier text in this doc; `[P]` protocol/catalog finding reconciling static vs. live data;
`[?]` unverified/open; `[F-*]` named security finding, cross-referenced to the offensive-audit
ranking doc.

**Related:** [`ethernet_networking.md`](ethernet_networking.md) (VLAN topology, listening ports, partition
addresses, firewall posture) · [`ethernet_networking.md`](ethernet_networking.md) (consolidated
port/VLAN/firewall reference) · [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)
(RemoteModuleHMI rendering pipeline, NFSA naming) · [`vip_ipc_ghs.md`](vip_ipc_ghs.md) (GHS VP
crash semantics) · [`ota_programming_roles.md`](ota_programming_roles.md) (Global-B HMI-only
demotion) · [`research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md)
(severity ranking for the `[F-*]` findings below)

> **Terminology.** GM's own code names this `com.gm.fsa.service` ("FSA"). The
> jun2026 logcat shows `FSAServiceConnectedClient`, `FSANetCommsService9016`,
> `FSAProperty`, `FSAServiceEventHandler` etc. and the literal log line
> *"FSA: Read Header size 20"*. The expansion **Feature Service Architecture**
> is used here. [`ethernet_networking.md`](ethernet_networking.md) refers to the same
> layer as **NFSA (Network Function Service Architecture)** — they are the same
> protocol; `com.gm.nfsa.*` is the cluster-side Java package name (see
> [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)).

FSA is GM's proprietary service-oriented middleware running over TCP between
hypervisor partitions on the vehicle backbone (VLAN 5, 192.168.1.0/24). Each
message is a **20-byte big-endian binary header** followed by a **Protocol
Buffers** payload. Service discovery uses SOME/IP-SD multicast to
`239.192.0.1`. The discovery **port** is contested between two evidence
sources (live Y181 network scan: UDP **30490**; decompiled `FSACatalog.java`
constant: UDP **3000**) and is not reconciled — see
[Open Conflicts](#open-conflicts). (The original intro called the earlier
`:3000` reading "superseded" by the live scan, while its own `[F-udp]` finding
called the discrepancy unresolved; the "superseded" claim is therefore not
carried forward as established.)

---

## Wire Format

```
Offset  Size  Field
------  ----  -----------------------------------------
0       2     uint16  serviceId
2       2     uint16  instanceId
4       2     uint16  functionId
6       2     uint16  opType
8       2     uint16  clientHandle
10      2     uint16  MAGIC = 0x5AA5  (decimal 23205)
12      4     uint32  reserved (always 0 on CSM; uptime/seq counter on IPC)
16      4     uint32  payloadSize
20      ...   protobuf payload
```

All multi-byte integers are **big-endian**. The constant `0x5AA5` at offset 10
is a frame sync/magic value written on send (matches the cluster wire
format documented in `cluster_navigation.md`). **It is never checked on
receive — not a framing gate** (jadx RE, confirmed by the live anonymous-peer
test under [Security Notes](#security-notes); History: corrected 2026-11-12,
earlier text implied it was validated). The 20-byte header size is
confirmed by the runtime log `FSA: Read Header size 20`.

> **Reserved field (offset 12).** `0` in the CSM (Android) implementation, but
> **non-zero on the IPC partition** (observed `0x6841b1ec` / `0x6841b21c` across
> successive messages, incrementing) — an uptime/sequence counter, not a
> constant. Frame parsers must not assume zero.

### OpType Values

| Name | Decimal | Hex |
|------|---------|-----|
| Request | 641 | 0x0281 |
| RequestResponse | 674 | 0x02A2 |
| Response | 595 | 0x0253 |
| Processing | 836 | 0x0344 |
| Get | 421 | 0x01A5 |
| Set | 422 | 0x01A6 |
| Status | 343 | 0x0157 |
| Event | 1032 | 0x0408 |

### System FunctionID Values

| Name | Value |
|------|-------|
| Heartbeat | 100 |
| OfferService | 110 |
| RemoveService | 111 |
| FindService | 112 |
| Subscribe | 120 |
| RemoveSubscription | 121 |

---

## Connection Handshake

1. Client opens a TCP connection to the service's `IP:port`.
2. Client sends a **Subscribe** message (`functionId=120`,
   `opType=RequestResponse`, `clientHandle=1`) whose protobuf payload is
   `Subscribe_request_response{ functionID: [100] }` (subscribing to Heartbeat).
3. Server replies with a **Response** (`opType=595`) carrying `Subscribe_response`
   indicating which subscriptions were accepted.
4. Server then streams **Heartbeat Status** messages (`functionId=100`,
   `opType=Status`, `clientHandle=0`) every **2000 ms**.
5. The client may then issue **Get / Set / RequestResponse** messages for
   service-specific functions.

The system domain server (`com.gm.domain.server.delayed`,
`DelayedWKSApp.apk`, uid=1000) holds **one** established client connection to
each partition FSA service. Partition FSA servers enforce a single-client limit,
which is why an ADB-shell connection to a *partition* FSA port is accepted then
immediately closed. The Android guest's **own** FSA servers (192.168.1.100) keep
additional connections open and are fully queryable from the shell.

### Verified interaction (shell → Android guest FSA servers)

```sh
# Subscribe to heartbeat on RemoteModuleHMI (serviceId 0x03EF=1007, port 9002)
printf '\x03\xef\x00\x01\x00\x78\x02\xa2\x00\x01\x5a\xa5\x00\x00\x00\x00\x00\x00\x00\x02\x08\x64' \
  | nc 192.168.1.100 9002

# Subscribe to heartbeat on NetworkAccessManager (serviceId 0x0402=1026, port 9016)
printf '\x04\x02\x00\x01\x00\x78\x02\xa2\x00\x01\x5a\xa5\x00\x00\x00\x00\x00\x00\x00\x02\x08\x64' \
  | nc 192.168.1.100 9016
```

Header byte breakdown (RemoteModuleHMI example):

| Bytes | Field | Value |
|-------|-------|-------|
| `03 ef` | serviceId | 1007 (RemoteModuleHMI) |
| `00 01` | instanceId | 1 |
| `00 78` | functionId | 120 (Subscribe) |
| `02 a2` | opType | 674 (RequestResponse) |
| `00 01` | clientHandle | 1 |
| `5a a5` | MAGIC | 0x5AA5 |
| `00 00 00 00` | reserved | 0 |
| `00 00 00 02` | payloadSize | 2 |
| `08 64` | protobuf | field 1 (varint) = 100 → `functionID:[100]` |

Both services returned the expected Subscribe response and emitted 2-second
heartbeat status frames.

---

## Service Catalog

### Port → Service → serviceId → hosting partition

| Port | Service | serviceId | Active instance(s) |
|------|---------|-----------|--------------------|
| 9001 | CustomChimeDownload | 0xF5 | AMP (.103, offline) |
| 9001 | VehicleDataHubACPFunctions | 1032 | ACP (172.16.4.14) |
| 9002 | RemoteModuleHMI | 1007 | CSM (.100, Android) |
| 9003 | TurnByTurn | 1008 | TCP (.102) |
| 9005 | OnStarFunctions | 1010 | TCP (.102) — active ESTAB |
| 9010 | DeviceInformation | 1001 | all partitions (instanceId varies) |
| 9011 | ProgrammingMaster | 1006 | CSM (.100) — **[P] dead code, see below** |
| 9012 | RemoteReflash | 1025 | TCP (.102) |
| 9013 | VehicleDataHubFunctions | 1028 | GEN12_TCP |
| 9015 | TCPConnectionNotification | 1030 | TCP (.102) |
| 9016 | NetworkAccessManager | 1026 | CSM (.100) — active |
| 9018 | RemoteReflashUI | 1027 | CGM_OTA (.112) — active ESTAB |
| 9019 | VehicleDataHubDataOffboard | 1031 | CGM_OTA (.112) |
| 9020 | DisplaysCoordination | 2027 | IPC (.106) |
| 9021 | FTPCONTROL | — | CSM (.100), dynamic; allowed from IPC; closed on bench |
| 9022 | FTPDATA | — | CSM (.100), dynamic; allowed from IPC; closed on bench |
| 9025 | MAPIMAGE | — | CSM (.100), dynamic; allowed from RSI1; closed on bench |
| 30490 | SOME/IP-SD multicast | — | `239.192.0.1` group (UDP; live-scan-confirmed; see [Open Conflicts](#open-conflicts)) |

This table is the service→address mapping of record; it is kept here (not in
`ethernet_networking.md`) because serviceId/port/partition is FSA-protocol
data. For VLAN topology, switch config, and the general listening-port/firewall
inventory, see [`ethernet_networking.md`](ethernet_networking.md).

### DeviceInformation instanceId → partition

serviceId 1001 runs on every partition; `instanceId` selects which one.

| instanceId | Device | IP |
|-----------|--------|-----|
| 1 | CSM (Android) | 192.168.1.100 |
| 2 | TCP | 192.168.1.102 |
| 3 | AMP | 192.168.1.103 (offline) |
| 4 | RSI1 | 192.168.1.104 (offline) |
| 5 | RSI2 | 192.168.1.105 (offline) |
| 6 | IPC | 192.168.1.106 |
| 7 | CGM / CGM_OTA | 192.168.1.112 |
| 8 | LOWRADIO | 192.168.1.108 (offline) |

### VCU-variant listening addresses (`ServiceListeningAdressesVCU`, unreachable on bench)

- ProgrammingMaster: `172.16.5.100:9011`
- RemoteModuleHMI: `192.168.118.1:9002` (VCU_AGVM)
- NetworkAccessManager: `172.16.4.100:9016, 172.16.5.100:9016` (dual)

See `projection/cluster_navigation.md` for the VCU/CIP (QNX) inter-VM FSA
topology (`192.168.118.x` / `172.16.5.x`).

### Live capture cross-check — IHU server/client roles (Y175, 2026-10-05)

A live socket snapshot (`net_sockets.txt`) independently confirms the IHU's
server/client split for the catalog above and adds timing/direction detail
the static catalog doesn't carry:

**IHU as server (LISTEN):** 192.168.1.100:9002, :9010, :9016 — matches the
catalog.

**IHU as client (connects out):** catalog says `.102:9005/9012/9018`
(TCP/CGM_OTA partitions). The live snapshot instead shows uid 1000 (system)
in **SYN_SENT to 192.168.1.112:9010 and 192.168.1.112:9018** (`.112` = CGM,
not `.102`), plus an established `192.168.1.100:9016 <-> 192.168.1.100:58814`
loopback-on-vlan5 pair. The `.102:9005/9012/9018` client targets were **not
observed** in this capture — not refuted, UNVERIFIABLE-FROM-LIVE. This capture
is from an out-of-vehicle bench (Radio + Display + GM USB receptacles, no
vehicle bus/ECUs); `.112` (CGM) and `.102` (TCP) are external vehicle nodes not
present on the bench, so the SYN_SENT to an absent `.112` peer is the IHU
reaching for a partner that isn't there — expected, not a defect.

---

## Services in Detail

### DeviceInformation (serviceId 1001) — `IDeviceInformation` fn 1–14

**CSM (Android) — fn1 (GET):** `Harman` / `CSModule` / SW `unknown` / HW
`unknown` / PN `unknown`. **AsBuiltInfo (fn2)** returns `unknown` — the real
as-built config lives on IPC and TCP, not the Android guest.

**IPC (instanceId=6) — fn1 (GET), CONFIRMED:** Company **`Visteon`**, Module
**`IPC`**, XML Version **`1.0`**, PN/serial empty. (IPC's reserved header field
is non-zero — see Wire Format.)

**TCP (instanceId=2):** connection accepted, Subscribe ACK, then immediate
close (single-client window). **CGM_OTA (instanceId=7):** no response — likely
accepts only its vlan4 source IP (172.16.4.112).

> **TCP dual-homed on vlan4 (2026-07-01).** With the telematics module's
> cellular antenna connected, `172.16.4.1` (MAC identical to `192.168.1.102`,
> confirming same physical module) now also answers on 9010
> (`DeviceInformation`) and 9012 (`RemoteReflash`) — previously dead on bench,
> see [`ethernet_networking.md`](ethernet_networking.md).
> Same accept-then-close single-client behavior as the vlan5 face; a raw
> `rmIdentification`/RemoteModuleHMI frame (wrong serviceId for this port) got
> no response, as expected, since 9010/9012 use serviceId 1001/1025, not 1007.
> `OnStarFunctions` (9005) and `RemoteReflash` (9012) are the two TCP-hosted
> services most directly tied to cellular/OTA function — worth revisiting once
> a way around the single-client lock is found.
>
> **[2026-11-13, live Bus 2 T1 tap] Radio also behaves as a client toward these same two
> ports — [C].** Posing as the gateway `.102` identity on vlan5, the radio was observed
> **initiating outbound TCP SYNs to us** on **9005** and **9012** roughly every **~4 s**,
> getting RST (nothing listened host-side). This is the reverse direction from the
> accept-then-close hosted behavior above — the radio itself polling/retrying toward the
> gateway's `OnStarFunctions`/`RemoteReflash` ports. [?] Cadence not characterized beyond a
> single capture window (retry-backoff vs. steady poll not distinguished); whether standing
> up a listener elicits a Subscribe/Heartbeat FSA handshake is untested. See
> `source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` §8.3 in the
> `Y175_2026-11-02` analysis tree.

### NetworkAccessManager (NAM — serviceId 1026, instance 1, CSM port 9016)

| FunctionID | Method | Type |
|-----------|--------|------|
| 2601 | `networkRequest` | RequestResponse |
| 2602 | `provideNetworkList` | RequestResponse |
| 2603 | `sessionNotSuccessful` | Request |
| 2604 | `networkStatus` | Event |
| 2605 | `AKAChallengeRequest` | Event |
| 2606 | `postAKAChallengeResponse` | Request |
| 2607 | `getControlledECUList` | Get |
| 2608 | `postEAP_AKA_Identity` | Request |
| 2609 | `postEAP_AKA_Identity_Response` | Request |
| 2610 | `EAP_AKA_Identity_Request` | Event |
| 2611 | `postVLANsAvailable` | Request |

The AKA / EAP-AKA functions implement **3GPP AKA** and **EAP-AKA** — SIM-based
cellular network authentication. NAM brokers the challenge/response between the
telematics SIM (TCP/CGM side) and the network and manages which VLANs/ECUs get
off-board connectivity.

**Live results, bench off-network (initial pass):** `provideNetworkList`
(fn2602) returned 1 entry — `display="None"`, `networkType=0` (`NAM_NONE`),
raw `0a 0c 0a 08 08 00 12 04 4e 6f 6e 65 10 00`. `networkStatus` (fn2604)
subscribe `08 AC 14` → `{functionID:2604, successful:true}`, no events in 10 s
(varint 2604 = `0xAC 0x14`, not `0xCC 0x14`). `getControlledECUList` (fn2607,
GET) returned empty — Android NAM controls no ECUs. The initial `networkRequest`
(fn2601, CELLULAR/WIFI, APID="CSM") got no Response, but the payload used an
not checked against the corrected required fields (see protobuf correction below);
missing fields are another explanation, so off-network state alone is not established.

**History (2026-11-15 follow-up, on-radio over USB ADB):** with the corrected
request layout, NAM9016/RemoteModuleHMI9002/DeviceInformation9010 all accepted
instance-1 heartbeat subscriptions and streamed heartbeats; NAM2602 with the
corrected APID-string request again returned the single `None`/NAM_NONE entry,
2607 again returned an empty controlled-ECU list, HMI705 returned an empty
app-list status. Correctly formed NAM2601 Wi-Fi and cellular acquire/release
pairs (temporary probe APID, synthetic network name) all four received
function2601/op595 responses; NAM logs confirmed required fields present and
dispatch to `WifiTrackerService`/`TcpTrackerService`; all returned network
status 0/DOWN. No off-board link or NAT forwarding was demonstrated. Wi-Fi was
enabled before and after the test; the Wi-Fi-release log line "Disabled WiFi"
is unconditional text, not an actual state measurement. None of this is proof
of host-to-radio T1 reachability — it is on-radio socket exchange over USB ADB.

**Transport note:** use bidirectional `adb shell -T` when piping FSA request
bytes into on-radio `nc`; `adb exec-out` did not deliver request stdin in this
harness, so the initial no-reply trials above are invalid service negatives,
not confirmed negatives. Localhost ADB forwards also closed without replies
because the FSA listeners bind the radio's VLAN address, not loopback. Direct
host-to-T1 attempts returned `[Errno 65] No route to host`; external peer
emulation for 9012/9005/9018 remains unperformed, not exhausted. Temporary
clients used bounded timeouts; no existing FSA service was stopped or replaced.

**Static control consequences (current Y175; live request dispatch above):**
`WifiTrackerService` gates enabling Wi-Fi through
`GMWlanServiceManager.canWifiEnabled()`, checks the requested SSID before
proxy setup, and can release an app or disable Wi-Fi when the last app leaves
in state 3. Proxy enable calls `setIpForwardingEnabled(true)`,
`startInterfaceForwarding(networkInterfaceName,WIFI_INTERFACE)` and
`enableNat`; disable reverses NAT/interface forwarding without an explicit
global-forwarding reset in the inspected code. `TcpTrackerService` resolves the
source IP and changes controlled-ECU allowed state; a firewall effect has not
been proven. These are network-policy controls, not a shell/debug API.

### Remote update and OnStar coordination (current Y175, 2026-11-15)

| Service | Recovered role | Applicability limit |
|---|---|---|
| RemoteReflash, port 9012, service 1025 | TCP-partition peer; fn1903 notifyRRUpdateStatus, fn1904 requestOMADMSession event | Not a radio listener or generic file flasher. |
| OnStarFunctions, port 9005, service 1010 | TCP-partition peer for status, TTY and location | No root/shell API demonstrated. |
| RemoteReflashUI, port 9018, service 1027 | Update coordination functions 2501–2513, including DM-tree read | Coordination and data access do not establish arbitrary updater/file execution. |

These roles come from the current matched APK noted in the schema section,
not the cached older APK. No live FSA calls accompanied this static follow-up.
See [`ota_programming_roles.md`](ota_programming_roles.md) for who actually
flashes what (ProgrammingMaster/CGM/VIP roles, DPS module inventory).

### RemoteModuleHMI (serviceId 1007, CSM port 9002) — Cluster HMI bridge

Android hosts the server; the Visteon **IPC connects as client**
(`192.168.1.106:65343 → 192.168.1.100:9002`, ESTABLISHED) to receive display
commands and send interaction responses. See
[`projection/cluster_navigation.md`](../projection/cluster_navigation.md) for
the navigation-glyph / maneuver-enum rendering pipeline that rides this service.

- **Android → IPC (events, push):** `overlayRequest`, `screenRequest`,
  `overlayCancelled`, `imageWidgetDataUpdate`, `labelWidgetDataUpdate`,
  `listContentChange`, `progressBarDataUpdate`, `activityIndicator`,
  `stopActivityIndicator`, `genericSWCEthernetFeedback`, `listRowUpdate`,
  `moveToTopOfList`
- **IPC → Android (RequestResponse):** `uploadAssets` (fn700), `callbackMethod`
  (fn709), `clientFocus` (fn712), `listSlice` (fn711), `assetsProcessed`
  (fn714), `overlayResponse` (fn703), `rmIdentification` (fn706)
- **IPC reads property:** `getServerAppList` (fn705)

**Cluster App IDs** (`ClusterHmiManager.java`): `CSM_APP_AUDIO=1`,
`CSM_APP_PHONE=2`, `CSM_APP_NAVIGATION=4`, `CSM_APP_OTHER=8`.
**View IDs:** `cluster_view_id`, `hud_view_id`, `all_view_id`.

**Confirmed shell session (acting as a fake IPC client):**

1. Subscribe (fn120) → heartbeat ✓; event subs (fn701–720) silently rejected
   (events push to all registered clients, not subscribe-based).
2. `rmIdentification` (fn706, RequestResponse, empty variantID) →
   frame `03ef 0001 02c2 02a2 0002 5aa5 00000000 00000000`,
   response `0a 04 08 01 10 02` = `extendedAssets:[{1:1,2:2}]`, no error →
   **registered as an HMI module**.
3. `getServerAppList` (fn705, GET) → frame `03ef 0001 02c1 01a5 0003 5aa5 …`,
   3-byte Status payload (minimal app list — bench).
4. `clientFocus` (fn712, RequestResponse, empty list) → frame
   `03ef 0001 02c8 02a2 0004 5aa5 …`, response `0a 00` = empty result → **SUCCESS**.

**Proto structures:**
- `ClientFocus_request_response`: 1(rep) `focusedWidget` { 1: ID string (e.g.
  `cluster_view_id`); 2: focusRow int32; 3: focusWidget enum tabOrderType }.
- `ScreenRequest_event` (push): 1: ID string; 2: persistenceFlag bool; 3: screen
  enum screenType.
- `RMIdentification_request_response`: 1: variantID string ("Info3x", "VCS", or
  empty).
- `RMIdentification_response`: 1: error enum methodResponseErrorType;
  2+: extendedAssets repeated { 1: assetType, 2: count }.

`fsaCatalog.FunctionID.RMIDENTIFICATION` = fn706; function IDs map directly to
`@FSAFunction(id=N)` Java annotations.

### DisplaysCoordination (IPC serviceId 2027, port 9020) — Vehicle telemetry

Hosted by Visteon IPC (192.168.1.106:9020). Not connected on bench (SYN timeout,
no RST — likely a switch ACL or no response to unknown clients; distinct from
"connection refused"). This is a documented FSA attack surface (see
[Security Notes](#security-notes)) that has **not** been live-fired: the host
is unreachable off-vehicle on this bench. When the vehicle is on it exposes:

- **READ (FSAProperty):** `getEngineOilLife`, `getTirePressure`,
  `getAirFilterLife`, `getBrakePadLife`, `getFuelEconomyKm_L`,
  `getFuelEconomyL_100km`, `getAverageVehicleSpeed`, `getBatteryVolts`,
  `getCoolantTemp`, `getOilPressure`, `getTransmissionFluidTemp`,
  `getTransmissionFluidLife`, `getDieselExhaustFluid`, `getEngineHours`,
  `getTrailerBrake`, `getTractionAndStability`, `getOffRoad`, `getTireLoad`,
  `getACCSpeedLimitStatus`, `getHUDOnOffStatus`, `getIPCLayout`,
  `getIPCSpeedConfig`, `getLifetimeFuelEconomyKm_L`, `getTrafficSignMemoryStatus`
  (+ more)
- **WRITE (RequestResponse):** `resetOilLife`, `resetFuelFilterLife`,
  `transmissionFluidReset`, `postTPMS_Relearn`, `setIPCLayout`,
  `setIPCSpeedConfig`, `postHUDUpDownButtons`, `postHUDIntensityButtons`,
  `postHUDOnOffButtons`, `postIPCNAV`, `postAugmentedReality`,
  `postTractionandStabilityRequest`, `postUnits` (+ more)

### TCPConnectionNotification (TCP serviceId 1030, port 9015)

Single function `tcpConnectionNotificationEvent` (fn3001, Event): TCP partition
notifies Android when the TCM (Telematic Control Module) connects/disconnects.
Not connected on bench (needs active cellular modem).

---

## Recovered Protobuf Definitions

From the FSA-annotated message classes in `DelayedWKSApp.apk`. **History:**
2026-11-15, re-pulled against the current Y175 `DelayedWKSApp` build (SHA-256
`5916ad9f7d40d2683e4dac49b7cc5086104dd27042c7fc32716fc3094288e241`) — confirmed
in both the Protos and the active legacy Nano serializer; the tables below are
from that build, not the older cached `8a4fd60d…78cfb9` APK the fields were
originally pulled from. The `NetworkRequest_request_response` layout changed
as a result (see below); all other message shapes were unaffected.

**`NetworkRequest_request_response`:**

| Field | Value/type |
|---|---|
| 1 | networkName, nested translated/display-name message |
| 2 | networkType, integer |
| 3 | aPIDString, string |
| 4 | networkAccess, boolean |
| 5 | sourceIPAddress, string |
| 6 | networkCost, integer |
| 7 | sourcePort, uint32 |

Active `NAMFsaMessenger` requires fields 2/3/4/5 present before calling the
network tracker. (The earlier four-field networkType/APID/priority/handle
layout, used in the first NAM test pass above, was incorrect.)

**`ProvideNetworkList_request_response` / `_response`:** request field 1 is
APIDString, **not a network-type filter**. Response field 1 networkList
(repeated) contains field 1 networkName and field 2 networkType enum
0=NAM_NONE,1=WIFI,2=CELLULAR.

**`NetworkStatus_event`:** 1 networkType; 2 status (connected/disconnected);
3 networkName{display}.

**`ControlledECUList_status`:** 1 eCUList (repeated) { 1 eCUName string; 2 vLAN
uint32 }.

**`DeviceInfo_status`** (6 string fields):

| # | Field | CSM | IPC |
|---|-------|-----|-----|
| 1 | company/manufacturer | `Harman` | `Visteon` |
| 2 | module | `CSModule` | `IPC` |
| 3 | swVersion/xmlVersion | `unknown` | `1.0` |
| 4 | hwVersion | `unknown` | *(empty)* |
| 5 | partNumber | `unknown` | *(empty)* |
| 6 | serial | *(empty)* | *(empty)* |

**`AsBuiltInfo_status`:** 1 asBuiltData (repeated bytes/string — VIN, options);
2 blockId (uint32).

**`VDHControlParameter_request_response`:** 1 parameterId (uint32); 2 value
(bytes/varint).

**`Subscribe_request_response` / `_response`:** request 1 functionID (repeated
uint32); response 1 functionID (uint32 echoed), 2 successful (bool).

---

## Live Query Results — Notable

### IPC ECUResetInfo (fn4, instanceId=6) — GHS Virtual Processor crash

An FSA query (`ReadECUResetInfo_status`, field 1 `eCUResetInfo` { timestamp,
reason }) returned a decoded GHS INTEGRITY hypervisor **Virtual Processor
crash record**: `"VP Failure ID: 007, Error ID: 0x0C03"`, timestamp
`1970-01-01 00:03:19` (epoch+199 s, clock unset at crash). This confirms the
IPC partition has visibility into hypervisor VP failure events. The raw bytes,
full decode, VP-to-partition-name correlation, and `0x0C03` error-code
analysis are owned by [`vip_ipc_ghs.md`](vip_ipc_ghs.md) — this FSA-layer
summary exists only to record *how* the data was obtained (query over FSA,
not a VIP-side log pull).

---

## Security Notes

- The FSA wire layer has **no authentication** — constant magic `0x5AA5` (see
  Wire Format; written on send, never checked on receive) plus a length field
  only. Peer identity is inferred from source IP and enforced (where at all)
  by `iptables` (INPUT policy DROP) and the single-client limit, not by the
  protocol. See `projection/cluster_navigation.md` for the (unverified)
  cluster-injection topology analysis and
  `research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt` for the broader posture.
- The Android guest's FSA servers (9002/9010/9016) accept unauthenticated
  Subscribe/Get/RequestResponse from the unprivileged shell (confirmed above).
- **[C] No authentication at the FSA protocol/app layer — jadx RE + live
  validation (2026-09).** The accept loop caps clients at 6 and dedups by
  source IP; the only gates ever checked **inside the FSA code itself** are
  equality of `serviceId`/`instanceId` against constants that are public in
  every FSA client APK. There is no TLS, no crypto, and no allow-list *in the
  protocol*. **Live-proven on the `gm_emu` emulator:** an anonymous vlan5 TCP
  peer sent one 22-byte fkt120 SUBSCRIBE frame (`opType=674`) and the real
  cluster service subscribed it to StateOfHealth and streamed live HEARTBEAT
  data; a follow-up GET (`opType=421`) returned a live property value. Tools:
  `~/gm_emu/ae/{fsaprobe,fsalisten4}` (raw-syscall `connect`/`accept4` to
  bypass the netd fwmark handshake, required because the emulator has no
  default data NIC). Full writeup:
  [`../research/AE_RESEARCH_HANDOFF.md`](../research/AE_RESEARCH_HANDOFF.md).

  **History (corrected 2026-11-11, per the Y175_2026-11-02 external Bus 2 tap
  bench finding):** the emulator result above was captured on `gm_emu`, which
  runs the real FSA/Android binaries but has no default data NIC ("no real bus
  and no real peers", `research/AE_RESEARCH_HANDOFF.md:184`) and so does not
  reproduce the physical radio's kernel-level `iptables` firewall. A live Y175
  bench tap (full 1–65535 scan from the external wire, 2026-11-02) found 9002
  and 9016 on the **real radio** are gated by a source-IP allowlist
  (`{.106,.109,.112}` and `{.102,.112}` respectively) — a non-allowlisted
  source gets no TCP reply at all, before any FSA frame is parsed. The two
  results do not contradict: the FSA **protocol itself** has zero app-layer
  authentication, true on both emulator and real radio (this file's own
  frame-format analysis confirms it independent of either test); but the
  **physical radio** additionally fronts the exposed FSA ports with a
  network-layer (netfilter) source-IP gate that the emulator does not model.
  Net effect: "any client that can reach a CSM FSA port can speak it" remains
  true as a protocol statement, but is no longer true as a *real-radio network
  reachability* statement for 9002/9016 specifically — reaching those two ports
  from the external wire now requires an allowlisted source IP. Whether other
  FSA-hosting ports/instances (vlan4, other partitions) carry the same gate is
  unverified; see `research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt` and
  `T1_RADIO_NETWORK_STRUCTURE.txt` (external bench corpus, not in this repo;
  path recorded in `research/GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md:382`)
  for the full allowlist table.

### [F-inject] Cluster-injection surface

`REQUEST`/`REQUESTRESPONSE` (`opType=641`/`674`) for `fktId >= 700` dispatch
straight into `ClusterViewManager` via the method handler, with no additional
gate beyond the service/instance check above: `712` `CLIENTFOCUS` (moves
cluster focus), `700`/`714` asset state, `707`/`708`/`710`/`711`/`713`/`715`
widget data, `720`/`721` activity indicator. Any anonymous peer that can reach
`9002` can drive the instrument cluster, pending each individual method's
protobuf field validation (not yet examined per-method).

**History (corrected 2026-09):** prior revisions of this doc (and of
`vehicle_network.md`, `emulator.md`, `research/AE_RESEARCH_HANDOFF.md`) stated
this surface fires via `EVENT`/`opType=1032`. That was wrong. Deobfuscated FSA
service library RE (`com/gm/fsa/service/`, cross-checked against
ClusterService's router `f/d.java`, `f/h.java`, `h/b.java`) shows `opType 1032`
(Event) in the router only ever drives `OfferService`/discovery multicast
logic — it never reaches `ClusterViewManager`. The cluster methods dispatch via
the method handler on `REQUEST`/`REQUESTRESPONSE` only, matching this doc's own
live-verified shell session above (`rmIdentification`/`clientFocus` both used
`opType=0x02a2=674`).

Ranked severity and Phase-2 plan:
[`research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).

### [F-udp] UDP/multicast discovery-listener crash (AIOOBE) — HIGH, unauthenticated

`NetCommsService.DiscoveryListenTask.SocketRead()`
(`com/gm/fsa/service/NetCommsService.java:212-258`) + the `FSAMessage(byte[])`
constructor (`FSAMessage.java:55-77`) — compiled into every FSA-hosting app
(9002/9010/9016/etc, shared library). The UDP receive buffer is a **fixed 256
bytes** (`NetCommsService.java:214`), reused every iteration, joined on
multicast group `239.192.0.1` at the port given by the `FSACatalog.java:97,115`
constant (**3000** in the decompiled source — see [Open Conflicts](#open-conflicts)
for the discrepancy against the live-scanned 30490). `FSAMessage` reads
`payloadLength` from header bytes 16-19 (attacker-controlled int32), then does
`new byte[payloadLength]; System.arraycopy(data, 20, bArr, 0, payloadLength)` —
`data` is always the 256-byte UDP buffer regardless of actual datagram size.
`payloadLength` in `[237, allocatable-range]` overruns the 256-byte source
array. The `arraycopy` is wrapped in
`catch(NegativeArraySizeException){}catch(OutOfMemoryError){}` but **not**
`catch(ArrayIndexOutOfBoundsException)` — the AIOOBE escapes uncaught, and
`DiscoveryListenTask.run()` (`NetCommsService.java:221-238`) only catches
`IOException` — no RuntimeException/Error handler — so the escaping AIOOBE
kills the discovery-listener thread **permanently** (process survives, SOME/IP-SD
discovery is dead for that process from then on). Contrast: the TCP ingest path
(`FSAServiceConnectedClient.java`) sizes its buffer correctly
(`new byte[20+payloadLength]`) and its `run()` does catch RuntimeException — the
bug is unique to the UDP/multicast path. Unauthenticated: connectionless,
spoofable source, no client-slot cap, no dedup (those only exist on the TCP
accept loop). Blast radius: every FSA-hosting process on the vlan5 segment
joins the same multicast group — one spoofed packet kills discovery in all of
them simultaneously. PoC shape (Phase 2, needs a UDP sender —
`fsaprobe`/`fsalisten4` are TCP-only): 20-byte datagram to `239.192.0.1:3000`
(or `:30490`, verify empirically which the real radio binds before building
the PoC), bytes 16-19 = large `payloadLength` (e.g. `0x00001000`).

### [F-udp-inject] UDP/multicast connectionless FSA injection bypasses all gates — HIGH

Same UDP ingest path as above: `DiscoveryListenTask.SocketRead()` builds an
`FSAMessage` and queues it with `sender=null` (`NetCommsService.java:253`)
**without ever calling `validateHeader()`** — that check (the only place
serviceId/instanceId equality is enforced, see the `[C]` note above) exists
only on the TCP path (`FSAServiceConnectedClient.java:253-260`). The message
router dispatches purely on opType+functionId, never re-checking serviceId. A
spoofed/forged multicast UDP datagram can therefore drive the same
unauthenticated cluster-injection primitives as the TCP path above (opType
641/674, see the `[C]` correction), but connectionlessly, spoofably, without
consuming one of the TCP accept loop's 6 client slots, and without the
source-IP dedup that gates TCP. Payload capped at 236 bytes (256-20 header) —
fits `clientFocus`/`screenRequest`/`listSlice`/`activityIndicator` protobuf
payloads. Open item: needs live confirmation that state-mutating (not just
request-response) handlers actually fire with a null sender — fire-and-forget
EVENT/SET handlers are the most likely to work since they don't depend on
responding to sender. Ranked writeup:
[`research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md`](../research/security/AAOS_OFFENSIVE_AUDIT_PHASE1_SEP2026.md).

### [F-bugs] Two FSA parser bugs (shared code, both `9002` and `9016`)

1. **Unbounded allocation / RAM-DoS.** `payloadLength` (signed int32, offset
   16) is checked only for `>= 0`, so a single 20-byte header with no payload
   can declare a length up to ~2 GiB and drive `new byte[20+len]`; the
   allocation is caught by `catch (OutOfMemoryError)` so the process survives.
   **Live-proven DoS (2026-09):** one 20-byte frame with `payloadLength =
   0x40000000` (no payload bytes sent) forced the real `com.gm.cluster`
   process to attempt a 1,073,741,856-byte allocation —
   `"Forcing collection of SoftReferences for 1024MB allocation"` + blocking
   GCs → `OutOfMemoryError` caught. Repeatable at one cheap packet per shot:
   a GC-stall + soft-cache-flush DoS against the cluster process, no crash.
2. **Framing desync on rejection.** When `serviceId`/`instanceId` fails the
   equality check, the payload bytes already on the wire are **not drained**
   before the next read — the next 20 bytes are misread as a header, putting
   the connection into permanent TCP framing desync for its remaining
   lifetime.

### [P] ProgrammingMaster (9011) is dead code

The FSA catalog above is a **static compiled-in table**, not a live picture of
what runs. `ProgrammingMaster` (serviceId 1006, fktId cluster 201–231, catalog
port 9011) is compiled into the CSM image but the class is **never
instantiated** in any decompiled app on this build, and port 9011 is never
bound — a live scan sees only `9002`/`9010`/`9016` LISTEN. This resolves the
earlier "why doesn't the live scan show a 9011 server?" contradiction between
the static catalog and the live-scan port list: Global-B demoted infotainment
from Programming Master to HMI-only (see
[`ota_programming_roles.md`](ota_programming_roles.md)), and the catalog
simply was never pruned of the dead entry. Independently corroborated (not
re-derived) by [`ota_update_stack.md`](ota_update_stack.md) and
[`ota_programming_roles.md`](ota_programming_roles.md), which both cite this
section as the source finding.

---

## Open Conflicts

- **SOME/IP-SD discovery port: 30490 vs 3000.** The intro and Service Catalog
  state UDP **30490** (live Y181 network scan, confirmed empirically on the
  real radio). The `[F-udp]` finding's code citation (`FSACatalog.java:97,115`,
  decompiled) hard-codes UDP **3000**. No dated correction reconciles these —
  it is unresolved which value the live radio actually binds for discovery
  vs. what the inspected code constant says, or whether the constant is
  overridden by config/build variant. Confirm empirically (packet capture on
  both ports) before building any UDP PoC against the discovery listener.

## Cross-References

- [`ethernet_networking.md`](ethernet_networking.md) — VLAN topology, listening ports,
  partition addresses, firewall posture
- [`ethernet_networking.md`](ethernet_networking.md) — consolidated VLAN/port/
  firewall reference (service→address mapping stays in this doc; general
  network topology lives there)
- [`projection/cluster_navigation.md`](../projection/cluster_navigation.md) —
  RemoteModuleHMI cluster nav pipeline, maneuver enum, CT5/QNX inter-VM FSA
- [`vip_ipc_ghs.md`](vip_ipc_ghs.md) — GHS INTEGRITY hypervisor, VP crash
  decode/semantics (raw bytes and full analysis live there, not here)
- [`ota_programming_roles.md`](ota_programming_roles.md) — who actually
  flashes what; Global-B HMI-only demotion behind the dead ProgrammingMaster
- [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)
  — the separate (non-FSA) UDS-over-TCP diagnostic channel on port 49156
- Source data: `enumeration/Y181/jun2026/raw/{logcat,open_ports,binder_services}.txt`
