# Building a design

`fr.build`, `fr.check` and `fr.write` are the three pipeline functions. `build` takes the design
(and any documents), merges them into a model and runs the passes, the validators, and layout
when there is a document.
`check` collects every finding about a built model, including some `build` itself never sees.
`write` writes the model's exports to a directory. It raises, and writes nothing, if any
finding is an `ERROR`.

## Where a build can fail

Four stages. Each fails differently. A mistake in an authoring call itself, such as a design call
the builder refuses, raises `fr.AuthorError` at that call, so a test catches it by name.

**1. Loading a part library.** `fr.design(...)` and `fr.parts(...)` lint every library they load
and raise `PartLibraryError` if linting finds an `ERROR`. Nothing is built from a library that fails its
own lint.

**2. The build itself.** `fr.build(d, *documents)` merges the design with the documents, then
freezes the result into a `Model`. Two structural problems can raise here. `build` catches neither.

- `MergeConflict`, when two records share one id with different content. This can even happen
  before `build` runs, at the second authoring call that creates the conflicting record.
- `FreezeError`, when freezing finds one or more structural problems inside the merged records: a
  dangling reference, a bad value, or a missing required field. It aggregates every problem it
  found in `.errors`, not just the first, so an author fixes a batch in one pass.

The case a consumer meets is two instances of one unit release, same name and revision, authored
with different content.

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
except fr.MergeConflict as e:
    assert "two different records share one id" in str(e)
    assert e.origin_a.file == e.origin_b.file
    assert e.origin_a.line != e.origin_b.line
else:
    raise AssertionError("expected MergeConflict")
```

Both functions declare the release `demo-io-board`, revision 1. The second gives a different
`interface`, so it conflicts instead of deduplicating. `e.origin_a` and `e.origin_b` name the two
call sites.

`fr.build(d)` always carries the part library the design was started from. Only the engine's own
draft, `d.draft()`, leaves it out, and building that shows what a missing library does: every
reference to a part is left dangling.

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

Four references are left dangling by the missing library: one `RefError` for each.
`e.errors` holds all four, not just the first one freezing happened to find.

Any exception out of `build` other than these two is a Fransys bug, not something a normal
script needs to guard against. Report it as a field case.

**3. The validators.** Every domain validator runs inside `build`, but an `ERROR` finding from
one of them does not raise. It comes back in `fr.check(result)`, and it also stops layout there:
a model with a validator `ERROR` is returned numbered but unlaid, findings and all.

**4. `write`.** `write` computes `fr.check(result)` itself and raises `BuildErrors` if any
finding in it is an `ERROR`, before touching `out_dir`. See below.

## `fr.check(result)` is the one list of findings

`fr.check(result)` returns every finding about a built model. That covers the PLC and numbering
passes, the validators, layout, and the board check. When the model holds a document it adds the
drawing and PDF checks. A script reads findings only through it.

The design above has one device and no wiring, so its document has nothing to draw:

```python
from pathlib import Path

cabinet_cover = Path("cabinet.md")
cabinet_cover.write_text("# Cabinet\n")
doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, x1, cover=cabinet_cover)

result = fr.build(d, doc)
assert len(fr.check(result)) == 6
```

`fr.check(result)` holds two `PORT_UNCONNECTED` `INFO` findings from the validators, two
`DOCUMENT_EMPTY_LIST` `INFO` findings and, most importantly, two `ERROR`s that only the drawing
and PDF checks find. A script that asserted the design clean would have shipped it.

`write` runs the same check internally, so it raises on those errors:

```python
try:
    fr.write(result, Path("out"))
except fr.BuildErrors as e:
    assert len(e.findings) == 2
    assert all(f.severity is fr.Severity.ERROR for f in e.findings)
else:
    raise AssertionError("expected BuildErrors")
