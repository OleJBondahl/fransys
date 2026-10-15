Fransys input: part-file loader and linter.

Input contract: produces a Draft. Every record carries an Origin (file, line). An input never calls freeze().

Turns a part library (TOML files under a `library.toml` root, `docs/contracts/part-file.md`) into
`Part`, `FunctionTemplate`, `PortTemplate`, `InternalLink`, the facets (`supply`, `footprint`,
`cable_product`, `connector`, `plc_channel`, `pcb`, and from the `[rating]`, `[function.rating]` and
`[function.operating]` tables `part_rating`, `rating` and `operating`, decision parts-0004; lint
codes `RATING_TABLE_EMPTY` and `RATING_VALUE_INVALID`; a rating value is positive, an operating
value may be 0, decision parts-0006) and one authored `layout.symbol_choice` per
function that names a `symbol`, selecting by `template` (model decision 0030). Every record's
origin names the part file and the line its table header started on: `tomllib` gives no line
numbers, so `_toml.py` scans a file's text once for its own headers. A `contact_co` port states
its throw role (`common`, `break` or `make`) and no `symbol_port`; lint codes `CHANGEOVER_ROLE`,
`CHANGEOVER_LINK` and `CHANGEOVER_SYMBOL_PORT` (decision parts-0007).
A switched link may state `rest` (`open` or `closed`), a protection function its `type`, and a fuse or
breaker link is `protective`; eight lint codes cover them (decisions parts-0008 and model-0122).
A part states `power_loss_w` once; `POWER_LOSS_TWICE` refuses both the part and a function (decision parts-0009).

- Lint findings are bare (no `Draft` to resolve an origin through), so file and line sit in the
  message text. `FLOAT_FORBIDDEN` and `MULTILINE_STRING` walk the whole parsed tree, unknown
  tables included, and report at the nearest known table header, else line 1. An inline
  `rating = { ... }` table has no header and is reported at its function's line.
- `lint(root)` runs every check in `docs/contracts/part-file.md` (decisions parts-0001 to parts-0004) and returns
  every finding; it never raises, even for a missing `library.toml`.
- `load_path(root)` runs the same checks first; an `ERROR` finding raises `PartLibraryError`
  (`findings` holds every one) and nothing is built. Otherwise it builds the `Draft`, trusting
  what `lint` already checked (no second, weaker validation, decision parts-0001).
- `load(package)` finds an installed data package with `importlib.resources` and calls the same
  code as `load_path`.
- `SUPPORTED_SCHEMAS: frozenset[int]` names the accepted `schema` values (`frozenset({1})`
  today).

## Worked examples

The files below are the start of the demo part library (`examples/demo-parts/`).
It is the worked example of the part-file contract and the fixture every test builds on.

The library file is `examples/demo-parts/demo_parts/library.toml`.

```toml
schema = 1
name = "demo-parts"
version = "0.1.0"
description = "Invented parts for Fransys's tests and documentation."
```

The relay is `examples/demo-parts/demo_parts/parts/relay-2co-24vdc.toml`.
It has a coil function and two changeover-contact functions, each contact's `links` marking the switched connectivity inside it.

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

The feed-through terminal is `examples/demo-parts/demo_parts/parts/terminal-feedthrough-2_5.toml`.
It has one function with `internal`/`external` ports joined by a `conductive` link, so a wire on either side is the same net.

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

The cable is `examples/demo-parts/demo_parts/parts/cable-4g1_5.toml`.
It has no functions of its own; its cores are conductors created when an item is instantiated as a cable, not functions or ports on the part itself.

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

Status: implemented (WP `parts`). See `docs/decisions/parts-0001-loader-and-lint-implementation-choices.md`
for what the spec left open and what this package chose.
