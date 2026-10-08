# Units

A unit is a released, independently built part of a design: a board, a cabinet, a box, anything
built and delivered on its own revision. This page shows how to write one, mark its interface,
record its revisions and nest it in a cabinet. A cabinet is itself a unit: it holds components,
units and wires, and it is never split into places.

`@fr.unit(name, revision=, interface_version=, date=, text=, by=)` turns a Python function into a unit.
The function builds the unit's devices on the design it receives and returns an instance of a
`typing.NamedTuple` class, one field per interface device. `d.add(fn, "U1")` builds the unit into
your design as instance `U1` and returns it, typed. Any other return raises. Every device the function creates belongs to that unit.

The second argument is the instance's printed tag, bare and with no lowercase letter: `"U3"`,
never `"u3"` or `"-U3"`. It is also the instance's key. A container prints the tag before the
unit's own designation, so a connector `J1` of instance `U3` prints `-U3-J1`. The unit's own document is unchanged.
`None` floats the number: `d.add(fn, None, name="module1")` takes the next free number of the
unit's class code, set with `class_code="U"` on `@fr.unit` (or by the part file's). `name=` is the
identity a released number holds to. A floating add with no `name=` or no class code raises.

`name` is a key, not a designation: write `demo-io-board`, never `-demo-io-board`. A prefix
raises an error. `version=` (default 1), `title=` and `number=` are the unit's own title-block
fields. An empty title or number gives a `TITLE_BLOCK_UNIT_IDENTITY_MISSING` warning on the
unit's own document.

`revision` and `interface_version` are numbers you bump by hand. Revisions count within one
version: a unit's first version runs `1.1`, `1.2`, and so on, and its second version starts again
at `2.1`. `interface_version` is the unit's boundary version.

## The interface

`d.device(tag, part, interface=True)` marks a device as part of the unit's interface: the
connector or terminal a container may reach into the unit through. Only a terminal or a
connector can be an interface; marking a coil or a contact gives the error `BOUNDARY_KIND` at
build time.

`d.device(tag, part, unused=True)` declares an interface device left unconnected on purpose,
so the build does not ask for it to be wired. `unused=True` on a device that is not an
interface marks it as one too. The tuple the function returns names the devices a
container can reach: `io.X1` is the field `X1`. A misspelt field is a type-checker error. A field may hold a nested unit's interface field. That connector, strip, run or terminal becomes this unit's interface too, one level at a time, and prints its full path. `fr.derive.black_box_unit(model, unit, set_unit)` returns the unit directly in `set_unit` that holds `unit`: the black box a page draws for it. A field that holds a strip, a run or a terminal is
typed `fr.TerminalStrip`, `fr.Run` or `fr.Terminal`.
`d.series` and `d.wire` from a container reach the unit strip's free boundary terminals, the PE core the unit's PE run, and never add one.

A device with several functions takes the names of the boundary ones: `interface=("x1",),
unused=("x2",)`. `True` takes every function. A name the part lacks raises and lists its
functions; a part class from `fr.parts` rejects it when the type checker runs.

`X1.x1.limits(rating=, operating=)` states the values the unit promises on one boundary
function. Read them from a part with `d.rating(part, fn)` and `d.operating(part, fn)`. It does not
mark the boundary: `interface=True` on the device does. Calling it with no value raises.
`X1[1].limits(rating=, operating=)` does the same for a terminal's boundary, with the same refusals.

```python
from typing import NamedTuple

import fransys as fr


class Feed(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-supply-strip", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def supply_strip(d):
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    x1[1].limits(rating=d.rating("DEMO-PSU-24", "input"))
    return Feed(x1)
```

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-supply-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def box(d):
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    x1.x1.limits(rating=d.rating("DEMO-PSU-24", "input"))
    return Io(x1)
```

A unit may hand back a value beside its devices. Annotate the field with its `fr.derive` type, for
example `fr.derive.Operating`.

```python
class Supply(NamedTuple):
    X1: fr.Device
    rated: fr.derive.Operating


