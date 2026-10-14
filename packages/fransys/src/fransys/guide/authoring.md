# Authoring a design

This page teaches how to write a design with `fr.design`: places, function blocks, devices, terminal
strips, wires, cables, supplies, PLC requests and layout advice. Each task has one spelling, shown
first written out and then with Python around it.

A `Design` is one object with no global state. Every call returns a handle, never a string, and later
calls take that handle. A design is a draft: `fr.build(d)` freezes it (see `build.md`).

## Easy and efficient

Each task is shown twice and builds the same model both times. The easy level writes the circuit out,
one device and one wire per line. The efficient level uses the same calls with Python around them: a
loop over a table, a function for a circuit that repeats. Neither level has a call the other lacks.

Tasks on this page: name a function block with devices; wire a terminal strip and a series;
run a cable. The sections after them list the one-call tasks.

## Name a place and a function block

A place is where units and field devices stand: a room, a site, a ship's hold. `d.location("HOLD", text)`
names it, and `place="HOLD"` on `d.device` or `fr.design` puts devices there. A cabinet is not a place.
It is a unit that holds components, units and wires (see `units.md`). A function block is one circuit,
such as one pump's or one string's: `with d.function("LAMPS", text):` puts every device made inside it
in that block, and a circuit is never a place. Tags are bare: `"HOLD"`, never `"+HOLD"`, and a prefixed
tag raises.

`d.device(tag, part, place=, parent=, mounted_on=, joins=, interface=, unused=, name=)` adds one device.
`joins={1: K1.coil["A1"]}` with `parent=K1` fits a housing on K1's own leads: pin 1 is that pin, no wire.
A contact block with `parent=` an operator head prints the head's tag, as `-S1:11` (guide `parts.md`).
`part` is a manufacturer part number such as `"DEMO-LAMP-24"`.

Floating tags: every item call takes `None` for the tag, `d.add` too, and numbers the item from
its class code. The letter comes from the part file's `class_code`, or from the release's for a unit.
Pass `name=`, the identity a released number holds to. A floating call with no `name=` raises.
An accessory takes its holder's designation and uses up no number.

`external=True` marks an item supplied by others. Every call that makes an item takes it: `d.device`,
`d.terminal_strip`, `d.cable` and `d.harness`. The item has no BOM line. A strip's terminals are external
with it; a cable's conductors carry no flag. Every drawing marks it: dashed boxes with "(by others)", dashed outlines round schematic symbols.

An external device or strip may take `None` for its part, when only its terminal names are known. It needs a tag and has no BOM line. A part-less device names its pins with `pins=` and draws as a box. A part-less strip's terminals offer only `.outer`.

```python
# easy: equipment others supply
import fransys as fr
from fransys.colours import BK

d = fr.design("demo_parts")
x8 = d.terminal_strip("X8", None, 4, external=True)
q8 = d.device("Q8", None, external=True, pins=("L1", "L2", "L3", "N", "PE"))
d.ac_supply("S", 400, q8["L1"], q8["L2"], q8["L3"], n=q8["N"])
d.wire(x8[1].outer, d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 1.5))
```

```python
# efficient: equipment others supply
import fransys as fr
from fransys.colours import BK

d = fr.design("demo_parts")
x8 = d.terminal_strip("X8", None, 4, external=True)
q8 = d.device("Q8", None, external=True, pins=("L1", "L2", "L3", "N", "PE"))
l1, l2, l3 = (q8[pin] for pin in ("L1", "L2", "L3"))
d.ac_supply("S", 400, l1, l2, l3, n=q8["N"])
motor = d.device("M1", "DEMO-MOTOR-4KW")
d.wire(x8[1].outer, motor["U"], wire=(BK, 1.5))
```

```python
# easy: function block
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
with d.function("RUN", "Pump run"):
    k1 = d.device("K1", "DEMO-CTR-3P-24")
    k2 = d.device("K2", "DEMO-CTR-3P-24")
    h1 = d.device("H1", "DEMO-LAMP-24")
    h2 = d.device("H2", "DEMO-LAMP-24")
    d.series(dc.plus, k1.aux, h1.lamp, dc.minus, wire=(BU, 0.75))
    d.series(dc.plus, k2.aux, h2.lamp, dc.minus, wire=(BU, 0.75))
```

