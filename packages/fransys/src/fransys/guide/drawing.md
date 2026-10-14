# Drawing well

Layout draws the structure you author and invents none. This page says what layout reads, how to author a cabinet that draws readably, which numbers change its size, and which findings mean the design lacks structure.

## How layout reads the model

- **Function blocks.** `with d.function("P1", "Pump 1"):` groups the devices made inside it. Layout packs whole blocks onto pages, left to right, in order, and never reorders them to fill a gap. A block wider than a page is split between columns and reports `GROUP_SPLIT`. `d.layout.order`, `keep_together`, `break_before` and the profile's `group_ranks` set the order.
- **Page ends.** A page holds the blocks whose widths sum to the content width, 1312 grid units on the house A3 sheet. A column's width is the room it took when placed: symbols, pin labels, link markers and the column gap. In the twelve-relay example below, the first relay blocks each take 176 units, so the first page holds the supply and six relays. A page ends at the first block that does not fit, at a `break_before`, at a `keep_together` set that does not fit, or at the end of a drawing set.
- **Current paths.** Layout finds a current path where each net between two devices holds exactly two poles. A pole is the pair of pins a symbol passes current through, such as a coil or one contact. The path stands as one column, top to bottom, with straight wires. A net of three or more poles ends a path.
- **How to author a path.** Author each path with `d.series`. Hand-wired `d.wire` hops form a path only while each net keeps to two poles. `d.series(a, b, c, wire=...)` wires every hop pole to pole, so its elements form a path. `d.layout.chain(...)` names a path outright, and a named path wins over discovery.
- **Block edges end a path.** A path never crosses from one function block into the next. When the two blocks land on different pages, the wire between them is cut into a marker pair and `CHAIN_BROKEN` warns. Keep each circuit inside one block.
- **Supplies.** A declared DC supply (`d.dc_supply`) draws a power symbol at each pin on its rails, with no wire or marker. `d.ac_supply` keeps AC rails as terminals and references. An undeclared rail is a plain net: wires and link markers.
- **Markers.** A marker pair stands where one wire's two ends land on different pages. A net of three or more ports that is not drawn as wires gets one marker per port. A terminal drawn on both pages needs none.
- **Flat designs.** A design of devices joined by point-to-point `d.wire` calls is drawn from its nets alone. Circuits that share no net fill pages one after the other. One large connected circuit with no declared supply piles onto a single page and overflows it. Declare the supply and write each path as a series.

The two blocks below build the same twelve relays on one 24 V supply. Only the second declares the supply.

```python
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU


class Cabinet(NamedTuple):
    pass


Path("cover.md").write_text("# Cabinet\n", encoding="utf-8")


def draw(body, top=None):
    """Build one cabinet with a schematic; return its finding codes and its page count."""

    @fr.unit(
        "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
        title="Cabinet", number="C-1",
    )
    def cabinet(c):
        body(c)
        return Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    if top:
        top(d)
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
    result = fr.build(d, doc)
    draw.model = result.model
    return [f.code for f in fr.check(result)], len(result.model.tables["layout.page"])
```

```python
def relays(c, declare):
    psu = c.device("G1", "DEMO-PSU-24")
    if declare:
        c.dc_supply("24VDC", psu.output)
    for i in range(1, 13):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
        c.wire(psu.output["+"], k.coil["A1"], wire=(BU, 0.75))
        c.wire(k.coil["A2"], psu.output["-"], wire=(BU, 0.75))


flat, _ = draw(lambda c: relays(c, declare=False))
declared, _ = draw(lambda c: relays(c, declare=True))
assert "OUT_OF_CONTENT_BOX" in flat
assert "OUT_OF_CONTENT_BOX" not in declared


def coil_x(model, n):
    return next(p.x for p in model.tables["layout.symbol_placement"].values() if p.key[-3:-1] == (f"F{n}/K{n}", "fn"))


assert coil_x(draw.model, 2) - coil_x(draw.model, 1) == 184
assert coil_x(draw.model, 7) < coil_x(draw.model, 1)
```

## A checklist for a readable cabinet

The pump-station example in the examples repository has this shape.

