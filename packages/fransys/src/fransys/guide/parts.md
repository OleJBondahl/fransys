# Parts

A part library is a Python data package: TOML files describing parts, and no code. Fransys
never reads a spreadsheet or a manufacturer's own format directly; every part your design
uses comes from an installed library written against the part-file contract. This page covers
starting a design from a library, the typed parts module, class codes, linting and load failures. The
contract itself is `docs/contracts/part-file.md` in the Fransys repository, at the tag you
pinned. Read it before you write a library.

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

The `part` argument of `d.device` is a string or a generated class. A string is checked when you
build. Two part names that map to one attribute fail generation.

A function stands in a `d.series` when its line side is known: a coil's A1 and a contact's odd pin give it, else state `side`.

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
building a model: every part file's fields, enum values, port and link shapes, and the
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
library that fails them: it raises `fr.PartLibraryError`, whose `findings` attribute holds
every finding lint collected, warnings included, not only the errors that caused the raise. So
does `fr.design`. A library with a genuine problem (a part file missing its required `[part]`
table, in this made-up example) never reaches your model:

```python
import sys
from pathlib import Path

Path("bad_parts/parts").mkdir(parents=True)
Path("bad_parts/__init__.py").write_text('"""A broken library, for this example only."""\n')
Path("bad_parts/library.toml").write_text(
    'schema = 1\nname = "bad-parts"\nversion = "0.0.1"\ndescription = "missing its [part] table"\n'
)
Path("bad_parts/parts/broken.toml").write_text("schema = 1\n")
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
finding the failed load collected, not only the one that raised, so you can report the library's
whole set of problems at once instead of fixing them one exception at a time.

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
`d.layout.profile(actuator_each_contact=False)` draws one actuator per device: the first block,
11-12, draws the symbol and the list of both contacts; the second draws its break contact with a
reference to the first.

## Ratings from a datasheet

A part's rating fields are read straight off its datasheet, but a battery or cell datasheet
often states its rating as a C-rate against the part's capacity rather than as a current: 1C
on 310 Ah is 310 A. Do that multiplication yourself before writing the part file. A
`[function.operating]` table's `max_current_dc_a` is a current, in amps, never a C-rate.
Fransys stores whatever number you give it and does not compute this conversion.

A protective device's datasheet gives its breaking capacity as points: the voltage, the current it breaks there
and, for DC, the circuit's time constant. A part states them in `[rating]` or `[function.rating]` as `breaking_ac` and
`breaking_dc`. A source's datasheet gives its fault current and time constant in `[function.operating]`.

```toml
# a DC fuse function
[function.rating]
voltage_dc_v = "1000"
current_dc_a = "125"
breaking_dc = [{ voltage_v = "1000", current_a = "15000", time_constant_ms = "15" }]

# a battery function
[function.operating]
nominal_voltage_v = "51.2"
fault_current_dc_a = "6000"
fault_time_constant_ms = "2"
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
voltage_dc_v = "1000"
current_dc_a = "4"
```

`d.rating("DEMO-FUSE-LINK-4A-T")` reads that rating. Put the link in its holder with `parent=`, as `authoring.md`
shows. A link with `min_breaking_current_a` is partial-range and bounds no current.

```python
import fransys as fr

d = fr.design("demo_parts")
rating = d.rating("DEMO-FUSE-LINK-4A-T")
assert rating is not None and rating.current_dc_a == 4
```

## Reading a part's rating while authoring

`d.rating(part, function)` and `d.operating(part, function)` read a rating or operating envelope
from the catalogue. It is a lookup, not a build step. Either gives `None` where the part states nothing.

```python
import fransys as fr

d = fr.design("demo_parts")
part_rating = d.rating("DEMO-TBLK-2P-DUAL")
terminal_rating = d.rating("DEMO-TBLK-2P-DUAL", "terminal")
lamp_operating = d.operating("DEMO-LAMP-24", "lamp")
```

## An accessory in its holder

A part with no function, put in another device with `parent=`, is an accessory. A fuse link in its PCB
holder is one: the link prints `F1` and has no number or row. An authored tag makes it an ordinary item.
`parent=` also takes a terminal strip, for a jumper bar on a bridged run.

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
