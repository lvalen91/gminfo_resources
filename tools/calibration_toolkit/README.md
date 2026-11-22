# Calibration Toolkit

Ingest, edit, repackage, and create GM "CalOvride" calibration modules for the A11
(gminfo37 CSM) radio platform — usable as a Python library/CLI by agents and scripts,
and as a local web UI for human editing. Read
[`CALIBRATION_SLOT_MAP.md`](../../research/eeprom-calibration/CALIBRATION_SLOT_MAP.md) and
[`CALIBRATION_CUSTOMIZATION_GUIDE.md`](../../research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md)
before using this on anything you intend to write to real hardware — this tool produces
correctly-formatted payloads, it does not tell you what a given change actually does.

## What this is NOT

- **Not a signer.** `caltool.container.reseal()` recomputes the one mutable payload digest
  and leaves the RSA header signature untouched (byte-identical to whatever template you
  gave it), which means it will be stale relative to any edit. Getting an edited container
  accepted by real hardware requires the separate CAN613/614 VIP-RAM bypass procedure
  documented in `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` — a live-bench action, not
  something this tool automates or should automate.
- **Not a hosted service.** The web UI is `127.0.0.1`-only, no account system, no database,
  nothing persists across a restart. Load/edit/download, same as the CLI.

## Format this implements

GM's CalOvride XML schema, verified byte-for-byte against every genuine LTZ and HC
container on this platform (28/28, independently re-verified — see the customization
guide §5): CRLF line endings, 2-space indent per nesting depth, no trailing newline, a
self-closing root when empty, and ten override value types (`Boolean`, `Integer`,
`Float`, `Enumeration`, `String`, `IntegerArray`, `FloatArray`, `EnumIntegerMap`,
`EnumFloatMap`, `Record`) plus `BinaryFile` for embedded blobs.

## Setup

```sh
cd tools/calibration_toolkit
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export GMINFO_REPO_ROOT=/path/to/your/gminfo_resources/checkout   # for CalDef lookups
```

`GMINFO_REPO_ROOT` follows the same convention already used elsewhere in `tools/` (see
`tools/mdi2_client/mdi2/dpdu_replay.py`) — unset by default, point it at your own checkout.
It's only needed for CalDef name/description/default lookups (`explain`, `search`, `add`,
and the web UI's add-entry flow); `ingest`/`set`/`pack` on an existing JSON work without it.

## CLI (agent/LLM-friendly — JSON in, JSON/files out, nothing interactive)

```sh
# Parse a signed container, an unwrapped container, or a bare .calovride file to JSON
.venv/bin/python cli.py ingest /path/to/spsCacheInternal/85102312 > slot0c.json

# Look up anything in the ~215 CalDef groups, including never-shipped ones
.venv/bin/python cli.py explain SXM_Enabled
.venv/bin/python cli.py search carplay
.venv/bin/python cli.py groups
.venv/bin/python cli.py group GIS513_DeviceProjection

# Edit an existing entry, or add one that isn't present in the loaded file yet
.venv/bin/python cli.py set slot0c.json SXM_Enabled false
.venv/bin/python cli.py add slot0c.json Enable_Application_Apple_Carplay false

# Entries from a never-shipped chime/safety group need an explicit flag -- see "Safety gate" below
.venv/bin/python cli.py add slot0c.json BEEP_2000_CHIME_GAIN 5 --i-understand-the-safety-risk

# Serialize back out -- plain XML, or a full container reusing a genuine file's header
.venv/bin/python cli.py pack slot0c.json -o custom.calovride --xml-only
.venv/bin/python cli.py pack slot0c.json -o custom_container --template /path/to/spsCacheInternal/85102312
```

`IntegerArray`/`FloatArray`/`EnumIntegerMap`/`EnumFloatMap`/`Record`/`BinaryFile` values
can be ingested and re-packed as-is, but adding or restructuring one of these types isn't
exposed as a CLI flag — edit the ingested JSON directly (the shapes match
`caltool/calovride.py`'s dataclasses) and `pack` it.

## Safety gate

`caltool.caldef.NEVER_SHIPPED_SAFETY_GROUPS` lists the CalDef groups that have never
appeared in any stock or custom override on this vehicle (chime/alert/driver-workload/
safety-volume behavior — see the customization guide §3). `add`/`set` on any entry from
one of these groups raises `SafetyGateError` unless explicitly acknowledged:
`--i-understand-the-safety-risk` on the CLI, or the confirmation dialog in the web UI
(`/api/caldef/entry` reports `safety_restricted`/`safety_warning`; the editor's `addEntry()`
shows a JS `confirm()` with the full warning text before proceeding). This is a friction/
awareness control for a single-user local tool, not a security boundary — someone editing
the JSON by hand can always bypass it, same as the CLI flag can always be passed. Its job
is to make sure nobody lands in that territory by accident.

## Web UI

```sh
.venv/bin/python web/app.py
# open http://127.0.0.1:5057/
```

- **`/`** — upload a file, edit scalar/String values inline (array/map/record/binary
  values show read-only with a type-appropriate note), search and add any CalDef entry,
  download the result as plain XML or a full container (borrowing the uploaded file's
  header; digest recomputed, signature stays stale, exactly like the CLI).
- **`/help`** — the 14-slot table, the never-shipped safety-group list, the proven-trial
  summary, and the verified type schema, condensed from `CALIBRATION_SLOT_MAP.md` and
  `CALIBRATION_CUSTOMIZATION_GUIDE.md`. Read those two docs directly for full detail and
  citations — this page is a quick reference, not a replacement.

## Library (for your own scripts/agents)

```python
from caltool import calovride, container, caldef

raw = open("spsCacheInternal/85102312", "rb").read()
c = container.parse(raw)
entries = calovride.parse(c.inner_xml)

sxm = next(e for e in entries if e.cal_id == caldef.lookup("SXM_Enabled").cal_id)
sxm.value = "false"

new_xml = calovride.serialize(entries)
unwrapped = container.reseal(c.header, new_xml)   # digest recomputed, signature stale
outer = container.pack_outer(unwrapped)
open("custom_container", "wb").write(outer)
```
