# Fransys

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Fransys is a Python toolkit for authoring electrical cabinet and harness designs and
producing their schematics, parts lists and manufacturing exports from one model. This page
lists every consumer task with its one spelling, then the install and the shape of a script.

Fransys is in Beta: the API may change between minor versions until 1.0.0, and each release's guide says what changed.
Paste the block in [AGENTS.md](AGENTS.md) into your project's `AGENTS.md` or `CLAUDE.md`, so a coding agent finds the docs and `python -m fransys help KEY`.

## The public surface

The public surface has four parts: `fr.__all__`, `fr.derive.__all__`, `fransys.colours`, and every keyword of every public call and every `d.*` method, with the `d.layout.profile` keywords and the `d.layout.sheet` numbers. Nothing else is public, and every part has an entry in this guide.

## Tiers

Every `fr.*` function and handle method opens its docstring with one of four tier words.

- `Core:` the calls a project is written with.
- `Detail:` a call for a case no core call writes; its docstring names the core call to try first.
- `Read:` reads a built model or a part library and changes nothing.
- `Output:` builds, checks, reports, writes or releases.

A namespace sets the tier of the names under it, so they carry no word: `d.*` is core, `d.detail.*` and `d.layout.*` are detail, and `fr.derive.*` is read.
Types, constants, colours and exceptions have no tier.

## Which call first

Write a design with the core calls below. They pair poles, take the next free terminal or core,
and give layout the structure it draws. The detail calls in the table are for their cases only
(detail.md).

1. A cabinet or a board is a unit: `@fr.unit`, then `d.add` (units.md).
2. Name places with `d.location`. Put each circuit in its own block, `with d.function(tag, text):`.
3. Declare every supply with `d.dc_supply` or `d.ac_supply`. Start and end each path on its rails.
4. Write each current path as one `d.series(...)`, source first. Devices, functions, rails, strips,
   runs and cables are its elements.
5. A branch between two neighbours is a `d.parallel(...)` element. A branch across several
   elements is a second series, from the split to the join.
6. Pass a strip, a run or a cable to the series. It takes the next free terminal or core, on the
   right side.
7. Bridge with `bridged=` on the strip or the run. Request a PLC signal on its function,
   `K1.coil.plc(fr.DO, name)`, and pass the PLC module whole to the series: it takes its lowest
   free channel (authoring.md, how channels are numbered).
8. A circuit that repeats is a Python function around these calls, fed by a table (examples.md).
9. Add `d.layout.*` advice last, only where the structure leaves the drawing a choice.

| detail call | only for |
|---|---|
| `d.detail.wire(a, b, wire=...)` | two named pins off any path, such as a signal pair; one signal daisy-chained, `d.detail.wire(a, b, c)`; a hop whose printed wire differs from its row |
| `X1[3]`, `.inner`, `.outer` | a terminal whose number or side is fixed: a published pinout, or several wires on one terminal |
| `W1.core(BN, a, b)` | a core whose colour or number a termination plan fixes |
| `d.detail.net(name, *pins)` | a named net that no wire joins, such as a bus; its name prints in the connector list |
| `d.detail.busbar(a, b)`, `d.detail.rail_bond(a, b)` | a rack's internal jumper; terminals bonded through their rail |