1. One unit per cabinet, and one function block per circuit: incoming supply, control supply, PLC, one block per motor starter.
2. Keep every device of a circuit inside its block, so no path crosses a block edge.
3. Declare each supply where it starts: `d.ac_supply` on the incoming terminals, `d.dc_supply` on the 24 V strip.
4. Distribute through terminal strips with named, bridged runs, and give each consumer its own terminal.
5. Wire each circuit as a path, source first: supply, protection, switching, load. Layout stands the bands in that order, with the first terminal on top and the last at the bottom.
6. Set the page order once with `d.layout.profile(group_ranks=...)`. A rank map replaces the house one whole, and an unranked block sorts last.
7. Set `hide_unused_pins=True` to leave unwired pins of box-drawn devices off the drawings. The lists keep them.
8. A terminal that only the parent wires is left off the unit's own pages; its table lists it.
9. Build, then read `fr.check(result)`. The last part of this page lists the findings that point at a missing item above.

Take each consumer's terminal inside the consumer's own block, since a terminal joins the block it is first taken in. One terminal shared by blocks on different pages needs a marker pair for each of them.

```python
def markers(own):
    """Count the link markers of 30 lamp blocks fed from one 24 V run."""

    @fr.unit(
        "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
        title="Cabinet", number="C-1",
    )
    def cabinet(c):
        psu = c.device("G1", "DEMO-PSU-24")
        run = c.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 40, bridged=True)
        c.wire(psu.output["+"], run[1], wire=(BU, 0.75))
        for i in range(1, 31):
            with c.function(f"F{i}", f"Lamp {i}"):
                lamp = c.device(f"H{i}", "DEMO-LAMP-24")
                terminal = run[i + 1] if own else run[1]
                c.wire(terminal, lamp.lamp["1"], wire=(BU, 0.75))
            c.wire(lamp.lamp["2"], psu.output["-"], wire=(BU, 0.75))
        return Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
    return len(fr.build(d, doc).model.tables["layout.link_marker"])


assert markers(own=True) < markers(own=False)
```

## Printed sizes and grid pitch

Authored numbers live on the sheet and the profile. A unit sets its own in its body, and a unit with none uses the house values. `layout-numbers.md` lists every sheet number and profile keyword with its house value and effect.

- **`module_mm`, on the sheet** (see `layout-numbers.md`). This is the grid pitch. One grid unit is `module_mm / 8` millimetres, and symbols and spacing scale with it; text and line widths are fixed in mm. The house value is 2.5. A smaller value fits more on a page, and a larger one fits less. Pitch is the reader's choice, not a fix: content that does not fit is split into function blocks.
- **`text_height_mm`, on the profile** (see `layout-numbers.md`). A style choice: the capital height in mm (ISO 3098) of the smallest text on every page kind, 1.8 in the house profile, which takes 8 `G`. A larger role prints at its ISO size (2.5, 3.5 or 5 mm) or this height, whichever is larger. Nothing shrinks text to fit. A value past what the symbols leave room for leaves tags without a place.
- **`min_text_height_mm`, on the profile.** This is the floor under the text, a capital height in millimetres: `Decimal("1.8")` in the house profile, the height the house `text_height_mm` prints. The floor changes no drawing. A profile that prints text under it gets one `TEXT_TOO_SMALL`.
- **`column_gap`, on the profile** (see `layout-numbers.md`). This is spacing: grid units between columns, 48 in the house profile. Change it to give wires and tags room, not to fit a page.

```python
def circuits(c, module_mm, text_height_mm=Decimal("1.8")):
    psu = c.device("G1", "DEMO-PSU-24")
    dc = c.dc_supply("24VDC", psu.output)
    for i in range(1, 34):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
            c.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))
    sheet = c.layout.sheet(
        "A3 compact", width_mm=420, height_mm=297, content_x_mm=5, content_y_mm=5,
        content_width_mm=410, content_height_mm=267, frame_columns=8, frame_rows=6,
        module_mm=Decimal(module_mm),
    )
    c.layout.profile(sheet=sheet, text_height_mm=text_height_mm)


_, house_pages = draw(lambda c: circuits(c, "2.5"))
_, compact_pages = draw(lambda c: circuits(c, "1.5"))
assert compact_pages < house_pages
```

## Which hint to use

Each hint advises the layout and invents nothing. Every name below is a method of `d.layout`.

