# Fransys

Fransys is a Python toolkit for authoring electrical cabinet and harness designs and
producing their schematics, parts lists and manufacturing exports from one model. This page
lists every consumer task with its one spelling, then the install and the shape of a script.

Fransys is in Beta: the API may change between minor versions until 1.0.0, and each release's guide says what changed.

## Tasks

Each task has one spelling. `P` is a generated parts module or an MPN string; `BU` and `BN` come
from `fransys.colours`.

| task | its one spelling | where it is taught |
|---|---|---|
| load a library, start a design | `d = fr.design("demo_parts")` | parts.md, Loading a library |
| load a library, no design | `fr.parts(*names)` | parts.md |
| lint a library | `fr.lint(*names)` | parts.md, Linting a library |
| name a place | `d.location("HOLD", text)`, then `place="HOLD"` | authoring.md, name a place |
| name a function block | `with d.function("M1", text):` | authoring.md, name a function block |
| add a device | `d.device("Q1", P.X, place=, parent=, mounted_on=)` | authoring.md, add a device |
| read a function or pin | `Q1.coil`, `Q1["A1"]`, `Q1[2]` | authoring.md, read a function or pin |
| add a terminal strip, take a terminal | `d.terminal_strip("X1", P.X, n)`, `X1[3]` | authoring.md, Strips and terminals |
| a named, bridged run on a strip | `X1.run(label, n, bridged=True)` | authoring.md, Bridges |
| bridge a set of auto-numbered terminals | `X1.run(label, bridged=True)`, then `d.wire(feed, pin, ...)` | authoring.md, Bridges |
| wire two or more pins | `d.wire(a, b, wire=(BU, 0.75))` | authoring.md, Wiring and cables |
| wire along a current path | `d.series(a, b, c, wire=(BU, 0.75))` | authoring.md, wire along a current path |
| branch inside a series | `d.parallel(a, b)` | authoring.md, branch inside a series |
| add a cable, wire a core | `d.cable("W1", P.X, length_m=)`, `W1.core(BN, a, b)` | authoring.md, Wiring and cables |
| name a wire colour | `from fransys.colours import BU`, then `wire=(BU, 0.75)` | authoring.md, Wire colours |
| earth pins | `d.earth(*pins)` | authoring.md, earth pins |
| a named signal net | `d.net(name, *pins, kind=)` | authoring.md, a named signal net |
| a busbar, a rail bond | `d.busbar(a, b)`, `d.rail_bond(a, b)` | authoring.md, a busbar, a rail bond |
| AC or DC supply and rails | `d.ac_supply(...)`, `d.dc_supply(...)` | authoring.md, AC or DC supply and rails |
| name a place inside a place | `d.location("BATT", text, within="HOLD")` | authoring.md, A place inside a place |
| list a function's pins in order | `fn.pins` | authoring.md, Cables |
| plug a connector | `d.mate(a, b)` | authoring.md, plug a connector |
| add a harness | `d.harness("W5")` | authoring.md, add a harness |
| request a PLC channel, scale it | `K1.coil.plc(fr.DO, name)`, `.scale(...)` | authoring.md, request a PLC channel |
| title block, revision | `d.project(...)`, `d.revision(...)` | authoring.md, title block, revision |
| read a part's rating while authoring | `d.rating(part, fn)`, `d.operating(part, fn)` | authoring.md, Reading a part's rating |
| advise the drawing | `d.layout.chain`, `keep_together`, `break_before`, `order`, `symbol`, `draw_in`, `sheet`, `profile` | authoring.md, Layout profile |
| define a unit | `@fr.unit(name, revision=, interface_version=, ...)` | units.md, define a unit |
| add a unit instance, reach its boundary | `d.add(fn, "U1")` returns the unit's `NamedTuple`, `io.X1` | units.md, Nesting units |
| mark a boundary device | `interface=True`, `unused=True` on `d.device` | units.md, The boundary |
| leave one placed instance's boundary open | `d.add(fn, "U2", unused=("X1",))` | units.md, Leaving one instance open |
| state a boundary's values | `X1.power.limits(rating=, operating=)` | units.md, The boundary |
| build the model | `fr.build(d, *documents)` | build.md |
| add a document | `fr.document(preset, subject, cover=)` | documents.md |
| all findings of a build | `fr.check(result)` | build.md, `fr.check` sees more |
| write exports | `fr.write(result, out_dir)` | build.md |
| the name of each export | `fr.export_names(result, unit=None)` | build.md, Export file names |
| release a baseline | `fr.release(result, into)` | build.md, Releasing |
| list changes since a release | `fr.diff(result, baselines)` | build.md, Getting the change list |
| test a baseline stays true | `fr.verify(result, baselines)` | build.md, Checking a baseline |
| list the releases on disk | `fr.releases(root)` | build.md, Listing the releases |
| read a built model | `fr.derive.<function>(model, ...)` | reading.md |
| an easy and an efficient level | same calls, a function or a loop around them | examples.md, easy and efficient |

<!-- --8<-- [start:install] -->
## Install

Fransys is not on PyPI yet. Pin it as a git dependency, at a release tag:

```toml
[project]
dependencies = [
    "fransys @ git+https://github.com/OleJBondahl/fransys@vX.Y.Z#subdirectory=packages/fransys",
]
```

Replace `vX.Y.Z` with the release you pin.
<!-- --8<-- [end:install] -->

## The shape of a build script

A script starts a design from an installed part library (`fr.design`), authors it with
`d.device` and wiring, adds a cabinet as a unit (`@fr.unit`, `d.add`), and passes the design to
`fr.build`, which merges and freezes a model and lays out the schematic when a document keeps a SCHEMATIC page. `fr.check` collects every finding about the built model;
`fr.write` writes the exports to a directory, raising instead of writing anything if `check`
found an `ERROR`. A design with no document has nothing to draw, so `build` still succeeds and
`write` still produces the parts-list exports.

```python
from pathlib import Path
from typing import NamedTuple

import fransys as fr


class Cabinet(NamedTuple):
    pass


@fr.unit("pump-cabinet", revision=1, interface_version=1, date="2026-01-01", text="First", by="AB")
def cabinet(c):
    c.device("X1", "DEMO-TB-2.5")
    return Cabinet()


d = fr.design("demo_parts")
d.add(cabinet, "U1")

result = fr.build(d)  # no document: no layout
findings = fr.check(result)
assert not [f for f in findings if f.severity is fr.Severity.ERROR]
fr.write(result, Path("out"))
```

## The rest of this guide

- `parts.md`: loading and linting a part library, and catching a bad one.
- `authoring.md`: places, functions, devices, wiring, cables, colours.
- `units.md`: a unit's boundary, its revisions, and nesting one unit inside another.
- `build.md`: `build`, `check`, `write`, `release`, `verify`, and where each can fail.
- `documents.md`: presets, covers, subjects, and one PDF per drawing.
- `reading.md`: reading a built model back: tables, rows, designations and ratings.
- `findings.md`: every finding code, what it means, and the usual fix.
- `kicad.md`: importing a board netlist into KiCad, with the settings to use.
- `examples.md`: worked examples, and a pointer to a full build script.
- `moving-to-0.6.md`: each break from 0.5, with the old spelling, the new one and why.
- `moving-to-fransys.md`: the alias, the pin line, the parts-module command and the intermediates folder for a 0.6.1 consumer of the old name.