```python
# efficient: function block
import fransys as fr
from fransys.colours import BU

LAMPS = {"H1": "K1", "H2": "K2"}  # lamp tag -> the contactor whose auxiliary contact lights it

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
with d.function("RUN", "Pump run"):
    for tag, contactor in LAMPS.items():
        k = d.device(contactor, "DEMO-CTR-3P-24")
        lamp = d.device(tag, "DEMO-LAMP-24")
        d.series(dc.plus, k.aux, lamp.lamp, dc.minus, wire=(BU, 0.75))
```

`getattr(dev, f"DI{n}")` is the one spelling for a computed name. A name the device lacks raises an
error that `hasattr` reads as absent, so `getattr(dev, "nope", None)` is `None`.

A device with one function and a marked pin is read the short way: `h1[1]`.

### A place inside a place

`d.location("BATT", text, within="HOLD")` puts the place `BATT` inside `HOLD`, named by its tag.
`HOLD` must exist already, or the call raises and lists the places. A device placed in `BATT`
prints `+HOLD+BATT`. Without `within=` a place sits at the root.

```python
import fransys as fr

d = fr.design("demo_parts")
d.location("HOLD", "Hold")
d.location("BATT", "Battery bay", within="HOLD")
d.device("Q1", "DEMO-MCB-C6", place="BATT")
```

### Read a function or pin

A device has functions, and a function has pins. Both are plain attributes and brackets.

```python
import fransys as fr

d = fr.design("demo_parts")
k1 = d.device("K1", "DEMO-RLY-2CO-24")
coil = k1.coil          # the function named `coil` in the part file
a1 = k1.coil["A1"]      # the pin marked A1 on that function
```

`Q1.coil` is a function by name, `Q1["A1"]` a pin by marking, and `Q1[2]` a pin by number. A name or
marking the part lacks raises and lists the choices. The vocabulary is the electrotechnical one: a
make contact closes when its coil is on, a break contact opens, a line conductor is `L1`, a neutral is
`N`.

## Typed or string part

The `part` argument is either a string or a generated class. A string MPN is the data path: it needs
no extra file and the part is checked when you build. A generated typed part is the checked path:
`python -m fransys parts-module demo_parts parts_demo.py` writes one class per part, so
`d.device("K1", P.DEMO_RLY_2CO_24)` makes an editor and a type checker reject an unknown function or
pin before the script runs.

```bash
uv run python -m fransys parts-module demo_parts parts_demo.py
```

A function named `24V+` is the attribute `dev.P_24V_plus`; `-` gives `_minus`. `getattr(dev, "24V+")`
reaches the raw name. Two names that map to one attribute fail generation.

Pass the module to `fr.design(P)`. A module whose library has since changed raises at
`fr.design` and tells you to regenerate it. Both spellings build the same model. The rest of this page
uses strings.

## Strips and terminals

`d.terminal_strip("X1", part, count, description=, pe=)` adds a terminal strip of `count` terminals,
and `X1[3]` takes terminal 3. `pe` names the protective-earth part, and a run labelled exactly `"PE"` (`X1.run("PE", 2)`) takes it; without `pe=` that run raises. A terminal has two sides: wiring
inside the unit reaches its inner side, a field cable its outer side. A wire or a series enters a
strip at the right side without you saying so.

With `count`, the strip makes all its terminals at once, so spares exist and count in the lists. A
terminal joins the function block where it is first taken, and a spare joins the strip's own group.
There is no `group=` keyword. `d.wire(x1[1], lamp[1], ...)` lands on the inner side. `x1[1].outer` is
the field side, and `W1.core(...)` lands there.
`interface=` and `unused=` on `d.terminal_strip` mark terminals a unit boundary: `True` marks every
terminal, and a tuple of numbers, `interface=(1, 2)`, only those; the others stay inside the unit. On
a run they take `True` only: `x1.run("24V", 4, bridged=True, interface=True)` (see `units.md`).

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
h1 = d.device("H1", "DEMO-LAMP-24")
with d.function("FEED", "Lamp feed"):
    d.wire(x1[1], h1[1], wire=(BU, 0.75))
