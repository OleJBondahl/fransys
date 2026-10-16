# Detail calls

Each call here is for a case no core call writes. Try the core call first (`authoring.md`): a
series pairs poles and takes the next free terminal or core, and layout reads its structure. `d.detail`
is a `fr.Detail` handle, as `d.layout` is a `fr.Layout`.

## When a detail call is right

| call | only for |
|---|---|
| `d.detail.wire(a, b, wire=...)` | two named pins off any path, such as a signal pair; one signal daisy-chained, `d.detail.wire(a, b, c)`; a hop whose printed wire differs from its row |
| `d.detail.star(src, targets, wire=...)` | one point wired to many, one wire each; `d.detail.wire(src, *targets)` chains them instead |
| `X1[3]`, `.inner`, `.outer` | a terminal whose number or side is fixed: a published pinout, or several wires on one terminal |
| `d.pair(a, w1, b)` | a signal pair through a cable, pin for pin, with no line or load side; it is a verb, not a detail |
| `W1.core(BN, a, b)` | a core whose colour or number a termination plan fixes |
| `d.detail.net(name, *pins)` | a named net that no wire joins, such as a bus shown by its label |
| `d.detail.busbar(a, b)`, `d.detail.rail_bond(a, b)` | a rack's internal power jumper; terminals bonded through their mounting rail |

A real circuit that no core call and no row here can write is a gap in Fransys. Report it with its
smallest shape.

## d.detail.wire

`d.detail.wire(a, b, wire=(BU, 0.75), label=, n=)` draws one wire. `wire=` takes the shapes `d.series` takes: a size, a table of rows or a
`(colour, size)`, but not a tuple per pole. A size or a table takes the row of the net. More than two
pins draw a daisy chain, one wire per neighbouring pair. `label="L1"` prints a label on the wire.
`n=2` draws a second wire in parallel between the same two pins. A strip or a run as a pin stands
for its next free terminal, on the inner side.

### One point to many

`d.detail.star(src, targets, wire=...)` draws one wire from `src` to each target in the tuple or list
`targets`, and none between targets. A strip as `src` stands for one terminal, shared by all
targets. `wire=` reads as it does for `d.detail.wire`.

### A wire with no row

A bare number is always a size. A row's value in a table is a colour or a `(colour, size)`, never a
bare number. When `d.series` or `d.detail.wire` cannot give a wire its row as written, the row is
read at build end from the rails its net carries. Only rails of the wire's own unit and the units
below it count. A rail never crosses a unit boundary from its container.

A net that holds a PLC channel's signal takes `DC_SIGNAL`. A pin whose part states `source_row`
(a drive's `U`, `V` and `W`) gives its row. A net with none of these is the error
`WIRE_ROW_UNRESOLVED`, which names the net and the wire; give `wire=(colour, size)` on that series.
A series of only cables, strips and loads needs no `wire=`.

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
h1 = d.device("H1", "DEMO-LAMP-24")
h2 = d.device("H2", "DEMO-LAMP-24")
d.detail.wire(x1[1], h1[1], wire=(BU, 0.75), label="S1")
d.detail.wire(x1[1], h1[1], wire=(BU, 0.75), n=2)
d.detail.wire(x1[2], h1[2], h2[2], wire=(BU, 0.75))
```

### Equipment others supply

A part-less external strip offers only `.outer`. A field wire on it is a fixed terminal.

```python
import fransys as fr
from fransys.colours import BK

d = fr.design("demo_parts")
x8 = d.terminal_strip("X8", None, 4, external=True)
q8 = d.device("Q8", None, external=True, pins=("L1", "L2", "L3", "N", "PE"))
d.ac_supply("S", 400, q8["L1"], q8["L2"], q8["L3"], n=q8["N"])
d.detail.wire(x8[1].outer, d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 1.5))
```

### Fixed terminals

`X1[3]` takes terminal 3 and `.inner` or `.outer` names its side. A series enters a strip at the
right side by itself. `.outer` and `.inner` decide which column of the terminal CSV a wire lands in. Name a side only when the plan fixes it; `d.series(x1[3].outer, f1.element)` takes it too. A series may also start at a pin: `d.series(k1.coil["A1"], a1.di_1)`.

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
h1 = d.device("H1", "DEMO-LAMP-24")
with d.function("FEED", "Lamp feed"):
    d.detail.wire(x1[1], h1[1], wire=(BU, 0.75))
d.detail.wire(x1[2].outer, h1[2], wire=(BU, 0.75))
```

### One wire to a PE terminal

