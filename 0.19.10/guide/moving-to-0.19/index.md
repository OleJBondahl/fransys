# Moving to 0.19

This page lists each call that 0.19 moves or changes, with the old spelling and the new one.
A consumer script that used an old spelling changes as below.

## The detail calls

Four calls moved to `d.detail`, with their keywords unchanged. The old names raise an `AuthorError`
that names the new home. There is no alias: one task has one spelling.

| old | new | why |
|---|---|---|
| `d.wire(a, b, wire=...)` | `d.detail.wire(a, b, wire=...)` | A path is `d.series`. A hand-wired hop is for a case no series writes (detail.md). |
| `d.net(name, *pins, kind=)` | `d.detail.net(name, *pins, kind=)` | A named net that no wire joins is a detail case. |
| `d.busbar(a, b)` | `d.detail.busbar(a, b)` | A busbar joins two fixed pins, a detail case. |
| `d.rail_bond(a, b)` | `d.detail.rail_bond(a, b)` | A rail bond joins two fixed pins, a detail case. |

A unit body's design moves the same way: `u.wire(...)` becomes `u.detail.wire(...)`. `d.earth`,
`d.mate` and `W1.core` keep their spellings.

## Grouped contacts

| before | after |
|---|---|
| one series per contact: `d.series(a.A_L1, k1.co_1.no, ...)`, and again for `co_2` and `co_3` | `q = d.poles(k1.co_1, k1.co_2, k1.co_3)`, then one `d.series(a, q.no, m1, ...)` |
| three single-pole changeover symbols | one three-pole symbol; with `selector=True` its throws face the line |

## From d.wire to d.series

Most `d.wire` calls were a current path written hop by hop. Write the path as one series instead:
it pairs the poles and takes the next free terminal or core.

A control path from rail to rail:

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
s1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
k1 = d.device("K1", "DEMO-CTR-3P-24")

# before: d.wire(dc.plus.pin, s1.no["13"], ...), d.wire(s1.no["14"], k1.coil["A1"], ...), ...
d.series(dc.plus, s1.no, k1.coil, dc.minus, wire=(BU, 0.75))
```

A power path through a strip and a cable to a motor:

```python
from fransys.colours import BK

x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", "230", *(x0[n] for n in (1, 2, 3)))
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
w1 = d.cable("W1", "DEMO-CBL-4G1.5")
m1 = d.device("M1", "DEMO-MOTOR-4KW")

# before: one d.wire per pole to X1, one W1.core per core, one d.wire per motor pin
d.series(ac, k1.main, x1, w1, m1, wire=(BK, 2.5))
```

A fixed terminal, as an as-built cabinet numbers them. `x1[3]` takes the place of the next free
terminal. `x1[1:4]` is terminals 1, 2 and 3 as one three-pole element, the end excluded. A tuple puts
one terminal on each pole when they sit on different strips. A fixed terminal counts as taken, so a
strip passed whole later skips it. A tuple that runs in order on one strip raises and names the
slice to write:

```python
x2 = d.terminal_strip("X2", "DEMO-TB-2.5")
h1 = d.device("H1", "DEMO-LAMP-24")
x3 = d.terminal_strip("X3", "DEMO-TB-2.5", 6)

# before: d.wire(dc.plus.pin, x2[3]), d.wire(x2[3].outer, h1.lamp["1"]), ...
d.series(dc.plus, x2[3], h1.lamp, x2[4], dc.minus, wire=(BU, 0.75))
# three phases on terminals 1, 2 and 3, and one terminal per pole across strips
d.series(ac, k1.main, x3[1:4], wire=(BK, 2.5))
x4, x5 = d.terminal_strip("X4", "DEMO-TB-2.5", 4), d.terminal_strip("X5", "DEMO-TB-2.5", 4)
d.series(d.device("Q9", "DEMO-MCB-3P").element, (x2[5], x4[3], x5[3]), wire=(BK, 2.5))
```

## Behaviour that changed

| before | now | why |
|---|---|---|
| `fr.derive.takes_energy` is `True` for a `load` only | `True` for a `load`, an `actuator` and a `coil` | A motor or coil draws from its supply, so `load_limits` counts its `nominal_current_a`. A part may still state `energy`. |
| A series through a cable landed the GNYE core only when the strip before it had a `pe=` part, else it raised. | The core lands on the load's PE port. The near end is the strip's PE terminal, else earthed open. | A cable's protective core reaches its load without a hand wire (author-0044). |
| A wire to the load's PE port after such a series built a `GNYE_NOT_PE` ERROR. | It raises an `AuthorError` that names the series. | The core is already landed; a second landing is refused at the call (author-0044). |
| `d.series(j1.x1, w5, j2.x1, ...)` between two connectors raised `has no poles: name its pins`; each pin pair was a `d.wire` call. | The series pairs the two connectors' pins in pin order. A function with no line side in the middle, or at one end against a supply, a rail or a function with poles, still raises. Unequal pin counts raise and name both counts. | One derive fact orders a sideless end's pins (model-0242). |
## Channels a series takes

A series now takes a PLC channel itself. Pass the module whole and it takes the lowest free channel
(authoring.md, how channels are numbered). A script that fixes every channel, `a1.di_7`, still works.

A package that keeps the channel map of existing software checks it once. Build the package both
ways, with the channels fixed and with the module passed whole, and compare the PLC list. If the
two lists are equal, use the core form. Where they differ, keep the fixed form for those channels.

```python
import fransys as fr
from fransys.colours import BU


def plc_list(fixed: bool) -> list[tuple[str, str | None]]:
    """The PLC list of a two-sensor package, the channels fixed or taken by the series."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    a1 = d.device("A1", "DEMO-PLC-DI-4P")
    for number in (1, 2):
        sensor = d.device(f"S{number}", "DEMO-PB-NC")
        sensor.sw.plc(fr.DI, f"Sensor {number}")
        target = getattr(a1, f"di_{number}") if fixed else a1
        d.series(dc.plus, sensor.sw, target, wire=(BU, 0.75))
    return [(r.pin, r.signal_name) for r in fr.derive.plc_channel_rows(fr.build(d).model)]


assert plc_list(fixed=True) == plc_list(fixed=False)  # equal: use the core form
```