d.wire(x1[2].outer, h1[2], wire=(BU, 0.75))
```

### Bridges

`X1.run(label, n, bridged=True)` takes `n` terminals as a named run, joined by jumpers when
`bridged=True`. A run's `bridged=` bridges a named run, and a strip's bridges plain terminals. Two terminals are a run of two.
Made inside a function block, a run puts all its terminals in that block. Made outside every block, it puts
none: each terminal joins the block it is first wired in.

`bridged=(first, last)` bridges terminals `first` to `last` only, one jumper between each
consecutive pair. A pair outside 1 to `n`, or with `first >= last`, raises and names the range.

A strip with a `count` bridges plain terminals with no run and no label:
`d.terminal_strip("X4", part, 6, bridged=(2, 6))` jumpers terminals 2 to 6, `bridged=((2, 3), (5, 6))`
makes two bridges, and `bridged=True` bridges them all. A bad range raises and names the fix.

`X1.run(label, bridged=True)` takes no size. The run grows as connections take its terminals, and
each new one is bridged to the one before. `feed[n]` names a terminal already taken; a higher `n`
raises. A strip or a run is also a pin of `d.wire` and a core's end: each place takes its next free
terminal, `d.wire` on the inner side and `W1.core` on the outer side.

```python
# a growing bridged run fed by d.series
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
for tag in ("H1", "H2", "H3"):
    d.series(dc.plus, feed, d.device(tag, "DEMO-LAMP-24").lamp, dc.minus, wire=(BU, 0.75))
```

## Wiring and cables

`d.wire` requires `wire=`: a colour code and a cross-section in mm2. `d.series` takes it in three shapes
(Wire colours).

### Wire along a current path

`d.series(a, b, c, wire=(BU, 0.75))` wires elements end to end: each one's load side to the next
one's line side, one wire per pole. A supply rail, a run, a device function, a cable and a strip
are all elements. A function is a series element when its part names its line side; else the
series raises and names it.

### Branch inside a series

`d.parallel(a, b)` is an element of a series: each member sits between the previous load and the next
line.

A branch across several elements is a second series, from the split to the join. Below, the second
series wires S1:NC to K3, K3 to K4 and K4 to the coil K2:A1 in WH 0.5.

```python
# easy: a branch across several elements
import fransys as fr
from fransys.colours import BU, WH

d = fr.design("demo_parts")
psu = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", psu.output)
s1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
s2 = d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
k2 = d.device("K2", "DEMO-CTR-3P-24")
k3 = d.device("K3", "DEMO-CTR-3P-24")
k4 = d.device("K4", "DEMO-CTR-3P-24")
d.series(dc.plus, s1.nc, s2.no, k2.coil, dc.minus, wire=(BU, 0.75))
d.series(s1.nc, k3.aux, k4.aux, k2.coil, wire=(WH, 0.5))
```

```python
# efficient: a branch across several elements
import fransys as fr
from fransys.colours import BU, WH

d = fr.design("demo_parts")
psu = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", psu.output)
s1, s2 = (d.device(tag, "DEMO-CTR-BLOCK-1NO1NC") for tag in ("S1", "S2"))
k2, k3, k4 = (d.device(tag, "DEMO-CTR-3P-24") for tag in ("K2", "K3", "K4"))
d.series(dc.plus, s1.nc, s2.no, k2.coil, dc.minus, wire=(BU, 0.75))
d.series(s1.nc, *(k.aux for k in (k3, k4)), k2.coil, wire=(WH, 0.5))
```

### A changeover in a series

`k1.co_1.no` and `k1.co_1.nc` are the two throws of a changeover, each a series element: line at the
common, load at the throw. The first series that reaches the common wires it once, for both series.
Passing the whole changeover raises: a changeover is two throws, so use `K1.co_1.no` or `K1.co_1.nc`.

```python
import fransys as fr

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
k1 = d.device("K1", "DEMO-RLY-2CO-24")
k2 = d.device("K2", "DEMO-CTR-3P-24")
k3 = d.device("K3", "DEMO-RLY-2CO-24")
d.series(dc.plus, k1.co_1.no, k2.coil, dc.minus, wire=0.75)
d.series(k1.co_1.nc, k3.coil, dc.minus, wire=0.75)
```

A selector part has its throws on the line side. The series enters it at its throws and draws it
turned.

The pair below feeds a coil from a supply through a bridged run.

```python
# easy: terminal strip and series
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
psu = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", psu.output)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
feed = x1.run("coil supply", 3, bridged=True)
k1 = d.device("K1", "DEMO-CTR-3P-24")
k2 = d.device("K2", "DEMO-CTR-3P-24")
d.series(dc.plus, feed, k1.coil, dc.minus, wire=(BU, 0.75))
d.series(dc.plus, feed, k2.coil, dc.minus, wire=(BU, 0.75))
```

```python
# efficient: terminal strip and series
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
psu = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", psu.output)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
feed = x1.run("coil supply", 3, bridged=True)


