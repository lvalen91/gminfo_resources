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

# Look up anything in the ~215 CalDef groups, including elevated-caution ones
.venv/bin/python cli.py explain SXM_Enabled
.venv/bin/python cli.py search carplay
.venv/bin/python cli.py groups
.venv/bin/python cli.py group GIS513_DeviceProjection

# Edit an existing entry, or add one that isn't present in the loaded file yet
.venv/bin/python cli.py set slot0c.json SXM_Enabled false
.venv/bin/python cli.py add slot0c.json Enable_Application_Apple_Carplay false

# Entries from an elevated-caution chime/safety group need an explicit flag -- see "Safety gate" below
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

`caltool.caldef.SAFETY_RESTRICTED_GROUPS` lists the CalDef groups that are treated as elevated-caution --
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
- **`/help`** — the 14-slot table, the elevated-caution safety-group list, the proven-trial
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

## Security review (2026-11-22)

This toolkit was reviewed and stress-tested (static code review, CLI fuzzing, and live
web-UI testing via real Safari/AppleScript automation plus direct API fuzzing). All
confirmed data-corrupting/exploitable findings were fixed and re-verified:

- `calovride.serialize()` now escapes `&`/`<`/`>` (previously unescaped text could produce
  invalid XML or, combined with no value validation, inject sibling `<OverrideValue>`
  elements past the safety gate entirely).
- The web UI's export previously flattened array/map/record/binary values to a display
  string and sent *that* back on export -- silently corrupting arrays and crashing on
  maps/records/binaries. Fixed: every entry now carries an authoritative `value_raw`
  alongside the display `value`; export always uses the former. Confirmed via a live
  round-trip of a module containing all ten types: byte-identical when untouched.
- `cli.py set`/`add` now validate a value against its type (`calovride.validate_value`)
  instead of writing an arbitrary string into any field.
- The safety gate is now enforced server-side at export time (`/api/export`,
  `/api/export_zip`, gated on `safety_ack`), not only client-side on add -- closing the
  asymmetry where editing an already-loaded restricted entry had no gate at all.
- **The gate's own premise was wrong and has been corrected**: the groups it restricts
  were documented as "never shipped"; direct verification found 162 real entries from
  these groups in stock slot 04 alone (seat-belt/forward-collision chime records,
  `ADASIS_SUPPORT`, etc.). The constant is now `SAFETY_RESTRICTED_GROUPS` (old name kept
  as a deprecated alias); the warning text no longer claims non-existence in shipped data.
- 154 real CalDef names collide across two different `.caldef` groups with different
  CalIDs; `caldef.lookup()` now raises on ambiguity instead of silently picking whichever
  group loaded last, and `cli.py set` resolves against entries already in the file by
  their own CalID first (never ambiguous, since that CalID is already known-correct).
- `container.parse_any()` now actually never raises (every gzip/zlib exception on
  malformed input is caught), and `container.parse()`/ingest expose a `digest_ok` flag so
  a tampered-but-structurally-valid container is flagged rather than silently trusted.
- Decompression is capped at 16MiB (real payloads top out around 600KB) against a small,
  highly-compressed file claiming to decompress to hundreds of MB.
- `export_zip` member names are sanitized against path-traversal-shaped names and
  deduplicated against basename collisions.
- `argparse`'s prefix-abbreviation let a bare `--i` silently satisfy
  `--i-understand-the-safety-risk`; the parser now disables abbreviation.
- The web app no longer runs with Flask's `debug=True` (which exposes the interactive
  Werkzeug debugger).

**Known, deliberately deferred limitations** (lower severity / cosmetic, not corruption or
security-relevant): a from-scratch `pack --template` repack of an unmodified container is
not byte-identical to the genuine original (Python's gzip writes different XFL/OS header
bytes than GM's own tool; the digest is still always correctly recomputed over whatever
bytes are actually present, so this doesn't affect correctness); the local CalDef
database's declared version for a given calibration often differs from the version an
actual shipped override uses (no way to know which version a brand-new, never-shipped
entry "should" claim); true concurrent (not just rapid-sequential) CLI writes to the same
JSON file can lose an update, same as any unlocked file write; and the narrow-width (under
~450px) layout can still scroll horizontally at the page level in extreme cases.
