# Authoring a design

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page teaches how to write a design with `fr.design`: places, function blocks, devices, terminal
strips, wires, cables, supplies, PLC requests and layout advice. Each task has one spelling, shown
first written out and then with Python around it.

A `Design` is one object with no global state. Every call returns a handle, never a string, and later calls take it. A design is a draft: `fr.build(d)` freezes it (see `build.md`).

## Easy and efficient

Each task is shown twice and builds the same model both times. The easy level writes the circuit out,
one device and one wire per line. The efficient level uses the same calls with Python around them: a
loop over a table, a function for a circuit that repeats. Both use the same calls.

The pairs below are: a function block with devices, and a terminal strip with a series. The branched series pair is on `series.md`.
The sections after them list the one-call tasks.

## Name a place and a function block

A place is where units and field devices stand: a room, a site, a ship's hold. `d.location("HOLD", text)`
names it, and `place="HOLD"` on `d.device` or `fr.design` puts devices there. A cabinet is not a place.
It is a unit that holds components, units and wires (see `units.md`). A function block is one circuit,
such as one pump's or one string's: `with d.function("LAMPS", text):` puts every device made inside it
in that block, and a circuit is never a place. Tags are bare: `"HOLD"`, never `"+HOLD"`, and a prefixed
tag raises.

What `place=` changes, on every call that takes it.

| value | effect |
|---|---|
| `...` (the default) | The item takes the design's place, the one `fr.design(place=)` named. With none named, it has no place. |
| `"HOLD"` | The item stands in that place. Its designation gains the prefix `+HOLD`, or `+HOLD+BATT` in a nested place. The place must exist. |
| `None` | The item has no place, even when the design names one. |

A place sorts the lists by place and sets the `+` part of the printed designation. It does not move a cell on a drawing: `d.layout.draw_in` does.

`d.device(tag, part, place=, parent=, mounted_on=, joins=, interface=, unused=, name=)` adds one device.
`joins={1: K1.coil["A1"]}` with `parent=K1` fits a housing on K1's own leads: pin 1 is that pin, no wire.
A contact block with `parent=` an operator head prints the head's tag, as `-S1:11` (guide `parts.md`).
`part` is a manufacturer part number such as `"DEMO-LAMP-24"`.

Floating tags: every item call takes `None` for the tag and numbers the item from its class code.
Pass `name=`, the identity a released number holds to; a floating call with no `name=` raises.
An accessory takes its holder's designation, no number of its own.

`external=True` marks an item supplied by others. Every call that makes an item takes it: `d.device`,
`d.terminal_strip`, `d.cable` and `d.harness`. The item has no BOM line. A strip's terminals are external
with it; a cable's conductors carry no flag. Every drawing marks it: dashed boxes with "(by others)", dashed outlines round schematic symbols.

An external device or strip may take `None` for its part, when only its terminal names are known. It needs a tag. A part-less device names its pins with `pins=`. A part-less strip offers only `.outer`: see `detail.md`, "Equipment others supply".

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
error that `hasattr` reads as absent.

A device with one function and a marked pin is read the short way: `h1[1]`.

### A place inside a place

`d.location("BATT", text, within="HOLD")` puts the place `BATT` inside `HOLD`, named by its tag.
`HOLD` must exist already, or the call raises and lists the places. A device placed in `BATT`
prints `+HOLD+BATT`. Without `within=` a place sits at the root.

### Read a function or pin

A device has functions, and a function has pins. Both are plain attributes and brackets.

`Q1.coil` is a function by name, `Q1["A1"]` a pin by marking, and `Q1[2]` a pin by number. A name or
marking the part lacks raises and lists the choices. The vocabulary is the electrotechnical one: a
make contact closes when its coil is on, a break contact opens, a line conductor is `L1`.

A printed marking that is not a Python name has two spellings. `dev["XLA+"]` reaches any pin by its
printed marking. `dev.XLA_plus` reaches a function or a pin named `XLA+`: `+` gives `_plus`, `-` gives `_minus`,
any other non-word character `_`, and a leading digit gets `P_`, so `24V+` is `P_24V_plus` and the pin `1/L1`
is `P_1_L1`. `getattr(dev, "24V+")` reaches the raw name.

## Strips and terminals

`d.terminal_strip("X1", part, count, description=, pe=)` adds a terminal strip of `count` terminals,
and `X1[3]` takes terminal 3. `pe` names the protective-earth part, and a run labelled exactly `"PE"` (`X1.run("PE", 2)`) takes it; without `pe=` that run raises. A terminal has two sides: wiring
inside the unit reaches its inner side, a field cable its outer side. A wire or a series enters a
strip at the right side without you saying so.
A series that starts on a strip and goes on to a function leaves the strip on its inner side.
One that goes on to a cable leaves it on the outer side.

With `count`, the strip makes all its terminals at once, so spares exist and count in the lists. A
terminal joins the function block where it is first taken, and a spare joins the strip's own group.
There is no `group=` keyword. A series picks the side itself. `x1[1].outer` is
the field side, and `W1.core(...)` lands there. `d.series(x1[3].outer, f1.element)` pins the side.
A series of only fixed terminals takes its width from the first; one terminal is one pole.
A tuple takes one-terminal runs, `(x4.l1[1], x4.l2[1])`, and the colours of the net an earlier series made.
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
    d.series(x1, h1.lamp, x1, wire=(BU, 0.75))
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
raises. A strip or a run is also a core's end: each place takes its next free terminal, a series on the
inner side and `W1.core` on the outer side.

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