| You want | Tool | What it does to the drawing |
| --- | --- | --- |
| These items in one column | `d.layout.chain(a, b, c)` | Stands them in one column, top to bottom, source first. |
| These groups on one sheet | `d.layout.keep_together(g1, g2)` | Moves the later groups beside the first, so they share a page when their widths fit. |
| This order | `d.layout.order(g1, g2)` | Moves `g2` after `g1`. The other groups keep their places. |
| This group starts a new sheet | `d.layout.break_before(g)` | Starts a new page at `g`. |
| This page title | `d.layout.page_title(thing, text)` | Prints `text` as the title of the pages that draw the block, function or device. |

`d.series` is a wiring call, not a layout hint, so it has no row.

The block below applies each row to three relay blocks and reads the result.

```python
def drawn(body):
    """Build one cabinet; return the block names on each page, and the x of each named function."""
    handles = {}

    @fr.unit(
        "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
        title="Cabinet", number="C-1",
    )
    def cabinet(c):
        handles.update(body(c))
        return Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
    result = fr.build(d, doc)
    names = {handle.id: name for name, handle in handles.items()}
    pages = sorted(result.model.tables["layout.page"].values(), key=lambda p: (p.drawing_set, p.number))
    x = {names[p.function]: p.x for p in result.model.tables["layout.symbol_placement"].values() if p.function in names}
    return [[names[g.group] for g in p.groups] for p in pages], x


def blocks(c, hint=None, count=3):
    groups = {}
    for i in range(1, count + 1):
        with c.function(f"F{i}", f"Relay {i}") as group:
            c.device(f"K{i}", "DEMO-RLY-2CO-24")
        groups[f"F{i}"] = group
    if hint:
        hint(c.layout, groups)
    return groups


def coils(c, chain):
    psu = c.device("G1", "DEMO-PSU-24")
    dc = c.dc_supply("24VDC", psu.output)
    ks = [c.device(f"K{i}", "DEMO-RLY-2CO-24") for i in (1, 2, 3)]
    lamp = c.device("H1", "DEMO-LAMP-24")
    c.series(dc.plus, *(k.coil for k in ks), dc.minus, wire=(BU, 0.75))
    c.series(ks[0].coil, lamp.lamp, dc.minus, wire=(BU, 0.75))
    if chain:
        c.layout.chain(ks[0].coil, ks[1].coil, ks[2].coil)
    return {f"K{i}": k.coil for i, k in enumerate(ks, 1)}


_, loose = drawn(lambda c: coils(c, chain=False))
_, chained = drawn(lambda c: coils(c, chain=True))
assert len(set(loose.values())) > 1
assert len(set(chained.values())) == 1
assert drawn(blocks)[0] == [["F1", "F2", "F3"]]
together, _ = drawn(lambda c: blocks(c, lambda hints, g: hints.keep_together(g["F1"], g["F3"])))
assert together == [["F1", "F3", "F2"]]
ordered, _ = drawn(lambda c: blocks(c, lambda hints, g: hints.order(g["F3"], g["F1"])))
assert ordered == [["F2", "F3", "F1"]]
broken, _ = drawn(lambda c: blocks(c, lambda hints, g: hints.break_before(g["F2"])))
assert broken == [["F1"], ["F2", "F3"]]
```

## What overrides what

The profile sets the numbers and the page order, and the hints then act on that order.

- **A sheet needs a profile.** `d.layout.sheet(...)` changes nothing until `d.layout.profile(sheet=...)` names it. A profile that leaves `sheet` out draws on the house A3 sheet.
- **A profile reaches only its own unit.** The top design's profile does not reach a unit, and a unit with no profile of its own uses the house numbers. A unit or the top design has at most one profile, and a second one with other numbers raises `AuthorError`.
- **A keyword left out keeps its house value.** A rank map you give replaces the house one whole.
- **`order` beats `group_ranks`.** The ranks sort the blocks first, then each `order` hint moves blocks from that order.
- **`keep_together` beats `order`.** It runs after the order hints, pulls its groups next to the first, and reports nothing when that breaks an `order` hint.
- **`break_before` on a later group of a `keep_together` set** leaves the set unkept and reports `KEEP_TOGETHER_UNMET`. On the set's first group it changes nothing.
- **Order hints that form a cycle** make the build raise `fr.AuthorError` naming the cycle.
- **A chain names a box-drawn function only at its head or its tail.** A PLC channel or a supply output stands there and anchors the path at its pin. In the middle the build raises `fr.AuthorError` that says where box-drawn functions may stand.

