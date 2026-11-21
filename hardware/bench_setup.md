# Bench hardware setup baseline

Validated 2026-11-15. This is the owning reference for bench hardware configuration
and access acceptance checks. Private addresses, device serials and host identities
are intentionally represented by placeholders. No packet, Android logcat, UART-event
or CAN-payload recording is required to establish this baseline.

**Current runtime override (2026-11-17):** the radio is running native
`7.3.5-probe-stable02`, with USB ACM shell and volatile T1/VLAN-5 root SSH,
rather than stock AAOS/ADB. The active bench experiment uses the previously
verified minimal CAN `0x529` keepalive, not the listen-only acceptance-test
configuration below. Wiring and adapter identity remain baseline facts; do not
interpret the older access-mode table as the current process state. See the
[current build/boot record](../research/GHS_BOOT_UPDATE_RECOVERY_ANALYSIS.md#linux-735-stable02--verified-2026-11-17).

## Hardware and wiring

| Component | Identity | Baseline connection/configuration |
|---|---|---|
| Radio | A11 GM Info 3.7 | Bench 12 V supply; harness MCU can be disconnected for direct CANable tests; USB ADB and automotive Ethernet available |
| Harness | **OPU Wiring Tester + Emulator, GM 85633185, HMI 3.7–3.8** | Existing repo identification; X5 p1/p3 power/ground, X6 p9/p10 CAN, X7 LVDS display |
| T1 host adapter | Realtek USB Gigabit Ethernet, USB `0bda:8153` | macOS `en12`, connected through the automotive-T1 path; observed host link 100baseTX full-duplex |
| UART adapter | Silicon Labs CP2102 USB-to-UART, USB `10c4:ea60` | macOS `/dev/cu.usbserial-0001`; RX-only connection to RH850 transmit output |
| CAN adapter | CANable gs_usb, USB `1d50:606f` | Tap on harness ↔ radio CAN 5; classic CAN, **500,000 bit/s**, hardware listen-only |

Harness identity and cavity assignments are owned by
[connectors.md](connectors.md), particularly its “Two as-wired datasets” note.
That note describes the harness itself as having no X11 Ethernet wiring; the
separate T1 bench connection is additional to that harness. The exact T1 media
converter make/model and current radio-end tap pins have not been established
by this baseline. Do not infer the automotive bus number from host interface `en12`.

CAN 5 is the X6 p9/p10 pair, also called SER DATA 5; see
[vehicle_network.md](../platform/vehicle_network.md#plane-1--can-from-the-dps-scan).
Connect CAN H, CAN L and **CANable GND directly to radio X5 pin 3 (Signal GND)**.
The owner reported successful script-driven radio operation with that signal-ground
connection after trying other ground points; chassis ground is not a substitute
for establishing this bench reference. The owner measured **60 ohms across H/L
with the CANable termination switch at E**. Resistance checks require power off;
60 ohms is consistent with two 120-ohm terminators in parallel. The complete
termination topology has not been independently traced. An already terminated
bus should not acquire a third terminator.
See the [CANable wiring guide](https://canable.io/getting-started.html).

## T1 Ethernet and ADB

The working host configuration is **VLAN 5 on en12**, exposed as `vlan0`, with
a static host address in the radio's service subnet. Keep the native adapter's
existing configuration; do not add an Internet default route for this bench link.

Supply these values privately, in memory:

| Placeholder | Meaning |
|---|---|
| `<BENCH_HOST_IP>` | Unused host address specifically allowed by the radio's VLAN-5 firewall for TCP 9040 |
| `<RADIO_T1_IP>` | Radio's current VLAN-5 address |
| `<BENCH_NETMASK>` | Service-subnet mask |
| `<USB_SERIAL>` | Radio's USB ADB serial, only needed when multiple USB devices are connected |

Inspect `ifconfig en12` and `ifconfig vlan0` before setup. If `vlan0` is absent:

```sh
sudo ifconfig vlan0 create
sudo ifconfig vlan0 vlan 5 vlandev en12
sudo ifconfig vlan0 inet <BENCH_HOST_IP> netmask <BENCH_NETMASK> up
```

If it already exists, verify its parent/tag before using it. An existing `vlan0`
on another parent is not this configuration. These `ifconfig` changes are runtime
settings; they are not a persistent network-service profile.

Validate USB ADB with `adb -d shell id -u`: expected UID **2000**. When more than
one USB ADB device is connected, use `adb -s <USB_SERIAL>` instead of `-d`.
Check Android epoch time and timezone against the Mac before time-sensitive work.
If drift exceeds about 90 seconds, set Android with `cmd alarm set-time` using
the Mac's epoch milliseconds and `cmd alarm set-timezone` using the Mac's timezone.
The RH850's own calendar is separate and is not corrected by Android clock sync.

Enable network ADB through the authorized USB transport:

```sh
adb -d tcpip 9040
```

**9040 is the verified bench port; 9060 is not the established baseline.**
The radio's shipped policy also checks source address and VLAN. Listener startup
alone is insufficient. The working fallback is a TCP relay bound to host loopback
port **19040**, with its outgoing socket explicitly bound to `<BENCH_HOST_IP>`
and connected to `<RADIO_T1_IP>:9040`. Keep the relay listening only on loopback.
Then use:

```sh
adb connect 127.0.0.1:19040
adb -s 127.0.0.1:19040 shell id -u
```

Acceptance: both USB and T1 return UID 2000, and their
`/proc/sys/kernel/random/boot_id` values match when compared in memory. Do not
save those identifiers. ICMP ping is not the acceptance test: the shipped firewall
can block it while a permitted TCP path works. The relay is a host runtime process,
not a persistent service; port and transport availability must be rechecked after
a radio restart. See [ethernet_networking.md](../platform/ethernet_networking.md#4-listening-ports-and-network-adb).

## UART baseline

Use **115200 baud, 8 data bits, no parity, 1 stop bit**. Disable software,
RTS/CTS and DSR/DTR flow control. Set DTR and RTS low before opening the port.
The CP2102 RX input observes RH850 TX; do not connect/transmit from adapter TX
for this baseline. The repo identifies the VIP console as owner-reported RH850
physical pin 52, P1_9/RLIN34TX; that attribution is not a new physical trace result.
See [the UART pinout reference](teardown.md#rh850f1k-package--uart-pinout).

Only one process should own the serial port. A receiver can count bytes, newlines
and printable characters in memory without writing event logs. A **35-second**
acceptance sample received **138 bytes / 3 newline characters**, **100% readable
ASCII**, and no serial read errors. Runtime output may be sparse; silence over
a short window alone is not a failed connection. Both UART open/read and USB ADB
worked under the normal user account, without sudo.

## CAN baseline and stability acceptance

The gs_usb adapter reports a **48 MHz CAN clock**, feature mask `0xf3`, and
listen-only support. Configure **500,000 bit/s**, **87.5% sample point**, and
mode flags **`0x11`**: listen-only (`0x01`) plus hardware timestamps (`0x10`).
These settings decoded the current bench traffic successfully. No transmit,
replay, bus wake-up or test-frame operation is part of this baseline.

Working userspace dependencies: Python with `pyusb`, `gs-usb` **0.3.1** and
`libusb-package` **1.0.30.1**. The validated temporary environment is
`/tmp/bench-listeners-venv`; recreate it if `/tmp` is cleared. Select the adapter
by USB VID/PID, not an assumed serial port: gs_usb is a USB protocol, not SLCAN.

For this macOS adapter, `usb.util.claim_interface(device, 0)` succeeds as the
normal user. The accepted initialization sequence is:

1. Discover `1d50:606f` with the packaged libusb backend and claim interface 0.
2. Issue gs_usb MODE RESET (request 2, little-endian mode/flags `0,0`).
3. Set HOST_FORMAT (request 0, little-endian `0x0000beef`).
4. Confirm listen-only support and set 500 kbit/s timing. At 48 MHz the validated
   segments are prop=1, phase1=12, phase2=2, SJW=1, BRP=6.
5. Issue MODE START (request 2, little-endian mode/flags `1,0x11`).
6. Drain receive endpoint `0x81`; retain no payloads. Treat USB timeouts as idle,
   count CAN error frames and receive-overflow flags separately, and report USB
   exceptions rather than silently converting them into “no traffic.”
7. On exit, issue MODE RESET and release the USB interface.

The stock `gs-usb` 0.3.1 `start()` path resets the USB device and attempts kernel
driver detachment; that path failed with
`usb.core.USBError: [Errno 13] Access denied (insufficient permissions)`.
Direct interface claiming and explicit control requests above worked without
detaching a driver or elevating privileges. Do not start through a library path
that briefly enters normal/active CAN mode before selecting listen-only.

Acceptance sample: **60 seconds**, **8,458 valid received frames**, **70 unique
IDs**, **zero reported CAN error frames**, **zero receive-overflow flags**,
**zero malformed frames**, **zero USB read errors**. Consecutive 10-second bins
contained **1409, 1410, 1409, 1410, 1409, 1410** frames. This establishes stable,
decodable 500-kbit/s traffic for the observed powered bench state; it does not
establish cold-start behavior or independently identify each transmitting node.
A shared tap observes both directions; CAN IDs alone do not prove sender identity.

The baseline listener remains in hardware listen-only and discards payloads.
It does not append CAN-message files. A second application cannot assume it can
claim the same USB interface while this listener owns it. Cangaroo was not
installed or used to establish these results.

## macOS privileges and persistence

macOS does not use Linux udev rules. No USB permission rule or sudo grant was
needed for the CANable's working interface-claim path, the CP2102, or USB ADB.
See the [libusb macOS FAQ](https://github.com/libusb/libusb/wiki/FAQ).

Creating/changing VLAN interfaces and host IP configuration requires administrator
authorization. Ordinary TCP access does not inherently require root. On this host,
the normal-user source-bound T1 socket returned
`OSError(65, 'No route to host')`, while the same source/destination through the
privileged relay worked. This is consistent with macOS Local Network privacy;
permission attribution has not yet been independently confirmed or resolved.
Do not treat it as proof of a missing route or a USB driver permission failure.

**Baseline decision, 2026-11-15:** retain sudo for T1 configuration and the
source-bound relay. Adding the signed Codex executable through Local Network's
add button produced no error but no visible list entry, as reported by the owner.
An effective permission grant was not established. Further Local Network
permission troubleshooting is deferred; sudo-free T1 access is not an acceptance
requirement for this baseline. CANable, UART and USB ADB remain unprivileged.

**Revalidated, 2026-11-17:** a source-bound T1 client launched with
`sudo -n /usr/bin/python3` completed three bidirectional diagnostic exchanges:
`3E00 → 7E00`, `22F181 → 62F181…`, and `22F0F1 → 62F0F10000`.
The existing interface and route configuration were retained, and the CAN
harness remained active. This establishes working T1 transmit/receive through
privileged execution; it does not establish that normal-user Local Network
permission has been repaired. Use the privileged source-bound client/relay for
bench testing until that separate permission issue is resolved.

Review **System Settings → Privacy & Security → Local Network** for the responsible
app/executable. macOS 27.2+ provides add/remove buttons; this host is on 27.3.
Adding a CLI executable may still require resolving the responsible app identity.
Apple documents automatic access for Terminal/SSH command-line tools and root,
while launch agents differ from system daemons. A Terminal-launched source-bound
relay is a candidate way to avoid sudo for ongoing data access; it has not yet
been validated on this host. Do not add broad sudoers grants or disable privacy
controls as part of this baseline. See
[Apple TN3179](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy).

The VLAN configuration and listener/relay processes are runtime state. Reapply
and verify after a host restart, USB re-enumeration, or bench power cycle; interface
and serial-port names may change. Persistent network-service settings, launch
services and permission grants have not been installed by this baseline.

### USB enumeration observation during CAN tests

A separate runtime macOS USB watcher polls the I/O Registry with a 0.5-second
delay between snapshots, alongside the passive ADB transport observer. It records
attachments, detachments and USB interface/configuration changes in
`/tmp/bench-usb-events.jsonl` with Mac wall/monotonic timestamps. New attachments
and configuration changes emit `USB_ALERT_*` output for review at each test step.
This detects unknown USB modes even when they do not enumerate as ADB. Polling
can miss enumerations shorter than a snapshot interval; the delay excludes the
time needed to obtain each snapshot.

Recorded fields are VID/PID, USB class/subclass/protocol, generic role and an
ephemeral instance label. Serial numbers, raw product/manufacturer strings and
USB location/registry IDs are omitted; registry identity and port comparison
remain in memory. Events are mode 0600. The initial watch baseline contained
the two hubs, Realtek, CP2102 and CANable, with no radio USB device present.
The watcher is a runtime process, not an installed persistent service.

### Controlled physical power cycling

The bench supply is now connected through a HomeKit smart outlet, controlled
by a locally configured macOS Shortcut. The `shortcuts run <SHORTCUT_NAME>`
path was tested with the unloaded outlet, then used to power the connected radio;
fresh RH850 UART output confirmed the latter power-on. The local accessory and
shortcut names are intentionally omitted from this reference.

One invocation toggles the outlet's current state; it is not an idempotent On
or Off command. Establish the actual starting state before the first invocation
and track completed transitions. Enforce **at least 10 seconds after a toggle
completes before issuing the next toggle**, as required for this bench supply.
Arm UART/CAN observation before power-on and stop application TX before power-off.
A timeout or uncertain result leaves the power state unknown; reconcile it before
another toggle rather than retrying a non-idempotent action automatically.

## Harness replacement candidate

The [CAN message reference](../platform/can_network.md) owns the captured-ID
dictionary, harness isolation evidence, and external signal-definition candidates.

The [CAN bench emulator tool](../research/tools/can_bench_emulator.py) can inspect
an isolated-harness JSONL capture and replay its fixed cyclic pattern. The
[terminal launcher](../research/tools/run_can_bench.sh) runs continuously until
Ctrl-C and reports errors without terminating on hardware faults. It deliberately
enables normal CAN transmission and requires exclusive ownership of the CANable.
`inspect` uses no USB access.

With radio CAN disconnected, the harness continued transmitting **32 fixed-payload
11-bit IDs** in a repeated **approximately 320-ms cycle**, one frame approximately
every **10 ms**. The payloads matched the same IDs in the radio-connected trace.
A harness-only power cycle produced a **23.17-second observed quiet gap** and then
the same 32 IDs/payloads; no additional startup command was observed. The first
post-gap frame was `0x145`. This does not prove an invariant starting phase under
every reset or identify the minimal subset needed to wake the radio.

In the earlier disconnected interval, a listen-only CANable left the harness
without an acknowledging peer: the recorded tail repeated `0x458` about 3,800
times/s. Enabling CANable acknowledgement restored the approximately 100-frame/s
loop. This establishes acknowledgement-dependent transmission behavior, not an
application-level command/response protocol. Forty IDs from the connected startup
trace disappeared when radio CAN was disconnected; subsequent radio-only RX
captures confirmed all 40 as radio-originated. See the owning CAN reference for
the later ACK-controlled repetition and power-state tests.

Launch from the repository root:

```sh
./research/tools/run_can_bench.sh
```

The installed runtime is `~/.local/share/gminfo-bench/venv`. The compact local
profile is `~/.local/share/gminfo-bench/harness-profile.json` (mode 0600). The
launcher does not depend on `/tmp`: captured payloads remain outside the repository.
The exported profile reproduces all 32 IDs/payloads and their measured offsets in
a **320.270-ms cycle**, anchored at `0x145`. Source code embeds no captured payloads
or private device identifiers. To regenerate the profile from an isolated capture:

```sh
~/.local/share/gminfo-bench/venv/bin/python research/tools/can_bench_emulator.py export-profile --capture /path/to/harness-only.jsonl
```

If rebuilding the local environment, use `uv venv ~/.local/share/gminfo-bench/venv`
and `uv pip install --python ~/.local/share/gminfo-bench/venv/bin/python gs-usb==0.3.1 libusb-package==1.0.30.1`.

Before replay, stop the process currently owning the CANable, disconnect the
original harness MCU from CAN, and connect the powered radio and CANable with
appropriate bus termination. Keep the radio's power/ground supply intact.
Replay follows the captured schedule without waiting after every USB transmit
echo. It bounds the outstanding queue and avoids catch-up bursts after a delay.
USB/OS scheduling jitter, missing acknowledgement and physical bus errors can
delay on-wire delivery; software cannot preserve successful bus timing through
those faults.

The terminal reports missing ACKs, controller warnings, overflows and periodic
counts for queued frames, adapter TX echoes, received data, errors and recovery
attempts. TX echoes are adapter records, not independent proof of peer acceptance.
Bus-off, USB failures and missing transmit echoes reset/reopen the adapter, wait
one second, and restart from the first captured frame. Before normal replay,
supported adapters drain stale firmware work in silent internal loopback; this
prevents old unacknowledged frames from blocking the new sequence. A MODE or USB
reset alone may leave software TX work queued. Recovery-internal frames are not
sent on the external bus. Repeated status messages
are rate-limited while error counts continue to accumulate. The process retries
until Ctrl-C; invalid profiles or missing software dependencies must be corrected
before transmission can start. `--status-interval 2` changes the summary interval.

Ctrl-C resets the adapter and releases USB ownership. Optional `--duration 60`
limits a run. Replay starts no capture, UART, ADB or background transmit service.

Offline validation: **19 tests** cover profile validation, captured ordering and
timing, hardware-timestamp wrap, power-cycle segment selection, delayed/missing
TX echoes, USB loss, bus-off, malformed frames, warning/overflow reporting,
missing-adapter retries, and actual process SIGINT/SIGTERM cleanup using fake USB
discovery, plus silent queue drain and reset-on-nonquiescent-drain behavior.
Subsequently, the owner reported the radio up and running through the
launcher with CANable GND on X5 pin 3, then cancelled the script and powered the
radio off. This is an owner-reported working configuration, not an independent
duration or power-mode measurement. Later isolated `529` testing sustained
operation for over 12 hours and identified a conditional b1 bit 7 On/Off
selector, plus `4DA` b7 bit 0 DriverDoorOpen for state-dependent shutdown;
see the [current CAN findings](../platform/can_bench_experiments.md#door-wake-and-explicit-shutdown-paths--2026-11-16).
Later observation with no application TX showed a timeout path through
LocalInfotainment, HmiInactive and Sleep, then ADB disconnection and an explicit
SoC power-level-0 report approximately 694 seconds after TX stopped. No Off payload
was sent; this is a timeout shutdown, not a validated immediate Off command. See
the [correlated shutdown timeline](../platform/can_bench_experiments.md#door-wake-and-explicit-shutdown-paths--2026-11-16).
The later [single-cycle comparison](../platform/can_bench_experiments.md#radio-only-single-cycle-result)
left the display off despite SoC-origin power-level reports and an HMI-ready UART
event. UART readiness must not be treated as proof that AAOS or the display is on.
