# `fransys`

## Functions

### build

```python
def build(*drafts: Draft | Design, releases: Path | None=None) -> BuildResult
```

Output: merge, freeze and lay out drafts or a `Design` into a `BuildResult`.

Runs PLC allocation, numbering, every validator and layout, collecting each pass's findings.
The schematic lays out only when no `ERROR` was found and a `Document` keeps a SCHEMATIC
page; a layout `SymbolPortError` becomes one `SYMBOL_PORT_MISSING` `ERROR`. `releases` seeds
numbering pins from that release root; `None` numbers freely. Raises `FreezeError` on a
structural problem in the merged draft.

Does not write files, run `check` or raise on findings; does not seed pins when `releases`
is `None`.

### check

```python
def check(result: BuildResult) -> tuple[Finding, ...]
```

Output: collect every finding about a built model.

They are `build`'s, plus the KiCad, PDF and render checks.

Findings come back ordered `ERROR`, `WARNING`, `INFO`, then by `(code, subjects, message)`,
each message already run through `describe` so subjects read `file:line (key)`. The PDF and
render checks run only on a laid-out model (no `ERROR`, at least one `Document`); the KiCad
check always runs.

Does not raise on findings, write files or draw a page for a model that was never laid out.

### design

```python
def design(*libraries: str | ModuleType, place: str | None=None, wiring: Mapping[WiringRow, RowValue] | None=None) -> Design
```

Core: start a `Design` from part libraries or generated parts modules.

Each library is checked fresh.

`place` names the first location, as a bare tag. `wiring` maps rows (`fr.DC_SUPPLY`, ...)
to a colour or a (colour, size): it replaces those IEC 60204-1 default rows for the design.

Does not write files, build, or create devices.

### diff

```python
def diff(result: BuildResult, baselines: Path, *, unit: object=None, against: str | None=None) -> str
```

Output: return the Markdown change list from a stored release to the model as it stands now.

By default `a` is the release stored at the model's current revision, else the previous
released revision; `against="1.3"` names a sibling `<version>.<revision>` folder directly.
`unit` resolves as in `release`. Raises `FileNotFoundError` when no release is found,
`TypeError` or `ValueError` for a bad `unit`.

Does not write files; does not guess a release by likeness.

### document

```python
def document(preset: DocumentPreset, subject: object, *, cover: Path, add: tuple[PageKind, ...]=(), remove: tuple[PageKind, ...]=(), logo: Path | None=None, notice: str='') -> Draft
```

Output: author a document record from a preset, a subject and a cover file.

Returns a `Draft`.

Reads `cover` (a missing file raises `FileNotFoundError`) and the optional `<stem>.notes.md`
beside it (absent: no notes page); `logo` is an optional SVG for the title block (missing
raises); `notice` is the title block's IP notice
text. Texts are stored in the record. `subject` is what `d.location(...)` returns, a
`Device`, a unit release name (`str`) or `None` (the `system` preset only);
any other value raises `TypeError`. Key: the cover stem, preset and subject, so documents
may share a cover path.

Does not build, render or read files at render time; has no `notes` argument.

### export_names

```python
def export_names(result: BuildResult, *, unit: object=None) -> dict[tuple[str, Id[Any] | None], str]
```

Read: the path from out_dir that `write` gives each export of `result`, by `(kind, subject)`.

A kind is `"bom"`, `"plc"`, `"wires"`, `"designations"`, `"overview"`, `"cables"` or `"cores"`
(subject `None`), `"terminals"`, `"connectors"` or `"wago"` (the strip, board or rack id), or
`"pdf"` (the document id). `unit=` is `write`'s. Writes nothing and compiles no PDF; raises what
`write` raises for a bad `unit` or a name two subjects share (`ExportNameClash`).

Does not write a file, compile a PDF or run `check`.

### lint

```python
def lint(*libraries: str) -> tuple[Finding, ...]
```

Read: lint part libraries by import name and return their findings.

Each root resolves as in `parts`; findings come library by library, in the order given, with
the part file and line already in the message. Zero libraries give `()`.

Does not build a model, load a library into a Draft or raise on findings.

### parts

```python
def parts(*packages: str) -> Draft
```

Detail: load part libraries by import name and merge them into one `Draft`.

For a draft that holds only parts, to merge beside other drafts. Try `fr.design(...)` first:
it loads its libraries itself.

Each name is an installed part-data package, loaded through `fransys_parts.load`. Zero
names give an empty Draft. Pass the result to `build` beside other drafts.

Does not build, lint or freeze; does not accept a folder path (use an import name).

### parts_module

```python
def parts_module(*sources: str) -> str
```

Detail: the text of the typed parts module for the libraries `sources` name.

For typed part classes in your editor. Try `fr.design(...)` with an MPN string first.

