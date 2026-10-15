# Documents

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

A `Document` record is what turns an authored design into a printable deliverable. `fr.document`
authors one such record as a `Draft`. Pass it to `fr.build(d, doc)` next to the design `d`;
the model does the rest at layout and write time.

## Presets, cover and notes text

`fr.document(preset, subject, cover=..., add=(), remove=(), logo=None, notice="")` takes a
`fr.DocumentPreset` (`CABINET_SCHEMATIC`, `HARNESS_DRAWING`, `PCB_SCHEMATIC`, `SYSTEM`), which
fixes the deliverable's default page kinds; `add` and `remove` adjust that set for one document.
`cover` is a required path to a Markdown file, read verbatim and stored on the model; any number of documents may share one cover path. A
missing `cover` is a `FileNotFoundError` naming the path. A file beside it, named the cover's
stem plus `.notes.md`, is read automatically when present and becomes the document's notes
page; there is no separate `notes` parameter, and a missing notes file is not an error, it just
means no notes page. `logo` is an optional path to an SVG for the title block's logo cell, read the same way; leaving it out (the
default) leaves that cell empty. `notice` is the text of the title block's IP notice cell, printed
on every page of that document; `""` (the default) leaves the cell empty. On A3 the cell is about 92 mm wide and holds about 370 characters at the label size. A longer notice gives `TITLE_BLOCK_NOTICE_OVERFLOW`. Customer and Author are narrower than with no notice. A unit released alone
needs no `d.project` for either; its Author cell prints `created` of the unit's current revision, a project document's the project's `author`. `d.project(notice=...)` raises: the notice moved here.

The page kinds each preset holds by default (`add` and `remove` change them).

| page kind | `CABINET_SCHEMATIC` | `HARNESS_DRAWING` | `PCB_SCHEMATIC` | `SYSTEM` |
|---|---|---|---|---|
| `COVER` | yes | yes | yes | yes |
| `NOTES` | yes | yes | yes | yes |
| `SHEET_INDEX` | yes | yes | yes | yes |
| `CONTENTS` | no | yes | no | no |
| `SCHEMATIC` | yes | no | yes | no |
| `BLOCK_DIAGRAM` | no | no | no | yes |
| `HARNESS_DRAWING` | no | yes | no | yes |
| `PLC_LIST` | yes | no | no | no |
| `TERMINAL_LIST` | yes | no | no | no |
| `CONNECTOR_LIST` | yes | no | yes | no |
| `CABLE_LIST` | no | no | no | yes |
| `BOM` | yes | yes | yes | yes |

Every preset also takes `PageKind.SHEET_INDEX`, a "Sheets" page after the notes that lists each
sheet (`3`, `2.3`, block diagram sheets `B1`, `B2`) with its title and PDF page. It prints from two
sheets; `remove=(fr.PageKind.SHEET_INDEX,)` drops it. The PDF is navigable and prints the same.
Cross references and Sheets rows are invisible links. The outline lists sheets and devices. The
viewer numbers a sheet by its sheet number and other pages in roman.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BK



class Cabinet(NamedTuple):
    pass


@fr.unit(
    "terminal-cabinet",
    revision=1,
    interface_version=1,
    date="2026-02-02",
    text="First",
    by="XX",
    title="Terminal cabinet",
    number="TC-1",
)
def terminal_cabinet(c):
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 2, description="Field strip")
    k1 = c.device("K1", "DEMO-CO-4P-24")
    c.series(x1, k1.coil, x1, wire=(BK, 1.5))
    return Cabinet()


d = fr.design("demo_parts")
d.add(terminal_cabinet, "U1")

cover = Path("cabinet.md")
cover.write_text("# Cabinet\n", encoding="utf-8")
Path("cabinet.notes.md").write_text("Site notes for the installer.\n", encoding="utf-8")

cabinet_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "terminal-cabinet", cover=cover)
result = fr.build(d, cabinet_document)
findings = fr.check(result)
assert not [f for f in findings if f.severity in (fr.Severity.ERROR, fr.Severity.WARNING)]
written = fr.write(result, Path("out"))
assert any(p.suffix == ".pdf" for p in written)
```

`out/` now holds one PDF for the cabinet, with the cover and notes text on their own pages
ahead of the schematic.

## Subjects

A document's `subject` is a unit, an item, or a place where units stand. It is one of:

- A location handle, what `d.location(...)` returns: a place where units stand.
- A device handle, what `d.device(...)` or `d.harness(...)` returns.
- A unit release's name, a plain `str`, such as a cabinet's: resolved to the one instance of that release at build
  and write time, not at the `fr.document` call itself.

Any other value, such as a bare design, is a `TypeError` at the call. The cabinet example above
passes its release name. A unit added with `d.add(fn, "U1")` is named by its release name:

```python
class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def board(u):
    x1 = u.device("X1", "DEMO-CONN-2P", interface=True)
    return Io(x1)


