# Units

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

A unit is a released, independently built part of a design: a board, a cabinet, a box, anything
built and delivered on its own revision. This page shows how to write one, mark its interface,
record its revisions and nest it in a cabinet. A cabinet is itself a unit: it holds components,
units and wires, and it is never split into places.

`@fr.unit(name, revision=, interface_version=, date=, text=, by=)` turns a Python function into a unit.
The function builds the unit's devices on the design it receives and returns an instance of a
`typing.NamedTuple` class, one field per interface device. `d.add(fn, "U1")` builds the unit into
your design as instance `U1` and returns it, typed. Any other return raises. Every device the function creates belongs to that unit.
A unit draws the IEC default wire colours, never its parent's rows (series.md, Wire colours).

The second argument is the instance's printed tag, bare and with no lowercase letter: `"U3"`,
never `"u3"` or `"-U3"`. It is also the instance's key. A container prints the tag before the
unit's own designation, so a connector `J1` of instance `U3` prints `-U3-J1`. The unit's own document is unchanged.
`name=` (optional) is the identity a released number holds to, when it must differ from the tag.

`name` is a key, not a designation: write `demo-io-board`, never `-demo-io-board`. A prefix
raises an error. `version=` (default 1), `title=` and `number=` are the unit's own title-block
fields. An empty title or number gives a `TITLE_BLOCK_UNIT_IDENTITY_MISSING` warning on the
unit's own document.

`revision` and `interface_version` are numbers you bump by hand. Revisions count within one
version: a unit's first version runs `1.1`, `1.2`, and so on, and its second version starts again
at `2.1`. `interface_version` is the unit's boundary version.

## The interface

`d.device(tag, part, interface=True)` marks a device as part of the unit's interface: the point a
container may reach into the unit through. Any function may be an interface: a connector, a terminal,
a PLC channel, a coil or a supply output. A cable landing straight on a channel, with no strip
between, is the use. `interface=True` marks every function of the device; `interface=("coil",)`
names some, and the others stay inside the unit.

On a terminal strip `interface=(1, 2)` names terminals by number and `unused=` works the same;
`True` marks every terminal. A run takes `interface=True` or `unused=True` for the whole run, or a tuple of terminal numbers: `x1.run("L1", 3, interface=(1,))`. A
container reaches only the boundary terminals.

`d.device(tag, part, unused=True)` declares an interface device left unconnected on purpose,
so the build does not ask for it to be wired. `unused=` works on a boundary device and on an
internal one. On an internal device it declares its functions open on purpose. No unused-pin
finding is raised, and the device is no interface field. A device the unit returns is a boundary
too. A function declared unused but wired gives `UNUSED_CONTRADICTED`. The tuple the function returns names the devices a
container can reach: `io.X1` is the field `X1`. A misspelt field is a type-checker error. A field may hold a nested unit's interface field. That connector, strip, run or terminal becomes this unit's interface too, one level at a time, and prints its full path. The black box a page draws for a nested unit is the unit directly in the page's unit that holds it. A field that holds a strip, a run or a terminal is
typed `fr.TerminalStrip`, `fr.Run` or `fr.Terminal`.
`d.series` from a container reach the unit strip's free boundary terminals, the PE core the unit's PE run, and never add one.
Carry a strip or a run in the interface when a container wires several terminals in one series, as `io.x5[1:5]`. Separate `fr.Terminal` fields cannot be sliced.

A device with several functions takes the names of the boundary ones: `interface=("x1",),
unused=("x2",)`. `True` takes every function. A name the part lacks raises and lists its
functions; a part class from `fr.parts` rejects it when the type checker runs.

```python
from typing import NamedTuple

import fransys as fr


class Feed(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-supply-strip", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def supply_strip(d):
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    return Feed(x1)
```

```python
import subprocess
import sys
from typing import NamedTuple

import fransys as fr

subprocess.run(
    [sys.executable, "-m", "fransys", "parts-module", "demo_parts", "demo_typed.py"], check=True
)
sys.path.insert(0, ".")
import demo_typed as P


class Io(NamedTuple):
    X1: P.DEMO_CONN_2P


@fr.unit("demo-supply-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def box(d: fr.Design) -> Io:
    x1 = d.device("X1", P.DEMO_CONN_2P, interface=True)
    return Io(x1)
```

Annotate each device field with the generated part class it was built from, as `P.DEMO_CONN_2P`
above. A bare `fr.Device` hides the part's functions from the type checker.

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X7: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def board(d):
    return Io(d.device("X7", "DEMO-CONN-2P", interface=True))


