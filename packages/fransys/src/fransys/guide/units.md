# Units

A unit is a released, independently built part of a design: a board, a cabinet, a box, anything
built and delivered on its own revision. This page shows how to write one, mark its interface,
record its revisions and nest it in a cabinet.

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
container can reach: `io.X1` is the field `X1`. A misspelt field is a type-checker error. A field that holds a strip, a run or a terminal is
typed `fr.TerminalStrip`, `fr.Run` or `fr.Terminal`.

A device with several functions takes the names of the boundary ones: `interface=("x1",),
unused=("x2",)`. `True` takes every function. A name the part lacks raises and lists its
functions; a part class from `fr.parts` rejects it when the type checker runs.

`X1.x1.limits(rating=, operating=)` states the values the unit promises on one boundary
function. Read them from a part with `d.rating(part, fn)` and `d.operating(part, fn)`. It does not
mark the boundary: `interface=True` on the device does. Calling it with no value raises.

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

## Leaving one instance open

`unused=True` on `d.device` sits inside the unit, so it marks every instance. To leave the boundary
of one placed instance open, the container names it on `d.add`. `unused=("X1",)` takes every boundary
function of the device in the unit's field `X1`. `unused=("X1.x1",)` takes that one function. A field that holds a tuple of devices takes an index, `"X[0]"` or `"X[0].x1"`. The bare `"X"` takes every element. A
misspelt field raises and lists the fields. A name that is no boundary raises and lists the boundary
functions. A boundary both mated and declared unused still gives `UNUSED_CONTRADICTED`.

```python
from typing import NamedTuple

import fransys as fr


class Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def board(d):
    return Io(d.device("X1", "DEMO-CONN-2P", interface=True))


d = fr.design("demo_parts", place="C1")
io1 = d.add(board, "U1")
io2 = d.add(board, "U2", unused=("X1",))
d.mate(d.device("B1", "DEMO-CONN-2P"), io1.X1)
```

The build holds no `BOUNDARY_UNCONNECTED` and no `UNUSED_CONTRADICTED`. U1's `X1` is mated, and U2's
prints `N/A` in its table only.

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

## Task: a board unit in a cabinet

The cabinet holds two identical io boards, `U1` and `U2`. A board has one connector the cabinet
plugs into and one spare connector left open. Both boards share one release and sit in one cabinet;
each instance prints its own tag, so no designation repeats. The same tag twice at one place gives
`PRODUCT_DESIGNATION_DUPLICATE`.

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


d = fr.design("demo_parts", place="C1")
d.location("C1", "Pump cabinet")
io1 = d.add(board, "U1")
io2 = d.add(board, "U2")
p1 = d.device("P1", "DEMO-CONN-2P")
p2 = d.device("P2", "DEMO-CONN-2P")
d.mate(p1, io1.X1)
d.mate(p2, io2.X1)
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


d = fr.design("demo_parts", place="C1")
d.location("C1", "Pump cabinet")
for n in (1, 2):
    io = d.add(board, f"U{n}")
    d.mate(d.device(f"P{n}", "DEMO-CONN-2P"), io.X1)
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


floating = fr.design("demo_parts", place="C1")
floating.location("C1", "Pump cabinet")
modules = [floating.add(numbered_board, None, name=f"module{n}") for n in (1, 2)]
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


d = fr.design("demo_parts", place="C1")
d.location("C1", "Pump cabinet")
d.add(board_r2, "U1")
```

`d.revision(revision, date=, text=, created=)` writes one history entry of the project itself,
the same way, on a design that is not a unit.

## Writing one unit

`fr.write(result, out_dir, unit="demo-io-board")` restricts `out_dir` to that unit's own
documents and lists. A unit's release name is the `unit=` value. The tuple `d.add` returns, such as
`io`, is not accepted there. To list a model's units, read `sorted(fr.derive.units(model))`.
