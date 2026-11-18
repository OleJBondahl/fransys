# Parts

A part library is a Python data package: TOML files describing parts, and no code. Fransys
never reads a spreadsheet or a manufacturer's own format directly; every part your design
uses comes from an installed library written against the part-file contract. This page covers
starting a design from a library, the typed parts module, class codes, linting and load failures. The
contract itself is the "Part file contract" page of the site, at the version you
installed. Read it before you write a library.

## Starting a design

`fr.design` takes the import names of one or more installed part-data packages and returns a
design `d` with every part, function and port of those libraries loaded. A device names its
part by manufacturer part number (MPN), as a string. This is the data-driven path: the part
list can come from a table or a file.

```python
# easy: start a design
import fransys as fr

d = fr.design("demo_parts")
d.device("H1", "DEMO-LAMP-24")
d.device("H2", "DEMO-LAMP-24")
```

A part is either a typed object from the generated parts module or an MPN string. That is one
argument of `d.device`, not two spellings of one task. Use the typed object when you write the
part by hand and want completion and checking, and the string when the MPN comes from data.
Two parts with one MPN from two makers have no spelling in this release.

## The typed parts module

The generator writes one Python module for a library: a class per part, with its functions and
pins as typed attributes. Your editor then completes `H1.lamp[1]` and flags a pin the part does
not have. Regenerate the module whenever the library changes. Run this from a shell:

```text
python -m fransys parts-module demo_parts demo_typed.py
```

`fr.parts_module("demo_parts")` returns the same module as text, when a script writes the file itself.

A library written in schema 1 (0.21) is refused with `PART_SCHEMA_OLD`. Rewrite each part file and `library.toml` to schema 2 by hand and set `schema = 2`; the converter was removed in 0.23.

The part library generates this module and ships it, and the projects that use the library import it
rather than generate their own. A pin whose marking is not a Python name gets an attribute by the
one name rule (authoring.md): the pin `1/L1` is `k.main.P_1_L1` and `24V1` is `psu.P_24V1`, each checked by ty.
The pin is also `k.main["1/L1"]`. Pass `interface=` a tuple of the part's function names and a
misspelt name is a ty error.

The `part` argument of `d.device` is a string or a generated class. A string is checked when you
build. Two part names that map to one attribute fail generation, and so do two pins of one function.

A function stands in a `d.series` when its line side is known: a coil's A1 and a contact's odd pin give it, else state `side`.

```toml
[[function.port]]
name = "output_1"
side = "line"
```

`side` is `line` for the pin that stands toward the supply, or `load`. A two-pin output with no `side` is wired pin by pin: `d.series(f.output_1, x1[3], wire=(BU, 0.75))`.

A pin that sources a wiring row, such as a drive's `U`, `V` and `W` outputs, states it with `source_row = "AC_L1"` (any `WiringRow` name). A `d.series` wire from that pin then takes the row's colour without `wire=`.

The module records the library's digest. `fr.design(P, ...)` compares that digest with the
library it loads and raises an error naming the command above when the module is stale. A
whitespace edit in a part file is not stale; any changed fact is. The efficient level of the
task builds the same model with the typed module and a loop:

```python
# efficient: start a design
import subprocess
import sys

import fransys as fr

subprocess.run(
    [sys.executable, "-m", "fransys", "parts-module", "demo_parts", "demo_typed.py"], check=True
)
sys.path.insert(0, ".")
import demo_typed as P

d = fr.design(P)
for tag in ("H1", "H2"):
    d.device(tag, P.DEMO_LAMP_24)
```

## Class codes

A part's `class_code` seeds its printed designation (`-Q1`, `-Q2`). Recommended codes, IEC 81346-2:2019:

| Object | Code |
|---|---|
| Contactor, main switch, switch-disconnector | Q |
| Fuse, MCB (protection) | F |
| Relay, PLC coupler and modules, network switch | K |
| Overload relay, sensor, current transformer | B |
| Signal lamp, meter, display | P |
| Terminal, terminal strip | X |
| Plug, socket, board header (connector) | J |
| Power supply, transformer | T |
| Motor, solenoid actuator | M |
| Suppressor diode, resistor | R |
| Board (PCB), rack | U |
| Cable, harness | W |
| Heater | E |
| Push button, selector, emergency stop | S |

A board with several connectors whose pins repeat (`P01` on each) models one function per connector (kind `connector`); a list end then reads `-U2-J3:P04`.

A connector function states its shape in `[function.connector]`:

```toml
[function.connector]
style = "header-4p"
poles = 4
gender = "female"
```

`style` and `poles` are required. `gender` (`male`, `female` or `genderless`) is optional; absent means the part does not state it. `marking` and `mates` are optional. `poles` is the elecdef `Connector` field of that name; `pincount` is no longer a key (decision model-0446).

## Loading a library without a design

`fr.parts` takes the same import names and returns a single `Draft` holding every part,
function, port and facet record, each carrying the file and line it came from. Use it to lint a
library or build without a design:

