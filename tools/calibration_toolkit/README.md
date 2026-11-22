# Calibration Toolkit

> **Owner:** repo owner (solo-maintained — see repo-root `AGENTS.md` for general
> contribution conventions; no separate review process for this tool).
> **Status:** living document — describes current behavior and auto-updates with the
> code. It is not a frozen record.
> **Review cadence:** re-read and correct this file whenever `caltool/`, `cli.py`, or
> `web/` changes in a way that affects what's described below; otherwise, treat it as
> good for 6 months before a deliberate re-check.
> **History:** [`CHANGELOG.md`](CHANGELOG.md) is the frozen, append-only record of past
> reviews and fixes. This file never accumulates a growing "past fixes" list — only the
> current, true-today description of the tool lives here.

## 1. Introduction

Ingest, edit, repackage, and create GM "CalOvride" calibration modules for the A11
(gminfo37 CSM) radio platform — usable as a Python library/CLI by agents and scripts,
and as a local web UI for human editing.

**Key terms:**
- **CalOvride** — GM's XML schema for a set of calibration value overrides (see
  [§8 Appendices](#8-appendices) for the verified byte-level format).
- **CSM container** — the signed, gzip-wrapped container format that CalOvride XML
  ships inside on real hardware (`caltool/container.py`).
- **CalDef** — GM's reference database of ~3,000 known calibration definitions across
  ~145 groups (name, type, default, description); `caltool/caldef.py` loads it from
  this repo's own `reference/` tree.
- **Safety gate** — a deliberate friction control (not a security boundary) that
  requires explicit acknowledgment before editing an entry from a CalDef group this
  toolkit treats as elevated-caution. See [§3](#3-component-descriptions).

**Scope:** this README covers the toolkit's own behavior and how to run it. It does
**not** re-derive vehicle-specific facts — which calibration actually does what, which
slots are safe to touch, what's been proven on a real bench — that material lives in
[`CALIBRATION_SLOT_MAP.md`](../../research/eeprom-calibration/CALIBRATION_SLOT_MAP.md)
and
[`CALIBRATION_CUSTOMIZATION_GUIDE.md`](../../research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md).
Read both before using this tool's output on anything you intend to write to real
hardware — this toolkit produces correctly-formatted payloads, it does not tell you
what a given change actually does.

## 2. System overview

Three surfaces share one core:

```
            ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
            │     CLI      │   │  Web UI       │   │ Your own     │
            │  (cli.py)    │   │ (web/app.py + │   │ script       │
            │              │   │  editor.js)   │   │ (import      │
            │ JSON in/out, │   │ upload/edit/  │   │  caltool.*)  │
            │ scriptable   │   │  download     │   │              │
            └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                   │                  │                  │
                   └──────────┬───────┴──────────┬───────┘
                              ▼                  ▼
                 caltool/calovride.py   caltool/container.py
                 (parse/serialize the   (parse/reseal the signed
                  CalOvride XML)         CSM container wrapper)
                              │
                              ▼
                    caltool/caldef.py
              (name→CalID/type/default lookups,
               the safety gate, group listing)
```

Every surface reads and writes the same canonical JSON shape for an `Override`
(`calovride.to_jsonable`/`from_jsonable`), so a file produced by `cli.py ingest` can be
edited by hand, by an agent, or re-uploaded to the web UI interchangeably.

## 3. Component descriptions

- **`caltool/calovride.py`** — parses and serializes the CalOvride XML itself. Must
  byte-exact round-trip every genuine container on this platform (verified 28/28 against
  real LTZ/HC containers — re-verify this claim per [§7](#7-maintenance-procedures) any
  time this module changes). Twelve override types are supported: `Boolean`, `Integer`,
  `Float`, `Enumeration`, `String`, `IntegerArray`, `FloatArray`, `StringArray`,
  `EnumIntegerMap`, `EnumFloatMap`, `Record`, `BinaryFile`.
- **`caltool/container.py`** — parses and reseals the signed CSM container wrapper.
  **Deliberately not a signer**: `reseal()` recomputes only the one mutable payload
  digest and leaves the RSA header signature byte-identical to whatever template it was
  given, which means that signature is stale relative to any edit. Getting an edited
  container accepted by real hardware requires the separate CAN613/614 VIP-RAM bypass
  procedure documented in `DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md` — a live-bench
  action this tool does not and should not automate.
- **`caltool/caldef.py`** — the CalDef reference database and the safety gate.
  `SAFETY_RESTRICTED_GROUPS` lists CalDef groups this toolkit treats as elevated-caution
  (chime/alert/driver-workload/safety-volume behavior — see the customization guide
  §3). Editing or adding an entry from one of these groups raises `SafetyGateError`
  unless explicitly acknowledged (`--i-understand-the-safety-risk` on the CLI, or the
  confirmation dialog in the web UI). **Why this exists, and what it isn't**: this is a
  friction/awareness control for a single-user local tool, not a security boundary —
  anyone editing the JSON by hand can always bypass it, same as the CLI flag can always
  just be passed. Its only job is making sure nobody lands in that territory by
  accident.
- **`cli.py`** — the agent/LLM-friendly surface: every subcommand that emits data
  defaults to JSON on stdout, and every edit is a plain argument, nothing interactive.
- **`web/app.py` + `web/static/editor.js`** — the local human-editing surface. Kept
  deliberately simple (no build step, no framework) so the whole client is one readable
  file; see inline comments there for UI-specific design rationale (e.g. why the
  add-entry search is scoped per-module rather than global).

## 4. Installation / setup

```sh
cd tools/calibration_toolkit
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export GMINFO_REPO_ROOT=/path/to/your/gminfo_resources/checkout   # for CalDef lookups
```

`GMINFO_REPO_ROOT` follows the same convention already used elsewhere in `tools/` (see
`tools/mdi2_client/mdi2/dpdu_replay.py`) — unset by default, point it at your own
checkout. It's only needed for CalDef name/description/default lookups (`explain`,
`search`, `add`, and the web UI's add-entry flow); `ingest`/`set`/`pack` on an existing
JSON work without it.

## 5. Usage instructions

### CLI

```sh
# Parse a signed container, an unwrapped container, or a bare .calovride file to JSON
.venv/bin/python cli.py ingest /path/to/spsCacheInternal/85102312 > slot0c.json

# Look up anything in the ~145 CalDef groups, including elevated-caution ones
.venv/bin/python cli.py explain SXM_Enabled
.venv/bin/python cli.py search carplay
.venv/bin/python cli.py groups
.venv/bin/python cli.py group GIS513_DeviceProjection

# Edit an existing entry, or add one that isn't present in the loaded file yet
.venv/bin/python cli.py set slot0c.json SXM_Enabled false
.venv/bin/python cli.py add slot0c.json Enable_Application_Apple_Carplay false

# Entries from an elevated-caution chime/safety group need an explicit flag -- see §3
.venv/bin/python cli.py add slot0c.json BEEP_2000_CHIME_GAIN 5 --i-understand-the-safety-risk

# Serialize back out -- plain XML, or a full container reusing a genuine file's header
.venv/bin/python cli.py pack slot0c.json -o custom.calovride --xml-only
.venv/bin/python cli.py pack slot0c.json -o custom_container --template /path/to/spsCacheInternal/85102312
```

`IntegerArray`/`FloatArray`/`StringArray`/`EnumIntegerMap`/`EnumFloatMap`/`Record`/
`BinaryFile` values can be ingested and re-packed as-is, but adding or restructuring one
of these types isn't exposed as a CLI flag — edit the ingested JSON directly (the shapes
match `caltool/calovride.py`'s dataclasses) and `pack` it.

### Web UI

```sh
.venv/bin/python web/app.py
# open http://127.0.0.1:5057/
```

- **`/`** — upload a file, edit scalar/String values inline (array/map/record/binary
  values show read-only with a type-appropriate note). Each loaded module has its own
  filter (for what's already loaded) and its own "+ Add entry…" control (to pull a new
  one in from the whole CalDef reference, scoped to that module — never a page-level
  search with a hidden target). Download the result as plain XML or a full container
  (borrowing the uploaded file's header; digest recomputed, signature stays stale,
  exactly like the CLI).
- **`/help`** — the 14-slot table, the elevated-caution safety-group list, the
  proven-trial summary, and the verified type schema, condensed from
  `CALIBRATION_SLOT_MAP.md` and `CALIBRATION_CUSTOMIZATION_GUIDE.md`. Read those two
  docs directly for full detail and citations — this page is a quick reference, not a
  replacement.

### Library

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

## 6. Troubleshooting guide

| Problem | Likely cause | Recommended steps |
|---|---|---|
| `CalDefError: GMINFO_REPO_ROOT is not set` | The env var isn't exported in this shell | `export GMINFO_REPO_ROOT=/path/to/your/checkout` (see [§4](#4-installation--setup)); not needed for `ingest`/`set`/`pack` on an already-ingested JSON |
| `'<name>' is ambiguous -- defined under 2 different groups` | One of 154 real CalDef names that collide across two `.caldef` groups with different CalIDs | Use `caldef.lookup_in_group(name, group)`, or the literal CalID, to disambiguate; `cli.py set` on an already-ingested entry resolves this automatically via the entry's own CalID |
| `SafetyGateError` on `add`/`set`, or a confirm dialog in the web UI that won't go away | The entry belongs to an elevated-caution CalDef group ([§3](#3-component-descriptions)) | Read `CALIBRATION_CUSTOMIZATION_GUIDE.md` §3, then pass `--i-understand-the-safety-risk` on the CLI or confirm the dialog in the web UI — this is a deliberate speed bump, not a bug |
| Web UI's "+ Add entry" shows a result as "not supported here" | The CalDef entry is an array/map/record/binary type, not yet addable from the web UI | Add it via `cli.py add` isn't available for these types either — ingest to JSON, hand-edit the entry matching `caltool/calovride.py`'s dataclass shape, then `pack` |
| A loaded container's digest doesn't match its content, but nothing in the web UI says so | Known gap: `digest_ok` is computed and exposed by the CLI/library but not yet surfaced in the web UI (tracked in [§7](#7-maintenance-procedures)) | Check from the CLI instead: `cli.py ingest <file>` prints a warning line to stderr when `digest_ok` is false |
| Export writes an obviously invalid value (e.g. text into an Integer field) with no error, from the web UI | Known gap: the web export path doesn't call `calovride.validate_value()` the way the CLI's `set`/`add` do (tracked in [§7](#7-maintenance-procedures)) | Validate the value yourself before typing it in, or use the CLI's `set`/`add`, which do validate |
| An exported module with an empty array element can't be re-ingested | Known round-trip gap: the parser rejects an empty `<ArrayValue/>` the serializer is willing to write (tracked in [§7](#7-maintenance-procedures)) | Avoid leaving an array cell empty before exporting; fill it with an explicit value first |

## 7. Maintenance procedures

**Re-verifying the core format claim:** the 28/28 byte-exact round-trip of
`caltool/calovride.py` against real containers should be re-run any time that module
changes. The reference containers and the re-verification method are described in
`CALIBRATION_CUSTOMIZATION_GUIDE.md` §5.

**Known gaps, tracked but not yet fixed** (found by a 2026-11-22 code review — see
`CHANGELOG.md`'s last entry for the full context of each):
- Web export performs no value validation (`web/app.py` never calls
  `calovride.validate_value()`, unlike `cli.py`).
- An array value containing an empty element round-trips to XML this tool can't
  re-ingest (`calovride.py`'s array parsing uses `.text`, which is `None` for an empty
  element, where scalar parsing already correctly uses `.findtext`).
- A container's `digest_ok: false` flag is computed but never surfaced in the web UI
  (CLI-only today).
- Zip-member decompression during a `.zip` upload has no size cap (the two gzip layers
  inside each member do, via `_bounded_decompress`, but the outer `zipfile` read does
  not).
- Several malformed export payload shapes return HTTP 500 instead of a clean 400.
- `BinaryFile` `Length`/`Checksum` fields are never verified on ingest or recomputed on
  edit (`calovride.verify_checksum()` exists but has no caller).

**Known, deliberately deferred limitations** (accepted trade-offs, not bugs — do not
"fix" these without discussion): a from-scratch `pack --template` repack of an
unmodified container is not byte-identical to the genuine original (Python's gzip
writes different XFL/OS header bytes than GM's own tool; the digest is still always
correctly recomputed over whatever bytes are actually present, so this doesn't affect
correctness); the local CalDef database's declared version for a given calibration
often differs from the version an actual shipped override uses (no way to know which
version a brand-new, never-shipped entry "should" claim); true concurrent (not just
rapid-sequential) CLI writes to the same JSON file can lose an update, same as any
unlocked file write; and the narrow-width (under ~450px) web layout can still scroll
horizontally at the page level in extreme cases.

## 8. Appendices

**CalOvride XML format**, verified byte-for-byte against every genuine LTZ and HC
container on this platform (28/28, independently re-verified — see the customization
guide §5): CRLF line endings, 2-space indent per nesting depth, no trailing newline, a
self-closing root when empty, and the twelve override value types listed in
[§3](#3-component-descriptions).

**Reference material:**
- [`CALIBRATION_SLOT_MAP.md`](../../research/eeprom-calibration/CALIBRATION_SLOT_MAP.md)
  — the full per-slot content catalog this toolkit's `/help` page condenses.
- [`CALIBRATION_CUSTOMIZATION_GUIDE.md`](../../research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md)
  — the safe-to-try/avoid risk triage; read before writing anything to real hardware.
- [`CHANGELOG.md`](CHANGELOG.md) — the frozen, dated history of reviews and fixes to
  this toolkit itself.