def feed_coil(tag: str) -> None:
    coil = d.device(tag, "DEMO-CTR-3P-24").coil
    d.series(dc.plus, feed, coil, dc.minus, wire=(BU, 0.75))


for tag in ("K1", "K2"):
    feed_coil(tag)
```

### Wire two named pins

`d.wire(a, b, wire=(BU, 0.75), label=, n=)` draws one wire; more than two pins draw a daisy chain.
Use it only off a path: two named pins such as a signal pair, one signal daisy-chained, or a hop
whose wire differs from the rest of its path. Anything that is a current path is a `d.series`.

### Cables

`d.cable("W1", part, length_m=)` adds a cable and `W1.core(BN, a, b)` wires one core between two pins,
named by its colour or its number. The core colours come from the cable part, not from you. A
green-yellow core goes to a protective-earth pin only. `parent=W5` puts the cable in a harness `W5`,
as `parent=` does on `d.device`.

```python
# easy: cable run
import fransys as fr
from fransys.colours import BK, BN, GY

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
h1 = d.device("H1", "DEMO-LAMP-24")
h2 = d.device("H2", "DEMO-LAMP-24")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
w1.core(BN, x1[1], h1[1])
w1.core(BK, x1[2], h1[2])
w1.core(GY, x1[3], h2[1])
```

```python
# efficient: cable run
import fransys as fr
from fransys.colours import BK, BN, GY

CORES = ((BN, 1, "H1", 1), (BK, 2, "H1", 2), (GY, 3, "H2", 1))  # colour, terminal, lamp, pin

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
lamps = {tag: d.device(tag, "DEMO-LAMP-24") for tag in ("H1", "H2")}
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
for colour, terminal, lamp, pin in CORES:
    w1.core(colour, x1[terminal], lamps[lamp][pin])
```

A core you leave unused is `w1.spare(GY)`, or `w1.spare()` for every core not wired so far. `at=x1[7]`
parks one on a pin. The cable drawing prints "spare" on its row, and the schematic draws nothing. A
screen (`SH`) earthed at one end takes one pin: `w2.core(5, pe[1])`. A part with `pairs` in its
`[cable_product]` table gets a bracket and a P1, P2 label over each pair's rows.

```python
import fransys as fr
from fransys.colours import GY

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
pe = d.terminal_strip("X2", "DEMO-TB-PE-2.5", 2)
h1 = d.device("H1", "DEMO-LAMP-24")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
w1.core(1, x1[1], h1[1])
w1.spare(GY, at=x1[7])
w1.spare()
w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP", length_m=25)
w2.core(1, x1[2], h1[2])
w2.core(5, pe[1])
w2.spare()
```

`fn.pins` gives a function's pins as a tuple, in the order the connector list prints (`1, 2, 10, A1`),
never the part file's. To land a cable's cores on two connectors pin by pin, loop over it. The
pairing rule stays yours.

```python
import fransys as fr

d = fr.design("demo_parts")
a = d.device("J1", "DEMO-CONN-4P")
b = d.device("J2", "DEMO-CONN-4P")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
for core, (pin_a, pin_b) in enumerate(zip(a.x1.pins, b.x1.pins, strict=True), start=1):
    w1.core(core, pin_a, pin_b)