Does not write a file: `python -m fransys parts-module` does.

### readability

```python
def readability(result: BuildResult) -> ReadabilityReport
```

Read: one row for each schematic page of `result`, and one for each unit.

A page row counts what a reader of the print feels: the profile's text height against
`min_text_height_mm`, how much of the page the drawing fills, wires crossing wires, text struck
by a wire, text overlaps, cells alone on a page, and the references the page makes. A unit row
adds its pages up. Pure: the same model gives the same rows. The layout runs again on
`result.model`, as `build` ran it, so the cost is about that of the layout.

Does not write a file, emit anything from `write`, or raise on findings.

### release

```python
def release(result: BuildResult, into: Path, *, unit: object=None) -> Path
```

Output: release a unit, or the system, as a frozen baseline under `into`.

Writes `<into>/<name>/<version>.<revision>/`: the unit's exports as `write` makes them,
`baseline/` (listing, model, manifest) and, after a first release, `changes.md` and
`changes.csv`. Runs the same gate as `write` plus the release checks: any `ERROR`
raises `BuildErrors` and writes nothing. An identical stored listing text returns the
existing path untouched. Files are built in a temporary sibling and renamed, so a failure
leaves nothing behind.

Does not release when `check` finds an ERROR; does not overwrite an identical release.

### releases

```python
def releases(root: Path) -> tuple[Release, ...]
```

Output: every release folder under `root`, read from its manifest.

They come in name, version, revision order.

`root` holds `<name>/<version>.<revision>/` folders, as `fr.release` writes them. Versions and
revisions sort as integers. A folder with no manifest is listed with empty `interface`,
`listing_digest`, `nested` and `files`. A missing `root` gives `()`.

Raises:
    ValueError: a manifest does not parse or lacks a key; the message names its path.

Does not write files, check a file's hash or read any model.

### report

```python
def report(result: BuildResult) -> str
```

Output: one text of `fr.check(result)`.

It holds a summary line, each ERROR and WARNING, then the notes.

Each ERROR and WARNING prints its message, then an `at:` line per subject, its fix and its
findings-row URL from the code's registry entry. INFO notes print counted per code on one line.
The text only reads the findings and their `CodeInfo`; it adds no rule of its own.

Does not write files, raise on an ERROR, or drop a finding.

### unit

```python
def unit(name: str, *, revision: int, interface_version: int | str, date: str, text: str, by: str, version: int=1, title: str='', number: str='', history: Sequence[Mapping[str, str | int]]=(), class_code: str | None=None, wiring: Mapping[WiringRow, RowValue] | None=None) -> Callable[[Callable[..., R]], UnitDef[R]]
```

Core: make a function the unit release `name`.

It takes a child design and returns its interface.

The interface is an instance of a `typing.NamedTuple` class, one field per boundary.

Does not build anything: `d.add(fn, "U1")` does. `history` entries take `d.revision`'s keywords.
`class_code` (1-3 uppercase letters) is the letter floating instances number from.
`wiring` replaces IEC rows in the unit's body; a unit never takes its parent's rows.

### verify

```python
def verify(result: BuildResult, baselines: Path) -> tuple[Finding, ...]
```

Output: return one `BASELINE_DIFFERS` `ERROR` per unit instance, or the system, that drifted.

Compares the rebuilt listing digest with the stored one under `baselines`, for every unit
and for the system when the model holds a `Project`. The model digest is never compared.
Also re-hashes every release file: `RELEASE_FILE_CHANGED`, `RELEASE_FILE_MISSING`.
Meant for a consumer's test, wherever they want it.

Does not write files, release or gate `write`; does not report a unit with no stored baseline.

### write

```python
def write(result: BuildResult, out_dir: Path, *, unit: object=None, intermediates: Path | None=None, releases: Path | None=None) -> tuple[Path, ...]
```

Output: write a built model's exports into `out_dir` and return their paths, sorted.

Writes CSV reports, WAGO XML, overview HTML and one PDF per document; `unit=` restricts them to
that unit's own set (no `overview.html`). Intermediates (SVGs, netlists, `.typ`
sources) go only to `intermediates`, if given. `releases` is a release root as `release`'s
`into`: with a stored release of the system there, `overview.html` marks what changed since it
(the release at the model's revision, else the previous one); `None` marks nothing. Any
`ERROR` in `check(result)` raises `BuildErrors` and leaves `out_dir` without an export,
whole-model, with no escape hatch.
Also raises `ExportNameClash`, `TypeError` or `ValueError` for a bad `unit`.

Does not write when `check` finds an ERROR; does not touch files in `out_dir` it does not own.

## Classes

### AcSupply

```python
class AcSupply
```

An AC supply: `L1`, `L2`, `L3` and `N` when it was given one.

Does not hold a voltage of its own: each rail's potential carries the declared voltage.

### AuthorError

```python
class AuthorError
```

A design mistake, caught at the call or, for a layout hint, at build.

### BuildErrors

```python
class BuildErrors
```

Raised by `write` or `release` when their own findings hold an `ERROR`.

No escape hatch: there is no `allow_errors`, `force` or `draft` parameter anywhere in
this package, and none will be added. `findings` holds every `ERROR` of the run that
raised; the exception's own message is each finding, then its fix and findings-row URL.
`write`'s own findings are resolved through `describe` first (`check`'s own contract);
`release`'s interface-bump findings are never `describe`d -- their `message` is already
self-contained, naming the unit, revision and differing sections in plain text.