d2 = fr.design("demo_parts")
d2.add(board, "U1")
board_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-io-board", cover=cover)
board_result = fr.build(d2, board_document)
assert not [f for f in fr.check(board_result) if f.severity is fr.Severity.ERROR]
assert any(p.name == "demo-io-board-v1.1.pdf" for p in fr.write(board_result, Path("out1")))
```

The PDF is named after the unit and its release, `demo-io-board-v1.1.pdf`.

## List pages

The terminal, PLC, connector, wire-label and designation lists flow in two columns. The cable list and the BOM take the full width. A row never splits. A table that reaches a column foot continues in the next column or page under its heading with " (cont.)". A split leaves at least two rows on each side, else the table moves whole. A long token breaks only at a hyphen or a slash. The cover's revision table stands one padding above the title block.

The connector list prints one table per connector, headed by its designation and the item's description, with a row per pin: Pin, Net, Mate and Ends. The `CABINET_SCHEMATIC` preset carries it. A pin no wire inside the unit reaches is not drawn on the unit's own pages, and its row in the connector table is where it shows. A cabinet document with no connector reports an INFO `DOCUMENT_EMPTY_LIST`, as it does for terminals.

## Cable drawings

A `HARNESS_DRAWING` page draws each cable as one block, and a harness of two or more cables as one block around its cables. A block has its end boxes with their pins, a box per cable with its heading, and one wire per core. A core whose two ends stand in one row is a short link at that row. Two cores on one pin stand side by side in the pin's cell. A harness whose cables interleave is not drawn yet. A document that shows it stops with
`DOCUMENT_NO_DRAWINGS`.

## A unit's own cable drawings

A `CABINET_SCHEMATIC` document leaves out the cable pages. To print a unit's own cable drawings and
cable list in its document, add their page kinds: `add=(fr.PageKind.HARNESS_DRAWING,
fr.PageKind.CABLE_LIST)`. `remove=` wins over `add=`: a kind named in both is left out.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BN


class Cabinet(NamedTuple):
    pass


@fr.unit("cable-cabinet", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def cable_cabinet(c):
    k1 = c.device("K1", "DEMO-CO-4P-24")
    k2 = c.device("K2", "DEMO-CO-4P-24")
    w1 = c.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
    w1.core(BN, k1.coil["A1"], k2.coil["A1"])
    return Cabinet()


d = fr.design("demo_parts")
d.add(cable_cabinet, "U1")
cover = Path("cabinet.md")
cover.write_text("# Cabinet\n", encoding="utf-8")
pages = (fr.PageKind.HARNESS_DRAWING, fr.PageKind.CABLE_LIST)
own = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cable-cabinet", cover=cover, add=pages)
result = fr.build(d, own)
assert not [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
assert any(p.suffix == ".pdf" for p in fr.write(result, Path("out")))
pdfs = {key: name for key, name in fr.export_names(result).items() if key[0] == "pdf"}
assert list(pdfs.values()) == ["cable-cabinet-v1.1.pdf"]  # the key is ("pdf", <document id>)
```

A `TERMINAL_LIST` page lists the terminal strips of each unit and location. A document whose design has no unit and no location lists nothing, so declare a unit or a location to get the page.

## Block diagrams

A `BLOCK_DIAGRAM` page draws a reading as boxes joined by one line per cable. The line carries the
cable's designation, and a tab names the strip or connector it lands on. The `SYSTEM` preset
carries the page after the notes: its boxes are the top-level units and items, its lines the
top-level cables. A unit document does not carry it by default; `add=(fr.PageKind.BLOCK_DIAGRAM,)`
puts it there, and the page shows that unit's own cables and its child units, never what lies
inside them. A reading with no cable line gets no page.

The page is A2 landscape, 594 x 420 mm, with a 12 x 8 frame; the other pages keep the
document's sheet. A diagram wider than one sheet continues on the next, and a line cut between
sheets ends in a marker naming the other sheet. A kept page whose diagram cannot be drawn stops the
export with `DOCUMENT_NO_DRAWINGS`.

## One PDF is one drawing

Each `fr.document(...)` call, and each resulting PDF, is one drawing: a cabinet schematic, a
harness drawing, or a PCB schematic, never several combined into one file. A unit follows the
same rule at the unit's own level: a unit is one physical thing in one place, so its own items
make one drawing set. **A unit's drawings take the unit as subject; an item inside a unit is not a
drawing.** Places only split drawing sets at the top level, outside any unit.

Concretely: naming the unit's release (as `"demo-io-board"` above) draws that unit's one
schematic. Naming a device that sits inside a unit (`X1`, not the unit) matches no
drawing set at all, because the layout that device belongs to is attributed to the
unit, not to the bare device. A schematic with nothing to draw adds no page and no finding while
the document has another content page (a list with rows, a harness drawing, a block diagram).
With none, `check` reports `DOCUMENT_NO_DRAWINGS` (an `ERROR`), and `write`
turns any `ERROR` into `fr.BuildErrors` with no export written. The harness and diagram messages
of `DOCUMENT_NO_DRAWINGS` stay `ERROR`s whatever else the document holds.

```python
d3 = fr.design("demo_parts")
io = d3.add(board, "U1")
inner_document = fr.document(
    fr.DocumentPreset.CABINET_SCHEMATIC,
    io.X1,
    cover=cover,
    remove=(fr.PageKind.PLC_LIST, fr.PageKind.TERMINAL_LIST, fr.PageKind.BOM),
)
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
