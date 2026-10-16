# Wiring a design

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page teaches how to wire a design: `d.series` along a current path, branches and changeovers, cables, wire colours and earth pins. It follows `authoring.md`, which holds the places, devices and strips these calls join.

## Wiring and cables

`d.series` takes `wire=` in four shapes (Wire colours): a colour code and a cross-section in mm2,
a size, a table of rows, or a tuple of `(colour, mm2)`, one per pole.

### Wire along a current path

`d.series(a, b, c, wire=(BU, 0.75))` wires elements end to end: each one's load side to the next
one's line side, one wire per pole. A supply rail, a run, a device function, a cable and a strip
are all elements. A function is a series element when its part names its line side; else the
series raises and names it. A part-less external device may end a series: its pins meet the poles in
declared order; anywhere else it raises.

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
Between two fixed terminals a throw is entered and the common leaves: `d.series(x6[2], k1.co_1.no, x7[2])`.
After a supply the common is wired to the supply's poles.

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

### Contacts that switch together

`d.poles(k1.co_1, k1.co_2, k1.co_3)` groups one-pole contacts of one device, in pole order, as one
element. It draws as one multi-pole symbol, and each contact keeps its place in the coil's table.
A changeover group gives `.no` and `.nc`. `selector=True` turns its throws to the line, here
selecting supply A or B for M1:

```python
d = fr.design("demo_parts")
xa, xb = d.terminal_strip("XA", "DEMO-TB-2.5"), d.terminal_strip("XB", "DEMO-TB-2.5")
a = d.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
b = d.ac_supply("B", "230", xb[1], xb[2], xb[3], names=("B_L1", "B_L2", "B_L3"))
qa, qb = d.device("QA", "DEMO-MCB-3P"), d.device("QB", "DEMO-MCB-3P")
k1, m1 = d.device("K1", "DEMO-RLY-4CO-24"), d.device("M1", "DEMO-MOTOR-4KW")
q = d.poles(k1.co_1, k1.co_2, k1.co_3, selector=True)
d.series(a, qa.element, q.no, m1, wire=2.5)
d.series(b, qb.element, q.nc, wire=2.5)
```

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

### How a series pairs

A series wires each element's load poles to the next element's line poles. The rule:

- Poles pair by conductor mark (`L1`, `L2`, `L3`, `N`) when every end has one, else in order.
- A function is an element when its part names its line side (`side = "line"`, `parts.md`).
- A strip or a cable takes the next free terminal or core, on the side the path enters.
- A path from a supply with `n=` joins N only where an element has a pole for it. A path of three poles
  from a three-phase supply leaves N unwired.
- Connectors pair their pins in pin order when they are a series' two ends.
- A tuple of one device's pins, `(s1.x1[1], s1.x1[4])`, is an element, first or last only; the written order is the pole order. `Fn.pins` lists them. A one-pole function and a pin make a two-wide end the same way: `(q1.pole_1, n1.N)`. A terminal slice has `.outer` and `.inner` as one terminal has: `x1[1:4].outer`.

A refusal starts with one of these texts. Each has one fix.

| refusal starts | fix |
|---|---|
| `<fn> has no line/load pole pair` | a bare function end never pairs its pins by position: pass `<fn>.pins` (or a slice), or `d.detail.wire` |
| `<device> has no function of N poles` | pass the function, such as `K1.main`, not the device |
| `<device>: a and b both have poles, say which` | pass the function you mean |
| `N poles into M: name the pins` | pass elements with equal pole counts |
| `conductors L1, L2 into L1, L3: name the pins` | pass elements whose conductor marks agree |
| `<element> has N poles; a path from S takes` | pass the supply's phases, or the phases and N |
| `row <row> value <n> is a bare number, a size` | give the colour and the size as a tuple, such as `("BK", 1.5)` |
| `a pin or a tuple of pins stands only` | put it first or last; else `d.detail.wire` |
| `a changeover is two throws` | pass `K1.co_1.no` or `K1.co_1.nc` |
| `a cable sits between two elements that are not cables` | put a plain element on each side of the cable |
| `<run a> and <run b> both take poles`, `<run> takes poles` | a bridged run in a series, alone or in a parallel, shorts its poles: give each pole its own sized run and take `(x1.run("L1", n, bridged=True)[1], ...)` as a tuple, one terminal per pole |

### Cables