@fr.unit("demo-assembly", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def assembly(d):
    return Io(d.add(board, "U2").X7)  # the board's connector is the assembly's interface too


d = fr.design("demo_parts")
unit = d.add(assembly, "U1")
d.cable("W1", "DEMO-CBL-4G1.5").core(1, d.device("P1", "DEMO-CONN-2P")[1], unit.X7[1])
assert not [f for f in fr.build(d).findings if f.code == "UNIT_BOUNDARY_BYPASSED"]
```

A unit's own `unused=` is the unit's fact. A carrier that leaves some boundary points of a unit it adds open for another carrier
declares them itself. `d.unused(pc.x3[3], pc.x4_1)` takes typed points of the returned fields, never a string.
The same call takes a port, `d.unused(m1.minus)`: the port is open on purpose and `FUNCTION_HALF_CONNECTED` stays silent for it.
A point or port that is wired gives `UNUSED_POINT_WIRED`, one that is no boundary point gives `UNUSED_NOT_BOUNDARY`,
and a point listed twice raises `UNUSED_LISTED_TWICE`.

```python
from typing import NamedTuple

import fransys as fr


class CabinetIo(NamedTuple):
    x3: fr.TerminalStrip


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def cabinet(d: fr.Design) -> CabinetIo:
    return CabinetIo(d.terminal_strip("X3", "DEMO-TB-2.5", 4, interface=(1, 2, 3, 4)))


d = fr.design("demo_parts")
pc = d.add(cabinet, "PC")
lamp = d.device("H1", "DEMO-LAMP-24")
d.series(pc.x3[1], lamp["1"], wire=("RD", 2.5))
d.series(pc.x3[2], lamp["2"], wire=("BU", 2.5))
m1, m2 = d.device("U1", "DEMO-MODULE-2P-COM4"), d.device("U2", "DEMO-MODULE-2P-COM4")
d.series(m1.plus, m2.plus, wire=("RD", 1.5))
d.unused(pc.x3[3], pc.x3[4], m1.minus, m2.minus)  # two boundary points and two ports left open on purpose
assert not [f for f in fr.check(fr.build(d)) if f.code in {"BOUNDARY_UNCONNECTED", "FUNCTION_HALF_CONNECTED"}]
```

## Variants and revised copies

A variant is a parameter of your own builders, never a Fransys feature. Fransys has no variant hook,
and nothing patches `fr.Design`. A revised copy of a unit is a factory around `@fr.unit`: a function that
takes the name, the revision and the variant, and returns the decorated unit.

```python
from typing import NamedTuple

import fransys as fr


class BoardIo(NamedTuple):
    X1: fr.Device


def board_unit(name: str, revision: int, *, pins: str = "DEMO-CONN-2P") -> fr.UnitDef[BoardIo]:
    @fr.unit(name, revision=revision, interface_version=1, date="2026-01-01", text="issue", by="AB")
    def board(d: fr.Design) -> BoardIo:
        return BoardIo(d.device("X1", pins, interface=True))

    return board


first = board_unit("demo-io-board", 1)
revised = board_unit("demo-io-board-r2", 2, pins="DEMO-CONN-4P")
d = fr.design("demo_parts")
u1 = d.add(first, "U1")
u2 = d.add(revised, "U2")
d.cable("W1", "DEMO-CBL-4G1.5").core(1, d.device("P1", "DEMO-CONN-2P")[1], u1.X1[1])
d.cable("W2", "DEMO-CBL-4G1.5").core(1, d.device("P2", "DEMO-CONN-2P")[1], u2.X1[1])
assert len(fr.derive.units(fr.build(d).model)) == 2
```

## Reaching a unit from outside

A container reaches a unit's connector with a cable core onto its pin, `d.cable("W1", P.CBL).core(1, plug[1], io.X1[1])`.
Mates are refused in 0.22 (`MATES_DISABLED`). A `d.series` wire onto a male or female connector of a nested
unit gives the warning `CONNECTOR_WIRED_WITHOUT_MATE`; a cable core onto it and a screw terminal give none.

A unit built alone, with nothing outside it, leaves its interface unconnected, and
`BOUNDARY_UNCONNECTED` stays silent: an open interface is what the next integrator connects.
The finding fires once the unit sits inside something larger and an interface device is neither
wired nor `unused`.

Nets do not cross a unit boundary. Join across it with `d.series(a, b, wire=...)`. A net with pins in two units that no wire joins gives
`NET_ACROSS_UNIT_BOUNDARY_OPEN` or `NET_ACROSS_UNIT_BOUNDARY_JOINED`, which names the net and the boundary pin.

A nested unit with a harness line at one of its interfaces draws on its parent's page as one
outline, with its columns above and below it. A unit with none keeps its usual frame. Inside stand
only its interfaces, title and revision. Each line-end interface is a connector box on the outline,
and the harness plug touches it from outside. The columns feeding top-edge interfaces stand above,
and those leaving bottom-edge interfaces stand below. Layout picks each interface's edge. A
single-wire interface keeps its column's flow. Harness interfaces split evenly, with supply-heavy
ones on top. The group stands at the left of its page and stays whole on one page.

## Tags and places

Instance tags count up inside their parent, the cabinet unit: `-U1`, `-U2`, with no prefix. One level
up, in the top design, they print behind the cabinet's own tag: `-U1-U2-X1`. A circuit, such as one
pump's or one string's, is a function block (`with d.function(...)`), never a place. A place is where
units and field devices stand: a room, a site, a ship's hold.

## A board with parts mounted on it

A part installed on the board as part of its assembly (pressed or bolted onto its copper) is a
child of the board: `parent=board`. The enclosure receptacles are not part of the board, so they
stay in the enclosure. For the board's parts and nets to draw, the board must be the only top-level
device of its own unit. So make the board assembly its own unit: the board plus its mounted parts.
Nest that unit in the enclosure unit, which holds the receptacles. Join the board's interface
connector to the receptacles with `d.series(..., wire=...)`; the wire crosses the unit
boundary and draws as a boundary connection. The board's parts draw on the board unit's pages, not
the enclosure's. A board that shares its unit with another top-level device draws as a black box,
and `BOARD_NETS_NOT_DRAWN` names its dropped nets.

## Task: a board unit in a cabinet

The cabinet is the unit that holds the boards. It holds two identical io boards, `U1` and `U2`. A
board has one connector the cabinet plugs into and one spare connector left open. Both boards share
one release; each instance prints its own tag, so no designation repeats. The same tag twice in one
unit gives `PRODUCT_DESIGNATION_DUPLICATE`. The cabinet is added to the top design.

```python
# easy: board units in a cabinet
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first release", by="AB")
def board(d):
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    d.device("X2", "DEMO-CONN-2P", interface=True, unused=True)
    return Io(x1)


class Cabinet(NamedTuple):
    pass


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first release",
    by="AB",
    title="Demo cabinet",
    number="DC-1",
)
def cabinet(c):
    io1 = c.add(board, "U1")
    io2 = c.add(board, "U2")
    p1 = c.device("P1", "DEMO-CONN-2P")
    p2 = c.device("P2", "DEMO-CONN-2P")
    c.cable("W1", "DEMO-CBL-4G1.5").core(1, p1[1], io1.X1[1])
    c.cable("W2", "DEMO-CBL-4G1.5").core(1, p2[1], io2.X1[1])
    return Cabinet()


