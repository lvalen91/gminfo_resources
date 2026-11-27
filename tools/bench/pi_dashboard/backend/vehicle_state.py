"""Engine/ignition power-mode and transmission/gear-position control surface.

ZERO-GUESSING RULE (project-wide, restated here because this module is exactly the kind
of thing it exists to stop): every CAN id/value below must trace to directly-verified
evidence -- a captured frame with an observed effect, or a firmware disassembly trace --
never inference from "how this is typically done on other GM platforms." A state with no
such evidence stays `verified: False` here and the API/UI refuse to transmit it, no matter
how plausible the byte pattern looks. Do not add a byte pattern to this file without a
citation to a specific bench observation or firmware trace below it.

== POWER MODE (CAN 0x284, DLC 6, tester -> radio, VHAL signal 58A SPMP_SysPwrModeAuth) ==

- "off": all-zero bytes (`000000000000`).
  VERIFIED -- platform/ota_update_stack.md, "Y175 full USB update bench observation --
  2026-11-17" (~line 712-715): "CAN284 was set to all-zero authenticated-Off ... UART
  confirmed PowerModeOff". This is a direct radio-side readback of the effect of this
  exact frame, not an inference from the precondition constant alone (the same value is
  also used operationally as `PRECONDITION_284` in
  tools/bench/bench_can/calibration_write_can5.py, for the unrelated purpose of gating a
  programming session -- see that file's own comment, which independently asserts the
  same mapping).

- "run": raw candidate 2, bytes `000000001000` (`00 00 00 00 10 00`).
  VERIFIED -- the same bench session, platform/ota_update_stack.md ~line 670-677:
  repeating this exact frame "changed SystemPowerMode to RUN, lifecycle to STATE_RUN,
  and logged `handlePowerModeMessage RUN available? true`, `PowerMode: 4 is valid`".
  Cross-referenced in platform/can_network.md:65 and platform/can_bench_experiments.md:36
  and :309-315 (both call this reading "verified").

- "accessory": raw candidate 1, bytes `000000000800` (`00 00 00 00 08 00`).
  VERIFIED 2026-11-26 -- live bench test (`platform/can_bench_experiments.md`): this exact
  frame was sent and UART directly reported `evt=evPowerModeOn` / `SystemState=Accessory
  (0x7)` / `st=Accessory` -- the HMI naming its own state, not an inference. Cross-checked
  against UDS DID F085 read live over raw CAN5 (`diagnostics/GM_CAN_UDS_REFERENCE.md` §13),
  which read back `01` for this same frame.

- "propulsion": raw candidate 4, bytes `000000002000` (`00 00 00 00 20 00`).
  VERIFIED 2026-11-26 -- same live test: UART reported `SystemState=Propulsion (0x6)` /
  `st=Propulsion`, a distinct sibling state under `RunPropulsionAccessory`, not the
  "Service Mode" the MDI2 BCM note below speculated for this raw value. F085 read back
  `04`.

- "service": NO verified byte pattern exists anywhere in the retained docs for this CAN
  ID or any other. This is the only remaining unverified raw-value gap on 0x284: all of
  0 (Off), 1 (Accessory), 2 (Run), 4 (Propulsion) are now bench-verified; no other raw
  value is known, and no distinct "Service"/"Technician" HMI state has been observed.
    * A textually similar Off/Accessory/Run/Crank enum exists on CAN 0x1F1, but it is an
      EXTERNAL public-DBC candidate for a *different* vehicle's signal layout
      (platform/can_network.md:253,371,411-412: "isolated/ordered Off/Accessory
      candidates did not command shutdown" -- a negative bench result), and 0x370's
      Off/Accessory/Run/Crank/Propulsion enum is an [X] Cadillac capture "not confirmed
      on this Silverado" (platform/vehicle_network.md:146,
      platform/pi_swap_feasibility.md:53). Neither establishes a service-mode encoding on
      *this* platform's 0x284 or any other writable id.
    * BCM DID F085 (read via UDS) was historically reported elsewhere as giving
      01/accessory, 02/Service Mode, 04/engine-running as *read-back* values
      (research/mdi2-bench-sessions/MDI2_RAW_UDS_BYPASS_GUIDE.md ~line 688-691) --
      **this project's own live F085 readback (2026-11-26) contradicts the "02=Service
      Mode" part**: raw 2 reads back as F085=02 *and* independently produces UART
      `SystemState=Run`, not a Service condition. Treat that historical BCM note as
      describing a different bench/context, not this platform's semantics; do not infer
      a Service-mode byte pattern from it.
  This one stays unverified scaffolding: the UI shows it, disabled, with this reason.

== GEAR / TRANSMISSION POSITION (PRNDL) ==

platform/can_network.md, "PRNDL/gear receive path" (firmware-traced 2026-11-21) identifies
the RX chain VIP_APP actually uses: CAN 0x40B (DLC 5, 2-bit field at start-bit 35, primary)
and 0x264 (DLC 8, 4-bit field at start-bit 45, fallback when 0x40B's validity byte reads 0)
feed decode function `FUN_0004d7dc` (raw code 1->3, 3->1, 4->4, else -> Park-default via
`DAT_0002922f`), which sets the SRAM gear state the firmware reports onward.

This is NOT enough to transmit a gear state, for two independent reasons documented in
can_network.md itself (~line 546-549):
  1. It is `FIRMWARE-TRACED` only -- "not yet bench-verified by driving 0x40B/0x264 live
     and observing AAOS react." No one has sent either ID and watched the gear indicator
     change.
  2. Even the decode function's own remap is only partially known: it is known THAT raw
     1, 3 and 4 map to three internal values (3, 1, 4) and everything else maps to a
     Park-default -- but WHICH internal value is Park vs. Reverse vs. Neutral vs. Drive is
     never established anywhere in the retained docs. Guessing "1=Park, 2=Reverse,
     3=Neutral, 4=Drive" (or any other assignment) here would be exactly the kind of
     inference this project's zero-guessing rule exists to forbid.

So there is no verified byte pattern for ANY of Park/Reverse/Neutral/Drive. All four stay
unverified scaffolding.
"""
from __future__ import annotations