`d.cable("W1", part, length_m=)` adds a cable. Pass it to a series between two elements: each
path takes the next free core, coloured by the cable part, and needs no `wire=`.
`parent=W5` puts the cable in harness `W5`, as on `d.device`.

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
d.series(dc.plus, x1, w1, d.device("H1", "DEMO-LAMP-24").lamp, dc.minus, wire=(BU, 0.75))
```

A core with a fixed colour or number is `W1.core(BN, a, b)`: see `detail.md`.
Use `d.pair(x8[1:3], w1, b1.sig)` rather than `d.series` when the ends state no line or load side: core `i` joins pin `i` to pin `i`.

## Wire colours

A colour is an IEC 60757 code imported from `fransys.colours`: `BK`, `BN`, `RD`, `OG`, `YE`, `GN`,
`BU`, `VT`, `GY`, `WH`, `PK`, `GD`, `SR`, `TQ`, and the two-colour `GNYE`. Write `wire=(BU, 0.75)` for
a blue 0.75 mm2 wire.

### Colour by what a wire carries

A design has nine wire rows: `fr.DC_SUPPLY`, `fr.DC_GROUND`, `fr.DC_CONTROL`, `fr.DC_SIGNAL`, `fr.AC_L1`, `fr.AC_L2`,
`fr.AC_L3`, `fr.AC_N` and `fr.AC_CONTROL`. A row's value is a colour, or a colour and a size.
`d.series` picks each wire's row from what it carries.

`fr.design(library, wiring={row: value})` sets rows for the design. `@fr.unit(..., wiring={row: value})`
sets rows for that unit's body. A unit never inherits its parent's rows. With no `wiring=` it draws
the IEC 60204-1 default: AC phases `BK`, `AC_N` `BU`, `AC_CONTROL` `RD`, every DC row `BU`, no sizes.

`d.series(..., wire=)` takes three shapes:

- a size, `wire=0.75`: every wire takes its row's colour at that size.
- a table, `wire={fr.DC_CONTROL: (WH, 0.75)}`: replaces only those rows for this series.
- a spec, `wire=(BU, 0.75)`: every wire gets that colour and size, and the rows are ignored.

A wire whose row has no size and no size on the series is `WIRE_ROW_UNRESOLVED`.

A series that starts on one rail (`dc.plus`, `ac.L1`) is a control path. A wire at the rail's
potential takes the rail's row. A fuse or a contact ends that potential: the wires after it take
`DC_CONTROL` or `AC_CONTROL`. A series that starts on a whole supply (`dc`, `ac`) is a power path:
each pole keeps its conductor's row through every element. On a supply with `n=`, the first
element with poles decides: as many as the phases leaves N unwired, one more takes N. A series that
starts on no rail takes the rows the earlier series gave its net.

A wire with no row when written is resolved at build end (`d.detail` page, "A wire with no row").

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

`d.earth(*pins)` declares the `PE` net; a wire to the PE terminal builds it. A unit has one `PE` net: each further `d.earth` call in it adds its pins to that net.
Call d.earth before draft(); a later call raises.
Every pin joined by `d.earth` draws the PE symbol, wired or not. A wire to a PE terminal adds its list row. A series through a cable lands its GNYE core on the load's PE port and the strip's next free PE terminal, else open and earthed. With no PE end and more poles than non-earth cores, the series raises an error.
It names the cable and both counts; pick a cable with that many non-earth cores. A load with no PE port leaves the far end open, the near end on the strip's PE terminal. A single wire to a PE terminal is `d.detail.wire`: see `detail.md`.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
pe = x1.run("PE", 2, bridged=True)
m1 = d.device("M1", "DEMO-MOTOR-4KW")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=3)
w1.core(GNYE, m1.motor["PE"], pe[1])
d.earth(m1.motor["PE"], pe[1])
```

A PE bar takes its landings. Pass the bar's function where a pin goes: it takes its next free screw
and joins it to the PE net. A bar with every screw taken raises. A bar cut to length from stock writes
no port, so each landing makes a screw. The bar is never drawn; each end on it draws the PE symbol.
A cable core lands on a screw as on any pin; a single wire is `d.detail.wire`: see `detail.md`.

```python
import fransys as fr
from fransys.colours import GNYE

d = fr.design("demo_parts")
pe1 = d.device("PE1", "DEMO-PEBAR-20")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=3)
w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP")
w1.core(GNYE, m1.motor["PE"], pe1.pe)  # screw 1
w2.core(5, pe1.pe)  # the one-ended screen, screw 2
```

