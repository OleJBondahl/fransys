# Part-file contract

Version 1. Parts are data, not code: TOML files in a data package that the loader reads and the
lint checks.

## Purpose and audience

This contract is for someone writing a part library without reading Fransys's source. A part
library is a Python data package of TOML files and no code. This document is enough to write one that
`fransys_parts.load` and `fransys_parts.lint` accept.

## Library layout

```
<library-package>/
  __init__.py
  library.toml
  parts/
    relay-2co-24vdc.toml
    terminal-feedthrough-2_5.toml
    cable-4g1_5.toml
    ...
```

- `__init__.py` carries a one-line docstring and no code: it only makes the directory importable
  by `load(package)`.
- `library.toml` sits at the package root and describes the library as a whole.
- Every part lives in its own file under `parts/`. The loader ignores the filename; a lowercased,
  hyphenated MPN or short description is expected.
- TOML is read with stdlib `tomllib` and `parse_float=Decimal`. No other file format is
  accepted.

## `library.toml` fields

| Field | Type | Meaning |
|---|---|---|
| `schema` | integer | The part-file schema version this library is written against. See "Versioning" below |
| `name` | string | The library's name, recorded on the model so a drawing states which library it used |
| `version` | string | The library's own version, recorded alongside `name` |
| `description` | string | Free text, not read by the loader |

## Part file tables

Every part file carries `schema = 1` at the top, then the tables below. Fields named here match
the model's records (the core kinds and the facets); a field not listed there is out of contract.

Any field below typed as "a `<Name>` value" takes the string value of a member of that enum in
`fransys_model.vocab.enums`. That module is the authority: the allowed-values lists in this
contract are copied from it and can go stale, the module cannot.

### `[part]`

One per file. Maps to the model's `Part`.

| Field | Type | Meaning |
|---|---|---|
| `mpn` | string | Manufacturer part number. The only home of this fact once loaded |
| `manufacturer` | string | |
| `description` | string | |
| `category` | string | A `PartCategory` value: `"electromechanical"`, `"protection"`, `"terminal"`, `"cable"`, `"connector"`, `"plc_module"`, `"board"`, `"generic"` |
| `class_code` | string | 1 to 3 uppercase letters, IEC 81346-2:2019, seeding numbering, e.g. `"K"`, `"Q"`, `"QA"`, `"X"`, `"W"`. The first letter is one of `B C E F G H J K M N P Q R S T U W X`; A, I and O are forbidden and D, L, V, Y and Z reserved (parts lint) |

### `[[function]]`

Zero or more per file, one array entry per function the part has. Maps to the model's
`FunctionTemplate`, with nested `ports` mapping to `PortTemplate` and nested `links` mapping to
`InternalLink`.

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Function name, stamped onto every instance, e.g. `"coil"`, `"co_1"` |
| `kind` | string | A `FunctionKind` value: `"coil"`, `"contact_no"`, `"contact_nc"`, `"contact_co"`, `"protection"`, `"switch"`, `"terminal"`, `"connector"`, `"plc_channel"`, `"supply"`, `"load"`, `"sensor"`, `"actuator"`, `"generic"` |
| `symbol` | string | Optional. Symbol key: a lowercase, hyphenated slug naming a symbol in `electrical-symbols`. A function with no `symbol` gets no authored `layout.symbol_choice`, and the layout engine's rules by kind apply |
| `energy` | string | Optional, on a supply or load function only: `"in"` or `"out"`. Default: load in, supply out. Any other kind fails lint (`ENERGY_ON_NON_POWER`) |
| `ports` | array of tables | See below. At least one entry |
| `links` | array of tables | See below. Optional; omit for a function with no internal connectivity |

`ports` entries:

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The part's own terminal marking, e.g. `"13"`, `"A1"`. Unique within the part, except pins of connectors that print a label. Name a terminal as the device prints it (`IN1+`, `OUT-`); where printed names repeat on the part, by its function, numbered (`L`, `N`, `PE`, `24V1`, `GND1`, `S24V`, `F24V1`) (owner 2026-09-26, parts-0005) |
| `role` | string | A `PortRole` value: `"generic"`, `"internal"`, `"external"`, `"pe"`, or a throw role `"common"`, `"break"` (closed at rest), `"make"` (closed when operated). Every port of a `contact_co` function takes a throw role, whatever its pin name (`CHANGEOVER_ROLE`, decisions model-0091, parts-0007) |
| `symbol_port` | string | Optional. The role-named port of `symbol` this port maps to, e.g. `"in"`, `"out"`. A port with no `symbol_port` keeps its own name. A `symbol_port` on a function with no `symbol` is a lint error (`SYMBOL_PORT_WITHOUT_SYMBOL`). A `contact_co` port takes none: the drawing binds a changeover by its throw roles (`CHANGEOVER_SYMBOL_PORT`) |
| `marking` | string | Optional. What a drawing prints on this pin, when it differs from `name`. Omit it to print `name`; write `""` to print nothing |
| `side` | string | Optional: `"line"` or `"load"`; else the marking fills it (parts-0010) |
| `conductor` | string | Optional: `"L1"`, `"L2"`, `"L3"`, `"N"`, `"L+"`, `"L-"`, `"M"`; not `"PE"` (use `role = "pe"`), filled likewise |

