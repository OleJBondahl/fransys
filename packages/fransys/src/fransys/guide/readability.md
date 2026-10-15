# Reading the pages as numbers

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

`fr.readability(result)` returns a `ReadabilityReport` with the numbers behind the findings: one `ReadabilityPage` row for each schematic page in `.pages` and one `ReadabilityUnit` row for each unit in `.units`. The three types are also in `fr.derive`. The same model gives equal rows, so compare a unit between revisions by its rows. It writes no file and `fr.write` does not emit it. It lays the schematic out again. Only a drawing set that some document prints gets rows. The look findings (`PAGE_UNDERFILLED`, `WIRE_OVER_LABEL`, `TEXT_OVERLAP`, `LONE_CELL`) skip the other sets too.

The findings these numbers back are in `drawing.md`.

- **`drawing_set`, `number` and `unit`.** The page as printed in the corner, and the unit it belongs to (`None` for the design's own pages).
- **`text_height_mm` and `min_text_height_mm`.** The smallest printed capital height in mm and its floor. Change nothing when `text_height_mm` is at or over the floor. When under, raise `text_height_mm` on the profile.
- **`fill_percent`.** The share of the page's content box the drawing covers, in whole percent. A low number is a mostly empty page with small text. Merge its group into the page before it, or drop a `break_before`.
- **`wire_crossings`.** How often a wire or a fan-out leg runs across a wire of another net or another cable's core line or leg. A cable's own legs and line meet by design. A high number means a tangled page. Order the groups with `order`, or put the crossing nets on separate pages.
- **`wire_bends`, `wire_length_mm`.** The direction changes and the total length in mm of every conductor line drawn on the page: routed wires, straight power leads and fan-out legs. A harness or cable line is not counted. Many bends or a long total mean a winding page: a shorter run or a nearer neighbour reads better. They are numbers to compare between revisions, not a target the layout optimises.
- **`struck_labels`.** Texts a wire runs through (`WIRE_OVER_LABEL`). It is INFO: report it with the smallest model.
- **`text_overlaps`.** Texts that overlap each other or a symbol they do not belong to (`TEXT_OVERLAP`).
- **`lone_cells`.** Symbols standing alone on a page (`LONE_CELL`). Keep the circuit in one block, or wire the symbol.
- **`contact_images`, `contact_image_targets` and `single_contact_images`.** The coil images on the page, the contacts they list and the images that list one. Many single images mean a relay used for one contact: a plain wire may read better.
- **`single_contact_images_other_page`.** The single images whose one contact is on another page, a part of `single_contact_images`. Such an image points off the page, so it reads less well than one beside its contact.
- **`stars`, `star_branches` and `single_branch_stars`.** The net references on the page, the branches they name on other pages and the references that name one. Many on several pages mean the net is cut across pages. Declare the supply so it is drawn once, or keep the net's ends together.
  A star can also stand on one page, and then it is no cut. A pin with two or more wires takes a reference for each end. One breaker pin feeding two coils gives each of the three ports a marker naming the other two. A wire that would turn back round its own device is a marker pair too. A contact above a box, with both pins wired to the box's top pins, is one. For the first, distribute through a terminal strip with a named, bridged run (checklist item 4). A bridged three-terminal run took one page from 2 stars to 1.
- **`contacts_not_drawn`.** The contact-image entries that print `N/A`: a contact no conductor reaches. Information only, with no finding, since `N/A` is how a contact with nothing drawn prints. Many on one coil mean a relay bought for contacts the circuit does not use.
- **`references_off_document`.** References on the page to a page of another document that print no location. A reader cannot tell which document to open. `REFERENCE_OFF_DOCUMENT` is a warning that names the reference and its page. The bar is 0. Print both drawing sets in one document. Or give the target's drawing set a location, so the reference names it. A reference that prints its location, such as `+FLDp1:2A`, is correct.
- **`page_cuts`.** The wires of two ports cut at a page break, each naming one other page. Keep the two ends in one block, or add a terminal where the circuit changes page.

A reference text reads `p<n>:<cell>` for sheet n of the reference's own drawing set. It reads `p<set>.<page>:<cell>` for a sheet of another set. A net reference adds the net's number, `#<n>`, then its first target. That target is a terminal of the net when it has one, else the first other end in reading order. A marker with more than two other ends prints that target and `+k` for the k others. A contact no conductor reaches prints `N/A` in place of a position. Pole-linked contacts of one item in one row print one back reference to the coil. The coil's table lists every contact.

`report.loose_symbols` counts the symbols of the whole build that no page draws, those with nothing connected. No page row carries it. A unit row counts its own loose symbols, adds up the counts of its pages and their wire length, and takes the smallest `text_height_mm` and `fill_percent` and the highest `min_text_height_mm`. Its `pages` is the page count.

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
report = fr.readability(fr.build(d, doc))
assert report.pages
assert all(page.text_height_mm >= page.min_text_height_mm for page in report.pages)
assert sum(unit.pages for unit in report.units) == len(report.pages)
```