The series, branches, changeovers, cables, wire colours and earth pins are on `series.md`.

## AC or DC supply and rails

`d.dc_supply(name, source)` declares a DC supply from the L+ and L- pins of a device; its rails are
`dc.plus` and `dc.minus`, and a series starts or ends on them. With no source device, such as a 24 V
feed on terminals, give the pins and `voltage=`: `d.dc_supply("24VDC", plus=X1[1], minus=X1[2], voltage=24)`.
A source whose part states a nominal voltage takes no `voltage=`. `mid=` adds a middle conductor, as
on a plus and minus 15 V supply.

Without `mid`, `minus` is 0 V and `plus` carries the voltage. With `mid`, `mid` is 0 V, `plus` is
plus the voltage and `minus` is minus the voltage. `names=(plus, minus, mid)` renames the potentials; `ac_supply` takes one name per phase pin, then one for `n`.

`earthing=fr.IT` declares a floating supply; the default is `fr.EARTHED`. Two 0 V rails are two supplies.

`fault_current_a=` is the supply's prospective fault current in amps; `dc_supply` also takes
`fault_time_constant_ms=`. A supply that states one is a source for the breaking-capacity check
(`reading.md`). A `dc_supply` declared from a `source` device refuses both.

A nested unit's declaration of a supply name its container also declares is not a source.

`d.ac_supply(name, voltage, *phases, n=None, names=None)` declares an AC supply on one or three phase pins in
phase order. Its rails are `ac.L1`, plus `ac.L2` and `ac.L3` for three phases. On three phases `voltage` is each phase's RMS to the star point: 230 for a 400 V supply. A pin's side and order
on a rail come from the supply you declare. A rail draws its power symbol only when declared. A fused
branch or a second source of one voltage is not a supply: make it a strip with a `description`, or
wire it point to point. `ac_supply` on a fuse's pins raises "a fused branch is not a supply".
A branch from the common feed is a second series; one looped at the line screws starts at its line pins (`index.md`).

```python
import fransys as fr

d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
mains = d.ac_supply("230V", 230, x0[1], n=x0[2])
dc = d.dc_supply("24VDC", plus=x1[1], minus=x1[2], voltage=24)
```

## Plug a connector

`d.mate(a, b)` plugs connector `a` into connector `b`, each a device with one function
(`units.md` covers a mate across a unit boundary).

## Add a harness

`d.harness("W5")` adds a harness item: see `harnesses.md`.


## Request a PLC channel

`K1.coil.plc(fr.DO, "Pump run")` asks for a digital output named for the signal, and
`.scale("bar", raw=(0, 100), eng=("0", "10"))` scales an analogue one. A series that ends or starts
at a PLC module binds the request to a channel (next section). A request no series wires keeps the
build's own allocation.
`d.rack("U1")` adds the part-less rack the modules sit under with `parent=`; a `d.harness` rack stops with `HARNESS_HOLDS_PLC_MODULE`.

## How channels are numbered

A PLC module passed whole to `d.series` takes its lowest-numbered free channel, as a strip takes
its next free terminal.

| rule | what happens |
|---|---|
| Order | A call takes the lowest free channel when it runs. Calls take channels in the order they run. |
| Direction | A module that ends a path gives an input. A module that starts a path gives an output. A module in the middle of a path raises. |
| Kind | The request on a function of the path, `s1.no.plc(fr.DI, name)`, names the kind. With no request, the module's only kind for that direction. Two kinds and no request raises, naming both kinds and the request that settles it. |
| Fixed | `a1.di_7` is a fixed channel, for one that an existing PLC program or IO list fixes. A fixed channel is taken, and the lowest-free rule skips it. |

Sixteen sensors from a table in IO-list order get channels 1 to 16:

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
a1 = d.device("A1", "DEMO-PLC-DI-16")
io_list = [f"Sensor {n}" for n in range(1, 17)]  # the IO list, in channel order
for number, name in enumerate(io_list, start=1):
    sensor = d.device(f"S{number}", "DEMO-PB-NC")
    sensor.sw.plc(fr.DI, name)
    d.series(dc.plus, sensor.sw, a1, wire=(BU, 0.75))  # S1 takes -A1:1, S2 takes -A1:2, ...
```

To reproduce an existing channel map, write the paths in channel order. Use the fixed form for a
channel that call order cannot reach, such as one after a gap. A program that reads channel 5 after
channel 1 needs `a1.di_5` for the second path. The paths after it continue from channel 2.

```python
d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
a1 = d.device("A1", "DEMO-PLC-DI-16")
start, reset, stop = (d.device(tag, "DEMO-PB-NC") for tag in ("S1", "S2", "S3"))
d.series(dc.plus, start.sw, a1, wire=(BU, 0.75))      # channel 1
d.series(dc.plus, reset.sw, a1.di_5, wire=(BU, 0.75))  # fixed: channel 5, after a gap
d.series(dc.plus, stop.sw, a1, wire=(BU, 0.75))       # channel 2: the lowest free one
```

## Title block, revision

`d.project(title=, number=, customer=, ...)` fills the title block and `d.revision(1, date=, text=)`
adds a history line. Both are optional.