`links` entries:

| Field | Type | Meaning |
|---|---|---|
| `a` | string | A `name` from this function's `ports` |
| `b` | string | A `name` from this function's `ports` |
| `kind` | string | A `LinkKind` value: `"conductive"`, `"switched"` or `"protective"` |
| `rest` | string | Optional, `switched` only: `"open"` or `"closed"` |

A `protective` link is a fuse or breaker, closed in service. It ends the physical net but not the
supply rail (decision model-0122). An overload's main path is `conductive`.

In a `contact_co` function, every `switched` link joins the `common` port to a `break` or a
`make` port (`CHANGEOVER_LINK`).

Rest state (decision parts-0008): a `contact_no` or `contact_nc` may omit `rest` and must agree
if it writes it. A `switch` or `generic` function must write `rest`. Lint, all
`ERROR`: `SWITCHED_LINK_WITHOUT_REST`, `REST_DISAGREES_WITH_KIND`, `REST_ON_UNSWITCHED_LINK`,
`CONTACT_WITHOUT_SWITCHED_LINK`, and `SYMBOL_REST_MISMATCH` (`make-contact` is open and
`break-contact` and `emergency-stop` closed).

### `[[supply]]`

Zero or more per file. Maps to the model's `supply` facet, which allows many per part.

| Field | Type | Meaning |
|---|---|---|
| `supplier` | string | |
| `supplier_part_number` | string | |
| `note` | string | Optional |

### `[footprint]`

At most one per file. Maps to the model's `footprint` facet (subject: `Part`).

| Field | Type | Meaning |
|---|---|---|
| `library` | string | A KiCad footprint library name |
| `name` | string | The footprint's name within that library |

Written into the KiCad netlist as `library:name` (design section 7). `fransys_kicad` writes
this reference; it does not read the footprint itself.

### `[cable_product]`

At most one per file. Maps to the model's `cable_product` facet (subject: `Part`).

| Field | Type | Meaning |
|---|---|---|
| `core_count` | integer | The author's checksum: the lint's `CABLE_CORE_COUNT` compares it with `core_colours`. The model stores no count; it reads `len(core_colours)` (model-0082) |
| `core_colours` | array of strings | One entry per core, in core index order, e.g. `["BN", "BK", "GY", "GNYE"]`. Each is an IEC 60757 colour code: a base code, two base codes joined (`GNYE`), a base code with a number (`BK1`), or `SH` for a shield (model-0070); anything else is an ERROR |
| `gauge_mm2` | string | Cross-section in mm², read as `Decimal` |
| `shielded` | boolean | |

### `[function.protection]`

A `protection` function names its device in `type`: `"fuse"`, `"mcb"`, `"motor_breaker"`,
`"overload"` or `"rcd"`. The loader writes it to `FunctionTemplate.protection_type`, null when absent.
Lint: `PROTECTION_WITHOUT_TYPE` (`WARNING`), `PROTECTION_TYPE_ON_NON_PROTECTION`
(`ERROR`), `PROTECTION_LINK_KIND` (`ERROR`, a
`switched` link) and `SYMBOL_TYPE_MISMATCH` (`ERROR`, a symbol of another type).

Default symbols (layout-0105). A `symbol` on the part or a layout choice always wins.

| Function | Symbol |
|---|---|
| switch, open at rest | `make-contact` |
| switch, closed at rest | `break-contact` |
| `fuse` | `fuse` |
| `mcb`, `motor_breaker` | `circuit-breaker` |
| `overload` | `thermal-overload`, one box per pole |
| `rcd` | `rcd` |
| protection with no type | `circuit-breaker` |

An emergency stop has no default: name `emergency-stop` in `symbol`.

Poles (F4, model-0128). A pole is a switched or protective link, or a protection function's
conductive link. Poles run in natural marking order, line side on top; no side fact keeps marking order.

The `[function.connector]` table is in `part-file-connectors.md`.

### `[function.plc_channel]`

A sub-table of the `[[function]]` entry it describes (P1): a multi-channel PLC module part has
one `[[function]]`, and one `[function.plc_channel]`, per channel. Maps to the model's
`plc_channel` facet (subject: `FunctionTemplate`).

