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

`d.device(tag, part, place=, parent=, mounted_on=, interface=, unused=, name=)` adds one device.
`part` is a manufacturer part number such as `"DEMO-LAMP-24"`.

Floating tags: every item call takes `None` for the tag, `d.add` too, and numbers the item from
its class code. The letter comes from the part file's `class_code`, or from the release's for a unit.
Pass `name=`, the identity a released number holds to. A floating call with no `name=` raises.
An accessory takes its holder's designation and uses up no number.

`external=True` marks an item supplied by others. Every call that makes an item takes it: `d.device`,
`d.terminal_strip`, `d.cable` and `d.harness`. The item has no BOM line. A strip's terminals are external
with it; a cable's conductors carry no flag.

```python
# easy: function block
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
with d.function("RUN", "Pump run"):
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    h1 = d.device("H1", "DEMO-LAMP-24")
    h2 = d.device("H2", "DEMO-LAMP-24")
    d.wire(k1.co_1["14"], h1[1], wire=(BU, 0.75))
    d.wire(k1.co_2["24"], h2[1], wire=(BU, 0.75))
```

```python
# efficient: function block
import fransys as fr
from fransys.colours import BU

LAMPS = {"H1": ("co_1", "14"), "H2": ("co_2", "24")}  # lamp tag -> the relay contact that lights it

d = fr.design("demo_parts")
with d.function("RUN", "Pump run"):
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    for tag, (function, pin) in LAMPS.items():
        lamp = d.device(tag, "DEMO-LAMP-24")
        d.wire(getattr(k1, function)[pin], lamp[1], wire=(BU, 0.75))
```

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
`interface=True` and `unused=True` on `d.terminal_strip` mark every terminal a unit boundary, as on
`d.device` (see `units.md`).

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
`bridged=True`. A run is the one spelling for a bridge. Two terminals are a run of two.

`bridged=(first, last)` bridges terminals `first` to `last` only, one jumper between each
consecutive pair. A pair outside 1 to `n`, or with `first >= last`, raises and names the range.

`X1.run(label, bridged=True)` takes no size. The run grows as connections take its terminals, and
each new one is bridged to the one before. `feed[n]` names a terminal already taken; a higher `n`
raises. A strip or a run is also a pin of `d.wire` and a core's end: each place takes its next free
terminal, `d.wire` on the inner side and `W1.core` on the outer side.

```python
# a growing bridged run fed by d.wire
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
for tag in ("H1", "H2", "H3"):
    d.wire(feed, d.device(tag, "DEMO-LAMP-24")["1"], wire=(BU, 0.75))
```

## Wiring and cables

`d.wire(a, b, wire=(BU, 0.75), label=, n=)` draws one wire; more than two pins draw a daisy chain.
`wire=` is required: a colour code and a cross-section in mm2.

### Wire along a current path

`d.series(a, b, c, wire=(BU, 0.75))` wires elements end to end: each one's load side to the next
one's line side, one wire per pole. A supply rail, a run, a device function, a cable and a strip
are all elements.

### Branch inside a series

`d.parallel(a, b)` is an element of a series: each member sits between the previous load and the next
line.

The pair below feeds a coil from a supply through a bridged run. A series element needs poles, so a
single-pin lamp is wired with `d.wire` instead.

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

## Earth pins

`d.earth(*pins)` joins the pins to protective earth as one `PE` net.

```python
import fransys as fr

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, pe="DEMO-TB-PE-2.5")
d.earth(x1[1], x1[2])
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

`d.harness("W5")` adds a part-less harness item and returns its handle, which a document can take
as its subject (see `documents.md`). A harness holding a cable needs a tag: `d.harness(name="loom")`
with no tag builds, then fails with `HARNESS_WITHOUT_TAG`. A part-less harness holding exactly one
cable prints that cable as its own designation (`-W5`, its cores `-W5:1`); its plugs stay `-W5-J1`.
With two cables they print `-W5-W1` and `-W5-W2`.
A harness with one cable prints the cable with the harness's designation. The cable's own tag is not printed.

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

## Title block, revision

`d.project(title=, number=, customer=, ...)` fills the title block and `d.revision(1, date=, text=)`
adds a history line. Both are optional and appear on the drawings and in the reports.

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

`d.layout` advises the drawing and never connects anything: `chain`, `keep_together`, `break_before`,
`order`, `symbol`, `draw_in`, `sheet` and `profile`. `d.layout.profile(hide_unused_pins=True)` hides
every box-drawn pin with no conductor, and a function with none, on the drawings. Every list keeps
every pin. The house value is off.

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
