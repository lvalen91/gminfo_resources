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
and, for human editing, as either a native macOS app or a local web UI.
The folder is self-contained: copy it anywhere and run it, with nothing to `pip install`.

**Key terms:**
- **CalOvride** — GM's XML schema for a set of calibration value overrides (see
  [§8 Appendices](#8-appendices) for the verified byte-level format).
- **CSM container** — the signed, gzip-wrapped container format that CalOvride XML
  ships inside on real hardware (`caltool/container.py`).
- **CalDef** — GM's reference database of ~3,000 known calibration definitions across
  ~145 groups (name, type, default, description); `caltool/caldef.py` loads the copy
  bundled in `data/caldefs/`.
- **Safety gate** — a deliberate friction control (not a security boundary) that
  requires explicit acknowledgment before editing an entry from a CalDef group this
  toolkit treats as elevated-caution. See [§3](#3-component-descriptions).

**Scope:** this README covers the toolkit's own behavior and how to run it. It does
**not** re-derive vehicle-specific facts — which calibration actually does what, which
slots are safe to touch, what's been proven on a real bench — that material lives in
[`CALIBRATION_SLOT_MAP.md`](docs/CALIBRATION_SLOT_MAP.md)
and
[`CALIBRATION_CUSTOMIZATION_GUIDE.md`](docs/CALIBRATION_CUSTOMIZATION_GUIDE.md).
Read both before using this tool's output on anything you intend to write to real
hardware — this toolkit produces correctly-formatted payloads, it does not tell you
what a given change actually does.

## 2. System overview

Four surfaces share one core. Both interactive UIs go through the same backend,
`caltool/service.py`, so loading, validation, search, the safety gate and export behave
the same in each:

```
  ┌────────────┐  ┌──────────────────┐        ┌──────────┐  ┌─────────────┐
  │ Desktop UI │  │      Web UI      │        │   CLI    │  │ Your script │
  │  (gui.py)  │  │ (web/app.py +    │        │ (cli.py) │  │             │
  │            │  │    editor.js)    │        │          │  │             │
  └─────┬──────┘  └────────┬─────────┘        └────┬─────┘  └──────┬──────┘
        └────────┬─────────┘                       │               │
                 ▼                                 │               │
        caltool/service.py                         │               │
                 └───────────────┬─────────────────┴───────────────┘
                                 ▼
        calovride.py (XML)   container.py (CSM wrapper)   caldef.py (lookups, gate)
                                                          └── data/caldefs/
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
- **`caltool/service.py`** — the shared backend of the two interactive UIs. Put
  behaviour here, not in a front end.
- **`gui.py`** — the native desktop UI (AppKit via PyObjC, macOS only). No server and no browser.
- **`run.py`** — the single entry point (`gui`, `web`, `cli`, `selftest`).
- **`vendor/`** — Flask 3.1.3 and its dependencies as pure Python, for the web UI.
- **`vendor_mac/`** — PyObjC 12.2.2 core and Cocoa (universal2, CPython 3.14 only), for
  the desktop UI. Licenses are in each `*.dist-info`.
- **`data/`, `docs/`, `tests/fixtures/`** — copies of repo material; see [§7](#7-maintenance-procedures).
- **`cli.py`** — the agent/LLM-friendly surface: every subcommand that emits data
  defaults to JSON on stdout, and every edit is a plain argument, nothing interactive.
- **`web/app.py` + `web/static/editor.js`** — the local human-editing surface. Kept
  deliberately simple (no build step, no framework) so the whole client is one readable
  file; see inline comments there for UI-specific design rationale (e.g. why the
  add-entry search is scoped per-module rather than global).

## 4. Installation / setup

Nothing to install into the folder. Copy it anywhere and run:

```sh
python3 run.py selftest
```

**Requirements**

| Mode | Needs |
|---|---|
| `cli` | Python 3.9+ (standard library only) |
| `web` | Python 3.10+; Flask comes from `vendor/` |
| `gui` | macOS and Python 3.14, which the bundled PyObjC is built for |

`gui` with another Python version works only if that Python has its own PyObjC. The
selftest skips, and names, whatever the current interpreter cannot run.

CalDef lookups read `data/caldefs/`. To use a different database, set
`CALTOOL_CALDEF_DIR` to its `caldefs` directory. `GMINFO_REPO_ROOT` is no longer read.

## 5. Usage instructions

### CLI

```sh
# Parse a signed container, an unwrapped container, or a bare .calovride file to JSON
python3 run.py cli ingest /path/to/spsCacheInternal/85102312 > slot0c.json

# Look up anything in the ~145 CalDef groups, including elevated-caution ones
python3 run.py cli explain SXM_Enabled
python3 run.py cli search carplay
python3 run.py cli groups
python3 run.py cli group GIS513_DeviceProjection

# Edit an existing entry, or add one that isn't present in the loaded file yet
python3 run.py cli set slot0c.json SXM_Enabled false
python3 run.py cli add slot0c.json Enable_Application_Apple_Carplay false

# Entries from an elevated-caution chime/safety group need an explicit flag -- see §3
python3 run.py cli add slot0c.json BEEP_2000_CHIME_GAIN 5 --i-understand-the-safety-risk

# Serialize back out -- plain XML, or a full container reusing a genuine file's header
python3 run.py cli pack slot0c.json -o custom.calovride --xml-only
python3 run.py cli pack slot0c.json -o custom_container --template /path/to/spsCacheInternal/85102312
```

`IntegerArray`/`FloatArray`/`StringArray`/`EnumIntegerMap`/`EnumFloatMap`/`Record`/
`BinaryFile` values can be ingested and re-packed as-is, but adding or restructuring one
of these types isn't exposed as a CLI flag — edit the ingested JSON directly (the shapes
match `caltool/calovride.py`'s dataclasses) and `pack` it.

### Desktop UI (macOS)

```sh
python3.14 run.py gui                       # then File > Open
python3.14 run.py gui 85102312 set.zip      # or pass files to open
```

A native AppKit window built to Apple's Human Interface Guidelines (sidebars, toolbars,
split views, lists and tables, alerts, the menu bar, toggles), so it follows the system's
light or dark appearance:

- **Sidebar:** loaded modules by slot, with part number and edit count.
- **Table:** entries grouped by CalDef group, enumeration values shown by label. Filter
  with the toolbar search, the All / Edited / Caution control and the type pop-up.
- **Inspector:** a switch for booleans, a pop-up for enumerations (with Custom Value…),
  a field for other scalars. Changes apply immediately and are validated; errors appear
  beside the control. Revert restores the loaded value. Structured types are read-only.
- **Add Entry** (toolbar or ⇧⌘N) is a sheet that searches the whole CalDef reference.
- **Export** (toolbar or File menu): container (⌘E), XML (⇧⌘E) or all as zip (⌥⌘E).

Elevated-caution entries ask for confirmation when added, and again at export if added or
changed; neither alert has a default button. Digest mismatches and skipped files are
shown above the table. The app refuses to save over a file you loaded in the same
session. The Dock shows the generic Python icon because this is not a packaged `.app`.

### Web UI

```sh
python3 run.py web                       # --port N to change it
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
| `no .caldef files found in …` | `data/caldefs/` is missing, or `CALTOOL_CALDEF_DIR` points elsewhere | Unset the variable, or refresh the bundle with `sync_bundle.py` |
| `the desktop UI needs Python 3.14` | The bundled PyObjC does not match this interpreter | Use `python3.14`, or see [§4](#4-installation--setup) |
| `'<name>' is ambiguous -- defined under 2 different groups` | One of 154 real CalDef names that collide across two `.caldef` groups with different CalIDs | Use `caldef.lookup_in_group(name, group)`, or the literal CalID, to disambiguate; `cli.py set` on an already-ingested entry resolves this automatically via the entry's own CalID |
| `SafetyGateError` on `add`/`set`, or a confirm dialog in the web UI that won't go away | The entry belongs to an elevated-caution CalDef group ([§3](#3-component-descriptions)) | Read `CALIBRATION_CUSTOMIZATION_GUIDE.md` §3, then pass `--i-understand-the-safety-risk` on the CLI or confirm the dialog in the web UI — this is a deliberate speed bump, not a bug |
| Web UI's "+ Add entry" shows a result as "not supported here" | The CalDef entry is an array/map/record/binary type, not yet addable from the web UI | Add it via `cli.py add` isn't available for these types either — ingest to JSON, hand-edit the entry matching `caltool/calovride.py`'s dataclass shape, then `pack` |
| An exported module with an empty array element can't be re-ingested | Known round-trip gap: the parser rejects an empty `<ArrayValue/>` the serializer is willing to write (tracked in [§7](#7-maintenance-procedures)) | Avoid leaving an array cell empty before exporting; fill it with an explicit value first |

## 7. Maintenance procedures

**Re-verifying the core format claim:** the 28/28 byte-exact round-trip of
`caltool/calovride.py` against real containers should be re-run any time that module
changes. The reference containers and the re-verification method are described in
`CALIBRATION_CUSTOMIZATION_GUIDE.md` §5.

**Bundled copies:** `data/`, `docs/` and `tests/fixtures/` are generated copies. Edit
the originals in a `gminfo_resources` checkout, then refresh (or check for drift):

```sh
python3 sync_bundle.py /path/to/gminfo_resources
python3 sync_bundle.py /path/to/gminfo_resources --check
```

Links in the copied guides that point outside the bundle become plain repo paths.
`slotinfo.py` and the web help page remain hand-condensed from the slot map.

**Tests:** `python3 run.py selftest` runs offline. It uses an unsigned synthetic
container built around the bundled sample document, so it does not replace the
real-container round-trip above.

**Known gaps, tracked but not yet fixed** (found by a 2026-11-22 code review — see
`CHANGELOG.md`'s last entry for the full context of each):
- An array value containing an empty element round-trips to XML this tool can't
  re-ingest (`calovride.py`'s array parsing uses `.text`, which is `None` for an empty
  element, where scalar parsing already correctly uses `.findtext`).
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
- [`CALIBRATION_SLOT_MAP.md`](docs/CALIBRATION_SLOT_MAP.md)
  — the full per-slot content catalog this toolkit's `/help` page condenses.
- [`CALIBRATION_CUSTOMIZATION_GUIDE.md`](docs/CALIBRATION_CUSTOMIZATION_GUIDE.md)
  — the safe-to-try/avoid risk triage; read before writing anything to real hardware.
- [`CHANGELOG.md`](CHANGELOG.md) — the frozen, dated history of reviews and fixes to
  this toolkit itself.