```python
import fransys as fr

parts = fr.parts("demo_parts")
```

Loading several libraries together, as in `fr.design("a", "b")` or `fr.parts("a", "b")`,
merges them into one library.

## Linting a library

`fr.lint(*libraries)` checks one or more libraries against the part-file contract without
building a model. It checks every part file's fields, enum values, port and link shapes, and the
cross-file rules (duplicate parts, duplicate connector labels, and so on), collected as
`Finding`s.

```python
findings = fr.lint("demo_parts")
assert not [f for f in findings if f.severity is fr.Severity.ERROR]
```

The argument is the library's import name, resolved exactly as `fr.parts` resolves it: an
installed package's own root, the directory that directly holds `library.toml`. For the demo
library that is `demo_parts`, the inner package, never `examples/demo-parts`, the outer
project folder that merely contains it (and holds the package's own `pyproject.toml`, not a
part file). Passing the project folder's name is the mistake to watch for. `fr.lint` and
`fr.parts` both want the package's own name, the same one you would give `uv add` or an
`import` statement.

## When a library fails to load

`fr.parts` runs the same checks `fr.lint` does before it builds anything, and refuses to load a
library that fails them. It raises `fr.PartLibraryError`, whose `findings` attribute holds
every finding lint collected, warnings included, not only the errors that caused the raise. So
does `fr.design`. A library with a genuine problem (a part file missing its required `[part]`
table, in this made-up example) never reaches your model.

```python
import sys
from pathlib import Path

Path("bad_parts/parts").mkdir(parents=True)
Path("bad_parts/__init__.py").write_text('"""A broken library, for this example only."""\n')
Path("bad_parts/library.toml").write_text(
    'schema = 2\nname = "bad-parts"\nversion = "0.0.1"\ndescription = "missing its [part] table"\n'
)
Path("bad_parts/parts/broken.toml").write_text("schema = 2\n")
sys.path.insert(0, ".")

try:
    fr.parts("bad_parts")
except fr.PartLibraryError as e:
    assert e.findings[0].code == "FIELD_MISSING"
else:
    raise AssertionError("expected PartLibraryError")
```

Catch `fr.PartLibraryError` around a load whose library you do not control yourself: one built
by a separate team or vendor. An uncaught `PartLibraryError` already stops your script right
there, with Python's own one-line traceback. Catching it instead gets you `e.findings`: every
finding the failed load collected, not only the one that raised. You can then report the library's
whole set of problems at once instead of fixing them one exception at a time.

## A module's catalogue wording

A PLC module part may state `catalogue_description = "2-channel analog input; For Pt100/RTD resistance sensors"` in `[part]`: the maker's catalogue text, apart from `description`, which stays BOM text. The Wago rack XML writes it as the module's `Description`; a part without it writes `description`.

## A contact a person or a machine operates

A push button, an emergency stop, a selector or a limit switch states what operates its
contacts in `[part]`: `operated_by = "push"`, `"mushroom"`, `"turn"` or `"position"`. Its
contacts are `switch` functions, and the drawing picks the symbol from the operator and the
rest state: a push button closed at rest draws `push-button-break`. A part that wants one
actuator over several contacts states one `switch` function per contact.

A complete device, such as a limit switch, states it on itself. A head sold apart from its
contact blocks states it and has no function. Each block holds one `switch` and joins the head
with `parent=`:

```python
s1 = d.device("S1", "DEMO-HEAD-ESTOP")
first = d.device(None, "DEMO-BLOCK-1NC", name="nc-1", parent=s1)
second = d.device(None, "DEMO-BLOCK-1NC-21", name="nc-2", parent=s1)
```

Both blocks print `-S1`, and each draws the emergency-stop symbol.

## A transformer drawn as a box

A transformer part states `symbol = "transformer-box"` on its primary and its secondary function. Each function names only its own pins with `symbol_port`: `p1` and `p2` for the primary, `s1` and `s2` for the secondary. The item then draws as one box with a two-winding sign, the primary pins above and the secondary pins below. A part without `symbol` draws as before.

## Ratings from a datasheet

A part's rating fields are read straight off its datasheet. But a battery or cell datasheet
often states its rating as a C-rate against the part's capacity rather than as a current: 1C
on 310 Ah is 310 A. Do that multiplication yourself before writing the part file. A
`[function.operating]` table's `max_current` is a current figure in amps, never a C-rate.
Fransys stores whatever number you give it and does not compute this conversion.

A protective device's datasheet gives its breaking capacity as points: the voltage, the current it breaks there
and, for DC, the circuit's time constant. A part states them as the `breaking_capacity` list of a function's `[function.block]`.
Each figure has `max` and the conditions it holds `at`, such as `["DC", "1000 V", "15 ms"]`. A figure with only `min` gives the
lowest current a partial-range fuse breaks. A breaker (`type = "mcb"` or `"motor_breaker"`) states `icn`, `icu` and `ics`, each one
figure, instead of the list. A source's datasheet gives its fault current and time constant in `[function.operating]`.