# --- Engine / ignition power mode (CAN 0x284) -----------------------------------
POWER_MODE_CAN_ID = 0x284
POWER_MODE_DLC = 6

POWER_MODES: dict[str, dict] = {
    "off": {
        "label": "Off",
        "verified": True,
        "can_id": POWER_MODE_CAN_ID,
        "dlc": POWER_MODE_DLC,
        "data_hex": "000000000000",
        "evidence": "platform/ota_update_stack.md, Y175 full USB update bench observation "
                    "(2026-11-17): this exact frame was sent and UART confirmed "
                    "PowerModeOff.",
    },
    "run": {
        "label": "Engine ON / Run",
        "verified": True,
        "can_id": POWER_MODE_CAN_ID,
        "dlc": POWER_MODE_DLC,
        "data_hex": "000000001000",
        "evidence": "platform/ota_update_stack.md, Y175 full USB update bench observation "
                    "(2026-11-17): this exact frame was sent and the service log showed "
                    "SystemPowerMode OFF->RUN, lifecycle ->STATE_RUN, 'PowerMode: 4 is "
                    "valid'. Cross-referenced in platform/can_network.md:65 and "
                    "platform/can_bench_experiments.md:36,309-315.",
    },
    "accessory": {
        "label": "Accessory",
        "verified": True,
        "can_id": POWER_MODE_CAN_ID,
        "dlc": POWER_MODE_DLC,
        "data_hex": "000000000800",
        "evidence": "Live bench test (2026-11-26, platform/can_bench_experiments.md): "
                    "this exact frame was sent and UART reported 'evt=evPowerModeOn', "
                    "'SystemState=Accessory (0x7)', 'st=Accessory'. Cross-checked against "
                    "UDS DID F085 (diagnostics/GM_CAN_UDS_REFERENCE.md sec 13), read back 01.",
    },
    "propulsion": {
        "label": "Propulsion",
        "verified": True,
        "can_id": POWER_MODE_CAN_ID,
        "dlc": POWER_MODE_DLC,
        "data_hex": "000000002000",
        "evidence": "Live bench test (2026-11-26, platform/can_bench_experiments.md): "
                    "this exact frame was sent and UART reported "
                    "'SystemState=Propulsion (0x6)', 'st=Propulsion' -- a distinct sibling "
                    "state under RunPropulsionAccessory, not 'run'. UDS DID F085 read back 04.",
    },
    "service": {
        "label": "Service / Technician",
        "verified": False,
        "reason": "no verified CAN frame exists for Service/Technician mode on this "
                  "platform. All four known raw values on 0x284 (0,1,2,4) are now "
                  "bench-verified as Off/Accessory/Run/Propulsion respectively (2026-11-26); "
                  "none produces a distinct Service/Technician HMI state. A historical BCM "
                  "DID F085 note elsewhere claimed 02='Service Mode', but this project's own "
                  "live F085 readback contradicts that for this platform: raw 2 reads back "
                  "F085=02 *and* independently produces UART 'SystemState=Run' -- that "
                  "historical note describes a different bench/context, not this platform.",
    },
}

# --- Transmission / gear position (PRNDL) ---------------------------------------
GEAR_RX_NOTE = (
    "CAN 0x40B (primary, DLC 5, byte4 bits5-7, 3-bit) and 0x264 (validity: byte3 bit6; "
    "fallback value: byte3 bit7 + byte4 bits0-2) are the firmware-traced PRNDL receive "
    "path (platform/can_network.md, 'PRNDL/gear receive path', corrected 2026-11-26). "
    "Live-tested 2026-11-26 (platform/can_bench_experiments.md, 'Gear/PRNDL: CAN-side "
    "send confirmed correct, no observable AAOS reaction found'): the CAN send itself is "
    "confirmed correct -- it matches the firmware's own decode-function remap exactly -- "
    "but no reaction was found across three independent channels (UART, which has no "
    "gear/PRNDL log tag at all; the visible display and the com.gm.cluster process, both "
    "silent; and a UDS C0xx telemetry sweep over raw-CAN5, which read identical values "
    "across gear states). Which internal value is Park vs. Reverse vs. Neutral vs. Drive "
    "remains unestablished. No verified CAN frame exists for any gear position; every "
    "control below is scaffolding only."
)

GEAR_POSITIONS: dict[str, dict] = {
    name: {"label": label, "verified": False, "reason": GEAR_RX_NOTE}
    for name, label in (
        ("park", "Park"),
        ("reverse", "Reverse"),
        ("neutral", "Neutral"),
        ("drive", "Drive"),
    )
}
