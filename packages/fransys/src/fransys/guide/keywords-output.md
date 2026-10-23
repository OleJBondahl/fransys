# Keywords of the fr functions

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page has one table for each `fr.*` function: each named keyword, its default, its effect and an example call fragment.
A call that takes only `*args` has no table, and one sentence says what it takes.

The tier of each call is the first word of its docstring (index.md, Tiers).
The design calls are in `keywords-design.md`, the handle methods and layout hints in `keywords-handles.md`.

## `fr.design`

`fr.design(*libraries, ...)` takes the part libraries or generated parts modules as `libraries`.

| keyword | default | effect | example |
|---|---|---|---|
| [`place`](authoring.md#name-a-place-and-a-function-block) | `None` | Names the first location as a bare tag. With `None` the design has no location until you call `d.location`. | `fr.design("demo_parts", place="C1")` |
| [`wiring`](series.md#colour-by-what-a-wire-carries) | `None` | Replaces the default wire colour and size of the rows it names, for this design. Rows not named keep the IEC 60204-1 default. | `fr.design("demo_parts", wiring={fr.DC_SUPPLY: (BU, 1.5)})` |

## `fr.unit`

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The unit release name. Instances print it, and the release folder under `fr.release` carries it. | `@fr.unit("pump-board", revision=2, ...)` |
| [`revision`](units.md#recording-revisions) | required | The current revision. It is the last entry of the unit's history. | `revision=2` |
| `interface_version` | required | The unit's boundary version. You bump it by hand when the interface changes. | `interface_version=1` |
| [`date`](units.md#recording-revisions) | required | Date of the current revision, as written in its history entry. | `date="2026-01-01"` |
| [`text`](units.md#recording-revisions) | required | What the current revision changed, as written in its history entry. | `text="added the fuse"` |
| [`by`](units.md#recording-revisions) | required | Who made the current revision. It prints in the history as `created`. | `by="AB"` |
| [`version`](units.md#recording-revisions) | `1` | The release version. Revisions count within a version, and `fr.release` names the folder `<version>.<revision>`. | `version=2` |
| `title` | `''` | The unit's own title-block title. Empty gives a `TITLE_BLOCK_UNIT_IDENTITY_MISSING` warning on its document. | `title="Pump board"` |
| `number` | `''` | The unit's own title-block number. Empty gives a `TITLE_BLOCK_UNIT_IDENTITY_MISSING` warning on its document. | `number="DWG-101"` |
| [`history`](units.md#recording-revisions) | `()` | Earlier revisions of the unit. Each entry is a mapping of the `d.revision` keywords `revision`, `date`, `text` and `created`. | `history=[{"revision": 1, "date": "2025-12-01", "text": "first", "created": "AB"}]` |
| [`class_code`](parts.md#class-codes) | `None` | One to three capital letters. A floating `d.add(fn, None, name=...)` numbers from this class. `None` gives no class, so a floating add raises. | `class_code="B"` |
| [`wiring`](series.md#colour-by-what-a-wire-carries) | `None` | Replaces wire colour and size rows inside this unit's body only. A unit never takes its parent's rows. | `wiring={fr.DC_SUPPLY: (BU, 1.5)}` |

## `fr.document`

`fr.document(preset, subject, ...)` takes the preset and the subject as positional arguments.

| keyword | default | effect | example |
|---|---|---|---|
| [`preset`](documents.md#presets-cover-and-notes-text) | required | The `fr.DocumentPreset` that fixes the deliverable's default page kinds (documents.md). | `fr.document(fr.DocumentPreset.SYSTEM, None, cover=Path("cover.md"))` |
| [`subject`](documents.md#subjects) | required | What the document is about: what `d.location(...)` returns, a `Device`, a unit release name, or `None` for the system preset. Another value raises `TypeError`. | `fr.document(preset, "pump-board", cover=cover)` |
| [`cover`](documents.md#presets-cover-and-notes-text) | required | The Markdown cover file, stored verbatim. Its stem is the document's key. A missing file raises `FileNotFoundError`. A `<stem>.notes.md` beside it becomes the notes page. | `cover=Path("cover.md")` |
| [`add`](documents.md#presets-cover-and-notes-text) | `()` | `fr.PageKind` values added to the preset's default pages. | `add=(fr.PageKind.HARNESS_DRAWING,)` |
| [`remove`](documents.md#presets-cover-and-notes-text) | `()` | `fr.PageKind` values removed from the preset's pages. | `remove=(fr.PageKind.NOTES,)` |
| [`logo`](documents.md#presets-cover-and-notes-text) | `None` | An SVG file for the title block's logo cell. `None` leaves the cell empty. A missing file raises. | `logo=Path("logo.svg")` |
| [`notice`](documents.md#presets-cover-and-notes-text) | `''` | The title block's IP notice text, printed on every page of this document. Empty leaves the cell empty. | `notice="Property of Demo Ltd"` |

## `fr.readability`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The `BuildResult` to measure. It reads the drawings the build kept and lays nothing out again; the call returns one row per drawn page, each naming its unit. | `fr.readability(result)` |

## `fr.settings`

`fr.settings(path=None, *, paper=None)` returns a `fr.Settings`: our defaults, the consumer's TOML file on top, and `paper` per drawing type (settings.md).

| keyword | default | effect | example |
|---|---|---|---|
| [`path`](settings.md#the-toml-file) | `None` | The consumer's TOML file, merged key by key over our defaults. `None` gives our defaults. | `fr.settings("fransys.toml")` |
| [`paper`](settings.md#the-paper-per-drawing-type) | `None` | A mapping of a `fr.PageKind` to a paper format's name, for that drawing type. | `fr.settings(paper={fr.PageKind.BLOCK_DIAGRAM: "A2"})` |

## `fr.build`

`fr.build(*drafts, ...)` takes the drafts or `Design` objects to merge as `drafts`.

| keyword | default | effect | example |
|---|---|---|---|
| [`releases`](build.md#keeping-designations-fixed-across-revisions) | `None` | A release root. Numbering pins are seeded from the releases stored there, so a released unit keeps its numbers. `None` numbers freely. | `fr.build(d, releases=Path("releases"))` |
| [`settings`](settings.md#frsettings) | `None` | The `fr.Settings` from `fr.settings(...)`, used for this build. `None` uses our defaults. | `fr.build(d, settings=fr.settings(paper={fr.PageKind.BLOCK_DIAGRAM: "A2"}))` |

## `fr.check`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The `BuildResult` to check. Returns its findings plus the KiCad, PDF and render checks, errors first. | `fr.check(result)` |

## `fr.report`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The `BuildResult` to report. Returns one text: a summary line, each ERROR and WARNING with its fix, then counted notes. | `print(fr.report(result))` |

## `fr.write`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The built model whose exports are written. Any ERROR in `fr.check(result)` raises `BuildErrors` and writes nothing. | `fr.write(result, Path("out"))` |
| [`out_dir`](build.md#export-file-names) | required | The folder that receives the exports: the CSV reports, WAGO XML, overview and one PDF per document. | `fr.write(result, Path("out"))` |
| [`unit`](units.md#writing-one-unit) | `None` | Writes only that unit's own set, with no `overview.html`. `None` writes the whole model. | `fr.write(result, out, unit="pump-board")` |
| [`intermediates`](build.md#export-file-names) | `None` | A folder for SVGs, netlists and `.typ` sources. `None` keeps them in memory. | `intermediates=Path(".fransys")` |
| [`releases`](build.md#export-file-names) | `None` | A release root. With a stored release of the system there, `overview.html` marks what changed since it. `None` marks nothing. | `releases=Path("releases")` |

## `fr.export_names`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The `BuildResult`. Returns the file name `fr.write` gives each export, keyed by kind and subject. Writes nothing. | `fr.export_names(result)` |
| [`unit`](build.md#export-file-names) | `None` | Names only that unit's exports, as `fr.write(unit=)` would. `None` names the whole model's. | `fr.export_names(result, unit="pump-board")` |

## `fr.release`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The built model to release. Any ERROR raises `BuildErrors` and writes nothing. | `fr.release(result, Path("releases"))` |
| [`into`](build.md#releasing-a-frozen-baseline) | required | The release root. The call writes `<into>/<name>/<version>.<revision>/`. An identical stored listing returns the existing path. | `fr.release(result, Path("releases"))` |
| [`unit`](build.md#releasing-a-frozen-baseline) | `None` | Releases that unit instead of the system. | `fr.release(result, into, unit="pump-board")` |

## `fr.releases`

| keyword | default | effect | example |
|---|---|---|---|
| [`root`](build.md#listing-the-releases) | required | The release root to read. Returns each release folder in name, version, revision order. A missing root gives `()`. | `fr.releases(Path("releases"))` |

## `fr.diff`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The built model to compare. Returns the Markdown change list against a stored release. | `fr.diff(result, Path("releases"))` |
| `baselines` | required | The release root that holds the stored release. A missing release raises `FileNotFoundError`. | `fr.diff(result, Path("releases"))` |
| `unit` | `None` | Compares that unit instead of the system. | `fr.diff(result, root, unit="pump-board")` |
| `against` | `None` | A `<version>.<revision>` folder to compare with. `None` takes the release at the model's revision, else the previous one. | `against="1.3"` |

## `fr.verify`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The rebuilt model. Returns one `BASELINE_DIFFERS` ERROR per unit instance, or the system, whose listing drifted, and an INFO (`BASELINE_RULES_MOVED`, `BASELINE_ROWS_UNCHECKED`) for a release cut by an older fransys: `fr.rebaseline` clears it. | `fr.verify(result, Path("releases"))` |
| [`baselines`](build.md#checking-a-baseline-stays-true) | required | The release root with the stored baselines. A unit with no stored baseline is not reported. | `fr.verify(result, Path("releases"))` |

## `fr.rebaseline`

| keyword | default | effect | example |
|---|---|---|---|
| `result` | required | The rebuilt model. Re-cuts each stored listing the current rules print differently, in `listing.json` and the manifest only, children before parents. Returns the folders rewritten, `()` when none. A real change raises `BuildErrors` with `BASELINE_DIFFERS` and writes nothing. | `fr.rebaseline(result, Path("releases"))` |
| `baselines` | required | The release root with the stored baselines. | `fr.rebaseline(result, Path("releases"))` |
| `unit` | `None` | `None` covers every unit and the system with a stored baseline. A unit covers it and the units below. | `fr.rebaseline(result, root, unit="pump-board")` |

## `fr.parts`

`fr.parts(*packages)` takes part-data package import names. It has no named keyword and returns one `Draft`. Zero names give an empty `Draft`. Example: `fr.parts("demo_parts")`.

## `fr.parts_module`

`fr.parts_module(*sources)` takes the library names to generate a typed parts module for. It has no named keyword and returns the module's text. Example: `fr.parts_module("demo_parts")`.

## `fr.lint`

`fr.lint(*libraries)` takes part-library import names. It has no named keyword and returns their findings, library by library. Zero libraries give `()`. Example: `fr.lint("demo_parts")`.
