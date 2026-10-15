# Examples

Worked examples of whole circuits, each shown the easy way and the efficient way, and a pointer to
a full build script outside this repository. All parts are from `demo_parts`.

## A motor starter with a start/stop latch

S1 and S2 are two contact blocks: S1's break contact (`nc`) stops, S2's make contact (`no`) starts.
The power circuit runs from the three-phase supply through a breaker, the contactor's make
contacts (`main`) and an overload relay to a terminal strip. A cable carries it to the motor. The
power supply G1 takes its mains from L1 and N of the same supply. The control circuit runs from the 24 V rail through
the stop contact, a latch and the overload's break contact to the contactor coil. The latch is the
start contact in parallel with the contactor's own
auxiliary make contact.

`d.series(a, b, ...)` is the one spelling for a chain of connections, and `d.parallel(...)` puts
branches between two neighbours. The design is a plain top design: no place and no cabinet.

```python
# easy: motor starter
import fransys as fr
from fransys.colours import BK, BU

d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
g1 = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", g1)
q0 = d.device("Q0", "DEMO-MCB-3P")
q1 = d.device("Q1", "DEMO-CTR-3P-24")
f1 = d.device("F1", "DEMO-OVERLOAD-3P")
s1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
s2 = d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
w1 = d.cable("W1", "DEMO-CBL-4G1.5")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1, wire=(BK, 2.5))
d.series(ac.L1, g1.input, ac.N, wire=(BK, 2.5))
d.series(dc.plus, s1.nc, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
```

The efficient version builds the same model. The devices come from one table of tag and part
number, so adding a device is one more line in the table.

```python
# efficient: motor starter
import fransys as fr
from fransys.colours import BK, BU

PARTS = {
    "G1": "DEMO-PSU-24",
    "Q0": "DEMO-MCB-3P",
    "Q1": "DEMO-CTR-3P-24",
    "F1": "DEMO-OVERLOAD-3P",
    "S1": "DEMO-CTR-BLOCK-1NO1NC",
    "S2": "DEMO-CTR-BLOCK-1NO1NC",
}

d = fr.design("demo_parts")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", "230", *(x0[n] for n in (1, 2, 3)), n=x0[4])
i = {tag: d.device(tag, mpn) for tag, mpn in PARTS.items()}
dc = d.dc_supply("24VDC", i["G1"])
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
w1 = d.cable("W1", "DEMO-CBL-4G1.5")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
d.series(ac, i["Q0"].element, i["Q1"].main, i["F1"].main, x1, w1, m1, wire=(BK, 2.5))
d.series(ac.L1, i["G1"].input, ac.N, wire=(BK, 2.5))
latch = d.parallel(i["S2"].no, i["Q1"].aux)
d.series(dc.plus, i["S1"].nc, latch, i["F1"].aux, i["Q1"].coil, dc.minus, wire=(BU, 0.75))
```

## Sixteen sensors to a terminal strip

Each sensor is one device, wired by its signal pin to its own terminal on a strip. The strip
takes its terminals in number order: each series that names the strip takes the next free one.
A series from a sensor's function to the strip wires its load pin `B` to that terminal. The first
sensor added lands on terminal 1, so the sensors are added from B16 down to B1.

```python
# easy: sensors to a strip
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
with d.function("SENS", "Sensors"):
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    b16 = d.device("B16", "DEMO-SWITCH-2P")
    d.series(b16.sw, x1, wire=(BU, 0.75))
    b15 = d.device("B15", "DEMO-SWITCH-2P")
    d.series(b15.sw, x1, wire=(BU, 0.75))
    b14 = d.device("B14", "DEMO-SWITCH-2P")
    d.series(b14.sw, x1, wire=(BU, 0.75))
    b13 = d.device("B13", "DEMO-SWITCH-2P")
    d.series(b13.sw, x1, wire=(BU, 0.75))
    b12 = d.device("B12", "DEMO-SWITCH-2P")
    d.series(b12.sw, x1, wire=(BU, 0.75))
    b11 = d.device("B11", "DEMO-SWITCH-2P")
    d.series(b11.sw, x1, wire=(BU, 0.75))
    b10 = d.device("B10", "DEMO-SWITCH-2P")
    d.series(b10.sw, x1, wire=(BU, 0.75))
    b9 = d.device("B9", "DEMO-SWITCH-2P")
    d.series(b9.sw, x1, wire=(BU, 0.75))
    b8 = d.device("B8", "DEMO-SWITCH-2P")
    d.series(b8.sw, x1, wire=(BU, 0.75))
    b7 = d.device("B7", "DEMO-SWITCH-2P")
    d.series(b7.sw, x1, wire=(BU, 0.75))
    b6 = d.device("B6", "DEMO-SWITCH-2P")
    d.series(b6.sw, x1, wire=(BU, 0.75))
    b5 = d.device("B5", "DEMO-SWITCH-2P")
    d.series(b5.sw, x1, wire=(BU, 0.75))
    b4 = d.device("B4", "DEMO-SWITCH-2P")
    d.series(b4.sw, x1, wire=(BU, 0.75))
    b3 = d.device("B3", "DEMO-SWITCH-2P")
    d.series(b3.sw, x1, wire=(BU, 0.75))
    b2 = d.device("B2", "DEMO-SWITCH-2P")
    d.series(b2.sw, x1, wire=(BU, 0.75))
    b1 = d.device("B1", "DEMO-SWITCH-2P")
    d.series(b1.sw, x1, wire=(BU, 0.75))
```

The efficient version is a list of sensor tags in the order the strip hands out terminals, and one
loop.

```python
# efficient: sensors to a strip
import fransys as fr
from fransys.colours import BU

SENSORS = [f"B{n}" for n in range(16, 0, -1)]

d = fr.design("demo_parts")
with d.function("SENS", "Sensors"):
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    for tag in SENSORS:
        sensor = d.device(tag, "DEMO-SWITCH-2P")
        d.series(sensor.sw, x1, wire=(BU, 0.75))
```

## The whole shape of a build script

The examples above build small pieces of a design. For a real build script end to end, see
`examples/pump-station/build.py` in the public `fransys` repository, at the tag you pinned. It has its
own parts library (`example_parts`), so it cannot run as a block on
this page. It shows:

- The project and its revision history, set up once at the top.
- A cabinet unit with a second unit, the relay-interface board, mated to it through headers.
- Locations and functions built section by section: incoming supply, control supply, a PLC rack,
  and a per-pump circuit written once as a function and called for each pump.
- Several documents for several audiences from one design, then one `fr.build` and a `fr.write`
  per audience.

Consumer bugs become permanent tests in `tests/field_cases/` of the Fransys repository. Each
module's docstring states the engineering shape and the decision that fixed it.
