# Reading the pages as numbers

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

`fr.readability(result)` returns a `DrawnReading`: one `DrawnPageReading` row for each page the build drew, in `.pages`. Both types are in `fr.derive`. The same model gives equal rows, so compare a page between revisions by its rows. It writes no file, `fr.write` does not emit it, and it lays nothing out again.

A set with a layout ERROR returns its pages and rows so you can see why; `fr.write` refuses the build.

The findings these numbers back are in `drawing.md`.

- **`page`.** The page's id.
- **`unit`.** The unit of the drawing set the page belongs to (its id), or None for a top-level set. A page belongs to exactly one set.
- **`symbols` and `markers`.** `symbols` counts every symbol drawn on the page. `markers` counts the reference markers among them, whatever their kind (every kind draws the one marker symbol, so the count is the total).
- **`fill_percent`.** The share, 0 to 100, of the page's content box that the placed ink spans: one box around every symbol body, text, wire and outline. Rounded down. A fuller page reads higher; it is a number to compare between revisions.
- **`wire_crossings`.** How often a wire runs across a wire of another id. A high number means a tangled page. Order the groups with `order`, or put the crossing nets on separate pages.
- **`wire_bends` and `wire_length_g`.** The direction changes and the total length of every wire on the page, in the Drawing unit of "Read the rows of a page". Many bends or a long total mean a winding page. They are numbers to compare between revisions, not a target the layout optimises.
- **`struck_labels`.** Texts a wire runs through.
- **`text_overlaps`.** Pairs of texts whose boxes overlap.

**Removed.** `page_cuts` is gone: a `Drawing` does not carry which markers cut a wire, so no honest count exists. Text height is not a reading: the text heights are the library's fixed heights. Counts a `Drawing` cannot give (printed numbers, lone cells, contact images, stars, loose symbols) are not in the row either.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU


class Cabinet(NamedTuple):
    pass


Path("cover.md").write_text("# Cabinet\n", encoding="utf-8")


@fr.unit(
    "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
    title="Cabinet", number="C-1",
)
def measured(c):
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24").output)
    for i in range(1, 6):
        k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
        h = c.device(f"H{i}", "DEMO-LAMP-24")
        c.series(dc.plus, k.co_1.no, h.lamp, dc.minus, wire=(BU, 0.75))
    return Cabinet()


d = fr.design("demo_parts")
d.add(measured, "U1")
doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
result = fr.build(d, doc)
report = fr.readability(result)
assert len(report.pages) == len(result.drawings)
assert report.pages
assert all(page.wire_crossings >= 0 for page in report.pages)
```

## Read the rows of a page

`result.drawings` holds one `Drawing` for each page. A Drawing is in layout units, and a finding prints G, so divide a Drawing value by 8 for G. An A3 page is `area.w` 1312 wide, and every row, symbol, wire and text value reads in that unit. Its `rows` are the placed rows that hold devices, top to bottom. A row has four fields.

- `devices`: the ids of its items as text, each item once. `fr.derive.drawn_designations(result.model, row.devices)` gives their designations.
- `height` and `width`: its size in the Drawing unit. The width is what the row needs packed left, the figure `WIDER_THAN_PAGE` tests. The symbols stand justified, so it can be less than their span.
- `term`: what set its height. It is `"body"` (a cell), `"card"`, `"marker_room"` (a marker hung at a cell), `"stub"` (a trunk's room) or `"annex"` (a label).

`PAGE_OVERFLOW` and `WIDER_THAN_PAGE` read these same figures. The widest row is `max(page.rows, key=lambda r: r.width)`.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU


class Cabinet(NamedTuple):
    pass


Path("cover.md").write_text("# Cabinet\n", encoding="utf-8")


@fr.unit(
    "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
    title="Cabinet", number="C-1",
)
def rows_unit(c):
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24").output)
    k = c.device("K1", "DEMO-RLY-2CO-24")
    h = c.device("H1", "DEMO-LAMP-24")
    c.series(dc.plus, k.co_1.no, h.lamp, dc.minus, wire=(BU, 0.75))
    return Cabinet()


d = fr.design("demo_parts")
d.add(rows_unit, "U1")
result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md")))
page = next(iter(result.drawings.values()))
widest = max(page.rows, key=lambda r: r.width)
assert widest.width > 0
assert widest.term in ("body", "card", "marker_room", "stub", "annex")
assert {"U1-K1", "U1-H1"} <= set(fr.derive.drawn_designations(result.model, widest.devices))
```