```

`e.findings` holds exactly the two `ERROR`s, not every finding of `fr.check(result)`. `out_dir` is
left with nothing written for this build. No bad export, ever. There is no `allow_errors`,
`force` or `draft` parameter on `write`, and none will be added.

## No document, no layout

Layout exists only to draw documents. A build with no `Document` draft skips layout entirely.
There is no flag, and no other function to call.

```python
result = fr.build(d)  # no document this time
codes = sorted(f.code for f in fr.check(result))
assert codes == ["PORT_UNCONNECTED", "PORT_UNCONNECTED"]

written = fr.write(result, Path("out"))
assert sorted(p.name for p in written) == [
    "bom.csv",
    "cables.csv",
    "designations.csv",
    "overview.html",
    "plc.csv",
    "wires.csv",
]
```

With no document, `check` never runs the drawing or PDF checks: neither has a layout to read.
`write` writes the same kind of file list as before, with no PDF, since a PDF comes only from a
document.

## Export file names

Export names follow rules EN1 to EN5. One function builds every
name, so a script never constructs its own. The `v` prefix is used only in file names, never in a
title block or history table. The names are a built-in default with no option or template.

- **EN1, the set prefix.** Every file belongs to one set: the unit written (`unit=U`) or the
  system (`unit=None`). The prefix is `<set name>-v<V>.<R>`, the set's name plus its version and
  revision in `derive.revision_text`'s print form. A unit's name is its release name
  (`demo-io-board-v1.1`); the system's is the project's number (`EX-1-v1.1`). A system write of
  a model with no project record has no prefix, and the system's own files keep their bare names
  (plain `bom.csv`), which is what the examples above wrote because this guide's design authors
  no project. A unit's document still takes its unit's prefix there.
- **EN2, prefix, kind, fragment.** A name is `<prefix>[-<kind>][-<fragment>].<ext>`:
  `demo-io-board-v1.1-bom.csv`, per item `demo-io-board-v1.1-terminals-X1.csv`, and for the
  unit's own root the bare kind `demo-io-board-v1.1-terminals.csv`.
- **EN3, a PDF is named by its subject, not its cover file.** A document of the set itself is
  `<prefix>.pdf`; a `harness_drawing` adds `-harness`; a document of an item or location inside
  the set adds that subject's fragment. A document whose subject is a unit takes that unit's
  name in every write, a system write included, so `out/all/` holds `EX-1-v1.1.pdf` beside
  `cabinet-v2.1.pdf`. Two instances of one release with a document each come to one name and
  raise a name-clash error; keep one document per release.
- **EN4, stale exports.** `write` runs `_clean_stale_exports` before writing. It deletes the
  files that start with the set's name and `-v` for any version, so a work folder reused across
  revisions keeps only the current ones. A system write also deletes the files that start with
  each unit release's name in the model and `-v`, for the unit documents. The old bare-name
  patterns are still cleaned for one more release. Known limit: a unit that leaves the model
  leaves its last PDF behind in `out/all/`.
- **EN5, releases.** `fr.release` writes the same names, and its manifest lists them.

Every file `write` writes is UTF-8 without a byte order mark, with `\n` line ends, on every OS.

## No export ever carries an error

This is the point of the `write` example above. `write` computes `fr.check(result)` before
writing anything. Any `ERROR` in it blocks every export into that `out_dir`, not just the one
the error is about. A half-finished design still draws its schematic pages into
`intermediates`, when given. `out_dir` only ever holds a design with zero `ERROR` findings.

## Releasing a frozen baseline

`fr.release(result, into, *, unit=None)` writes one unit's (or the whole system's) frozen
baseline: its document set, exactly as `write` would write it for that unit, plus a canonical
listing, a manifest of file hashes and package/tool versions, and the model itself. The target
is `<into>/<unit release name>/<version>.<revision>/`, or `<into>/<project number>/<version>.
<revision>/` for the system (`unit=None`). Every check runs first -- the same gate `write` uses,
plus five checks of its own -- and any `ERROR` writes nothing, the same as `write`.

A unit's change list is relative to the unit, so a place that holds all of its items, added or removed, shows no change.

```python
from typing import NamedTuple