```

## Wire colours

A colour is an IEC 60757 code imported from `fransys.colours`: `BK`, `BN`, `RD`, `OG`, `YE`, `GN`,
`BU`, `VT`, `GY`, `WH`, `PK`, `GD`, `SR`, `TQ`, and the two-colour `GNYE`. Write `wire=(BU, 0.75)` for
a blue 0.75 mm2 wire.

A wire spec shared by many wires is a module constant: `CTRL = (BU, 0.75)`, with `BU` imported. Pass it
as `wire=CTRL` to `d.wire`, and to `d.series` for a whole path. `wire=` stays required on `d.wire` only.

```python
import fransys as fr
from fransys.colours import BU

CTRL = (BU, 0.75)  # the control wire spec, written once

d = fr.design("demo_parts")
psu = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", psu.output)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
feed = x1.run("coil supply", 3, bridged=True)
k1 = d.device("K1", "DEMO-CTR-3P-24")
k2 = d.device("K2", "DEMO-CTR-3P-24")
d.series(dc.plus, feed, k1.coil, dc.minus, wire=CTRL)
d.series(dc.plus, feed, k2.coil, dc.minus, wire=CTRL)
```

### Colour by what a wire carries

A design has eight wire rows: `fr.DC_SUPPLY`, `fr.DC_GROUND`, `fr.DC_CONTROL`, `fr.AC_L1`, `fr.AC_L2`,
`fr.AC_L3`, `fr.AC_N` and `fr.AC_CONTROL`. A row's value is a colour, or a colour and a size.
`d.series` picks each wire's row from what it carries, so you write the colours once.

`fr.design(library, wiring={row: value})` sets rows for the design. `@fr.unit(..., wiring={row: value})`
sets rows for that unit's body. A unit never inherits its parent's rows. With no `wiring=` it draws
the IEC 60204-1 default: AC phases `BK`, `AC_N` `BU`, `AC_CONTROL` `RD`, every DC row `BU`, no sizes.

`d.series(..., wire=)` takes three shapes:

- a size, `wire=0.75`: every wire takes its row's colour at that size.
- a table, `wire={fr.DC_CONTROL: (WH, 0.75)}`: replaces only those rows for this series.
- a spec, `wire=(BU, 0.75)`: every wire gets that colour and size, and the rows are ignored.

A wire whose row has no size, with no size on the series, raises. Name the size in either place.

A series that starts on one rail (`dc.plus`, `ac.L1`) is a control path. A wire at the rail's
potential takes the rail's row. A fuse or a contact ends that potential, so the wires after it take
`DC_CONTROL` or `AC_CONTROL`. A series that starts on a whole supply (`dc`, `ac`) is a power path:
each pole keeps its conductor's row through every element. On a supply with `n=`, the first
element with poles decides: as many as the phases leaves N unwired, one more takes N. A series that
starts on no rail takes the rows the earlier series gave the net it starts on.

```python
import fransys as fr
from fransys.colours import BK, RD, WH

d = fr.design("demo_parts", wiring={
    fr.DC_SUPPLY: RD, fr.DC_CONTROL: WH, fr.DC_GROUND: BK,
})
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
s1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
k1 = d.device("K1", "DEMO-CTR-3P-24")
d.series(dc.plus, s1.no, k1.coil, dc.minus, wire=0.75)  # RD, WH, BK, each 0.75 mm2
```

## Earth pins

`d.earth(*pins)` declares the `PE` net; a wire to the PE terminal builds it. Every pin joined by
`d.earth` draws the PE symbol, wired or not. A wire to a PE terminal adds its list row.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
pe = x1.run("PE", 2, bridged=True)
m1 = d.device("M1", "DEMO-MOTOR-4KW")
d.wire(m1.motor["PE"], pe[1], wire=(GNYE, 2.5))
d.earth(m1.motor["PE"], pe[1])
```

