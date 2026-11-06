# Building a design

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

`fr.build`, `fr.check` and `fr.write` are the three pipeline functions. `build` takes the design
(and any documents), merges them into a model and runs the passes, the validators, and layout
when there is a document. `check` collects every finding about a built model, including some
`build` never sees. `write` writes the model's exports to a directory. If any finding is an
`ERROR` it raises `BuildFailedError`, writes no export, and removes the exports an earlier `write` left
there. `check` also places the system overview (`overview.html`) and returns its findings.
`settings=fr.settings(...)` sets the build's paper (settings.md).

`fr.__version__` gives the installed version. It is not in `fr.__all__`.

## Where a build can fail

Four stages, each failing differently. A design call the builder refuses raises `fr.AuthorError`
at that call.

**1. Loading a part library.** `fr.design(...)` and `fr.parts(...)` lint every library they load
and raise `PartLibraryError` if linting finds an `ERROR`. 

**2. The build itself.** `fr.build(d, *documents)` merges the design with the documents, then
freezes the result into a `Model`. Two structural problems can raise here.

- `MergeConflictError`, when two records share one id with different content. It can raise at the second authoring call that creates the record.
- `FreezeError`, when freezing finds one or more structural problems inside the merged records: a
  dangling reference, a bad value, or a missing required field. It aggregates every problem it
  found in `.errors`, so an author fixes a batch in one pass.

