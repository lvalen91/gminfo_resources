# Qualcomm / Cadillac Radio Platform (SA8155P) — external RE notes [X]

> **Scope & provenance.** This repo's hardware/boot/CAN work is all the **Intel Apollo Lake
> gminfo37 / A11 Silverado** radio ([`hardware.md`](hardware.md), [`security.md`](security.md),
> [`boot_chain.md`](boot_chain.md)). GM's **newer Global-B radio is a different SoC** — Qualcomm
> **SA8155P** under a **QNX** hypervisor — used on Cadillac Lyriq / CT5 and going forward on all GM
> head units after Intel exited automotive. This repo has **no** Qualcomm hardware teardown or
> CAN-security capture, so everything here is **[X]** = external, single-source, unverified against
> our own hardware.
>
> **Sources:** Snipesy / Surreal Development, *"Rooting the Cadillac Part 1: Lay of the Land"*
> (2026-08-15) and *"The ABCs of Global B"* (2026-06-16, **CC0 1.0**) — full URLs/licenses in the
> [Sources](#sources--surrealdevcom-canonical-x) table below. Primary vehicles: 2025 Cadillac Lyriq
> / 2025 CT5-V (Qualcomm) and a 2023 Chevy Colorado (Intel).
> Deeper GM-side CT5 firmware RE (Android layer) lives in the separate `/Volumes/.../GM_research`
> tree (`aaos/gm_aaos/2026_CT5/MASTER_REFERENCE.md`), which agrees on SA8155P + QNX + the 33-inch
> 8960×1320 panel.

## Platform split (Intel → Qualcomm) [X]

| | Intel radio (this repo) | Qualcomm radio (this doc) |
|---|---|---|
| Vehicles | lower-trim Silverado/Sierra, 2023 Colorado | Cadillac Lyriq, CT5, newer GM lineup |
| App SoC | Intel Atom x7-A3960 (Apollo Lake) | **Qualcomm Snapdragon SA8155P** |
| Hypervisor | GHS INTEGRITY (Type-1) | **QNX** mini-hypervisor |
| Host OS | (GHS partitions) | **QNX** — safety-critical: speedo, cameras, lights |
| Guest | Android 12 AAOS w/ GAS | **AAOS w/ GAS** (CT5 on **AAOS 14**, YouTube OTB) |
| Status | Intel discontinued automotive; legacy | GM's forward platform (OTA focus) |

Per the article, GM's AAOS variant is **AAOS w/ GAS** — Android Automotive partnered with Google
for **Google Automotive Services** — and **AAOS ≠ Android Auto** (the phone-projection product).

Author's claim that **Intel scuttled its automotive line in 2025** (*ABCs of Global B*: "Intel
scuttled their entire automotive offerings in 2025") is an external assertion, not verified here. [X]

## Radio internal architecture [X]

Two primary CPUs, same division of labour as the Intel board:

- **RH850 "VIP" MCU** — power management, reset/watchdog, and **CAN** comms (vehicle state, SDGM
  handshakes). Same VIP role as this repo's Intel board; its deep-sleep / CAN-phy-wake / sub-mA
  behavior is documented once in [`hardware.md`](hardware.md) → VIP MCU (don't restate here).
- **SA8155P SOC** — runs Android; DisplayPort-capable; smartphone-class Snapdragon with extra
  pins/PCIe. Boots the AAOS guest under the QNX host.
- **Ethernet switch** — automotive-Ethernet channels to the radio (same role as the Intel board's
  BCM89551/88Q5050).
- **SDGM** ties the vehicle networks together and is the anti-theft handshake anchor (see
  [`ota_programming_roles.md`](ota_programming_roles.md) → Global B provisioning; heed the
  SDGM/CGM/SGM naming caveat there).
- **Telematics module** — internet uplink + the actual OTA downloader; not critical to radio
  function. Wi-Fi is on-board (a trace), not a separate module on this unit.

## Display [X]

- **33-inch diagonal "9K" FALD** (Full Array Local Dimming) panel — behaves as one panel but is
  physically **"two screens in a trench coat"** (Cadillac consolidates two into one; Chevy Equinox
  runs the same system as two separate screens). Explains 12/14-pin connectors that are only
  half-populated. GM markets by diagonal-inch + "9K"/"8K" branding; the `/Volumes` CT5 tree records
  the actual panel as **Innolux, 8960×1320 @60**, QNX-driven.
- **Link:** SOC emits **DP 1.4**, converted to **FPD-Link IV** over 2 twisted pairs, converted back
  to DP 1.4 at the screen (consumed like a normal PC monitor). FPD-Link IV carries an **I²C side
  channel** for **brightness** and **touch**.
- **No parts-pairing on the screen** — a 2025 Lyriq screen works on a 2025 CT5-V and vice-versa
  (mounting plastics differ); works on any radio with a similar screen.

## Board BOM (2025 Lyriq unit) [X]

Board has **no silkscreen**. Author-reported components:

- Qualcomm SA8155P module + **2× 6 GB Micron LPDDR4X**, 2× PMICs
- **RH850/F1x** variant (VIP)
- **128 GB UFS** NAND
- Molex **HSAL2** (High-Speed AutoLink II) — 12-pin gray, 14-pin black
- **Aptiv AMEC 050**, Molex **stAK50h**

> **Do not graft onto the Intel spec.** This repo's A11 board is **8 GB LPDDR4** (4× Micron),
> **64 GB eMMC**, RH850/**P1M-E** — different RAM type/size, storage, and MCU variant. These are
> genuine platform differences, not corrections to [`hardware.md`](hardware.md). (Molex HSAL2 /
> stAK50h connector families do also appear on the A11 harness — see
> [`../hardware/connectors.md`](../hardware/connectors.md) — but as different shells.)

## Boot & VIN gate [X]

- **VIN is effectively the only boot gate.** Provide the correct VIN and the radio boots (with minor
  errors). VIN is **broadcast on CAN** — author cites IDs **`0x712`, `0x75F`, `0x49B`** — and there
  is **no security on the VIN**: you can ask the radio its own VIN over normal UDS diagnostic CAN
  (repo note: the standard VIN read is `$22 F190` ReadDataByIdentifier — the article says only "over
  normal UDS", without naming the DID) and immediately re-broadcast it. *These arbitration IDs are
  Cadillac captures; this
  Silverado uses `0x80`/`0x45` diagnostic addressing (see [`vehicle_network.md`](vehicle_network.md))
  — do not assume the IDs carry over.*
- **Wrong VIN → "Theft Locked"** overlay on the Android side, but even that is worked around and the
  unit runs. This laxity is by design: the radio must still show safety-critical data (speed, airbag
  and warning lights) in fault conditions. (Our Intel VIP shows the analogous `Theftlocked
  Active` / `evTheftlockedCleared` states — `/Volumes/.../VIP_BOOT_CONTROL_ANALYSIS.md`.)
- **Bootloader locked from factory (efuses burned).** Overwriting images just partial-bricks it.
  Per-module secure boot + HSM/TEE means an end-to-end aftermarket fix would need physical
  chip-level work on *every* module — consistent with this repo's Intel secure-boot findings
  ([`security.md`](security.md)).

## See also
- [`vehicle_network.md`](vehicle_network.md) — SecOC CAN authentication (Plane 1a) and the VLAN-502
  CAN-over-Ethernet mirror, both from the same surrealdev source.
- [`ota_programming_roles.md`](ota_programming_roles.md) — Global B provisioning, SDAC/U1962, SPS/DPS
  economics, GM cloud-auth composition (ABCs of Global B).
- [`hardware.md`](hardware.md) / [`security.md`](security.md) — the Intel-platform counterparts.

## Sources — surrealdev.com (canonical) [X]

Canonical bibliography for the *"Rooting the Cadillac"* series and related posts by **Snipesy /
Surreal Development LLC**. All other docs that cite this site (`vehicle_network.md` Plane 1a & vlan502,
`ota_programming_roles.md` Global-B provisioning, `hardware.md` VIP sleep,
`research/MDI2_RAW_UDS_BYPASS_GUIDE.md` §7) draw from these and should point here.

| Article | Published | License | URL |
|---|---|---|---|
| Rooting the Cadillac Part 1: Lay of the Land | 2026-08-15 | author's commentary (no explicit license; "at your own risk") | `https://surrealdev.com/rooting-the-cadillac-part-1-lay-of-the-land/` |
| Rooting the Cadillac Part 2: SecOc | 2026-09-22 | author's commentary (no explicit license) | `https://surrealdev.com/rooting-the-cadillac-part-2-secoc/` |
| The ABCs of Global B | 2026-06-16 | **CC0 1.0** (public domain) | `https://surrealdev.com/the-abcs-of-global-b/` |
| Maybe you should decline OTAs? | 2026-07-30 | author's commentary (opinion; not integrated) | `https://surrealdev.com/maybe-you-should-decline-otas/` |

- **Author/credits:** posts by *Snipesy*; Part 1 also credits Jessie Hoogestraat, Stephanie
  Howanietz, and Kevin Pham (Deoxy). Disclaimed as personal/independent research, not official
  Surreal Development guidance.
- **License precision:** only *The ABCs of Global B* is released **CC0 1.0** — text/figures from it
  may be reused freely. The two *Rooting the Cadillac* posts carry no reuse license, so this repo
  paraphrases their facts (with attribution) rather than copying text.
- **Reliability:** single-source, other-vehicle (Cadillac Lyriq/CT5 + 2023 Colorado). Tagged `[X]`
  throughout and cross-checked against our own Intel-platform findings; see each citing doc for the
  specific agree/conflict caveats (notably the SDGM/CGM/SGM naming and the "$27-against-SDGM"
  framing, which conflict with this repo's captures).
