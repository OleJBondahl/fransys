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

Status: implemented (WP `parts`). See `docs/decisions/parts-0001-loader-and-lint-implementation-choices.md`
for what the spec left open and what this package chose.