### BuildResult

```python
class BuildResult
```

A frozen, laid-out model plus every finding collected while building it.

### Cable

```python
class Cable
```

One cable: `W1.core(BN, a, b)` wires a core by colour or number; a series lands it.

Does not guess a core: a doubled or missing colour raises and lists the candidates.

### DcSupply

```python
class DcSupply
```

A DC supply: `plus`, `minus` and `mid` when the source has an M conductor.

Stands in a series whole, as a power path's poles, or by one rail, as a control path's.
Does not have a `mid` rail unless the source has an M conductor.

### Design

```python
class Design
```

One circuit under construction, built through one engine `Design`.

Does not start a design: call fr.design.

### Detail

```python
class Detail
```

The detail calls of one design: `d.detail.wire`, `star`, `net`, `busbar` and `rail_bond`.

Each is for a case no core call writes; try `d.series` first.
Does not pair poles or take the next free terminal, as `d.series` does.

### Device

```python
class Device
```

One device: `Q1`. A function by name (`Q1.coil`), a pin by `[ ]` (`Q1[2]`, `Q1["A1"]`).

Does not guess: an unknown function or pin raises and lists the candidates.

### DocumentPreset

```python
class DocumentPreset
```

The kind of deliverable a `Document` defines.

Example: `CABINET_SCHEMATIC` is the document of one cabinet. A preset fixes the default
page kinds; a new one needs a decision record.

### Draft

```python
class Draft
```

The only mutable type in the repo. Collects records before `freeze()`.

Accepts a duplicate `add` of identical content as a no-op; a conflicting `add` under
the same id raises `MergeConflict` immediately, naming both origins. Nothing here
depends on the order things were added in: the accessors sort. A draft that raised is
to be discarded, not repaired.

### Finding

```python
class Finding
```

One reported engineering problem: one shape for every domain validator.

`code` is a stable `UPPER_SNAKE` string (e.g. `NET_UNREALISED`), listed in the module
that emits it. `subjects` names the ids the finding is about, stored in `Id` order so
that neither the order a validator happened to find them in nor a repeat matters.

Attributes:
    code: A stable `UPPER_SNAKE` string identifying the kind of problem (e.g.
        `NET_UNREALISED`), listed in the module that emits it.
    severity: How much this finding should block a downstream output.
    subjects: The ids this finding is about, stored once each, in `Id` order.
    message: The human-readable text of the finding.

### Fn

```python
class Fn
```

One function of a device: `K1.coil`; a pin by `[ ]` (`Q1.main[2]`) or by name (`K1.coil.A1`).

Does not accept a guessed name: an unknown pin raises and lists the pins it has.

### FreezeError

```python
class FreezeError
```

Aggregates every error `freeze()` found.

So an author fixes a batch, not one error per run.

### Layout

```python
class Layout
```

The drawing hints of one design, each written through the engine.

Does not draw or place anything itself: every hint only advises the layout engine.

### MergeConflict

```python
class MergeConflict
```

Two drafts or models declare the same id with different content.

Nothing wins silently: both origins are named.

### Model

```python
class Model
```

The immutable, validated result of `freeze()`.

Not a `@value`: it is never nested in a record, and `tables` is keyed by `Id`,
outside the closed set `@value` enforces on its fields.

Everything reachable from a `Model` is deeply immutable, checked at freeze, not
assumed. `tables` stays generic here (`kind -> id -> record`); `vocab` adds typed
accessors (`items(model)`, `ports(model)`, ...) over it. `digests` holds one digest
per registered namespace, so a change to `layout.*` records leaves the `core` and
`facet` digests alone; `digest` combines them (design/kernel-model.md 5.6).

### PageKind

```python
class PageKind
```

A kind of page in a document, in the one canonical page order.

Declaration order is the canonical order: a document's pages are its preset's pages plus
`add`, minus `remove`, in this order, so no project specifies one. The set is closed.

### PartLibraryError

```python
class PartLibraryError
```

A part library failed `lint`; `findings` holds every finding of that run.