```python
def compact_sheet(scope):
    return scope.layout.sheet(
        "A3 compact", width_mm=420, height_mm=297, content_x_mm=5, content_y_mm=5,
        content_width_mm=410, content_height_mm=267, frame_columns=8, frame_rows=6,
        module_mm=Decimal("1.5"),
    )


def numbers(c, sheet=False):
    for i in range(1, 34):
        with c.function(f"F{i}", f"Relay {i}"):
            c.device(f"K{i}", "DEMO-RLY-2CO-24")
    compact = compact_sheet(c)
    if sheet:
        c.layout.profile(sheet=compact)


assert draw(lambda c: numbers(c, sheet=False))[1] == house_pages
assert draw(lambda c: numbers(c, sheet=True))[1] < house_pages

ranked = lambda hints, g: hints.profile(group_ranks={"F3": 1, "F2": 2, "F1": 3})
assert drawn(lambda c: blocks(c, ranked))[0] == [["F3", "F2", "F1"]]


def ranked_then_ordered(hints, g):
    ranked(hints, g)
    hints.order(g["F1"], g["F3"])


assert drawn(lambda c: blocks(c, ranked_then_ordered))[0] == [["F2", "F1", "F3"]]


def kept_and_ordered(hints, g):
    hints.keep_together(g["F1"], g["F3"])
    hints.order(g["F2"], g["F3"])


assert drawn(lambda c: blocks(c, kept_and_ordered))[0] == [["F1", "F3", "F2"]]


def kept_and_broken(hints, g):
    hints.keep_together(g["F1"], g["F2"])
    hints.break_before(g["F2"])


unkept = lambda c: blocks(c, kept_and_broken)
assert "KEEP_TOGETHER_UNMET" in draw(lambda c: unkept(c))[0]
assert drawn(unkept)[0] == [["F1"], ["F2", "F3"]]


def cycle(hints, g):
    hints.order(g["F1"], g["F2"])
    hints.order(g["F2"], g["F1"])


top_only = draw(lambda c: numbers(c), top=lambda d: d.layout.profile(sheet=compact_sheet(d)))[1]
assert top_only == house_pages

try:
    draw(lambda c: (c.layout.profile(text_height_mm=Decimal("1.8")), c.layout.profile(text_height_mm=Decimal("2.0"))))
except Exception as error:
    assert type(error).__name__ == "AuthorError"
else:
    raise AssertionError("a second profile must raise")

try:
    drawn(lambda c: blocks(c, cycle))
except Exception as error:
    assert type(error).__name__ == "AuthorError" and "cycle" in str(error)
else:
    raise AssertionError("an order cycle must raise")
```

## Findings that mean missing structure

- **`FUNCTION_UNPLACED_IN_COLUMN`.** No current path reaches the function, so it stands alone in a column. A box-drawn device, such as a power supply or a lamp, has no pole of its own. It stands in a path only when a path ends on it. A lamp wired straight across two rails is on none, and wired after a contact it ends that contact's path. Many of these in one unit mean many devices hang on no path.
- **`LABEL_UNPLACED`.** A tag, marking or cross-reference found no free place. A `text_height_mm` above the house value is one cause. Put it back to 1.8.
- **`CHAIN_BROKEN`.** A path was cut by a page break between two blocks. Keep the circuit in one block.
- **`PAGE_OVERFULL` and `OUT_OF_CONTENT_BOX`.** A circuit is too big for its page. Declare its supply, wire it as paths, or split it into blocks. Else send the smallest model. `PAGE_PAD` frames the ink.
- **Readability.** Five findings tell you whether the printed pages can be read. `TEXT_TOO_SMALL` says the profile prints text under `min_text_height_mm`. `PAGE_UNDERFILLED` says a page's content covers under half of its content box. `TEXT_OVERLAP`, `WIRE_OVER_LABEL` and `LABEL_UNPLACED` say text collides with text or a wire, or has no place. To print text larger, raise `text_height_mm` on the profile.

