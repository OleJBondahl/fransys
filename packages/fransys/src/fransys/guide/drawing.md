# Drawing well

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Layout draws the structure you author and invents none. This page says what layout reads, how to author a cabinet that draws readably, which numbers change its size, and which findings mean the design lacks structure.

## How layout reads the model

- **Function blocks.** `with d.function("P1", "Pump 1"):` groups the devices made inside it. Layout packs whole blocks onto pages, left to right, in order, and never reorders them to fill a gap. A block wider than a page is split between columns. `d.layout.order` sets the order.
- **Page ends.** A page holds the blocks whose widths sum to the content width, 1312 grid units on the house A3 sheet. A column's width is the room it took when placed: symbols, pin labels, link markers and the column gap. Read how many pages a build took from `fr.readability(result)` (`fill_percent` of each page), not from positions. A page ends at the first block that does not fit, or at the end of a drawing set.
- **Current paths.** Layout finds a current path where each net between two devices holds exactly two poles. A pole is the pair of pins a symbol passes current through, such as a coil or one contact. The path stands as one column, top to bottom, with straight wires. A net of three or more poles ends a path.
- **How to author a path.** Author each path with `d.series`. `d.series(a, b, c, wire=...)` wires every hop pole to pole, so its elements form a path.
- **Block edges end a path.** A path never crosses from one function block into the next. When the two blocks land on different pages, the wire between them is cut into a marker pair. Keep each circuit inside one block. A device with two or more functions can split across blocks, a coil here and a contact there. A function of such a device, written in another block's `d.series`, draws in that block, and its coil's contact table names that page.
- **Tall paths.** A path taller than the page continues at the top of the next column, on the same sheet while there is room, then on the next sheet. The wire across each cut becomes a marker pair. The path keeps its order, and nothing runs off the page.
- **Coils on PLC channels.** A coil that a PLC channel drives stands under that channel's pin, always, whatever the row spacing. A column too tall for the page continues as tall paths do.
- **Box pins in marking order.** A box prints its pins in marking order, whatever order its wired partners stand in, and the columns hung under it follow those pins.
- **Device chains.** Some devices draw no symbol of their own, such as modules with an IN and an OUT connector. When such devices in one block are wired hop to hop, each wire alone, they form a chain. Each device then draws as one box with its wired pins only, and the chain stands as one column. A box's top pins face the device above and its bottom pins the device below, so each hop's wires run straight down. A chain starts at its end that sorts first by designation. A ring opens at its device that sorts first, and the wire that closes the ring becomes a marker pair.
- **Supplies.** A declared DC supply (`d.dc_supply`) draws a power symbol at each pin on its rails, with no wire or marker. `d.ac_supply` keeps AC rails as terminals, drawn at each pin they feed. An undeclared rail is a plain net: wires and link markers.
- **Markers.** A marker pair stands where one wire's two ends land on different pages. A net of three or more ports that is not drawn as wires gets one marker per port. A terminal is drawn at each of its wires instead. A net reference is filled with one of eight colours; every reference of the same net in the PDF has the same colour, and the text is the reference.
- **Nothing connected, nothing drawn.** A symbol with nothing connected is not drawn; its list holds it.
- **An actuator on every contact.** Every contact of a manually operated device draws its own actuator symbol.
- **Flat designs.** A design of devices joined by point-to-point `d.series` calls is drawn from its nets alone. Circuits that share no net fill pages one after the other. One large connected circuit with no declared supply piles onto a single page and overflows it. Declare the supply and write each path as a series (see `detail.md`).

The `draw` helper below builds a cabinet and reads its findings. The block after it builds twelve relays on
one declared 24 V supply.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU


class Cabinet(NamedTuple):
    pass


Path("cover.md").write_text("# Cabinet\n", encoding="utf-8")


def rows(model, table):
    """The rows of a layout table: `Record` values, whose fields are read by name."""
    return model.tables[table].values()


def draw(body, top=None):
    """Build one cabinet with a schematic; return its finding codes and its page count."""

    @fr.unit(
        "cab",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="First",
        by="XX",
        title="Cabinet",
        number="C-1",
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
    return [f.code for f in fr.check(result)], len(result.model.tables["layout.page"])
```

```python
def relays(c):
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24").output)
    for i in range(1, 13):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
        c.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))