Warnings included, not only the `ERROR`s that triggered the raise: a caller
fixing the library wants the whole report, not a partial one.

### Pin

```python
class Pin
```

One port of one `Fn`, reached by its marking or role.

Attributes:
    id: This port's id.
    key: This port's authoring key.
    name: The marking `__getitem__` matches it by.
    role: What this port is for (e.g. `INTERNAL`/`EXTERNAL`).

### Release

```python
class Release
```

One release folder under a releases root, read from its manifest.

`name`, `version` and `revision` come from the folder's path. `interface`, `listing_digest`,
`nested` and `files` (path, sha256 pairs) come from `baseline/manifest.json`; a folder with no
manifest has them empty. `path` is the folder.

### ReleasePin

```python
class ReleasePin
```

A release nested in another, as its manifest records it.

### Run

```python
class Run
```

`count` terminals of a strip that count up inside their own label, from 1.

Does not share numbering with the strip or another run; a series may name it as a strip.

### Severity

```python
class Severity
```

How much a `Finding` should block a downstream output.

Fransys, not this repo, decides which severities block which outputs.

Attributes:
    INFO: Worth noting; blocks nothing in the facade's own policy.
    WARNING: Worth a look; also blocks nothing in the facade's own policy.
    ERROR: Blocks every export: the facade's `write` raises and writes nothing while
        any `Finding` of this severity remains.

### SignalType

```python
class SignalType
```

The electrical nature of a PLC channel or field request, read as `fr.SignalType`.

Example: a 4-20 mA transmitter requests `AI_CURRENT`; a Pt100 requests `RTD`.
`fr.DI`, `fr.DO`, `fr.AI` and `fr.AO` stay the spelling for `DI`, `DO`, `AI_CURRENT` and
`AO_CURRENT`; this enum is the home of every other signal, such as `fr.SignalType.RTD`.

### SupplyRail

```python
class SupplyRail
```

One rail of a supply: its source pin, the potential it carries and its conductor mark.

Does not wire itself: it stands in a `series` as a one-conductor element.

### Terminal

```python
class Terminal
```

One terminal of a `Strip`: one function, ports `inner`/`outer`.

Attributes:
    id: This terminal's id.
    key: This terminal's authoring key.
    function: This terminal's one function, whose ports `inner` and `outer` reach.

### TerminalStrip

```python
class TerminalStrip
```

One strip: `X1[3]` is its terminal 3, made on first use and the same handle after.

A terminal joins the function block it is first taken in, else the strip's own group.
Does not pick a terminal for `X1[3]`: a number is explicit; `take` picks the next free ones.

### Throw

```python
class Throw
```

One throw of changeovers in a series: line at the common, load at the throw.

A selector (its throws on the line side, or a `d.poles` group with `selector=True`) is
entered at the throws and left at the commons. Several functions are one pole each, in order.

Does not wire by itself: it stands in a `d.series` call.

### TypedDevice

```python
class TypedDevice
```

The base a generated module subclasses for one part; `mpn` is its whole contract.

`N` is the part's function names and `S` the subclass itself: `device` types `interface=` by
one and returns the other.

Does not add behaviour: its subclass only declares functions and pins.

### TypedFn

```python
class TypedFn
```

The base a generated module subclasses for one function of one part.

Does not add behaviour: its subclass only declares pins for the type checker.

### UnitDef

```python
class UnitDef
```

A function made a unit by `@unit`: the release facts `d.add` writes.

Does not run the function; `d.add` builds the child and calls it.

## Constants

### ABOVE

```python
ABOVE: Side
```

### AC_CONTROL

```python
AC_CONTROL: WiringRow
```

### AC_L1

```python
AC_L1: WiringRow
```

### AC_L2

```python
AC_L2: WiringRow
```

### AC_L3

```python
AC_L3: WiringRow
```

### AC_N

```python
AC_N: WiringRow
```

### AI

```python
AI: SignalType
```

### AO

```python
AO: SignalType
```

### BELOW

```python
BELOW: Side
```

### CONTROL

```python
CONTROL: NetClass
```

### DC_CONTROL

```python
DC_CONTROL: WiringRow
```

### DC_GROUND

```python
DC_GROUND: WiringRow
```

### DC_SIGNAL

```python
DC_SIGNAL: WiringRow
```

### DC_SUPPLY

```python
DC_SUPPLY: WiringRow
```

### DI

```python
DI: SignalType
```

### DO

```python
DO: SignalType
```

### EARTHED

```python
EARTHED: Earthing
```

### GENERIC

```python
GENERIC: NetClass
```

### IT

```python
IT: Earthing
```

### SIGNAL

```python
SIGNAL: NetClass
```

### derive

```python
derive: submodule
```