@fr.unit("demo-supply-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def supply_box(d):
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    operating = d.operating("DEMO-STRING-864V", "string")
    x1.x1.limits(operating=operating)
    return Supply(x1, operating)
```

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
d.mate(d.device("P1", "DEMO-CONN-2P"), unit.X7)
assert not [f for f in fr.build(d).findings if f.code == "UNIT_BOUNDARY_BYPASSED"]
```

## Leaving one instance open

`unused=True` on `d.device` sits inside the unit, so it marks every instance. To leave the boundary
of one placed instance open, the container names it on `d.add`. `unused=("X1",)` takes every boundary
function of the device in the unit's field `X1`. `unused=("X1.x1",)` takes that one function. A field that holds a tuple of devices takes an index, `"X[0]"` or `"X[0].x1"`. The bare `"X"` takes every element. A
misspelt field raises and lists the fields. A name that is no boundary raises and lists the boundary
functions. A boundary both mated and declared unused still gives `UNUSED_CONTRADICTED`.

A field typed `fr.Terminal` names that terminal's one function: `unused=("X1",)`. A field typed
`fr.Run` or `fr.TerminalStrip` names every boundary terminal it holds. `"X1[1].f"` on a terminal
raises. A run or strip with no boundary terminal raises, as a device that is no boundary does.

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def board(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


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
    io2 = c.add(board, "U2", unused=("X1",))
    c.mate(c.device("B1", "DEMO-CONN-2P"), io1.X1)
    return Cabinet()


d = fr.design("demo_parts")
d.add(cabinet, "U1")
```

The build holds no `BOUNDARY_UNCONNECTED` and no `UNUSED_CONTRADICTED`. U1's `X1` is mated, and U2's
prints `N/A` in its table only.

## Variants and revised copies

A variant is a parameter of your own builders, never a Fransys feature. Fransys has no variant hook,
and nothing patches `fr.Design`. A revised copy of a unit is a factory around `@fr.unit`: a function that
takes the name, the revision and the variant, and returns the decorated unit.

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


def board_unit(name, revision, *, pins="DEMO-CONN-2P"):
    @fr.unit(name, revision=revision, interface_version=1, date="2026-01-01", text="issue", by="AB")
    def board(d):
        return Io(d.device("X1", pins, interface=True))

    return board


first = board_unit("demo-io-board", 1)
revised = board_unit("demo-io-board-r2", 2, pins="DEMO-CONN-4P")
d = fr.design("demo_parts")
d.add(first, "U1")
d.add(revised, "U2")
assert len(fr.derive.units(fr.build(d).model)) == 2
```

## Reaching a unit from outside

A container reaches a unit's connector through a plug and `d.mate(plug, io.X1)`. Do not wire
onto the connector's own pins. A direct wire onto a male or female connector of a nested unit
gives the warning `CONNECTOR_WIRED_WITHOUT_MATE`. A screw terminal has no gender and takes the
wire silently. The core lands on the plug's pin (`P1[1]`), because the plug is what the
container's own wiring reaches, and the mate makes plug and connector conduct as one.

A unit built alone, with nothing outside it, leaves its interface unconnected, and
`BOUNDARY_UNCONNECTED` stays silent: an open interface is what the next integrator connects.
The finding fires once the unit sits inside something larger and an interface device is neither
mated nor `unused`.

A nested unit with a harness line at one of its interfaces draws on its parent's page as one
outline, with its columns above and below it. A unit with none keeps its usual frame. Inside stand
only its interfaces, title and revision. Each line-end interface is a connector box on the outline,
and the harness plug touches it from outside. The columns feeding top-edge interfaces stand above,
and those leaving bottom-edge interfaces stand below. Layout picks each interface's edge. A
single-wire interface keeps its column's flow. Harness interfaces split evenly, with supply-heavy
ones on top. `d.layout.side(u1.bus_in, fr.ABOVE)`, or `fr.BELOW`, fixes one interface's edge when
the default reads wrong. The group stands at the left of its page and stays whole on one page.

## Tags and places

Instance tags count up inside their parent, the cabinet unit: `-U1`, `-U2`, with no prefix. One level
up, in the top design, they print behind the cabinet's own tag: `-U1-U2-X1`. A circuit, such as one
pump's or one string's, is a function block (`with d.function(...)`), never a place. A place is where
units and field devices stand: a room, a site, a ship's hold.

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
    c.mate(p1, io1.X1)
    c.mate(p2, io2.X1)
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
        c.mate(c.device(f"P{n}", "DEMO-CONN-2P"), io.X1)
    return Cabinet()


d = fr.design("demo_parts")
d.add(cabinet, "U1")
```

A loop of boards can leave the numbers to the build. Give the release a `class_code` and each
instance a `name=`, the identity its number holds to in later releases.

```python
@fr.unit(
    "demo-io-board",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first release",
    by="AB",
    class_code="U",
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
        c.add(numbered_board, None, name=f"module{n}")
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