d = fr.design("demo_parts")
d.add(cabinet, "U1")
```

The efficient level builds the same model. The cabinet's boards and plugs come from one loop.

```python
# efficient: board units in a cabinet
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first release", by="AB")
def board(d):
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    d.device("X2", "DEMO-CONN-2P", interface=True, unused=True)
    return Io(x1)


class Cabinet(NamedTuple):
    pass


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first release",
    by="AB",
    title="Demo cabinet",
    number="DC-1",
)
def cabinet(c):
    for n in (1, 2):
        io = c.add(board, f"U{n}")
        c.cable(f"W{n}", "DEMO-CBL-4G1.5").core(1, c.device(f"P{n}", "DEMO-CONN-2P")[1], io.X1[1])
    return Cabinet()


d = fr.design("demo_parts")
d.add(cabinet, "U1")
```

A loop of boards takes a tag for each instance, and a `name=` is the identity its number holds to in later releases.

```python
@fr.unit(
    "demo-io-board",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first release",
    by="AB",
)
def numbered_board(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


@fr.unit(
    "demo-numbered-cabinet",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first release",
    by="AB",
    title="Numbered cabinet",
    number="NC-1",
)
def numbered_cabinet(c):
    for n in (1, 2):
        c.add(numbered_board, f"U{n}", name=f"module{n}")
    return Cabinet()


floating = fr.design("demo_parts")
floating.add(numbered_cabinet, "U1")
```

Check that the cabinet build has no errors.

```python
result = fr.build(d)
assert not [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
```

## Recording revisions

A unit's `revision=` only states which revision is current. Earlier entries go in `history=`, a
list of mappings with `revision`, `date`, `text` and `created`. The decorator writes the history
first, then the unit's own entry from `date=`, `text=` and `by=`. If the current revision has no
entry, the build reports `REVISION_CURRENT_MISSING`.
Each history entry also takes `version`. An entry with no `version` takes the unit's current
version, so after a version bump, earlier entries must name their old `version`.

```python
from typing import NamedTuple

class Io(NamedTuple):
    X1: fr.Device


@fr.unit(
    "demo-io-board",
    revision=2,
    interface_version=1,
    date="2026-02-02",
    text="added a spare connector",
    by="AB",
    history=[{"revision": 1, "date": "2026-01-01", "text": "first release", "created": "AB"}],
)
def board_r2(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


d = fr.design("demo_parts")
d.add(board_r2, "U1")
```

`d.revision(revision, date=, text=, created=)` writes one history entry of the project itself,
the same way, on a design that is not a unit.

`fr.release` refuses a history entry that names a revision never released, as
`RELEASE_HISTORY_UNRELEASED`. The cutoff is the first entry, in history order (date, then version
and revision), that names a released revision. Entries before it are free text, such as an old
register's. Each later entry needs a folder under `into` in its own version, or must be the revision
being released. A first release has no folders, so every entry is free. A system release checks the
project's history the same way.

## Writing one unit

`fr.write(result, out_dir, unit="demo-io-board")` restricts `out_dir` to that unit's own
documents and lists. A unit's release name is the `unit=` value. The tuple `d.add` returns, such as
`io`, is not accepted there. To list a model's units, read `sorted(fr.derive.units(model))`.