```toml
[[function]]
name = "di_3"
kind = "plc_channel"
ports = [{ name = "3", role = "generic" }]

[function.plc_channel]
signal = "di"
channel = 3
```

| Field | Type | Meaning |
|---|---|---|
| `signal` | string | A `SignalType` value: `"di"`, `"do"`, `"ai_current"`, `"ai_voltage"`, `"ao_current"`, `"ao_voltage"`, `"rtd"`, `"relay"` |
| `channel` | integer | Channel number on the module |

### `[rating]`, `[function.rating]` and `[function.operating]`

`[rating]` (top level, at most one per file) is the part's own rating, e.g. a cable's rated
voltage or a fuse link in its holder; it maps to the `part_rating` facet (subject: `Part`).
`[function.rating]` and `[function.operating]` are sub-tables of a `[[function]]` entry (P1); they
map to the `rating` and `operating` facets (subject: `FunctionTemplate`). `power_loss_w` is the heat given off at the rated load. `resistance_ohm`, `nominal_power_w` and
`nominal_current_a` are stated at `nominal_voltage_v`. No check reads the first two (model-0125, parts-0009).
A part states `power_loss_w` once, in `[rating]` or per function: both is `POWER_LOSS_TWICE` (`ERROR`).
A function takes its template's rating, else its part's, as a whole record: a template rating with only an AC value
hides the part's DC value (decisions model-0079, parts-0004).

```toml
[[function]]
name = "coil"
kind = "coil"
ports = [{ name = "A1", role = "generic" }, { name = "A2", role = "generic" }]

[function.rating]
voltage_ac_v = "250"
```

| Table | Fields, all optional |
|---|---|
| `[rating]`, `[function.rating]` | `voltage_ac_v`, `voltage_dc_v`, `current_ac_a`, `current_dc_a`, `min_breaking_current_a`, `power_loss_w`, `breaking_ac`, `breaking_dc` |
| `[function.operating]` | `voltage_ac_v`, `voltage_dc_v`, `nominal_voltage_v`, `max_voltage_v`, `min_voltage_v`, `capacity_ah`, `max_current_ac_a`, `max_current_dc_a`, `resistance_ohm`, `nominal_power_w`, `nominal_current_a`, `fault_current_ac_a`, `fault_current_dc_a`, `fault_time_constant_ms` |

A breaking list is non-empty. A `breaking_dc` point may add `time_constant_ms`:

```toml
breaking_dc = [{ voltage_v = "1000", current_a = "15000", time_constant_ms = "15" }]
```

`min_breaking_current_a` marks a partial-range fuse (an aBat link): the lowest current it
breaks. It bounds no continuous current. `max_current_ac_a` and `max_current_dc_a` are a source's continuous current limit, charging included (decision model-0088).