A PE bar takes its landings. Pass the bar's function where a pin goes: it takes its next free screw
and joins it to the PE net. A bar with every screw taken raises. A bar cut to length from stock writes
no port, so each landing makes a screw. The bar is never drawn, and each end on it draws the PE symbol.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
pe1 = d.device("PE1", "DEMO-PEBAR-20")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP")
d.wire(m1.motor["PE"], pe1.pe, wire=(GNYE, 2.5))  # screw 1
w2.core(5, pe1.pe)  # the one-ended screen, screw 2
```

## A named signal net

`d.net(name, *pins, kind=)` names a net of pins that no wire joins, such as a bus shown by its label.
`kind` is `fr.CONTROL` (the default), `fr.SIGNAL` or `fr.GENERIC`. A `PE` or supply net has its own call.

## A busbar, a rail bond

`d.busbar(a, b)` joins two pins by a rack's internal power jumper. `d.rail_bond(a, b)` joins two
terminals bonded through their mounting rail. Neither has a wire-list row, colour or gauge, and
both close the net like a conductor.

## AC or DC supply and rails

`d.dc_supply(name, source)` declares a DC supply from the L+ and L- pins of a device and its nominal
voltage; its rails are `dc.plus` and `dc.minus`, and a series starts or ends on them. With no source
device, such as a 24 V feed on terminals, give the pins:
`d.dc_supply("24VDC", plus=X1[1], minus=X1[2], voltage=24)`. Then `voltage=` is required. A
source whose part states a nominal voltage takes no `voltage=`; one without it needs `voltage=`. `mid=` adds a middle conductor, as on a plus and
minus 15 V supply.

Without `mid`, `minus` is 0 V and `plus` carries the voltage. With `mid`, `mid` is 0 V, `plus` is
plus the voltage and `minus` is minus the voltage. `names=(plus, minus, mid)` renames the potentials. `ac_supply` takes `names=` too: one name per phase pin in order, then one for `n`. A second three-phase supply beside L1, L2, L3 takes, say, `names=("EL1", "EL2", "EL3")`. The rails stay `ac.L1`, `ac.L2`, `ac.L3` and `ac.N`, and phases and wire colours do not change.

`earthing=fr.IT` declares a floating supply on `ac_supply` or `dc_supply`; the default is `fr.EARTHED`.
Two 0 V rails are two supplies.

`ac_supply` and `dc_supply` take `fault_current_a=`, the supply's prospective fault current in amps. `dc_supply` also takes
`fault_time_constant_ms=`. A supply that states a fault current is a source for the breaking-capacity check (`reading.md`). A
`dc_supply` declared from a `source` device refuses both, since that part states its own fault data.

A nested unit's declaration of a supply name its container also declares is not a source. The container's declaration counts.

`d.ac_supply(name, voltage, *phases, n=None, names=None)` declares an AC supply on one or three phase pins in
phase order. Its rails are `ac.L1`, plus `ac.L2` and `ac.L3` for three phases. On three phases `voltage` is each phase's RMS to the star point: 230 for a 400 V supply. A 230 V line-to-line IT supply is declared 132.79. A pin's side and order
on a rail come from the supply you declare, never from the rail's name. A rail draws its power symbol
only when declared. A fused branch or a second source of one voltage is not a supply: make it a strip
with a `description`, or wire it point to point.

```python
import fransys as fr

d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
mains = d.ac_supply("230V", 230, x0[1], n=x0[2])
dc = d.dc_supply("24VDC", plus=x1[1], minus=x1[2], voltage=24)
```

## Plug a connector

`d.mate(a, b)` plugs connector `a` into connector `b`. Each is a device with exactly one function
(see `units.md` for a mate across a unit boundary).

## Add a harness

`d.harness("W5")` adds a harness item: see `harnesses.md`.

## Read a model id

`Q1.id` and `Q1.coil.id` give the model id of a device and a function. Read them after the build, as
`fr.derive.item_designation(result.model, Q1.id)` does. Ids exist for reading only, never to wire.

```python
import fransys as fr