A cable's green-yellow core is the core way (`series.md`, Earth pins). A single wire is a detail.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
pe = x1.run("PE", 2, bridged=True)
m1 = d.device("M1", "DEMO-MOTOR-4KW")
d.detail.wire(m1.motor["PE"], pe[1], wire=(GNYE, 2.5))
d.earth(m1.motor["PE"], pe[1])
```

### A PE bar's screws

A bar's function takes its next free screw (`series.md`, Earth pins). One wire to a screw is a detail.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
pe1 = d.device("PE1", "DEMO-PEBAR-20")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP")
d.detail.wire(m1.motor["PE"], pe1.pe, wire=(GNYE, 2.5))  # screw 1
w2.core(5, pe1.pe)  # the one-ended screen, screw 2
```

## d.detail.net, d.detail.busbar, d.detail.rail_bond

`d.detail.net(name, *pins, kind=)` names a net of pins that no wire joins. `kind` is `fr.CONTROL`
(the default), `fr.SIGNAL` or `fr.GENERIC`. It does not make a `PE` or supply net: those have
`d.earth` and the supply calls.

`d.detail.busbar(a, b)` joins two pins by a rack's internal power jumper. `d.detail.rail_bond(a, b)`
joins two terminals bonded through their mounting rail. Neither has a wire-list row, colour or
gauge, and both close the net like a conductor.

```python
import fransys as fr

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
d.detail.net("BUS", x1[1], x1[2], kind=fr.SIGNAL)
d.detail.busbar(x1[3], x1[4])
d.detail.rail_bond(x1[1], x1[3])
```

## W1.core

`W1.core(BN, a, b)` wires one core between two pins, named by its colour or its number. The core
colours come from the cable part. A green-yellow core goes to a protective-earth pin only.

```python
import fransys as fr
from fransys.colours import BK, BN, GY

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
pe = d.terminal_strip("X2", "DEMO-TB-PE-2.5", 2)
h1 = d.device("H1", "DEMO-LAMP-24")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
w1.core(BN, x1[1], h1[1])
w1.core(BK, x1[2], h1[2])
w1.spare(GY, at=x1[7])
w1.spare()
w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP", length_m=25)
w2.core(1, x1[3], h1[1])
w2.core(5, pe[1])
w2.spare()
```

A core you leave unused is `w1.spare(GY)`, or `w1.spare()` for every core not wired so far. `at=x1[7]`
parks one on a pin. The cable drawing prints "spare" on its row. A screen (`SH`) earthed at one end
takes one pin: `w2.core(5, pe[1])`. A part with `pairs` in its `[cable_product]` table gets a bracket
and a P1, P2 label over each pair's rows.

`fn.pins` gives a function's pins as a tuple, in the order the connector list prints (`1, 2, 10, A1`).
To land a cable's cores on two connectors pin by pin, loop over it. The pairing rule stays yours.

```python
import fransys as fr

d = fr.design("demo_parts")
a = d.device("J1", "DEMO-CONN-4P")
b = d.device("J2", "DEMO-CONN-4P")
w3 = d.cable("W3", "DEMO-CBL-4G1.5", length_m=2)
for core, (pin_a, pin_b) in enumerate(zip(a.x1.pins, b.x1.pins, strict=True), start=1):
    w3.core(core, pin_a, pin_b)
```

## Worked example: star-delta winding ends

A star-delta starter wires the six winding ends of a motor. The demo parts have no six-end motor, so
a strip stands for its terminal box: `X2` terminals 1 to 6 are U1, V1, W1, U2, V2, W2. K1 feeds
U1, V1, W1 through a series. K3 joins U1-W2, V1-U2 and W1-V2. K2 shorts U2, V2, W2.

```python
import fransys as fr
from fransys.colours import BK

WIRE = (BK, 2.5)
d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", 230, x0[1], x0[2], x0[3])
k1, k2, k3 = (d.device(tag, "DEMO-CTR-3P-24") for tag in ("K1", "K2", "K3"))
xm = d.terminal_strip("X2", "DEMO-TB-2.5", 6)
d.series(ac, k1.main, xm, wire=WIRE)
for pole, delta_load in enumerate((6, 4, 5)):  # K3 pole 1 joins U1-W2, 2 V1-U2, 3 W1-V2
    line, load = str(2 * pole + 1), str(2 * pole + 2)
    d.detail.wire(xm[pole + 1], k3.main[line], wire=WIRE)
    d.detail.wire(k3.main[load], xm[delta_load], wire=WIRE)
    d.detail.wire(xm[pole + 4], k2.main[line], wire=WIRE)
d.detail.wire(k2.main["2"], k2.main["4"], k2.main["6"], wire=WIRE)
```

The winding ends stay detail for two reasons. Each end is a fixed terminal, since the motor
plate fixes which end is U2. The star bridge joins three load-side pins that no path pairs.