Every value is a string in plain decimal notation (digits with an optional fraction), read as
`Decimal`. A rating value is above 0; a `[function.operating]` value
may also be 0 (`"0"`, `"0.0"`: a source's minimum voltage), decision parts-0006. A bare TOML
float is `FLOAT_FORBIDDEN` and an integer is `FIELD_TYPE`. The lint refuses, as `ERROR`, a table
with no field (`RATING_TABLE_EMPTY`) and a value outside those rules, negative or not plain
(`RATING_VALUE_INVALID`). The `RATING_VOLTAGE_BELOW_CIRCUIT` and
`RATING_CURRENT_BELOW_BRANCH` checks read a rating. Of the operating values, only `max_current_*`, `nominal_current_a` and `fault_*` are read. A part
with no current rating limits no branch (model-0088).

### `[pcb]`

At most one per file. Maps to the model's `pcb` facet (subject: `Part`); marks a board part.

| Field | Type | Meaning |
|---|---|---|
| `revision` | string | |

## Rules

- **No floats.** Every table is read with `parse_float=Decimal`. A bare TOML float (`1.5`
  unquoted) is `FLOAT_FORBIDDEN` wherever it sits in the file; write it as a string (`"1.5"`).
- **Quantities are strings read as `Decimal`.** `gauge_mm2` is the example.
- **Lengths are integer millimetres.** A length field is a plain TOML integer.
- **The symbol key is a slug.** `symbol` is lowercase and hyphenated (`"operating-device"`,
  `"change-over-contact"`), naming a key in `electrical-symbols`. `fransys_parts` checks the
  slug's shape only; the layout engine reports an unknown symbol or unbound port.
- **`symbol_port` names a role of the symbol, not a marking of the part.** The symbol knows
  shapes and calls its ports by role (`in`, `out`, `com`, `nc`, `no`); the part knows markings
  and calls the same ports by what is printed on it. `ports.marking` overrides what is printed (design section 6). A changeover binds by its throw roles.
- **Footprint is `library:name`.** Never a bare name.
- **No multi-line strings.** The loader finds a record's line by scanning the file text once for
  table headers (decision parts-0001); a multi-line string could hide a header. No string value
  may contain a line break (lint: `MULTILINE_STRING`, checked on the parsed values).
- **A file that cannot be read is a finding, not a crash.** An unreadable or non-UTF-8 part file is
  `FILE_UNREADABLE`; `lint` and `load_path` still check every other file.

## Worked examples

The files below are the start of the demo part library (`examples/demo-parts/`), the worked
example of this contract and the fixture every test builds on.

`examples/demo-parts/demo_parts/library.toml`:

```toml
schema = 1
name = "demo-parts"
version = "0.1.0"
description = "Invented parts for Fransys's tests and documentation."
```

`examples/demo-parts/demo_parts/parts/relay-2co-24vdc.toml`: a relay with a coil function and two
changeover-contact functions, each contact's `links` marking the switched connectivity inside it:

```toml
schema = 1

[part]
mpn = "DEMO-RLY-2CO-24"
manufacturer = "Demo"
description = "Relay, 2 changeover contacts, 24 V DC coil"
category = "electromechanical"
class_code = "K"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [{ name = "A1", role = "generic", symbol_port = "in" }, { name = "A2", role = "generic", symbol_port = "out" }]

[[function]]
name = "co_1"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    { name = "11", role = "common" },
    { name = "12", role = "break" },
    { name = "14", role = "make" },
]
links = [{ a = "11", b = "12", kind = "switched" }, { a = "11", b = "14", kind = "switched" }]

[[function]]
name = "co_2"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    { name = "21", role = "common" },
    { name = "22", role = "break" },
    { name = "24", role = "make" },
]
links = [{ a = "21", b = "22", kind = "switched" }, { a = "21", b = "24", kind = "switched" }]

[[supply]]
supplier = "Demo Supply"
supplier_part_number = "DS-0001"
```

`examples/demo-parts/demo_parts/parts/terminal-feedthrough-2_5.toml`: a feed-through terminal, one
function with `internal`/`external` ports joined by a `conductive` link, so a wire on either side
is the same net:

```toml
schema = 1

[part]
mpn = "DEMO-TB-2.5"
manufacturer = "Demo"
description = "Feed-through terminal block, 2.5 mm2"
category = "terminal"
class_code = "X"

[[function]]
name = "terminal"
kind = "terminal"
symbol = "terminal"
ports = [
    { name = "internal", role = "internal", symbol_port = "n" },
    { name = "external", role = "external", symbol_port = "s" },
]
links = [{ a = "internal", b = "external", kind = "conductive" }]
```

`examples/demo-parts/demo_parts/parts/cable-4g1_5.toml`: a cable part with no functions of its own; its
cores are conductors created when an item is instantiated as a cable, not functions or ports on the part itself:

```toml
schema = 1

[part]
mpn = "DEMO-CBL-4G1.5"
manufacturer = "Demo"
description = "Control cable, 4 cores including PE, 1.5 mm2"
category = "cable"
class_code = "W"

[cable_product]
core_count = 4
core_colours = ["BN", "BK", "GY", "GNYE"]
gauge_mm2 = "1.5"
shielded = false
```

## Packaging and pinning

A part library is an ordinary Python data package: no build step beyond packaging the TOML
files, no Fransys code inside it.

- **Normal use.** A project pins the library as a git dependency with an exact
  revision: `co-parts = { git = "https://...", rev = "<sha>" }` in its `pyproject.toml`.
  `uv.lock` then pins the resolved commit, so a build needs no access to the library
  repository.
- **While authoring new parts.** The project instead points `[tool.uv.sources]` at a local
  checkout (`co-parts = { path = "../co-parts", editable = true }`), so edits to a part file are
  picked up without a commit and a re-pin. This is switched back to the git form before the
  change ships.
- `fransys_parts.lint` is meant to run in the library's own CI, so a bad part fails there and
  never reaches a project's build.

## Versioning

- `schema` (an integer, `1` today) is the part-file schema version, not the library's own `version`.
  A library can ship many releases against one `schema`.
- A breaking change to this contract (a renamed field, a changed meaning, a removed table) bumps
  `schema`. It is never changed in place under the same number.
- `fransys_parts.SUPPORTED_SCHEMAS: frozenset[int]` names the accepted `schema` values;
  today `frozenset({1})`. `library.toml` and every part file carry `schema`; a value outside
  `SUPPORTED_SCHEMAS` is the lint finding `SCHEMA_UNSUPPORTED`, naming the file and the value
  found, and a part file whose `schema` differs from its `library.toml` is `SCHEMA_MIXED`.
- There is no migration framework. A library bumps `schema` for every part file in one commit.