declared, _ = draw(relays)
```

## A checklist for a readable cabinet

The pump-station example in the examples repository has this shape.

1. One unit per cabinet, and one function block per circuit: incoming supply, control supply, PLC, one block per motor starter.
2. Keep every device of a circuit inside its block, so no path crosses a block edge. Put each series in the block of the circuit it belongs to. If the page that results reads badly, report it; a block chosen to shape the page hides a layout defect.
3. Declare each supply where it starts: `d.ac_supply` on the incoming terminals, `d.dc_supply` on the 24 V strip.
4. Distribute through terminal strips with named, bridged runs, and give each consumer its own terminal.
5. Wire each circuit as a path, source first: supply, protection, switching, load. Layout stands the bands in that order, with the first terminal on top and the last at the bottom.
6. Set `hide_unused_pins=True` to leave unwired pins of box-drawn devices off the drawings. The lists keep them.
7. A terminal that only the parent wires is left off the unit's own pages; its table lists it.
9. Build, then read `fr.check(result)`. The last part of this page lists the findings that point at a missing item above.

Take each consumer's terminal inside the consumer's own block, since a terminal joins the block it is first taken in. A terminal shared by blocks adds no marker.

## Printed sizes and grid pitch

Authored numbers live on the profile. A unit sets its own in its body, and a unit with none uses the house values. `layout-numbers.md` lists every profile keyword with its house value and effect.


```python
def circuits(c, hide):
    psu = c.device("G1", "DEMO-PSU-24")
    dc = c.dc_supply("24VDC", psu.output)
    for i in range(1, 34):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
            c.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))
    c.layout.profile(hide_unused_pins=hide)


for hide in (False, True):
    draw(lambda c: circuits(c, hide))
```

## Which hint to use

Each hint advises the layout and invents nothing. Every name below is a method of `d.layout`.

| You want | Tool | What it does to the drawing |
| --- | --- | --- |
| This order | `d.layout.order(g1, g2)` | Moves `g2` after `g1`. The other groups keep their places. |

`d.series` is a wiring call, not a layout hint, so it has no row.

The block below applies each row to three relay blocks and reads the result.

```python
def drawn(body):
    """Build one cabinet; return the block names on each page and the finding codes."""
    handles = {}

    @fr.unit(
        "cab",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="First",
        by="XX",
        title="Cabinet",
        number="C-1",
    )
    def cabinet(c):
        handles.update(body(c))
        return Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
    result = fr.build(d, doc)
    names = {handle.id: name for name, handle in handles.items()}
    pages = sorted(rows(result.model, "layout.page"), key=lambda p: (p.drawing_set, p.number))
    return [[names[g.group] for g in p.groups] for p in pages], [f.code for f in fr.check(result)]


def blocks(c, hint=None, count=3):
    groups = {}
    for i in range(1, count + 1):
        with c.function(f"F{i}", f"Relay {i}") as group:
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
            feed = c.terminal_strip(f"X{i}", "DEMO-TB-2.5", 2)
            c.series(feed, k.coil, feed, wire=(BU, 0.75))  # a symbol with nothing connected is not drawn
        groups[f"F{i}"] = group
    if hint:
        hint(c.layout, groups)
    return groups


assert drawn(blocks)[0] == [["F1", "F2", "F3"]]
ordered, _ = drawn(lambda c: blocks(c, lambda hints, g: hints.order(g["F3"], g["F1"])))
assert ordered == [["F2", "F3", "F1"]]
```

## What overrides what

The profile sets the numbers, and the hints set the page order.

- **A profile reaches only its own unit.** The top design's profile does not reach a unit, and a unit with no profile of its own uses the house numbers. A unit or the top design has at most one profile, and a second one with other numbers raises `AuthorError`.
- **A keyword left out** keeps its house value.
- **Order hints that form a cycle** give the ERROR finding `ORDER_HINT_CYCLE`, which names the file and line of each hint in the cycle.
- **A chain names a box-drawn function only at its head or its tail.** A PLC channel or a supply output stands there and anchors the path at its pin. In the middle the build raises `fr.AuthorError` that says where box-drawn functions may stand.

```python
def numbers(c):
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24").output)
    for i in range(1, 34):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
            c.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))


draw(lambda c: (numbers(c), c.layout.profile(hide_unused_pins=True)))

ranked = lambda hints, g: hints.order(g["F3"], g["F2"], g["F1"])
assert drawn(lambda c: blocks(c, ranked))[0] == [["F3", "F2", "F1"]]


def cycle(hints, g):
    hints.order(g["F1"], g["F2"])
    hints.order(g["F2"], g["F1"])


draw(lambda c: numbers(c), top=lambda d: d.layout.profile(hide_unused_pins=True))  # the top design's profile reaches no unit

try:
    draw(lambda c: (c.layout.profile(), c.layout.profile()))
except Exception as error:
    assert type(error).__name__ == "AuthorError"
else:
    raise AssertionError("a second profile must raise")

assert "ORDER_HINT_CYCLE" in draw(lambda c: blocks(c, cycle))[0]
```

## Readability findings

The numbers that tell whether the printed pages can be read are in `fr.readability`: `readability.md`. The text heights are the library's fixed heights.
