"""Steering-wheel / media / volume controls via UDS InputOutputControlByIdentifier
($2F) over the T1 Ethernet diagnosticsd transport.

ZERO-GUESSING RULE (restated, see vehicle_state.py's module docstring for the full
statement): every IOCID/param below must trace to a citable, bench-observed entry in
diagnostics/GM_CAN_UDS_REFERENCE.md (sec 6 IOCID catalog, sec 11e avoiding-NRC table),
never inference. A control with no such evidence stays `verified: False` and the
API/UI refuse to send it -- same discipline as vehicle_state.py's power-mode/gear
scaffolding.

Mechanism: a "press" is one short-term-adjustment request immediately followed by a
returnControl request -- `2F <IOCID-hi> <IOCID-lo> 03 <param>` then
`2F <IOCID-hi> <IOCID-lo> 00` -- a momentary press-and-release, not a held state.
Both IOCID families used here (41DB "steering-wheel key sim", 41D8 "general key sim")
need only an extended session (`10 03`) plus the bench-confirmed degenerate
SecurityAccess level-01 grant (diagdata.DEGENERATE_KEY) -- see
diagnostics/GM_CAN_UDS_REFERENCE.md sec 11e.
"""
from __future__ import annotations

STEERING_WHEEL_CONTROLS: dict[str, dict] = {
    "volume_up": {
        "label": "Volume Up",
        "group": "Volume",
        "verified": True,
        "iocid": 0x41DB,
        "param": 0x03,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 6/11e: IOCID 41DB "
                    "(steering-wheel key sim) control=03 param=03 = VolUp (Android keycode "
                    "24); [live] confirmed via a 15->14->15 volume-DID readback cycle.",
    },
    "volume_down": {
        "label": "Volume Down",
        "group": "Volume",
        "verified": True,
        "iocid": 0x41DB,
        "param": 0x04,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 6/11e: IOCID 41DB control=03 "
                    "param=04 = VolDown (Android keycode 25); same bench-verified volume "
                    "cycle as Volume Up.",
    },
    "mute": {
        "label": "Mute",
        "group": "Volume",
        "verified": True,
        "iocid": 0x41DB,
        "param": 0x06,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 2/6/8: IOCID 41DB control=03 "
                    "param=06 = Mute (Android keycode 164), maps to HW_KEY_INJECT internal "
                    "key 1003.",
    },
    "media_prev": {
        "label": "Media Previous",
        "group": "Media",
        "verified": True,
        "iocid": 0x41D8,
        "param": 0x0A,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 6: IOCID 41D8 (general key sim) "
                    "control=03 param=0A = MediaPrev (Android keycode 88).",
    },
    "media_next": {
        "label": "Media Next",
        "group": "Media",
        "verified": True,
        "iocid": 0x41D8,
        "param": 0x0B,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 6: IOCID 41D8 control=03 "
                    "param=0B = MediaNext (Android keycode 87).",
    },
    "voice_assist": {
        "label": "Voice Assist",
        "group": "Voice / Calls",
        "verified": True,
        "iocid": 0x41DB,
        "param": 0x05,
        "evidence": "diagnostics/GM_CAN_UDS_REFERENCE.md sec 2/6/8: IOCID 41DB control=03 "
                    "param=05 = Speech (Android keycode 231), maps to HW_KEY_INJECT internal "
                    "key 1002.",
    },
    "call_answer_end": {
        "label": "Answer / End Call",
        "group": "Voice / Calls",
        "verified": False,
        "reason": "no verified IOCID exists for a call-answer/end control on this platform. "
                  "IOCID 41DB (steering-wheel key sim) and 41D8 (general key sim) are fully "
                  "catalogued in diagnostics/GM_CAN_UDS_REFERENCE.md sec 6/11e and cover "
                  "media/volume/mute/voice-assist only -- neither documents a call key. "
                  "Scaffolding only; refuses to send.",
    },
}


def iocid_press_request(iocid: int, param: int) -> bytes:
    return bytes([0x2F, (iocid >> 8) & 0xFF, iocid & 0xFF, 0x03, param])


def iocid_release_request(iocid: int) -> bytes:
    return bytes([0x2F, (iocid >> 8) & 0xFF, iocid & 0xFF, 0x00])
