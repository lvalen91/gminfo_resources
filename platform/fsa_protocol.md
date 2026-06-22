# GM FSA (Feature Service Architecture) Protocol

**Device:** GM Info 3.7 (gminfo37)
**Platform:** Intel Apollo Lake (Broxton), Android 12 guest under GHS INTEGRITY
**Research Date:** June 2026 (Y181 `W231E-Y181.3.2-SIHM22B-499.3`)
**Data source:** live ADB shell (uid=2000), `enumeration/Y181/jun2026/` capture, `DelayedWKSApp.apk` decompilation

> **Terminology.** GM's own code names this `com.gm.fsa.service` ("FSA"). The
> jun2026 logcat shows `FSAServiceConnectedClient`, `FSANetCommsService9016`,
> `FSAProperty`, `FSAServiceEventHandler` etc. and the literal log line
> *"FSA: Read Header size 20"*. The expansion **Feature Service Architecture**
> is used here. [`platform/networking.md`](networking.md) refers to the same
> layer as **NFSA (Network Function Service Architecture)** — they are the same
> protocol; `com.gm.nfsa.*` is the cluster-side Java package name (see
> [`projection/cluster_navigation.md`](../projection/cluster_navigation.md)).

FSA is GM's proprietary service-oriented middleware running over TCP between
hypervisor partitions on the vehicle backbone (VLAN 5, 192.168.1.0/24). Each
message is a **20-byte big-endian binary header** followed by a **Protocol
Buffers** payload. Service discovery uses SOME/IP-SD multicast
(`239.192.0.1:3000`).

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
is a frame sync/magic value used to validate framing (matches the cluster wire
format documented in `cluster_navigation.md`). The 20-byte header size is
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
| 9011 | ProgrammingMaster | 1006 | CSM (.100) |
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
| 3000 | SOME/IP-SD multicast | — | `239.192.0.1` group |

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

### NetworkAccessManager (NAM — serviceId 1026, CSM port 9016)

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

**Live results (bench, off-network):**
- `provideNetworkList` (fn2602): 1 entry — `display="None"`, `networkType=0`
  (`NAM_NONE`). Raw: `0a 0c 0a 08 08 00 12 04 4e 6f 6e 65 10 00`.
- `networkStatus` (fn2604) subscribe `08 AC 14` → `{functionID:2604,
  successful:true}`; no events in 10 s. **Varint:** 2604 = `0xAC 0x14` (not
  `0xCC 0x14`).
- `getControlledECUList` (fn2607, GET): empty — Android NAM controls no ECUs.
- `networkRequest` (fn2601, CELLULAR/WIFI, APID="CSM"): no Response (off-network).

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
"connection refused"). When the vehicle is on it exposes:

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

From the FSA-annotated message classes in `DelayedWKSApp.apk`.

**`NetworkRequest_request_response`:** 1 networkType (enum 1=WIFI,2=CELLULAR);
2 aPID (string, e.g. "CSM"); 3 priority (enum/uint); 4 requestHandle (uint32).

**`ProvideNetworkList_request_response` / `_response`:** request 1 networkType
(filter); response 1 networkList (repeated) { 1 networkName{1 display string};
2 networkType enum 0=NAM_NONE,1=WIFI,2=CELLULAR }.

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

Raw response payload (63 bytes):
```
0a 3b 12 13 31 39 37 30 2d 30 31 2d 30 31 20 30 30 3a 30 33 3a 31 39
1a 24 56 50 20 46 61 69 6c 75 72 65 20 49 44 3a 20 30 30 37 2c 20 45
72 72 6f 72 20 49 44 3a 20 30 78 30 43 30 33 10 01
```

Decoded `ReadECUResetInfo_status`: field 1 `eCUResetInfo` { 2 timestamp
`"1970-01-01 00:03:19"` (epoch+199 s, clock unset at crash); 3 reason
**`"VP Failure ID: 007, Error ID: 0x0C03"`** }; field 2 = `1`.

**Interpretation:** "VP" = **Virtual Processor** in the GHS INTEGRITY
hypervisor. The Visteon IPC logs GHS partition (VP) crashes — VP 007 failed with
`0x0C03`. This confirms the IPC partition has **visibility into hypervisor VP
failure events**. Open: correlate VP 007 with a partition name
(`/dev/hvc*`, `/vendor/etc/init/*.rc`); decode `0x0C03` (likely an INTEGRITY
kernel error code). See [`research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md`](../research/GHS_INTEGRITY_COMPREHENSIVE_ANALYSIS.md).

---

## Security Notes

- The FSA wire layer has **no authentication** — constant magic `0x5AA5` + length
  field only; peer identity is inferred from source IP and enforced (where at all)
  by `iptables` (INPUT policy DROP) and the single-client limit, not by the
  protocol. Any client able to reach a CSM FSA port and not blocked by the
  firewall can speak it. See `projection/cluster_navigation.md` for the
  (unverified) cluster-injection topology analysis and
  `research/security/GM_AAOS_Y181_SECURITY_ANALYSIS.txt` for the broader posture.
- The Android guest's FSA servers (9002/9010/9016) accept unauthenticated
  Subscribe/Get/RequestResponse from the unprivileged shell (confirmed above).

## Cross-References

- [`platform/networking.md`](networking.md) — VLAN topology, listening ports,
  partition addresses, firewall posture
- [`projection/cluster_navigation.md`](../projection/cluster_navigation.md) —
  RemoteModuleHMI cluster nav pipeline, maneuver enum, CT5/QNX inter-VM FSA
- [`diagnostics/ethernet_uds_diagnosticsd.md`](../diagnostics/ethernet_uds_diagnosticsd.md)
  — the separate (non-FSA) UDS-over-TCP diagnostic channel on port 49156
- Source data: `enumeration/Y181/jun2026/raw/{logcat,open_ports,binder_services}.txt`