## Reversing starter

`d.parallel` of two contactors shares the poles in order, so it makes no phase swap. Until an option
for a swap lands, write the reverse contactor's crossing with `d.detail.wire`: K2's line poles 2
and 3 take L3 and L2.

```python
import fransys as fr
from fransys.colours import BK

WIRE = (BK, 2.5)
d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", 230, x0[1], x0[2], x0[3])
k1, k2 = (d.device(tag, "DEMO-CTR-3P-24") for tag in ("K1", "K2"))
xm = d.terminal_strip("X2", "DEMO-TB-2.5", 3)
d.series(ac, k1.main, xm, wire=WIRE)
for line, crossed in (("1", "1"), ("3", "5"), ("5", "3")):
    d.detail.wire(k1.main[line], k2.main[crossed], wire=WIRE)
for pole, terminal in enumerate((1, 2, 3)):
    d.detail.wire(k2.main[str(2 * pole + 2)], xm[terminal], wire=WIRE)
```

## Flat wiring and fixed terminals on a page

Two drawing effects need a detail call to show, and `drawing.md` states the rules. Point-to-point
`d.detail.wire` hops with no declared supply give layout nets only: one large connected circuit
piles onto a single page and overflows it (`OUT_OF_CONTENT_BOX`). Declare the supply and write each
path as a series, and the same twelve relays spread over pages. A lamp wired from one fixed
terminal of a shared run adds no marker, and neither does a terminal taken in each block.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU


class Cabinet(NamedTuple):
    pass


Path("cover.md").write_text("# Cabinet\n", encoding="utf-8")


def built(body):
    @fr.unit(
        "cab", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX",
        title="Cabinet", number="C-1",
    )
    def cabinet(c):
        body(c)
        return Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=Path("cover.md"))
    return fr.build(d, doc)


def relays(c, declare):
    psu = c.device("G1", "DEMO-PSU-24")
    dc = c.dc_supply("24VDC", psu.output) if declare else None
    for i in range(1, 13):
        with c.function(f"F{i}", f"Relay {i}"):
            k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
        if dc is not None:
            c.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))
        else:
            c.detail.wire(psu.output["+"], k.coil["A1"], wire=(BU, 0.75))
            c.detail.wire(k.coil["A2"], psu.output["-"], wire=(BU, 0.75))


flat = {f.code for f in fr.check(built(lambda c: relays(c, declare=False)))}
declared = {f.code for f in fr.check(built(lambda c: relays(c, declare=True)))}
assert "OUT_OF_CONTENT_BOX" in flat
assert "OUT_OF_CONTENT_BOX" not in declared


def markers(own):
    """Count the link markers of 30 lamp blocks fed from one 24 V run."""

    def body(c):
        psu = c.device("G1", "DEMO-PSU-24")
        run = c.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 40, bridged=True)
        c.detail.wire(psu.output["+"], run[1], wire=(BU, 0.75))
        for i in range(1, 31):
            with c.function(f"F{i}", f"Lamp {i}"):
                lamp = c.device(f"H{i}", "DEMO-LAMP-24")
                c.detail.wire(run[i + 1] if own else run[1], lamp.lamp["1"], wire=(BU, 0.75))
            c.detail.wire(lamp.lamp["2"], psu.output["-"], wire=(BU, 0.75))

    return len(built(body).model.tables["layout.link_marker"])


assert markers(own=True) == markers(own=False)
```

## Layout profile

`d.layout` advises the drawing and connects nothing: `chain`, `keep_together`, `break_before`, `order`,
`symbol`, `draw_in`, `side`, `sheet`, `page_title` and `profile`. Add it last, only where the structure
leaves the drawing a choice. `d.layout.side(u1.bus_in, fr.ABOVE)` puts a unit's interface above its
outline, and `fr.BELOW` below it. An interface with no harness line ignores it.
`d.layout.page_title(x1, "Field terminals")` names the pages drawing a block, function, device or nested unit.

The profile keywords, and the rule that a unit sets its own, are in [`layout-numbers.md`](../layout-numbers/index.md#profile-keywords).

`d.layout.chain(r1.lamp, k3.main, f3.element, beside=k1.main)` draws the chain beside the element
`k1.main`, joined by short unmarked horizontals. Wire first: the chain joins the element by each end
net they share, one or two, else `AuthorError` names them.

```python
import fransys as fr

d = fr.design("demo_parts")
with d.function("RUN", "Pump run") as run:
    d.device("K1", "DEMO-RLY-2CO-24")
with d.function("LAMPS", "Lamps") as lamps:
    d.device("H1", "DEMO-LAMP-24")
d.layout.order(run, lamps)
d.layout.profile(hide_unused_pins=True)
```
