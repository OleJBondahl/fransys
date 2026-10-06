Fransys output: derive rows formatted as CSV.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

Status: implemented. Each name in `__all__` is one report, and `just api fransys-reports` lists them. The CSV reports take a `Model`. How a row becomes CSV is recorded in `docs/decisions/reports-0001-csv-format-rulings.md`. `changes_markdown`/`changes_csv` render a `derive.baseline.diff` result (a `ListingDiff`), not a `Model` (decision reports-0004).

## Rules moved from docstrings

- `_identity`: `units` is `` `<instance>` (<name>) ``; `conductors` and `mates` are `` between `<a>` and `<b>` ``. Every other section is one backticked identity.
- `_bullet`: a single row with `field == ""` and `change != "changed"` is a whole subject added or removed. It prints the identity, then `: <detail>.` when `detail` is non-empty, else a bare `.`.
- `_bullet`: every other group is one `- Changed <identity>: <clauses>.` bullet, clauses joined by `; `. Order: `ports added n, ...` (the rows' `after` values, sorted), `ports removed n, ...` (`before`, sorted), then each `changed` row's `field before to after`.
- `changes_markdown`: the heading names the unit and the two revision texts. The `##` sections run `Items`, `Units`, `Boundary`, `Conductors`, `Mates`, `Nets`, in that fixed order. A diff with no change outside `unit` is the heading, the interface line and `No changes.`.
- `terminal_csv`: the header is `designation,group,index,side_a,side_b,jumper_group`. A jumper partner stays in its ends column; `jumper_group` names the bridge.
- `terminal_csv`: with `context`, an end inside the location prints short (`-B12:2/T1`) and one outside prints its location path first (`+EXT-M1:U1`). `None` prints every located end with its full path.
- `plc_csv`, `connectors_csv`: `context` works as in `terminal_csv`. For `connectors_csv` it applies to mate pins.
- `bom_csv`: `scope` restricts as `bom_lines` does. An item counts itself and its descendants. A location node counts the items at or below it. A unit counts its own items plus one line per unit instance directly nested in it (units spec U5). `derive.TOP_LEVEL` does the same at the top level.
- `cables_csv`: a harness cable is included the same as a loose one (`cable_list_rows`'s rule). It has no `unit=`, since a cable scoped to a unit would always be empty.
