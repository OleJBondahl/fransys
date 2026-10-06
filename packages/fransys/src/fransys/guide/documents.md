# Documents

A `Document` record is what turns an authored design into a printable deliverable. `fr.document`
authors one such record as a `Draft`. Pass it to `fr.build(d, doc)` next to the design `d`;
the model does the rest at layout and write time.

## Presets, cover and notes text

`fr.document(preset, subject, cover=..., add=(), remove=(), logo=None)` takes a
`fr.DocumentPreset` (`CABINET_SCHEMATIC`, `HARNESS_DRAWING`, `PCB_SCHEMATIC`, `SYSTEM`), which
fixes the deliverable's default page kinds; `add` and `remove` adjust that set for one document.
`cover` is a required path to a Markdown file, read verbatim and stored on the model. A
missing `cover` is a `FileNotFoundError` naming the path. A file beside it, named the cover's
stem plus `.notes.md`, is read automatically when present and becomes the document's notes
page; there is no separate `notes` parameter, and a missing notes file is not an error, it just
means no notes page. `logo` is an optional path to an SVG for the title block's logo cell,
read the same way; leaving it out (the default) leaves that cell empty.

```python
from pathlib import Path

import fransys as fr
from fransys.colours import BK

d = fr.design("demo_parts", place="C1")
cabinet = d.location("C1", "Terminal cabinet")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, description="Field strip")
k1 = d.device("K1", "DEMO-CO-4P-24")
d.wire(x1[1], k1["32"], wire=(BK, 1.5))

cover = Path("cabinet.md")
cover.write_text("# Cabinet\n", encoding="utf-8")
Path("cabinet.notes.md").write_text("Site notes for the installer.\n", encoding="utf-8")

cabinet_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)
result = fr.build(d, cabinet_document)
findings = fr.check(result)
assert not [f for f in findings if f.severity is fr.Severity.ERROR]
written = fr.write(result, Path("out"))
assert any(p.suffix == ".pdf" for p in written)
```

`out/` now holds one PDF for the cabinet, with the cover and notes text on their own pages
ahead of the schematic.

## Subjects

A document's `subject` names what it draws. It is one of:

- A location handle, what `d.location(...)` returns: a cabinet or another top-level place.
- A device handle, what `d.device(...)` or `d.harness(...)` returns.
- A unit release's name, a plain `str`: resolved to the one instance of that release at build
  and write time, not at the `fr.document` call itself.

Any other value, such as a bare design, is a `TypeError` at the call. The cabinet example above
passes the location `cabinet`. A unit added with `d.add(fn, "U1")` is named by its release name:

```python
from typing import Any, NamedTuple

class Io(NamedTuple):
    X1: fr.Device
    B1: Any


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def board(u):
    b1 = u.location("B1", "Board")
    return Io(u.device("X1", "DEMO-CONN-2P", interface=True), b1)


d2 = fr.design("demo_parts")
d2.add(board, "U1")
board_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-io-board", cover=cover)
board_result = fr.build(d2, board_document)
assert not [f for f in fr.check(board_result) if f.severity is fr.Severity.ERROR]
assert any(p.name == "demo-io-board-v1.1.pdf" for p in fr.write(board_result, Path("out1")))
```

The PDF is named after the unit and its release, `demo-io-board-v1.1.pdf`.

## One PDF is one drawing

Each `fr.document(...)` call, and each resulting PDF, is one drawing: a cabinet schematic, a
harness drawing, or a PCB schematic, never several combined into one file. A unit follows the
same rule at the unit's own level: a unit is one physical thing in one place, so its own items
make one drawing set, whatever sub-locations they stand in inside it. **A unit's drawings take
the unit as subject; a location inside a unit is not a drawing.** Locations only split
drawing sets at the top level, outside any unit.

Concretely: naming the unit's release (as `"demo-io-board"` above) draws that unit's one
schematic. Naming a location that sits inside a unit (`B1`, not the unit) matches no
drawing set at all, because the layout that location's items belong to is attributed to the
unit, not to the bare location. `check` reports `DOCUMENT_NO_DRAWINGS` (an `ERROR`), and `write`
turns any `ERROR` into `fr.BuildErrors` with no export written.

```python
d3 = fr.design("demo_parts")
io = d3.add(board, "U1")
inner_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, io.B1, cover=cover)
inner_result = fr.build(d3, inner_document)
inner_findings = fr.check(inner_result)
assert "DOCUMENT_NO_DRAWINGS" in {f.code for f in inner_findings}

try:
    fr.write(inner_result, Path("out2"))
except fr.BuildErrors as error:
    assert any(f.code == "DOCUMENT_NO_DRAWINGS" for f in error.findings)
else:
    raise AssertionError("expected BuildErrors")
```

The fix is never to add pages or merge drawings by hand: it is to name the unit's release as the
document's subject, as the unit example on this page does.