class Io(NamedTuple):
    pass


def board(revision, *, spare=None):
    """One unit design: the release `demo-io-board`, X1 on its boundary, X3, an optional spare."""

    @fr.unit(
        "demo-io-board", revision=revision, interface_version=1, date="2026-09-27", text=f"Revision {revision}", by="OJB"
    )
    def io_board(d):
        d.device("X1", "DEMO-CONN-2P", interface=True)
        d.device("X3", "DEMO-CONN-2P")
        if spare:
            d.device(spare, "DEMO-CONN-2P")
        return Io()

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

An unchanged release is a no-op: nothing is rebuilt, no file's timestamp changes. A released
revision is frozen: releasing a unit again with different content raises `BuildErrors` naming
`REVISION_ALREADY_RELEASED` instead of overwriting it (see `findings.md`). The files are the
consumer's -- commit them in your own repo, alongside the design script that produced them.

## Getting the change list

`fr.diff(result, into, *, unit=None, against=None)` gives the Markdown change list from a
stored release to the model as it stands now, without writing anything -- useful while a
revision is still being worked on, before deciding to release it. `release()` itself writes
the same text into `changes.md` (and the same rows as `changes.csv`) once a previous release
exists to compare against; the first release of a unit gets neither file, since there is
nothing yet to diff against. The revision text you author stays yours. `changes.md` is the
detailed evidence beside it, and nothing fills or overwrites the history text.

```python
second_result = fr.build(board(2, spare="X2"))
second_errors = [f for f in fr.check(second_result) if f.severity is fr.Severity.ERROR]
assert second_errors == [], second_errors

preview = fr.diff(second_result, Path("releases"), unit="demo-io-board")
assert "Added `-X2`" in preview

second_target = fr.release(second_result, Path("releases"), unit="demo-io-board")
assert (second_target / "changes.md").read_text(encoding="utf-8") == preview
assert (second_target / "changes.csv").exists()
```

`against=` names a specific released revision's folder (`"1.1"`) to diff against instead of the
default (the model's own current release if it is already stored, otherwise the previous
released revision below it, possibly in an earlier version). `fr.diff` raises
`FileNotFoundError` when no released revision is found either way.

## Checking a baseline stays true

`fr.verify(result, baselines) -> tuple[Finding, ...]` reruns the same comparison `release`'s own
`BASELINE_DIFFERS` check does, for every unit instance the model has (and the system, when the
model has a project) that a stored baseline already exists for. It writes nothing, and
`fr.write` never calls it -- a consumer runs it wherever they want the check, most often a test
that guards against an accidental change to a released revision.

```python
assert fr.verify(second_result, Path("releases")) == ()

third_result = fr.build(board(2, spare="X9"))  # X2, mistagged X9
third_errors = [f for f in fr.check(third_result) if f.severity is fr.Severity.ERROR]
assert third_errors == [], third_errors

findings = fr.verify(third_result, Path("releases"))
assert [f.code for f in findings] == ["BASELINE_DIFFERS"]
```

`second_result` is unchanged since its own release above, so `verify` gives nothing. `third_result`
shares `demo-io-board`'s revision `2` release identity but was never released itself, and its
spare connector's tag differs from what `1.2` actually released, so `verify` catches the drift
without anyone calling `release` again. A unit or the system with no stored baseline at all is
not reported.

## Keeping designations fixed across revisions

`fr.build(d, *documents, releases=None)` takes a keyword-only `releases`, the same root `fr.release`
writes into. Left at `None` (the default), numbering is free, exactly as above. Given the
releases root, `build` reads each unit's own previously released numbering before assigning
new tags: an item still in the same group keeps the number it was released with, and a number
freed by a removed or moved item is never handed to a different item within that unit's
version. A tag the engineer authors may still equal a pinned or reserved number by mistake;
that is `DESIGNATION_DUPLICATE` (see `findings.md`), not silently allowed. Releasing without
`releases=` still catches a moved number, as `DESIGNATION_MOVED`.
