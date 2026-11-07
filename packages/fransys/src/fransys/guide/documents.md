# Documents

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

A `Document` record is what turns an authored design into a printable deliverable. `fr.document`
authors one such record as a `Draft`. Pass it to `fr.build(d, doc)` next to the design `d`;
the model does the rest at layout and write time.

## Presets, cover and notes text

`fr.document(preset, subject, cover=..., logo=None, notice="")` takes a
`fr.DocumentPreset` (`CABINET_SCHEMATIC` or `SYSTEM`), which fixes the deliverable's page kinds.
`cover` is a required path to a Markdown file, read verbatim and stored on the model; any number of documents may share one cover path. A
missing `cover` is a `FileNotFoundError` naming the path. A file beside it, named the cover's
stem plus `.notes.md`, is read automatically when present and becomes the document's notes
page. There is no separate `notes` parameter. A missing notes file is not an error; it just
means no notes page. `logo` is an optional path to an SVG for the title block's logo cell, read the same way; leaving it out (the
default) leaves that cell empty. `notice` is the text of the title block's IP notice cell, printed
on every page of that document; `""` (the default) leaves the cell empty. On A3 the cell is about 92 mm wide and holds about 370 characters at the label size. A longer notice gives `TITLE_BLOCK_NOTICE_OVERFLOW`. Customer and Author are narrower than with no notice. A unit released alone
needs no `d.project` for either; its Author cell prints `created` of the unit's current revision, a project document's the project's `author`. `d.project(notice=...)` raises: the notice moved here.

The page kinds each preset holds, in the order of the PDF: the cover, the drawings, then the notes, the index and the lists. The cover is page 1 and the drawings start on page 2.

| page kind | `CABINET_SCHEMATIC` | `SYSTEM` |
|---|---|---|
| `COVER` | yes | yes |
| `BLOCK_DIAGRAM` | no | yes |
| `SCHEMATIC` | yes | no |
| `HARNESS_DRAWING` | no | yes |
| `NOTES` | yes | yes |
| `SHEET_INDEX` | yes | yes |
| `PLC_LIST` | yes | no |
| `TERMINAL_LIST` | yes | no |
| `CONNECTOR_LIST` | yes | no |
| `CABLE_LIST` | no | yes |
| `BOM` | yes | yes |

Every preset also takes `PageKind.SHEET_INDEX`, a "Sheets" page after the notes that lists each
drawing page with its title and its PDF page. It prints from two pages. The PDF is navigable and
prints the same. Cross references and Sheets rows are invisible links. The outline lists pages and
devices. A page has one number: its place in its PDF, counted from 1 with the cover as page 1. Every reference,
the Sheets page, the outline and the viewer print it. The title block prints it as `m of N`, with the
PDF's page count.

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
    f1 = c.device("F1", "DEMO-FUSE-ABAT")
    c.series(x1, f1.element, x1, wire=(BK, 1.5))
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
- What `d.add(...)` returned: that one unit instance. Use it when a release stands more than once, since a name
  then matches several units and `DOCUMENT_UNIT_UNRESOLVED` follows.

Any other value, such as a bare design, is a `TypeError` at the call. The cabinet example above
passes its release name. A unit added with `d.add(fn, "U1")` is named by its release name:

```python
class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def board(u):
    x1 = u.device("X1", "DEMO-CONN-2P", interface=True)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5", 3)
    h1 = u.device("H1", "DEMO-LAMP-24")
    u.series(x2, h1.lamp, x2, wire=(BK, 0.5))
    return Io(x1)


d2 = fr.design("demo_parts")
d2.add(board, "U1")
board_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-io-board", cover=cover)
board_result = fr.build(d2, board_document)
assert not [f for f in fr.check(board_result) if f.severity is fr.Severity.ERROR]
assert any(p.name == "demo-io-board-v1.1.pdf" for p in fr.write(board_result, Path("out1")))
```

The PDF is named after the unit and its release, `demo-io-board-v1.1.pdf`.

What `d.add` returned names its instance, so a document can follow the instance rather than the release name:

```python
d3 = fr.design("demo_parts")
placed = d3.add(board, "U1")
placed_document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, placed, cover=cover)
placed_result = fr.build(d3, placed_document)
assert not [f for f in fr.check(placed_result) if f.severity is fr.Severity.ERROR]
```

A release added more than once resolves by name to no single unit. Name each instance by what `d.add` returned. Each placement writes its own PDF, `<release>-v<V>.<R>-<tag>.pdf`; the unit's own PDF stays `<release>-v<V>.<R>.pdf`.

## List pages

The terminal, PLC, connector, wire-label and designation lists flow in two columns. The cable list and the BOM take the full width. A row never splits. A table that reaches a column foot continues in the next column or page under its heading with " (cont.)". A split leaves at least two rows on each side, else the table moves whole. A long token breaks only at a hyphen or a slash. The cover's revision table stands one padding above the title block.

The connector list prints one table per connector, headed by its designation and the item's description, with a row per pin: Pin, Net, Mate and Ends. The `CABINET_SCHEMATIC` preset carries it. A pin no wire inside the unit reaches is not drawn on the unit's own pages, and its row in the connector table is where it shows. A cabinet document with no connector reports an INFO `DOCUMENT_EMPTY_LIST`, as it does for terminals.

## Cable drawings

A `HARNESS_DRAWING` page draws each cable as one block, and a harness of two or more cables as one block around its cables. A block has its end boxes with their pins, a box per cable with its heading, and one wire per core. A core whose two ends stand in one row is a short link at that row. Two cores on one pin stand side by side in the pin's cell. A harness whose cables interleave is not drawn yet. A document that shows it stops with
`DOCUMENT_NO_DRAWINGS`.

A `TERMINAL_LIST` page lists the terminal strips of each unit and location. A document whose design has no unit and no location lists nothing, so declare a unit or a location to get the page.

## Block diagrams

A `BLOCK_DIAGRAM` page draws a reading as boxes joined by one line per cable. The line carries the
cable's designation, and a tab names the strip or connector it lands on. The `SYSTEM` preset
carries the page after the notes: its boxes are the top-level units and items, its lines the
top-level cables. A `CABINET_SCHEMATIC` document does not carry it. A reading with no cable line
gets no page.

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
drawing set at all. That is because its layout belongs to the unit, not
to the bare device. A schematic with nothing to draw adds no page and no finding while
the document has another content page (a list with rows, a harness drawing, a block diagram).
With none, `check` reports `DOCUMENT_NO_DRAWINGS` (an `ERROR`), and `write`
turns any `ERROR` into `fr.BuildFailedError` with no export written. The harness and diagram messages
of `DOCUMENT_NO_DRAWINGS` stay `ERROR`s whatever else the document holds.


The fix is never to add pages or merge drawings by hand: name the unit's release as the
document's subject, as the unit example on this page does.