The next block counts the first two. Lamps wired across the rails stand alone, lamps after a contact do not, and a text height of 24 leaves tags without a place.

```python
def lamps(c, after_contact):
    psu = c.device("G1", "DEMO-PSU-24")
    for i in range(1, 6):
        k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
        h = c.device(f"H{i}", "DEMO-LAMP-24")
        if after_contact:
            c.wire(psu.output["+"], k.co_1["11"], wire=(BU, 0.75))
            c.wire(k.co_1["14"], h.lamp["1"], wire=(BU, 0.75))
        else:
            c.wire(psu.output["+"], h.lamp["1"], wire=(BU, 0.75))
        c.wire(h.lamp["2"], psu.output["-"], wire=(BU, 0.75))


across, _ = draw(lambda c: lamps(c, after_contact=False))
after, _ = draw(lambda c: lamps(c, after_contact=True))
assert across.count("FUNCTION_UNPLACED_IN_COLUMN") > after.count("FUNCTION_UNPLACED_IN_COLUMN")

big_text, _ = draw(lambda c: circuits(c, "2.5", text_height_mm=Decimal("5.4")))
assert "LABEL_UNPLACED" in big_text
```

## Reading the pages as numbers

`fr.readability(result)` returns a `ReadabilityReport` with the numbers behind the findings: one `ReadabilityPage` row for each schematic page in `.pages` and one `ReadabilityUnit` row for each unit in `.units`. The three types are also in `fr.derive`. The same model gives equal rows, so compare a unit between revisions by its rows. It writes no file and `fr.write` does not emit it. It lays the schematic out again. Only a drawing set that some document prints gets rows. The look findings (`PAGE_UNDERFILLED`, `WIRE_OVER_LABEL`, `TEXT_OVERLAP`, `LONE_CELL`) skip the other sets too.

- **`drawing_set`, `number` and `unit`.** The page as printed in the corner, and the unit it belongs to (`None` for the design's own pages).
- **`text_height_mm` and `min_text_height_mm`.** The smallest printed capital height in mm and its floor. Change nothing when `text_height_mm` is at or over the floor. When under, raise `text_height_mm` on the profile.
- **`fill_percent`.** The share of the page's content box the drawing covers, in whole percent. A low number is a mostly empty page with small text. Merge its group into the page before it, or drop a `break_before`.
- **`wire_crossings`.** How often a wire runs across a wire of another net. A high number means a tangled page. Order the groups with `order`, or put the crossing nets on separate pages.
- **`struck_labels`.** Texts a wire runs through (`WIRE_OVER_LABEL`). Give the text room: a shorter tag, or a wider column gap.
- **`text_overlaps`.** Texts that overlap each other or a symbol they do not belong to (`TEXT_OVERLAP`). The same two changes.
- **`lone_cells`.** Symbols standing alone on a page (`LONE_CELL`). Keep the circuit in one block, or wire the symbol.
- **`contact_images`, `contact_image_targets` and `single_contact_images`.** The coil images on the page, the contacts they list and the images that list one. Many single images mean a relay used for one contact: a plain wire may read better.
- **`single_contact_images_other_page`.** The single images whose one contact is on another page, a part of `single_contact_images`. Such an image points off the page, so it reads less well than one beside its contact.
- **`stars`, `star_branches` and `single_branch_stars`.** The net references on the page, the branches they name on other pages and the references that name one. Many mean the net is cut across pages: declare the supply so it is drawn once, or keep the net's ends together.
- **`page_cuts`.** The wires of two ports cut at a page break, each naming one other page. Keep the two ends in one block, or add a terminal where the circuit changes page.

A unit row adds up the counts of its pages and takes the smallest `text_height_mm` and `fill_percent` and the highest `min_text_height_mm`. Its `pages` is the page count.

```python
@fr.unit(
    "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
    title="Cabinet", number="C-1",
)
def measured(c):
    lamps(c, after_contact=True)
    return Cabinet()


d = fr.design("demo_parts")
d.add(measured, "U1")
doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
report = fr.readability(fr.build(d, doc))
assert report.pages
assert all(page.text_height_mm >= page.min_text_height_mm for page in report.pages)
assert sum(unit.pages for unit in report.units) == len(report.pages)
```
