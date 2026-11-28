#!/usr/bin/env python3
"""Show which traced effects differ after calibration or runtime-state changes. Reads map.json; touches no radio.

  ./predict.py --set Apple_CarPlay_enableWireless=0 --set AndroidAuto_enableWireless=0
  ./predict.py --set Apple_CarPlay_enableWireless=0 --state hmi_hotspot_disable_status=1
"""
import argparse
import json
import pathlib

from rules import RULES, STATE, VALUE_EFFECTS


def typed(text):
    low = str(text).lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(text)
    except (TypeError, ValueError):
        return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", action="append", default=[], metavar="CAL=VALUE")
    ap.add_argument("--state", action="append", default=[], metavar="NAME=VALUE")
    ap.add_argument("--from", dest="source", choices=["bench", "image"], default="bench")
    args = ap.parse_args()
    cals = json.loads((pathlib.Path(__file__).parent / "map.json").read_text())["settings"]
    before = {n: typed(c[args.source]) for n, c in cals.items()}
    before.update(STATE)
    after = dict(before)
    for item in args.set:
        name, value = item.split("=", 1)
        if name not in cals:
            ap.error(f"unknown or out-of-scope calibration: {name}")
        after[name] = typed(value)
    for item in args.state:
        name, value = item.split("=", 1)
        if name not in STATE:
            ap.error(f"unknown state: {name}")
        before[name] = after[name] = typed(value)

    changed = [i.split("=", 1)[0] for i in args.set if before[i.split("=", 1)[0]] != after[i.split("=", 1)[0]]]
    print(f"baseline: {args.source}; changed: {', '.join(changed) or 'nothing'}")
    for r in RULES:
        a, b = (bool(eval(r["expr"], {"__builtins__": {}}, v)) for v in (before, after))
        if a != b:
            print(f"\n{r['feature']}: {a} -> {b}  [evidence: {r['level']}; a predicted change is not a tested one]\n  rule: {r['effect']}\n  check: {r['check']}")
            if r["note"]:
                print(f"  note: {r['note']}")
    for name in changed:
        if name in VALUE_EFFECTS:
            print(f"\n{name}: {before[name]} -> {after[name]}\n  {VALUE_EFFECTS[name][0]}")
        elif not any(name in r["expr"] for r in RULES):
            print(f"\n{name}: no traced rule (status: {cals[name]['status']}). Effect unknown, not 'none'.")
    print("\nOnly traced effects are listed. Reboot after a calibration change before checking.")


if __name__ == "__main__":
    main()