d = fr.design("demo_parts")
h1 = d.device("H1", "DEMO-LAMP-24")
result = fr.build(d)
assert fr.derive.item_designation(result.model, h1.id) == "H1"
```

## Request a PLC channel

`K1.coil.plc(fr.DO, "Pump run")` asks for a digital output named for the signal, and
`.scale("bar", raw=(0, 100), eng=("0", "10"))` scales an analogue one. The allocation pass binds the
request to a channel later; you never pick the channel.
`d.rack("U1")` adds the part-less rack the modules sit under with `parent=`; a `d.harness` rack stops with `HARNESS_HOLDS_PLC_MODULE`.

## Title block, revision

`d.project(title=, number=, customer=, ...)` fills the title block and `d.revision(1, date=, text=)`
adds a history line. Both are optional and appear on the drawings and in the reports.

## Point a finding past a helper

A finding names the file and line of the call that authored the thing. A helper that builds a repeated
circuit would make every finding name the helper's own line. Set `__tracebackhide__ = True` in the helper,
as a local or as a module global, and the finding names the line that called the helper instead. It is
pytest's own convention.

```python
import fransys as fr


def lamp_pair(d, first, second):
    __tracebackhide__ = True
    return d.device(first, "DEMO-LAMP-24"), d.device(second, "DEMO-LAMP-24")


d = fr.design("demo_parts")
h1, h2 = lamp_pair(d, "H1", "H2")
```

## An accessory in its holder

A part with no function, put in another device with `parent=`, is an accessory of it. A fuse link in its
PCB fuse holder is one: the holder carries the pads and the footprint, and the link carries the rated current.

```python
import fransys as fr

d = fr.design("demo_parts")
f1 = d.device("F1", "DEMO-FUSE-HOLDER-PCB")
link = d.device(None, "DEMO-FUSE-LINK-4A-T", name="link", parent=f1)
model = fr.build(d).model
assert fr.derive.item_designation(model, link.id) == fr.derive.item_designation(model, f1.id)
```

The link prints `F1` and has no number or row of its own. An authored tag makes it an ordinary item. The
holder's protection function then bounds its branch at the link's rated current. The part page shows the
link's `[rating]`, and `reading.md` shows the branch check ("Checking a branch's current").

`parent=` also takes a terminal strip. A jumper bar on a bridged run is an accessory of its strip: it prints
the strip's designation and the BOM counts it. `parent=` refuses a run or a terminal and names its strip.
You state the bar yourself; the bridge adds none.

```python
import fransys as fr

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
run = x1.run("L", 3, bridged=True)
bar = d.device(None, "DEMO-JUMPER-BAR-3P", name="bar", parent=x1)
model = fr.build(d).model
assert fr.derive.item_designation(model, bar.id) == "X1"
```

## Reading a part's rating

`d.rating(part, function)` and `d.operating(part, function)` read a part's or a function's rating or
operating envelope from the catalogue. It is a lookup, not a build step. Either gives `None` where
the part file states nothing.

```python
import fransys as fr

d = fr.design("demo_parts")
part_rating = d.rating("DEMO-TBLK-2P-DUAL")
terminal_rating = d.rating("DEMO-TBLK-2P-DUAL", "terminal")
lamp_operating = d.operating("DEMO-LAMP-24", "lamp")
```

## Layout profile

`d.layout` advises the drawing and connects nothing: `chain`, `keep_together`, `break_before`,
`order`, `symbol`, `draw_in`, `side`, `sheet`, `page_title` and `profile`. `d.layout.side(u1.bus_in, fr.ABOVE)` puts a
unit's interface above its outline, and `fr.BELOW` below it. It takes a field of the `d.add` tuple.
An interface with no harness line ignores it. `d.layout.page_title(x1, "Field terminals")` names the pages drawing a block, function or device. `d.layout.profile(hide_unused_pins=True)` hides
every box-drawn pin with no conductor, and a function with none, on drawings. Every list keeps
all pins. The house value is off. `min_text_height_mm` is the floor ([Drawing well](drawing.md)).
The design's profile governs only its pages. A unit sets its own in its body; with none it
uses the house values, never its parent's.

`d.layout.chain(r1.lamp, k3.main, f3.element, beside=k1.main)` draws the chain beside the element `k1.main`, joined by short unmarked horizontals. Wire first: the chain joins the element by each end net they share, one or two, else `AuthorError` names them. A one-pin box (a PLC channel) may end a chain and joins nothing.

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