A consumer meets this with two instances of one unit release authored with different content.

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-09-27", text="First", by="OJB")
def board_a(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


@fr.unit("demo-io-board", revision=1, interface_version=2, date="2026-09-27", text="First", by="OJB")
def board_b(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


conflict_design = fr.design("demo_parts")
conflict_design.add(board_a, "U1")

try:
    conflict_design.add(board_b, "U2")
except fr.MergeConflictError as e:
    assert "two different records share one id" in str(e)
    assert e.origin_a.file == e.origin_b.file
    assert e.origin_a.line != e.origin_b.line
else:
    raise AssertionError("expected MergeConflictError")
```

Both declare the release `demo-io-board`, revision 1, but with a different `interface`, so they
conflict instead of deduplicating. `e.origin_a` and `e.origin_b` name the call sites.

`fr.build(d)` always carries the design's part library. Only `d.draft()` leaves it out; building
that shows what a missing library does.

```python
d = fr.design("demo_parts")
x1 = d.device("X1", "DEMO-CONN-2P")

try:
    fr.build(d.draft())  # the authored records without the library
except fr.FreezeError as e:
    assert len(e.errors) == 4
else:
    raise AssertionError("expected FreezeError")
```

The missing library leaves four references dangling, one `RefError` each. `e.errors` holds all four.

Any other exception out of `build` is a Fransys bug. Report it as a field case.

**3. The validators.** Every domain validator runs inside `build`, but an `ERROR` finding from
one of them does not raise. It comes back in `fr.check(result)` and stops layout: the model is returned numbered but unlaid.

**4. `write`.** `write` computes `fr.check(result)` itself and raises `BuildFailedError` if any
finding in it is an `ERROR`, before touching `out_dir`. See below.

## `fr.check(result)` is the one list of findings

`fr.check(result)` returns every finding about a built model: the PLC and numbering passes, the
validators, layout and the board check, plus the drawing and PDF checks when it holds a document.

A cabinet with no device in it has nothing to draw. Its document holds the preset's pages, and
its empty lists are reported:

```python
from pathlib import Path

cabinet_cover = Path("cabinet.md")
cabinet_cover.write_text("# Cabinet\n")
c1 = d.location("C1", "Cabinet")
doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cabinet_cover)

result = fr.build(d, doc)
assert len(fr.check(result)) == 5
```

`fr.check(result)` holds four `DOCUMENT_EMPTY_LIST` `INFO` findings and one `ERROR`, `DOCUMENT_NO_DRAWINGS`,
that only the drawing and PDF checks find. The cabinet holds nothing, so the document has no drawing.

`write` runs the same check internally, so it raises on those errors:

```python
try:
    fr.write(result, Path("out"))
except fr.BuildFailedError as e:
    assert len(e.findings) == 1
    assert all(f.severity is fr.Severity.ERROR and f.fix for f in e.findings)
else:
    raise AssertionError("no error")
```

`e.findings` holds only the `ERROR` findings. `out_dir` is left with nothing written for this build.
`write` has no `allow_errors`, `force` or `draft` parameter.

## `fr.report(result)` prints them for a person or an agent

`fr.report(result)` returns one text of `fr.check(result)`. Its first line counts the errors,
warnings and notes. Each `ERROR` and `WARNING` follows with its message, one `at:` line per
subject (the authoring call's `file:line`), its fix, and its row's URL. The notes come last,
counted per code on one line.

```python
text = fr.report(result)
assert text.startswith("build: 1 error, 0 warnings, 4 notes\n")
assert "  see: https://olejbondahl.github.io/fransys/" in text
assert "/guide/findings-pdf/#document_no_drawings\n" in text
assert text.endswith("notes: DOCUMENT_EMPTY_LIST 4\n")
```

The fix and the URL come from the code's row in [`findings.md`](findings.md). Print the report on every build.

## Which route carries which finding

| route | carries | when you read it |
|---|---|---|
| `result.findings` | What `fr.build` collected: the PLC and numbering passes, the validators and layout. | After `fr.build`. |
| `fr.check(result)` | `result.findings` plus the KiCad, PDF and render checks, errors first. | Any time after `fr.build`. |
| `fr.report(result)` | The text of `fr.check(result)`, with each fix and the URL of its findings row. | Any time after `fr.build`. |
| `fr.BuildFailedError.findings` | The `ERROR` findings of the `fr.write` or `fr.release` run that raised. `fr.release` adds its checks. | When the call raises. |

## No document, no layout

Layout exists only to draw documents. A build with no `Document` draft skips layout; there is no flag.

```python
result = fr.build(d)  # no document this time
codes = sorted(f.code for f in fr.check(result))
assert codes == []

written = fr.write(result, Path("out"))
assert sorted(p.relative_to("out").as_posix() for p in written) == [
    "data/bom.csv",
    "data/cables.csv",
    "data/cores.csv",
    "data/designations.csv",
    "data/plc.csv",
    "data/wires.csv",
    "overview.html",
]
```

`fr.export_names(result, *, unit=None)` gives the name `write` gives each export, by `(kind, subject)`,
without writing anything. A kind is `bom`, `plc`, `wires`, `designations`, `overview`,
`cables`, `cores`, `terminals` or `connectors` (subject `None`); `wago` with the rack's id; or `pdf` with
the document's id. The key is a tuple: `("bom", None)` for a whole-set file, `("pdf", <document id>)`
for a document.

```python
names = fr.export_names(result)
assert names[("bom", None)] == "data/bom.csv"
assert [key for key in names if key[0] == "pdf"] == []  # no document: no ("pdf", id) key
assert sorted(names.values()) == sorted(p.relative_to("out").as_posix() for p in written)
```

With no document, `check` runs no drawing or PDF checks, and `write` writes no PDF.

## Export file names

One function builds every export name, so a script never constructs its own. The `v` prefix
appears only in file names, never in a title block or history table. The names have no option or template.

- **The set prefix.** Every file belongs to one set: the unit written (`unit=U`) or the
  system (`unit=None`). The prefix is `<set name>-v<V>.<R>`, the set's name plus its version and
  revision in `derive.revision_text`'s print form. A unit's name is its release name
  (`demo-io-board-v1.1`); the system's is the project's number (`EX-1-v1.1`). A system write of
  a model with no project record has no prefix: its own files keep bare names (`bom.csv`).
- **Prefix, kind, fragment.** A name is `<prefix>[-<kind>][-<fragment>].<ext>`:
  `demo-io-board-v1.1-bom.csv`, and per PLC rack `demo-io-board-v1.1-wago-U1.xml`.
- **Lists.** `terminals.csv` holds every strip, `connectors.csv` every board.
- **Where each list is.** A unit's cables stay in its own `cables.csv`; a parent sees the unit as a black box.
- **A PDF is named by its subject, not its cover file.** The set's own document is
  `<prefix>.pdf`. A document of an item or location inside
  the set adds that subject's fragment. A document whose subject is a unit takes that unit's
  name in every write, so `out/all/` holds `EX-1-v1.1.pdf` beside `cabinet-v2.1.pdf`. A whole-model write adds each placement's instance tag
  (`cabinet-v2.1-P1.pdf`); a unit's own write names its PDF bare. Untagged instances of one release clash.
- **The `data/` folder.** Every CSV and XML export goes into `<out_dir>/data/`, `changes.csv` included;
  the PDFs, `overview.html` and `changes.md` stay in `out_dir`. `fr.export_names` gives the path from `out_dir` (`data/EX-1-v1.1-bom.csv`).
- **Stale exports.** `write` first deletes the set's old files in `out_dir` and `data/`. These are files whose names start
  with the set's name and `-v`, and the flat CSV and XML files a write made before `data/` existed.
  A system write also deletes the files that start with each unit release's name and `-v`.
  The old bare-name patterns are still cleaned for one more release. Known limit: a unit that leaves the model leaves its last PDF in `out/all/`.
- **Build times.** `result.times` holds the CPU and wall seconds of each build step, and `print(result.times)` shows one line per step with its CPU share. With `intermediates=`, `write` also saves `build-times.json` there; `out_dir` never holds it.
- **Releases.** `fr.release` writes the same paths, and its manifest lists them (`data/...`).
  A release stored before `data/` keeps its flat paths and still verifies.
- **Changes in the overview.** `fr.write(result, out_dir, releases=into)` takes the folder you pass
  to `fr.release`. When it holds a release of the system (at the model's revision, else the previous), `overview.html` gains a Changes switch that marks what changed since it.
  Without `releases`, or with no release there, the page has no such switch.

Every file `write` writes is UTF-8 without a byte order mark, with `\n` line ends, on every OS.

## No export ever carries an error

Any `ERROR` in `fr.check(result)` blocks every export into `out_dir`. A half-finished design
still draws its schematic pages into `intermediates`, when given.

## Releasing a frozen baseline

`fr.release(result, into, *, unit=None)` writes one unit's (or the whole system's) frozen
baseline. It has its document set, as `write` would for that unit, plus a canonical
listing, a manifest of file hashes and package/tool versions, and the model itself. The target
is `<into>/<unit release name>/<version>.<revision>/`, or `<into>/<project number>/<version>.<revision>/`
for the system (`unit=None`). Every check runs first -- the same gate `write` uses,
plus five checks of its own -- and any `ERROR` writes nothing.

```python
def board(revision, *, spare=None):
    """One unit design: the release `demo-io-board`, X1 on its boundary, X3, an optional spare."""

    @fr.unit(
        "demo-io-board", revision=revision, interface_version=1, date="2026-09-27", text=f"Revision {revision}", by="OJB"
    )
    def io_board(d):
        x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
        d.device("X3", "DEMO-CONN-2P")
        if spare:
            d.device(spare, "DEMO-CONN-2P")
        return Io(x1)

    release_design = fr.design("demo_parts")
    release_design.add(io_board, "U1")
    return release_design


release_result = fr.build(board(1))
release_errors = [f for f in fr.check(release_result) if f.severity is fr.Severity.ERROR]
assert release_errors == [], release_errors

target = fr.release(release_result, Path("releases"), unit="demo-io-board")
assert target == Path("releases") / "demo-io-board" / "1.1"
assert (target / "baseline" / "listing.json").exists()
assert (target / "baseline" / "manifest.json").exists()

# releasing the same, unchanged model again writes nothing new
same_target = fr.release(release_result, Path("releases"), unit="demo-io-board")
assert same_target == target
```

An unchanged release is a no-op. A released
revision is frozen: releasing a unit again with different content raises `BuildFailedError` naming
`REVISION_ALREADY_RELEASED` instead of overwriting it (see `findings-validators.md`). Commit the files in your own repo, beside the design script.

A container rebuilt against an old child release uses the child's old source from git. Fransys loads no frozen child.
A history entry that names a revision never released is `RELEASE_HISTORY_UNRELEASED`; `units.md` has the rule.

## Getting the change list

`fr.diff(result, into, *, unit=None, against=None)` gives the Markdown change list from a
stored release to the model as it stands now, without writing anything: use it during a revision. `release()` writes the same text into `changes.md` (and the same rows
into `data/changes.csv`) once a previous release exists; the first release of a unit gets neither
file. Nothing overwrites the history text you author. A unit's change list is relative to the unit, so a place that holds all of its items, added or removed, shows no change.

```python
second_result = fr.build(board(2, spare="X2"))
second_errors = [f for f in fr.check(second_result) if f.severity is fr.Severity.ERROR]
assert second_errors == [], second_errors

preview = fr.diff(second_result, Path("releases"), unit="demo-io-board")
assert "Added `-X2`" in preview

second_target = fr.release(second_result, Path("releases"), unit="demo-io-board")
assert (second_target / "changes.md").read_text(encoding="utf-8") == preview
assert (second_target / "data" / "changes.csv").exists()
```

`against=` names a released revision's folder (`"1.1"`) to diff against. The default is the model's
own release if stored, else the previous one; `fr.diff` raises `FileNotFoundError` when neither exists. A renamed item shows as one `Renamed` line; `moving-to-0.20.md` has the rule.

## Checking a baseline stays true

`fr.verify(result, baselines) -> tuple[Finding, ...]` reruns `release`'s `BASELINE_DIFFERS`
comparison for every unit instance (and the system, when the model has a project) with a stored
baseline. It writes nothing, and `fr.write` never calls it: run it in a test that guards a released revision.

```python
assert fr.verify(second_result, Path("releases")) == ()

third_result = fr.build(board(2, spare="X9"))  # X2, mistagged X9
third_errors = [f for f in fr.check(third_result) if f.severity is fr.Severity.ERROR]
assert third_errors == [], third_errors

findings = fr.verify(third_result, Path("releases"))
assert [f.code for f in findings] == ["BASELINE_DIFFERS"]
```

`second_result` is unchanged since its release, so `verify` gives nothing. `third_result` shares
revision `2` but its spare connector's tag differs from what `1.2` released, so `verify` catches
the drift. A unit with no stored baseline is not reported.

When a child moved release, `BASELINE_DIFFERS` names it right after `units`, as in
`demo-cabinet 1.1 differs from its released baseline in: units (demo-io-board revision 1.1 → 1.3)`.
It names direct children only; a grandchild's move shows in its parent's finding.

`verify` also re-hashes every release file under `baselines`, with no model needed.
`RELEASE_FILE_CHANGED` means a listed file's bytes differ, an unlisted file is present, or the manifest does not parse. `RELEASE_FILE_MISSING` means a listed file, or the manifest, is gone.
A text file (`.csv`, `.json`, `.md`, `.xml`, `.html`, `.txt`) whose bytes differ only by CRLF line ends passes,
so a Windows checkout passes.

After an upgrade that moved a printing rule, `fr.verify` gives `BASELINE_RULES_MOVED_NOTE` (INFO) for each release cut by an older Fransys and `fr.release` refuses over one. Run `fr.rebaseline(result, Path("releases"))` once and commit the rewritten `listing.json` and `manifest.json`; the exports are untouched.

```python
found = fr.verify(second_result, Path("releases"))
if any(f.code.startswith(("BASELINE_RULES_MOVED", "BASELINE_ROWS_UNCHECKED")) for f in found):
    fr.rebaseline(second_result, Path("releases"))  # commit the rewritten baseline files
assert fr.verify(second_result, Path("releases")) == ()
```

A patch release reads every revision; rebaseline only on `BASELINE_RULES_MOVED_NOTE`.

## Listing the releases

`fr.releases(root) -> tuple[Release, ...]` reads every `<name>/<version>.<revision>/` folder under
`root`, in name, version and revision order. Versions and revisions sort as integers. A
`Release` has `name`, `version`, `revision`, `interface`, `listing_digest`, `nested`, `files` and `path`.
`nested` holds one `ReleasePin` (`name`, `version`, `revision`, `listing_digest`) per release nested
in it. `files` holds `(path, sha256)` pairs. A folder with no manifest is listed with empty fields.
A manifest that does not parse raises `ValueError`.

Later versions may add manifest keys and keep reading every earlier manifest.

```python
listed = fr.releases(Path("releases"))
assert [(r.name, r.version, r.revision) for r in listed] == [
    ("demo-io-board", 1, 1),
    ("demo-io-board", 1, 2),
]
assert listed[0].interface == "1"

# Which parents to bump: a release whose pin of a child is older than the child's latest release.
latest = {r.name: (r.version, r.revision) for r in listed}
stale = [
    (r.name, f"{r.version}.{r.revision}", pin.name)
    for r in listed
    for pin in r.nested
    if latest.get(pin.name) not in (None, (pin.version, pin.revision))
]
assert stale == []
```

The policy stays yours: tag names, who releases and which findings block. Fransys keeps no issue record.

## Keeping designations fixed across revisions

`fr.build(d, *documents, releases=None)` takes a keyword-only `releases`, the same root `fr.release`
writes into. At `None` (the default), numbering is free. Given the releases root, `build` reads each unit's
released numbering before assigning new tags. An item still in the same group keeps the number it was released with. A number
freed by a removed or moved item is never handed to a different item within that unit's
version. An authored tag that equals a pinned or reserved number is `DESIGNATION_DUPLICATE`
(see `findings-build.md`). Releasing without
`releases=` still catches a moved number, as `DESIGNATION_MOVED`.

## Point a finding past a helper

A finding names the file and line of the call that authored the thing. Set `__tracebackhide__ = True`
in a helper that builds a repeated circuit, and the finding names the helper's caller.

```python
import fransys as fr


def lamp_pair(d, first, second):
    __tracebackhide__ = True
    return d.device(first, "DEMO-LAMP-24"), d.device(second, "DEMO-LAMP-24")


d = fr.design("demo_parts")
h1, h2 = lamp_pair(d, "H1", "H2")
result = fr.build(d)
assert fr.derive.item_designation(result.model, h1.id) == "H1"
```

## Read a model id

`Q1.id` and `Q1.coil.id` give the model id of a device and a function. Read them after the build, as
`fr.derive.item_designation(result.model, Q1.id)` does. Never wire with ids.
