# Reading the pages as numbers

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

`fr.readability(result)` returns a `DrawnReading`: one `DrawnPageReading` row for each page the build drew, in `.pages`. Both types are in `fr.derive`. The same model gives equal rows, so compare a page between revisions by its rows. It writes no file, `fr.write` does not emit it, and it lays nothing out again.

An error build has no drawings and gives no rows. The shape of the rows may change before 1.0.

The findings these numbers back are in `drawing.md`.

- **`page`.** The page's id.
- **`unit`.** The unit of the drawing set the page belongs to (its id), or None for a top-level set. A page belongs to exactly one set.
- **`symbols` and `markers`.** `symbols` counts every symbol drawn on the page. `markers` counts the reference markers among them, whatever their kind (every kind draws the one marker symbol, so the count is the total).
- **`fill_percent`.** The share, 0 to 100, of the page's content box that the placed ink spans: one box around every symbol body, text, wire and outline. Rounded down. A fuller page reads higher; it is a number to compare between revisions.
- **`wire_crossings`.** How often a wire runs across a wire of another id. A high number means a tangled page. Order the groups with `order`, or put the crossing nets on separate pages.
- **`wire_bends` and `wire_length_g`.** The direction changes and the total length in G of every wire on the page. Many bends or a long total mean a winding page. They are numbers to compare between revisions, not a target the layout optimises.
- **`struck_labels`.** Texts a wire runs through.
- **`text_overlaps`.** Pairs of texts whose boxes overlap (`TEXT_OVERLAP`).

**Removed.** `page_cuts` is gone: a `Drawing` does not carry which markers cut a wire, so no honest count exists. `text_height_mm` is a setting, not a reading: read it from `[font.heights]` in the settings and from the profile's `min_text_height_mm`. Counts a `Drawing` cannot give (printed numbers, lone cells, contact images, stars, loose symbols) are not in the row either.

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
