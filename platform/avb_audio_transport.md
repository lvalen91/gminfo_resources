# AVB Audio Transport (gPTP / AVTP AAF / VLAN 2)

Scope: the radio-to-amplifier audio path: gPTP, IEEE 1722 AVTP AAF streams and TSCF control on VLAN 2, the
AAOS usage-to-bus-to-wire-position mapping, the firmware audio stack (AVB StreamHandler, early AVB audio, local
TDF8532 I2S alternative), and what a replacement endpoint still lacks.
Not here: VLAN 4/5 tables, switch config, physical bus map ([ethernet_networking.md](ethernet_networking.md)); panel, touch, serdes
display chain ([hardware_specs.md](hardware_specs.md), [pi_swap_feasibility.md](pi_swap_feasibility.md)).

Evidence tags: **[confirmed-fw]** seen in extracted Y181B firmware; **[confirmed-vehicle]** owner's real radio-removal
test; **[confirmed-service]** GM ALLDATA / prior repo docs; **[inferred]** / **[general]** platform knowledge, not
vehicle-specific. Measured wire results carry their capture date (2026-11-15 unless noted); "configuration evidence"
means policy/config text, not a measured playback.

Related: [ethernet_networking.md](ethernet_networking.md), [vehicle_network.md](vehicle_network.md),
[hardware_specs.md](hardware_specs.md), [pi_swap_feasibility.md](pi_swap_feasibility.md),
[vehicle_config.md](vehicle_config.md), [emulator.md](emulator.md), [fsa_protocol.md](fsa_protocol.md),
[AAOS Audio Probe](../research/tools/aaos_audio_probe/README.md),
[UDS live-control reference](../diagnostics/diagnosticsd_protocol.md#live-bench-controls-2026-11-15).

## 1. Summary and inventory

Audio recovery and usage-mapping measurements are dated 2026-11-15. Hardware/software inventory and earlier
captures retain their own dates; not every item below was freshly measured on that date.

- **NIC:** Intel I210, 1 Gbps (only `I210` appears in artifacts; `WGI210CL` marking is prose-only; "I211" was an unverified near-twin reading, see `hardware/teardown.md`).
- **gPTP role:** configured grandmaster; wire transmission observed, elected role not independently decoded (see 2).
- **AVB streamhandler:** v3.2.7.2 (GM3/CSM).
- **External audio endpoint:** Bose amplifier (`.103 = AMP_ETH`, owner-confirmed; vlan5 table in [ethernet_networking.md](ethernet_networking.md)). Physical speaker count and the correspondence between AVTP sample positions and speaker outputs are unverified; the earlier four-speaker claim was not supported by the capture.
- **Physical pair:** GM service data names Ethernet bus **6** (circuits 7214/7215) = A11 to T3 Bose amp, "the AVB audio pair" [confirmed-service]. Full bus map: [ethernet_networking.md](ethernet_networking.md) (Physical Automotive-Ethernet bus map).
- **Audio-output buses (live `media.audio_policy`, 2026-11-15):** 12 (numbers 0-8 and 11-13). `audio_zones` is unverified: logical buses do not establish zone count. Occupant zones: driver_only. (TS L266-294 `android_automotive` block.)

## 2. gPTP

Firmware configures the IHU as gPTP grandmaster for the AVB domain feeding the external Bose amplifier
(`igb_avb.ko`; `daemon_cl -GM`, `audio` group; TSN Tspec; see [vehicle_network.md](vehicle_network.md) Automotive Ethernet). Captured gPTP frames prove
transmission, but packet presence alone does not establish elected grandmaster status (corrected evidence scope, 2026-11-15).

**Live confirmation of transmission (2026-11-13).** The configured role was previously grounded in firmware structure,
not a direct capture. A live Bus 2 T1 tap capture saw **146 frames** from the radio's own MAC to the IEEE 802.1 PTP
multicast address `01:80:c2:00:00:0e`, confirming gPTP transmission. The same session decoded the VLAN 2 AVB flood
as **3 IEEE-1722 AAF audio streams + 1 TSCF/ACF control stream**, not a generic "4 audio channels." Source:
`source_notes/BUS2_DIRECT_T1_TAP_BREAKTHROUGH_2026-11-02.md` section 5 in the `Y175_2026-11-02` analysis tree.
Bus 2 (A11 to K56 gateway, circuits 4757/4758) tag-multiplexes VLAN 2 (PCP 2, AVB/TSN audio, ~2,900 pps flood, harmless
bench artifact) with VLAN 5 (PCP 1) and VLAN 4 (PCP 1) plus untagged native traffic ([vehicle_network.md](vehicle_network.md) open item 1).

gPTP frames are **untagged**, EtherType `0x88f7`, seen alongside tagged audio.

## 3. Live AVTP player audio recovery (2026-11-15)

**Audio payload recovered and matched to a known source.** While the owner looped `sample-55s.mp3` in the radio's Audio
Player, a 70-second live T1 observation decoded VLAN-2 IEEE-1722 AAF payloads in memory. Source MP3: stereo **44.1 kHz**,
duration **54.949887 s**. No raw packet file, Ethernet addresses or stream identifiers were saved with the audio artifacts.

Three AAF streams were present. The **768-byte-payload stream** had 52,448 packets over approximately 69.930 s;
51,745 packets contained nonzero data. The 512- and 128-byte-payload streams were entirely zero-filled during this
observation. All three streams had zero observed sequence discontinuities.

The active payload is **six interleaved signed 16-bit big-endian PCM positions at 48 kHz**, with **64 sample frames
per packet**, consistent with approximately 750 packets/s. Positions **1 and 2** carried the player audio; positions
3-6 were zero-filled. This describes payload positions, not a verified Bose speaker-position map. The generic
dissector's user-specified sample-rate / channel-count fields were insufficient: packing and rate were checked
against packet cadence and the decoded reference waveform.

**Sample-rate scope (2026-11-15).** The extracted audio policy configures the media output mix port and other named
output mix ports as 48 kHz PCM16; some device-port profiles also list lower rates. The 44.1 kHz source reaching T1 as
48 kHz confirms conversion somewhere inside the radio, but does not isolate the converting component. Higher-rate
media downsampling has not been tested. Neither the active transport rate nor the policy establishes the Bose
amplifier's maximum accepted rate or internal DSP/DAC rate. Source: extracted Y181 `pulled_files/audio_policy_configuration.xml`
in the existing `analysis/adb` enumeration tree.

**Waveform match.** The MP3 was decoded/resampled to 48 kHz for comparison. Aligned half-second windows at recovered
times **0, 10 and 30 s** had normalized waveform correlations **0.999960, 0.999923 and 0.999959**. This confirms the
player's audio reaches the external T1 stream; it is not merely an idle audio-format advertisement. It does not
establish which component originally brought up the transport or prove amplifier playback. A further half-second
comparison at recovered time **60 s**, after the player's loop transition, correlated **0.999939** after allowing an
additional **0.938104 s** timing offset, consistent with a short player loop delay; the AVTP sequence remained
continuous, so no transport packet loss was observed at that transition.

**Artifacts.** Audio-only outputs were created in the owner's `Downloads/T1_audio` directory: a 12-second stereo WAV
preview, a 69.930667-second stereo WAV, the full six-position WAV, individual active-position mono WAVs and the
unwrapped six-position `.s16be.pcm` payload. WAVs use 48 kHz signed 16-bit little-endian PCM for macOS playback;
amplitude was not normalized. macOS `afinfo` recognized the preview as a valid stereo Int16 WAVE file. The raw PCM file
contains sample payloads only, not Ethernet/AVTP headers or a directly replayable Bose wire stream. No exact physical
speaker-channel assignment or amplifier control/SRP procedure was recovered in this step.

## 4. VLAN, stream inventory and packet layout

| Captured traffic | Encapsulation | Measured content / limitation |
|---|---|---|
| AAF audio, subtype `0x02` | 802.1Q **VID 2, PCP 2**, EtherType `0x22f0` | Three distinct stream IDs; continuous PCM, including silence |
| TSCF, subtype `0x05` | 802.1Q **VID 2**, EtherType `0x22f0` | Small control frames; payload semantics unresolved |
| gPTP | **Untagged**, EtherType `0x88f7` | Clock traffic observed alongside tagged audio |

VLAN 2 audio is raw Ethernet AVTP, **not IP/UDP/RTP**. A UDP listener on the service VLAN cannot receive/decode it.
Stream IDs and destination MACs must be learned from the actual link; the size labels below are local aliases, not
fixed protocol-assigned stream numbers. Classification must include subtype, stream ID and declared payload length.

| Local stream alias | AAF payload bytes | Cadence | Packing evidence |
|---|---:|---|---|
| A768 | 768 | Approximately 750 packets/s | Validated 64 frames x 6 positions x 2 bytes, 48 kHz PCM16 BE |
| A512 | 512 | Approximately 750 packets/s | Silent; 64 x 4 x 2 is an **inference**, not validated channel packing |
| A128 | 128 | Approximately 750 packets/s | Silent; 64 x 1 x 2 is an **inference**, not validated channel packing |

Tagged A768 frame (offsets exclude preamble, start at destination MAC):

| Byte offset | Bytes | Field / observed value |
|---:|---:|---|
| 0 | 6 | `<AUDIO_DESTINATION_MAC>` |
| 6 | 6 | `<RADIO_SOURCE_MAC>` |
| 12 | 2 | TPID `81 00` |
| 14 | 2 | TCI `40 02`: PCP 2, DEI 0, VID 2 |
| 16 | 2 | EtherType `22 f0` |
| 18 | 1 | AAF subtype `02` |
| 19 | 1 | Observed flags `81`: stream-ID valid, timestamp valid |
| 20 | 1 | Sequence number, modulo 256 |
| 21 | 1 | Timestamp-uncertain/reserved byte; observed `00` |
| 22 | 8 | `<STREAM_ID>` |
| 30 | 4 | AVTP timestamp; wrap and validity must be handled |
| 34 | 1 | Format `04` (PCM16) |
| 35 | 2 | Raw rate/channel word `00 05` |
| 37 | 1 | Bit depth `10` (16 decimal) |
| 38 | 2 | Stream data length `03 00` (768) |
| 40 | 2 | Observed tail `00 06` |
| 42 | 768 | Interleaved PCM sample bytes |

The corresponding format/length/tail bytes (offsets 34-41) were `04 00 05 10 02 00 00 04` for A512 and
`04 00 05 10 00 80 00 01` for A128. A generic AAF dissector reports user-specified sample rate and five channels from
`00 05` **for all three**. That header interpretation conflicts with empirically validated A768 packing. Do not silently
rewrite the header as six channels or assume the final byte is a standardized channel count merely because its value
matches the observed packing. Preserve the raw bytes when implementing compatibility and resolve this vendor convention
before transmitting to an amplifier.

A768 payload addressing is `payload[2 * (6 * frame + position)]`, zero-based `frame=0..63`, `position=0..5`. Each signed
sample is big-endian. Illustrative **synthetic** sample frame:

```text
03 e8  fc 18  00 00  00 00  00 00  00 00
 +1000  -1000      0      0      0      0
   P1     P2     P3     P4     P5     P6
```

After removing Ethernet/VLAN/AVTP headers, concatenate complete payloads by stream ID and decode with this
interleaving. Do not include padding/FCS as PCM. A768's tagged frame is 810 captured bytes without FCS (18 + 24 + 768).
Sequence gaps require explicit handling; concatenation without gap handling shortens audio and corrupts timing. The
example is a payload decoding recipe, not sufficient instructions for a synchronized AVTP talker.

The TSCF dissector's suggested LIN/ACF interpretation previously reported a length mismatch (`expected: 1024 bytes,
available: 12 bytes`). Its control payload must remain **undecoded** until corroborated; this is not evidence that
ordinary LIN frames traverse this link.

## 5. Public AAOS usage to AVTP mapping (2026-11-15)

The lightweight [AAOS Audio Probe](../research/tools/aaos_audio_probe/README.md) exercised **all 16 public Android 12
usage IDs**, including UNKNOWN and the four deprecated notification variants. Each two-second probe received focus;
requested/effective usage IDs remained equal in the retained log observations. Live decoding inspected all three AAF
streams. Positions below are one-based within the **768-byte stream**, not physical speaker labels.

| Usage ID | AudioAttributes usage | Actual AudioTrack bus | Nonzero PCM positions |
|---:|---|---|---|
| 0 | UNKNOWN | `bus0_media_out` | 1, 2 |
| 1 | MEDIA | `bus0_media_out` | 1, 2 |
| 2 | VOICE_COMMUNICATION | `bus4_call_out` | 1, 2 |
| 3 | VOICE_COMMUNICATION_SIGNALLING | `bus4_call_out` | 1, 2 |
| 4 | ALARM | `bus5_alarm_out` | 4 |
| 5 | NOTIFICATION | `bus6_notification_out` | 4 |
| 6 | NOTIFICATION_RINGTONE | `bus3_call_ring_out` | 1, 2 |
| 7 | NOTIFICATION_COMMUNICATION_REQUEST (deprecated) | `bus6_notification_out` | 4 |
| 8 | NOTIFICATION_COMMUNICATION_INSTANT (deprecated) | `bus6_notification_out` | 4 |
| 9 | NOTIFICATION_COMMUNICATION_DELAYED (deprecated) | `bus6_notification_out` | 4 |
| 10 | NOTIFICATION_EVENT (deprecated) | `bus6_notification_out` | 4 |
| 11 | ASSISTANCE_ACCESSIBILITY | `bus2_voice_command_out` | 1, 2 |
| 12 | ASSISTANCE_NAVIGATION_GUIDANCE | `bus1_navigation_out` | 3 |
| 13 | ASSISTANCE_SONIFICATION | `bus7_system_sound_out` | 4 |
| 14 | GAME | `bus0_media_out` | 1, 2 |
| 16 | ASSISTANT | `bus2_voice_command_out` | 1, 2 |

Media **left-only** isolated position 1; **right-only** isolated position 2. The 128- and 512-byte AAF streams remained
zero-filled throughout these tests; positions 5/6 in the 768-byte stream remained zero. Alarm/notification/system
results establish another logical mix position, not a center/rear/chime speaker. Earlier four-second tests independently
confirmed media/navigation/assistant/call. The call path changed amplitude relative to the source, so source amplitude
is not a direct predictor of amplifier gain. Real call state, simultaneous mixing, volume groups, balance/fade and
proprietary tags remain separate experiments.

The live policy exposes **12 output buses**, numbered 0-8 and 11-13: `media`, `navigation`, `voice_command`, `call_ring`,
`call`, `alarm`, `notification`, `system_sound`, `ecall_ring`, `mix_unduck`, `audio_cue`, `high_priority_mutex` (each
named `busN_<name>_out`). The final four have not been driven by a verified application-to-wire test. Bus count is not
zone count.

The device also reports five supported **system** usages: CALL_ASSISTANT (17), EMERGENCY (1000), SAFETY (1001),
VEHICLE_STATUS (1002), ANNOUNCEMENT (1003). The live dynamic-policy criteria list 1000-1003 on `bus0_media_out`, but
this is **configuration evidence only**, not a measured privileged playback result. Android 12 defines these using
`setSystemUsage`; public `setUsage` is not an interchangeable way to test them. The probe attempted all five via
`setSystemUsage`: each returned `focus_result=0` (not granted), so no tone or wire route was produced. These are
attempted but **unmapped** system paths. The normal probe does not grant itself privileged routing permission or change
hidden-API policy. Usage 15 is not a public playback usage in this SDK; no route is asserted for it. See the
[Android 12 AudioAttributes source](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android12-release/media/java/android/media/AudioAttributes.java)
and [AAOS audio configuration](https://source.android.com/docs/automotive/audio/audio-policy-configuration).

## 6. Diagnostic tone correlation follow-up (2026-11-15)

The [UDS live-control reference](../diagnostics/diagnosticsd_protocol.md#live-bench-controls-2026-11-15) records four
speaker selectors requesting 475 Hz. Two memory-only T1 correlation captures (74,126 and 59,045 captured frames, zero
kernel drops) found all three AAF payloads zero in their selected LF/RF/RR/LR windows. However, their same-run 440 Hz
AAOS media-probe windows were also zero. These experiments therefore do not establish missing tone transport or a
speaker map: the required known-signal positive control was not observed. Probe logs separately showed focus granted
and `bus0_media_out`, which is Android-side admission, not proof of the downstream wire route.

A separate 35,176-frame/zero-drop capture after source/tuner activation found nonzero A768 bytes, with A128/A512 still
zero; it did not independently identify 440 Hz. Changing source/backend state and restarting the probe were not isolated
variables, so no single cause for the differing result is established. No raw packets or new audio files were saved.
Earlier known-source/usage mappings above retain their original measurement scope.

Current Java tracing shows tone frequency and channel-mute readbacks come from `Settings.Global` even though setters also
forward toward GMAudioService and vendor IGMAudioControl. This reinforces why a positive UDS response plus readback
cannot establish acoustic output. A later three-second capture again showed three AAF sizes plus 60-byte subtype 5 TSCF
frames; the generic ACF decoder reported type 3 with an invalid 1024-byte length. This remains an unresolved
vendor-control format, not a demonstrated LIN/CAN record.

## 7. Firmware audio stack (Y181B, kernel 4.19.305, Intel Apollo Lake "broxton", Android 12 under GHS)

Evidence base: `Y181B_cleanroom.img` (ext4, read via `7z`; not mountable on macOS, no `debugfs`). Audio and display
blocks are Intel-SoC peripherals (Intel SST/SOF DSP, i915 display), not ARM/Qualcomm. (Added 2026-09-27.)

**Two amp paths exist in firmware; this vehicle uses the Ethernet-AVB one.**

- **Local path [confirmed-fw]:** Intel SST DSP to I2S/TDM to **NXP TDF8532** 4-ch class-D amplifier-codec. Driver `snd-soc-tdf8532.ko` (`sound/soc/codecs/tdf8532.c`, `alias=i2c:tdf8532`) + Intel machine driver `snd-soc-sst_bxt_tdf8532.ko`. Amp control is I2C: `init.audio.rc` chowns `/dev/i2c-3` to `audioserver` (matches [hardware_specs.md](hardware_specs.md): "i2c-3 = TDF8532 codec control").
- **AVB path [confirmed-fw]:** a full automotive Ethernet AVB audio stack is present and gates audio bring-up:
  - `vendor/lib/modules/igb_avb.ko`: Intel I210 GbE driver with AVB/TSN extensions (mainline `igb` is disabled per [hardware_specs.md](hardware_specs.md)).
  - **AVB StreamHandler** service (COVESA/GENIVI-style, IEEE 1722/AVTP). `init.audio.rc` blocks on `init.svc.vendor.avbstreamhandler=running` and `vendor.avb.streamhandler.ready=true` before starting PulseAudio and the audio HAL.
  - `service vendor.earlyavbaudio /vendor/bin/early_audio_alsa_avb.sh`: **early-boot AVB audio**, i.e. audio over AVB before Android is fully up; likely carrier for safety-relevant early chimes [inferred].
  - Route/param configs select transport: default `persist.vendor.audio.audioConf = AudioParameterFramework-tdf8532-no-eavb.xml` (local I2S to TDF8532), with alternates `...-eavb-master-raw.xml`, `...-eavb-master.xml`, `...-eavb-slave.xml`, keyed on `persist.vendor.eavb.mode` and AVB profile names `MRB_Master_Audio` / `MRB_Slave_Audio` (IEEE 1722a compatibility flag `d6_1722a`). Same SST DSP, switchable output route.
- **Active path for this vehicle [confirmed-service]:** Ethernet AVB to an **external Bose T3 amplifier**. GM ALLDATA *Data Link Communications*: physical Ethernet **bus 6 (ports 7214/7215) = A11 to T3 Bose amp, "the AVB audio pair."** The A11's Intel I210 is configured as gPTP grandmaster for that AVB domain (see 2 and Open conflicts). The default `no-eavb` config in the generic image is therefore a base-trim/build fallback; the LTZ-with-Bose truck streams IEEE-1722 audio over Ethernet to T3. The local TDF8532 I2S path is almost certainly the base-audio, no-Bose variant [inferred].
- **Radio is the whole-vehicle audio hub [confirmed-vehicle]:** with the A11 radio physically removed the owner had no audio at all: no media, no turn-signal ticks, no door chimes. Chimes/turn-signal audio are generated by a body/chime module elsewhere but are rendered to the speakers through the radio. Consistent with both firmware facts: the radio is either the mixer/source of that audio **or** the AVB gPTP grandmaster (remove it and the AVB clock domain collapses and T3 goes silent regardless of who sourced the stream); not distinguished. Removal-risk behaviour and chime-callback firmware evidence (`vehicleaudiocontrol` "chime-playback-status", `libgmaudiopowermode.so`): [vehicle_config.md](vehicle_config.md) (VN L464-507 content).

## 8. What a replacement endpoint still needs

A replacement amplifier can already extract the verified audio payloads. A replacement radio must additionally produce
the expected wire headers, stream identity, sequence and presentation timing, and compatible control. Neither direction
is a verified drop-in replacement yet. Missing evidence:

- Bose output-speaker routing, EQ/crossover, gain/limiter and balance/fade behavior.
- Meaning and use of A128/A512, A768 positions 5/6 and proprietary audio buses/tags.
- AVTP presentation offset, clock recovery and exact timestamp semantics.
- TSCF control payloads, stream admission/discovery and whether SRP/MSRP or other negotiation is required with the actual amplifier attached.
- Amplifier wake/power/mute and vehicle/CAN sideband dependencies.

The measured flow is AAOS usage, logical bus, shared transport positions, external amplifier. Final physical speaker
processing is expected downstream, but the captured traffic alone does not establish how much processing Bose performs
or exclude additional speaker-specific streams in other vehicle modes.

Pi-based replacement feasibility (TSN NIC, `linuxptp`, COVESA StreamHandler, TDF8532 not a Pi target, chime relay,
analog fallback) and the panel/touch/serdes chain: [pi_swap_feasibility.md](pi_swap_feasibility.md); serdes/touch
hardware: [hardware_specs.md](hardware_specs.md).

## 9. Emulator audio

The emulator treats this transport as a physical-network dependency with no libipc fix (EM L356-365; build-level
status lives in [emulator.md](emulator.md)).

- Real audio HAL = `vendor.hardware.audio@5.0-harman-custom-service` on a real **AVB (802.1BA)** network (`daemon_cl` / `avb_streamhandler` / `eavbmgr`). It stays stubbed permanently; the emulator substitutes stock Google `audio@6.0`.
- **Update (2026-09-26):** `-no-audio` removed from `boot.sh`; live PRIMARY mixer output now reaches host CoreAudio (confirmed via `dumpsys media.audio_flinger` `AudioOut_D`).
- Guest **mic** pipeline PASSES (`AudioRecord` captures at correct real-time pacing, not muted; consumers include `carassistant`, `com.gm.car.input`, `gmaudio.tuner`, BT-HFP).
- Host delivery is still **blocked** over headless SSH: the Mac Pro has no hardware audio input (a BlackHole 2ch virtual loopback was installed to give it one), and macOS mic-privacy (TCC) denies mic to SSH-launched processes and cannot be granted over SSH. Closing it needs a GUI/Screen-Sharing console session on the Mac Pro to grant the emulator mic permission (as was done for CT5's mic). Not an emulator defect.

## Open conflicts

1. **gPTP grandmaster status.** vehicle_network.md L435 ("`-GM` grandmaster") and L598-599, L607-611 ("I210 is gPTP grandmaster", "AVB gPTP grandmaster" as removal mechanism) assert the role as fact. networking.md L641-644 and vehicle_network.md L305-307 (corrected 2026-11-15) state firmware configures GM and gPTP transmission is observed, but elected role is not decoded. This doc follows the 2026-11-15 correction; the VN assertions are stale unless re-measured (e.g. BMCA/announce decode).
2. **Which bus carried the capture vs which bus is the amp pair.** The VLAN 2 AAF/gPTP captures were taken on a **Bus 2** T1 tap (A11 to K56 gateway; networking.md L648; vehicle_network.md L288-300), while service data names the amp pair as **Bus 6** (vehicle_network.md L285, L598). Not reconciled in either source: it is not established whether the Bus 2 VLAN 2 traffic is a gateway-forwarded copy of the Bus 6 stream, a separate stream, or the same domain tag-multiplexed. Also unreconciled: ~2,900 pps VLAN 2 flood (VN L290) vs 3 x ~750 pps AAF streams (+ TSCF) measured in 3.
3. **Radio as chime source vs gPTP grandmaster.** vehicle_network.md L605-608 offers both mechanisms for "no chimes when radio removed" without choosing; see 7.

Open questions (not conflicts; unresolved evidence): A128/A512 packing inference; `00 05` raw rate/channel word vs six validated positions; TSCF payload format; sample-rate conversion location (44.1 to 48 kHz); SRP/MSRP requirement; physical speaker map; buses 8/11/12/13 (`ecall_ring`, `mix_unduck`, `audio_cue`, `high_priority_mutex`) and system usages 1000-1003 unmapped on the wire.

## History

- 2026-09-27: firmware audio-path analysis (Plane 3a) added.
- 2026-09-26: emulator `-no-audio` removed.
- 2026-11-13: gPTP transmission confirmed on live Bus 2 tap (146 frames).
- 2026-11-15: AVTP audio recovery, usage mapping, tone follow-up; gPTP role evidence scope corrected (configured vs elected); four-speaker claim withdrawn.