```toml
# a DC fuse function
[function.rating]
voltage = [{ nom = "1000 V", at = ["DC"] }]
current = [{ nom = "125 A", at = ["DC"] }]

[function.block]
type = "fuse"
breaking_capacity = [{ max = "15000 A", at = ["DC", "1000 V", "15 ms"] }]

# a battery function
[function.operating]
voltage = [{ nom = "51.2 V", at = ["DC"] }]
fault_current = [{ max = "6000 A", at = ["DC"] }]
fault_time_constant = "2 ms"
```

A replaceable part, such as a fuse link in its holder, is its own part file. It states a top-level
`[rating]` and has no `[[function]]`. The holder keeps the pads and the footprint.

```toml
[part]
mpn = "DEMO-FUSE-LINK-4A-T"
manufacturer = "Demo"
description = "Replaceable fuse link for a PCB holder, 4 A time-lag, 1000 V DC"
category = "protection"
class_code = "F"

[rating]
voltage = [{ nom = "1000 V", at = ["DC"] }]
current = [{ nom = "4 A", at = ["DC"] }]
```

Put the link in its holder with `parent=`, as `authoring.md`
shows. A link states a breaking minimum only in a part-level `[block]`: it takes none from its holder, and bounds no current.

## An accessory in its holder

A part with no function and no footprint, put in another device with `parent=`, is an accessory. A fuse link in its PCB
holder is one: the link prints `F1` and has no number or row. An authored tag makes it an ordinary item.
`parent=` also takes a terminal strip, for a jumper bar on a bridged run.

An untagged device with `parent=` and `unused=True` is an accessory whatever its part holds, a function or a footprint.
It prints its holder's designation and has no row or netlist line, and draws nothing. One BOM line counts the part's tagged and accessory uses.

```python
import fransys as fr

d = fr.design("demo_parts")
f1 = d.device("F1", "DEMO-FUSE-HOLDER-PCB")
link = d.device(None, "DEMO-FUSE-LINK-4A-T", name="link", parent=f1)
x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
x1.run("L", 3, bridged=True)
bar = d.device(None, "DEMO-JUMPER-BAR-3P", name="bar", parent=x1)
model = fr.build(d).model
assert fr.derive.item_designation(model, link.id) == "F1"
assert fr.derive.item_designation(model, bar.id) == "X1"
```

The BOM prints one line per part: count is its installed items, designations are the holders'. F1 is shown; with F2 alike, four bars give one line for the bar part, count 4, F1 F2; a name is unique, and the bars draw nothing.

```python
import fransys as fr

d = fr.design("demo_parts")
f1 = d.device("F1", "DEMO-FUSE-HOLDER-PCB")
d.device(None, "DEMO-JUMPER-BAR-3P", name="f1_bar_a", parent=f1)
d.device(None, "DEMO-JUMPER-BAR-3P", name="f1_bar_b", parent=f1)
```

## How many conductors a terminal point takes

A terminal part states the conductors each point takes in a `[connection]` table, `conductors_per_clamp = 2`. An unstated count is 1.

A point with more wires and cable cores than that is an ERROR, `TERMINAL_POINT_OVERFILLED`. Bridges do not count. Fix it with a part that takes more, such as `DEMO-TB-2.5-TWIN`, or bridge a second terminal to this one.

```toml
[connection]
conductors_per_clamp = 2
```

## The marking printed for a port

A `[[function.port]]` has a `name` and may state a `marking`. The marking is the text printed for the port; from 0.22.5 it prints on the drawing and in every list. A port without `marking` prints its `name`, here `port_4_1`. A short label on the as-built part is a `marking`; set it on every port that has one.

```toml
[[function.port]]
name = "port_4_1"
marking = "1"
```

This port prints `1`, not `port_4_1`. A role function (plc_channel, supply, load) prints the marking of its port and no connector designation. 

A port of a role function names the connector pin it sits at. The key reads like `joins`: a connector function of the same part, a dot, the pin.

```toml
[[function.port]]
name = "A1"
connector = "j3.1"
```

This port prints as pin `1` of connector `j3`, for example `-U2-J3:1`. The pin is one of the connector's `poles`. One port names it. A header pin does not also `joins` the port. `PORT_PIN_NOT_ON_CONNECTOR`, `PORT_PIN_TAKEN` and `PORT_CONNECTOR_AND_JOIN` (ERROR) refuse the rest. `connector` closes no net; `joins` does.

## One side of the box for every pin

A function drawn as a generic box splits its pins over the top and the bottom. A part pins every pin of a function to one side with `box_side`, whatever the pin count:

```toml
[[function]]
name = "io"
kind = "load"
box_side = "top"
ports = [{ name = "p1", role = "generic" }, { name = "p2", role = "generic" }]
```

`box_side` is `top` or `bottom`. Any other value is an `ENUM_VALUE` error that names the function.

It decides before the power rule and the halves. A function without it keeps them.
