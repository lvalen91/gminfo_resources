# Changelog

**Status:** frozen per entry — this is an append-only historical record. Once a dated
entry is written it is not edited or deleted, even if later work supersedes it; a
correction gets its own new entry. (See `README.md`'s doc-control header for the
distinction between this file and that one.)

Entries are grouped by date, oldest first within each date, newest date at the bottom.

## 2026-11-22

- `7895118` **feat:** added the calibration toolkit itself — CLI (`cli.py`), library
  (`caltool/calovride.py`, `caltool/container.py`, `caltool/caldef.py`), and a local
  Flask web UI, for ingesting, editing, and repacking GM CalOvride calibration modules.
- `545f2af` **fix:** `container.parse()` raised an uncaught exception on non-gzip input
  instead of a clean `ContainerError`.
- `61c1041` **fix:** enum label resolution never worked at all — the code assumed the
  wrong `EnumID`/`EnumValueDefinition` XML schema for the CalDef reference database.
- `67578fb` **feat:** zip import (a whole `spsCacheInternal/` directory in one upload),
  the multi-module list UI, enum dropdowns in place of raw integers, and info popovers.
- `2c5ba00` **fix:** the value column was clipped by an unconstrained `<select>` width
  on wide tables.
- `9addc9e` **fix, stress-tested via parallel agents (Fable analysis, Opus fixes):**
  - `calovride.serialize()` never escaped `&`/`<`/`>` — unescaped text could produce
    invalid XML or inject a sibling `<OverrideValue>` element past the safety gate.
  - The web UI flattened structured values (array/map/record/binary) to a display
    string and exported *that* string back — silently corrupting arrays and crashing
    on maps/records/binaries. Fixed with an authoritative `value_raw` field alongside
    the display `value`; confirmed via a live round-trip of all 10 types.
  - `cli.py set`/`add` validated nothing; any string could be written into any typed
    field. Added `calovride.validate_value()`.
  - The safety gate was enforced only client-side on add, never at export time — an
    already-loaded restricted entry could be edited with no gate at all. Added
    server-side enforcement in `/api/export` and `/api/export_zip`.
  - **The gate's own premise was found to be false and corrected**: its restricted
    groups were documented as "never shipped"; direct verification found 162 real
    entries from these groups already present in stock slot 04 alone. Renamed
    `NEVER_SHIPPED_SAFETY_GROUPS` → `SAFETY_RESTRICTED_GROUPS` (old name kept as a
    deprecated alias) and corrected the warning text.
  - 154 real CalDef names collide across two different `.caldef` groups with
    different CalIDs; `caldef.lookup()` now raises on ambiguity instead of silently
    picking whichever group loaded last.
  - `container.parse_any()` now genuinely never raises; `digest_ok` added so a
    tampered-but-structurally-valid container is flagged, not silently trusted.
  - Decompression capped at 16 MiB (zip-bomb protection); `export_zip` member names
    sanitized against path traversal and basename collisions.
  - `argparse`'s prefix-abbreviation let a bare `--i` silently satisfy
    `--i-understand-the-safety-risk`; abbreviation is now disabled.
  - Flask no longer runs with `debug=True`.
- `6477e3f` **redesign:** full editor UI redesign (grouped entry rows, elastic identity
  column, Boolean segmented toggle, coupled enum number+select, structured-type expand
  panels, light/dark theming), driven by two independent human-interface design research
  passes after a reported Name-column truncation bug.
- `a3b23d3` **fix, critical regression:** the above redesign broke every module after one
  edit or one collapse/expand — `renderModuleList()` destroyed and recreated each
  module's body `<div>` on every call, while the body-builder's lazy-render guard
  assumed the DOM would persist across calls. Fixed by splitting "build once"
  (`buildModuleShell`) from "update in place" (`updateModuleShell`); re-verified against
  the exact reported repro using real `.click()`/`dispatchEvent()` interactions, not
  direct state mutation.
- `96c0a02` **fix:** the CalDef search-results section (separate from the redesigned
  entry rows above) still dumped full, unclamped descriptions with a button whose
  position drifted with description length. Fixed with the same clamp-plus-fixed-column
  pattern already used for entry rows.