`d.series` raises `has no pole pair: its part states no line side` when a part does not say which pin is the line
side. Fix the part file (`side = "line"`, parts.md), or wire the pins with `d.detail.wire`. A real circuit that no
core call can write is a gap in Fransys: report it with its smallest shape.

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
| add a device | `d.device("Q1", P.X, place=, parent=, mounted_on=, joins=)` | authoring.md, add a device |
| read a function or pin | `Q1.coil`, `Q1["A1"]`, `Q1[2]` | authoring.md, read a function or pin |
| add a terminal strip, take a terminal | `d.terminal_strip("X1", P.X, n)`, `X1[3]` | authoring.md, Strips and terminals |
| a named, bridged run on a strip | `X1.run(label, n, bridged=True)` | authoring.md, Bridges |
| bridge a set of auto-numbered terminals | `X1.run(label, bridged=True)`, then the run passed to each `d.series` | authoring.md, Bridges |
| wire along a current path | `d.series(a, b, c, wire=(BU, 0.75))` | series.md, wire along a current path |
| branch inside a series | `d.parallel(a, b)` | series.md, branch inside a series |
| a branch across part of a path | a second `d.series(split, ..., join, wire=...)` | series.md, Branch inside a series |
| a series from one pin, or a branch looped at a fuse's line pins | `d.series(k1.coil["A1"], a1.di_1)`, `d.series((f4.element[1], f4.element[3], f4.element[5]), f8.element)` | keywords-handles.md |
| bridge adjacent plain terminals | `d.terminal_strip("X4", P.X, 6, bridged=(2, 6))` | authoring.md, Bridges |
| wire one point to many | `d.detail.star(src, (a, b, c), wire=...)` | detail.md, One point to many |
| wire two named pins off a path | `d.detail.wire(a, b, wire=(BU, 0.75))` | detail.md, d.detail.wire |
| add a cable | `d.cable("W1", P.X, length_m=)` in a `d.series`, which takes the next free core | series.md, Cables |
| a signal pair through a cable, pin for pin | `d.pair(a, cable, b)` | keywords-design.md, d.pair |
| choose one core of a cable | `W1.core(BN, a, b)` | detail.md, W1.core |
| name a wire colour | `from fransys.colours import BU`, then `wire=(BU, 0.75)` | series.md, Wire colours |
| colour wires by what they carry | `fr.design(..., wiring=)`, `@fr.unit(wiring=)` or `wire={row: ...}` | series.md, Wire colours |
| a changeover throw in a series | `k1.co_1.no`, `.nc` | series.md, A changeover in a series |
| earth pins | `d.earth(*pins)` | series.md, earth pins |
| a named signal net | `d.detail.net(name, *pins, kind=)` | detail.md |
| a busbar, a rail bond | `d.detail.busbar(a, b)`, `d.detail.rail_bond(a, b)` | detail.md |
| AC or DC supply and rails | `d.ac_supply(...)`, `d.dc_supply(...)` | authoring.md, AC or DC supply and rails |
| name a place inside a place | `d.location("BATT", text, within="HOLD")` | authoring.md, A place inside a place |
| take one pole of a multi-pole function | `s1.main.pole(2)` | keywords-handles.md, Fn.pole |
| list a function's pins in order | `fn.pins` | detail.md, W1.core |
| plug a connector | `d.mate(a, b)` | authoring.md, plug a connector |
| add a harness | `d.harness("W5")` | harnesses.md, add a harness |
| group PLC modules in a rack | `d.rack` | authoring.md |
| request a PLC channel, scale it | `K1.coil.plc(fr.DO, name)`, `.scale(...)` | authoring.md, request a PLC channel |
| wire a path to a PLC channel | `d.series(dc.plus, s1.no, a1)`; fixed: `a1.di_7` | authoring.md, how channels are numbered |
| title block, revision | `d.project(...)`, `d.revision(...)` | authoring.md, title block, revision |
| read a part's rating while authoring | `d.rating(part, fn)`, `d.operating(part, fn)` | parts.md, Reading a part's rating while authoring |
| advise the drawing | `d.layout.chain`, `keep_together`, `break_before`, `order`, `symbol`, `draw_in`, `side`, `pins_below`, `sheet`, `profile` | detail.md, Layout profile |
| put a unit's interface above or below its outline | `d.layout.side(u1.bus_in, fr.ABOVE)`, `fr.BELOW` | detail.md, Layout profile |
| draw all of a box's pins below its body | `d.layout.pins_below(a1)` | detail.md, Layout profile |
| define a unit | `@fr.unit(name, revision=, interface_version=, ...)` | units.md, define a unit |
| add a unit instance, reach its boundary | `d.add(fn, "U1")` returns the unit's `NamedTuple`, `io.X1` | units.md, Nesting units |
| mark some terminals of a strip a unit boundary | `d.terminal_strip("X1", P.X, 4, interface=(1, 2))`, `unused=` the same | units.md, The boundary |
| mark a boundary device | `interface=True`, `unused=True` on `d.device` | units.md, The boundary |
| leave one placed instance's boundary open | `d.add(fn, "U2", unused=("X1",))` | units.md, Leaving one instance open |
| state a boundary's values | `X1.power.limits(rating=, operating=)` | units.md, The boundary |
| build the model | `fr.build(d, *documents)` | build.md |
| set the paper or a consumer's settings for a build | `s = fr.settings("fransys.toml", paper={fr.PageKind.BLOCK_DIAGRAM: "A2"})`, then `fr.build(d, settings=s)` | settings.md |
| add a document | `fr.document(preset, subject, cover=)` | documents.md |
| all findings of a build | `fr.check(result)` | build.md, `fr.check` sees more |
| a readable report of them | `fr.report(result)` | build.md, `fr.report` |
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
print(fr.report(result))  # the summary, each error and warning with its fix, then the notes
findings = fr.check(result)
assert not [f for f in findings if f.severity is fr.Severity.ERROR]
fr.write(result, Path("out"))
```

`fr.report(result)` prints what the build found, so a script shows its warnings on every run.

## The rest of this guide

### Writing a project

- `parts.md`: loading and linting a part library, the typed parts module, and a part's rating.
- `authoring.md`: places, functions, devices, strips, bridges, supplies and channels.
- `series.md`: series, branches, changeovers, cables, wire colours and earth pins.
- `units.md`: a unit's boundary, its revisions, and nesting one unit inside another.
- `harnesses.md`: adding a harness, and how its cables and plugs print.
- `documents.md`: presets, covers, subjects, and one PDF per drawing.
- `build.md`: `build`, `check`, `write`, `release`, `verify`, and where each can fail.
- `examples.md`: worked examples, and a pointer to a full build script.
- `examples/demo-skid/skid.py`, outside the guide: a whole skid cabinet on demo parts, as a worked design of high-level calls (its README says how to build it).

### Detail and edge cases

- `detail.md`: each `d.detail` call, `W1.core`, fixed terminals and `d.layout` advice, with the cases they are for.
- `drawing.md`: what layout reads, a checklist for a readable cabinet, printed sizes and grid pitch.
- `layout-numbers.md`: every `d.layout.profile` keyword and every `d.layout.sheet` number.
- `readability.md`: `fr.readability`, the per-page and per-unit numbers behind the readability findings.

### Reading a built model

- `reading.md`: reading a built model back: tables, rows, designations and ratings.
- `reading-rows.md`: the column constants, row types, row functions and printed texts of `fr.derive`.
- `reading-records.md`: the record types, lookups and ratings of `fr.derive`.
- `overview.md`: reading the system overview page `write` makes.

### Findings

- `findings.md`: every finding code, what it means and the usual fix, on six pages by source: `findings-validators.md`, `findings-release.md`, `findings-render.md`, `findings-pdf.md`, `findings-kicad.md` and `findings-parts.md`.

### Reference

- `keywords.md`: the signal types, handles, `Severity` and the keywords of the record constructors.
- `keywords-design.md`, `keywords-handles.md` and `keywords-output.md`: one table for each public call, with each keyword's default, effect and an example.
- `kicad.md`: importing a board netlist into KiCad, with the settings to use.

### Moving from an older release

- `moving-to-0.20.md`: the new `fr.rebaseline` call for baselines cut by an older release.
- `moving-to-0.19.md`: the detail calls that moved to `d.detail`, and the rewrite from `d.wire` to `d.series`.
- `moving-to-0.16-and-0.17.md`: what may newly stop a 0.15 or 0.16 build, the changed outputs and the new names.
- `moving-to-0.15.md`: each renamed profile and readability name, the new `releases=` keyword and the system overview's Changes switch.
- `moving-to-0.14.md`: every `fr.derive` name 0.14 removes, and what to use instead.
- `moving-to-0.6.md`: each break from 0.5, with the old spelling, the new one and why.
- `moving-to-fransys.md`: the alias, the pin line, the parts-module command and the intermediates folder for a 0.6.1 consumer of the old name.