- `655c4bc` **redesign:** replaced the global "look up any calibration" section (which
  only worked if some module happened to already be expanded, tracked by a hidden
  `expandedIndex` global with no visible UI connection to it — reported as "detached and
  disorganized") with a per-module "+ Add entry…" control, scoped to its own module by
  JS closure instead of a global pointer. Design grounded in a researched spec citing
  real prior art (GitHub Projects' "Add item" row, Airtable/Notion's per-table
  "+ add field", Xcode's target-scoped "+ Capability").
- `aea5fb7` **fix:** a Fable-agent review of the above redesign found four regressions,
  confirmed live and fixed: a failed Add (e.g. one of the 154 ambiguous CalDef names)
  still marked the row "Added"; the add-time safety dialog showed no real warning text
  (wrong field read from the search-result shape vs. the full-entry shape); adding into
  a currently-filtered-out or collapsed group made the new entry invisible with no way
  to find it; and reloading a second file into a reused module slot left the old file's
  slot-summary text on screen. Also fixed in the same pass: the filter bar's sticky
  positioning broke when the redesign wrapped it in a new, shorter parent element.

  The same review surfaced further gaps **not yet fixed, tracked here as of this entry**:
  web export performs no value validation (the CLI's `validate_value` is not called from
  `web/app.py`); an array value with an empty element round-trips to XML this tool then
  cannot re-ingest; a container's `digest_ok: false` is surfaced in CLI output but never
  in the web UI; zip-member decompression has no size cap (only the two gzip layers do);
  malformed export payloads return HTTP 500 instead of a clean 400; and `BinaryFile`
  `Length`/`Checksum` fields are never verified or recomputed on edit. See `README.md`'s
  Maintenance section for current status of each.

## 2026-11-25 — self-contained folder and desktop UI

- CalDef database, linked guides, a sample document Flask (pure Python) and PyObjC are bundled;
  `sync_bundle.py` refreshes or checks the copies. `GMINFO_REPO_ROOT` is no longer read;
  `CALTOOL_CALDEF_DIR` overrides the bundled database.
- Added `run.py`, `tests/`, and a native AppKit desktop UI for macOS (`gui.py`).
- Moved shared UI behaviour from `web/app.py` into `caltool/service.py`. As a result the
  web UI now validates scalar/String values on export, caps zip member size, returns 400
  for the malformed export payloads covered by the tests, shows a digest-mismatch badge,
  and can add a CalDef name defined in two groups.
- `fix, two independent review passes (core library; web + desktop UI):`
  - `calovride.py`: an array value with an empty element now round-trips to XML this tool
    can re-ingest (the gap the previous entry tracked as open); `validate_value("Float", …)`
    rejects `inf`/`nan`; `Enumeration` values must now be integers (previously any string
    validated and was written into a container bound for hardware).
  - `web/app.py`: structured members (array/map/record) were never validated on export --
    only scalar/String was. A new `_check_structured` runs every structured member through
    the public `validate_value` at export time, closing the data-corruption gap the prior
    entry's own "not yet fixed" list named. Also: the 8 MiB upload cap was wrongly applied
    to export response bodies (a real container's export is ~26x larger than its on-disk
    size); invalid JSON returned werkzeug's HTML error page instead of a clean JSON error.
  - `editor.js`: ~154 CalDef names that exist in two different groups were matched by name
    only, so the second group's entry showed as already-present and could not be added, and
    "Show" jumped to the wrong row; now matched by name+group. CalDef search, the Add lookup,
    and export all had no network-error handling (a failed request could fail silently, or
    leave Add disabled forever). The structured-entry panel's "Reset to loaded value" just
    closed the panel instead of restoring it.
  - `gui.py`: `list.index()` compares dicts by value, so with two structurally-equal loaded
    modules, editing then reverting one could silently switch the sidebar selection to the
    other, and Remove Entry could delete the wrong duplicate -- now indexed by identity.
    Quit/Open could replace the module underneath an open Add sheet. A typed-but-uncommitted
    value could be lost on Quit/Open without being committed first.
  - Two regression tests added (`tests/test_toolkit.py`); full suite green before and after.
