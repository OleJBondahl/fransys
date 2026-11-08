# Moving to 0.22

This page lists each call that 0.22 adds, changes or removes, with the old spelling and the new one.

## Rating is the elecdef Rating

`fr.derive.Rating` is removed, with `BreakingPoint` and `effective_rating`. A rating is a `fr.elecdef.Rating`: its voltage and current are tuples of `fr.elecdef.Range`, each with the current kind in `at`.
`Rating(voltage_ac_v=Decimal(250))` becomes
`fr.elecdef.Rating(voltage=(fr.elecdef.Range(fr.elecdef.Role.RATED, nom=fr.elecdef.Unit.V(250), at=fr.elecdef.At(fr.elecdef.Current.AC)),))`.
The rating has no breaking fields: a breaking figure is in the function's `[function.block]`
(`breaking_capacity` for a fuse; `icn`, `icu` and `ics` for a breaker). A fuse link with no function states a breaking minimum in its part-level `[block]`.

## Operating has Range and Quantity fields

`fr.derive.Operating` keeps its name. `voltage_ac_v`, `voltage_dc_v`, `nominal_voltage_v`, `min_voltage_v` and `max_voltage_v` are one `voltage` tuple of `Range`
(a nominal with a window is one `Range` with `nom`, `min` and `max`). `max_current_ac_a` and `max_current_dc_a` are `max_current`;
`fault_current_ac_a` and `fault_current_dc_a` are `fault_current`. The rest drop the unit suffix and hold a `fr.elecdef.Quantity`,
for example `fault_time_constant=fr.elecdef.Unit.MS(15)`. In a part file the keys are the same names; see `parts.md`.

## Current comes from elecdef

The AC/DC enum is `fr.elecdef.Current` (`Current.AC`, `Current.DC`). The old model enum is gone; the authoring string `current="ac"` is unchanged.

## A rail is declared

Bridged DC or PE strips are no longer rails: add `rail=True` to the bridged `run` or `d.terminal_strip` that is the rail. An unflagged terminal draws as a terminal, and `d.detail.rail_bond` is gone with the `rail` link kind.

## Removed in 0.22

Each row is a name that 0.22 removed. A removed attribute raises an error that names its row here.

| 0.21 spelling | 0.22 spelling |
|---|---|
| `fr.ABOVE`, `fr.BELOW`, `d.layout.side(target, fr.ABOVE)` | Removed on purpose: Fransys decides (R1486) |
| `fr.IT`, `fr.EARTHED` | Removed on purpose: Fransys decides (R1494); supplies are the earthed default only |
| `fr.BuildErrors` | `fr.BuildFailedError`, e.g. `except fr.BuildFailedError:` |
| `fr.MergeConflict` | `fr.MergeConflictError`, e.g. `except fr.MergeConflictError:` |
| `d.busbar(a, b)` | `d.detail.busbar(a, b)` |
| `d.rating(part, function)`, `d.operating(part, function)` | Removed on purpose: Fransys decides (R1490); read part data through the part's elecdef `Rating` |
| `d.detail.wire(a, b, wire=w, label=, n=)` | `d.series(a, b, wire=w)`; `label=` and `n=` have no replacement |
| `d.detail.star(src, targets, wire=w)` | `d.series(src, t, wire=w)` for each target |
| `d.detail.net(name, *pins, kind=)` | Removed on purpose: Fransys decides (R1490); connect with `d.series(a, b)` |
| `d.detail.rail_bond(a, b)`, link kind `rail` | Declare the rail with `rail=True`; bond PE with `d.series(incoming_pe, pe, wire=(GNYE, 1.5))` |
| `d.layout.chain(*functions, beside=...)` | Removed on purpose: Fransys decides (R1490); `d.series` names the path |
| `d.layout.page_title(thing, text)` | Removed on purpose: Fransys decides (R1490); the default page title stays |
| `d.layout.symbol(target, symbol, port_map)` | `symbol = "..."` on the part file's `[[function]]` entry |
| `d.layout.break_before(group)` | Removed on purpose: Fransys decides (R1490); order with `d.layout.order(*groups)` |
| `d.layout.keep_together(*groups)` | Removed on purpose: Fransys decides (R1490) |
| `d.layout.draw_in(function, group)` | Removed; `d.series` and `group=` place the function |
| `d.layout.pins_below(box)` | Removed on purpose: Fransys decides (R1490); `hide_unused_pins=True` stays |
| `d.layout.profile(sheet=, column_gap=, row_gap=, row_spacing=, route_margin=, text_height_mm=, min_text_height_mm=, marker_padding=, route_turn_penalty=, route_crossing_penalty=, actuator_each_contact=, band_ranks=, group_ranks=)`, `d.layout.sheet(name, ...)` | `d.layout.profile(hide_unused_pins=False)` is the only keyword left; order groups with `d.layout.order(*groups)`; paper with `fr.settings(paper=...)` |
| `@fr.unit(..., wiring={...})` | Removed on purpose: Fransys decides (R1493); per-wire colour: `d.series(a, b, wire=(BU, 0.75))` |
| `fr.unit(..., class_code="K")`, `d.add(defn, None)` | `d.add(board, "U1")`: an authored tag, a bare string; `None` is no longer allowed |
| `[font.heights]` in the settings file | Removed on purpose: Fransys decides (R1458); delete the table |
| `text_height_mm`, `min_text_height_mm`, `TEXT_TOO_SMALL` | Removed on purpose: Fransys decides (R1458); text heights are fixed library data |
| `fr.document(..., add=, remove=)`, presets `HARNESS_DRAWING`, `PCB_SCHEMATIC` | `fr.document(preset, subject, cover=, logo=, notice=)`; the preset sets the pages. `remove=(fr.PageKind.SHEET_INDEX,)` and every other `remove=` has no replacement: a preset prints its fixed pages |
| `d.add(defn, tag, unused=(...))` | `d.device(tag, part, unused=True)` for the unit's own open pins; `d.unused(pc.x3[3], pc.x4_1)` in the carrier for a unit's boundary points it leaves open (0.22.3) |
| `Port.role` (`PortRole`) | `Port.boundary` (`fr.derive.PortBoundary`), and new `Port.pin_role` |
| `Cable.core(which, a, fn)` with a PE-bar function | Use a PE terminal strip: `W1.core(GNYE, x1[1].outer)` |
| `DrawnReading.units` | No change: the name never existed at either version; the unit is `DrawnPageReading.unit` per page |
| `Fn.limits(rating=, operating=)`, `Terminal.limits(...)` | Removed on purpose: Fransys decides (R1490) |
| Mated connector, PCB board document, harness line | Refused with ERROR `MATES_DISABLED` (R1216); draw the connection as a cable or wires |
| Terminal part with more than two pins | Refused with ERROR `TERMINAL_MORE_THAN_TWO_PINS`; use a two-pin part: `d.terminal_strip("X1", "DEMO-TB-2.5", 2)` |
| `[colours]`, `[grid]`, `[layout]`, `[profile]`, `[pdf]`, `[look]`, `[lines]`, `[dash]`, `[reference]`, `[frame]`, `[stub]`, `[wire_label]`, `[harness]`, `[title_block]`, `[revision_table]`, `[revision]`, `[designation]` | Removed on purpose: Fransys decides (R1458); a `SettingsError` names the table; delete it |
| Part schema 1 (`schema = 1`) | `schema = 2`; convert with `python -m fransys migrate-parts DIR` |
| `TERMINAL_POINT_OVERFILLED` (new in 0.22, no 0.21 spelling) | Set `conductors_per_clamp = 2` in the terminal part's `[connection]` table, or use a twin part, or bridge a second terminal |

## New in 0.23.1

- `.plc(..., description="...")` gives a PLC channel a line of text. The PLC list prints it in a `description` column beside the signal name (PDF and `plc.csv`, which gains the column). The description lives in the PLC list only, and the Wago rack XML is unchanged. A blank description raises. listing_version 9: no listing text moves; a stored model of schema 25 is refused: rebuild it.

## New in 0.22.9

- The Wago rack XML `<Modules>` follows the CDP reference, so every consumer's file changes. A module is named `<order>_<channels><kind>_<letter>` with the kind DI, AI, DO or AO (an RTD is AI, a relay output DO, an analogue output AO). A module whose channels mix kinds is named by the bare order number. A channel is named by its bare signal name, else `<kind><Nr>` (DO0, DI14). An analogue channel has no `Nr`. A mixed module lists outputs first and restarts `Nr` for each direction (decision wago-0003).
- New spellings: `.plc(signal, name, routing=)`, `.plc(name=)` and `.plc(configured=False)` on a module's channel handle, `.scale(raw=, eng=)` with no unit, and `.scale(...)` on a spare analogue channel. `SCALING_UNIT_EMPTY` is gone: a blank unit raises at the call. `PLC_SIGNAL_NAME_TWICE` is new.
- Page text: pages replace sheets. The title block shows "page m of N" and has no sheet cell. A reference prints the page number alone (`p<n>:<cell>`), led by the far PDF's scope path across PDFs. The PDF order is the cover, the drawings, then the index and the lists. Drawings can move: the wider reserved reference text re-lays out some pages.
- listing_version 8: no listing text moves. A stored model of schema 24 is refused: rebuild it. A wire made inside a `d.function` block now carries that block. A pin wired only in one other block that draws a function of its own is drawn there. A terminal, supply, connector or PLC channel stays with its item (decision model-0442).
- Tags stand at a symbol corner, top-left first, then bottom-left, top-right, bottom-right, one grid step out, then turned. Tags move on many pages; nothing to change in your code.
- A unit's drawing no longer changes with the names of the units above it.
- `OVERLAP` now also counts text resting on a wire's edge and diagonal runs. A new `OVERLAP` WARNING is a Fransys looks defect: report it.
- Fixed: phantom loops around a part's internal links with no conductor (KI-732), and a trunk drawn through a neighbouring card (KI-731).
- Fixed: a connection lost when a net crossed a page cut twice, as with two output cards (KI-739), and a reference leg starting inside its trunk (KI-736).

### Known issues in 0.22.9

- `MARKER_UNPLACED` on a 40-circuit demo-flags build leaves one tag marker unplaced at two salts. It is old (KI-745) and fixed in 0.23.1.

## New in 0.22.8

- One `terminals.csv` holds every terminal strip, and one `connectors.csv` every board. They replace the files per strip or board: read the one file instead (decision model-0437).
- `[export] hide_pe = true` leaves the PE rail's wires and the PE symbols on device pins, with their markings, off every drawing sheet; the lists keep them. A flagged PE terminal never draws. Off by default: drawings do not change (decisions model-0435, el-0119).

## New in 0.22.7

- A leg's run is cleared of a footprint's pin tips. Only the PE terminal joined by `d.earth` stops being a spare. The shorts this drew there (`DRAWING_SHORTS_NETS`) are gone (KI-708, layout-0446, model-0429). No action.
- A copied cut piece joins no pins: its ends pair two by two (KI-710). No action.
- `OVERLAP`, `WIRE_OVER_MARKER` and the width refusal name the elements and the fix. The guide gained the width table, net rows, bare-pin use and the full-cabinet path. No action.

## New in 0.22.6

- A revision cut by 0.22.4 or earlier reads again, with no rebaseline needed. `fr.verify` finds nothing to report. `fr.release` cuts the next revision, also for a container that pins such a revision (decisions model-0289, model-0428).

## New in 0.22.5

- listing_version 7: a list end prints the pin's marking when it is set and unique under its printed prefix, else its name (decisions model-0428, model-0431).
- 0.22.5 cannot read a revision cut by 0.22.4 or earlier: `fr.verify` reports `BASELINE_TOO_OLD`, and `fr.release` and `fr.rebaseline` refuse. Stay on 0.22.4 to release; 0.22.6 reads them again.
- A connected cable screen (`core(SH, ...)`, `spare(SH, at=...)`) is refused with `SCREEN_DISABLED` until screen connections return; the cable heading still prints "shielded" (decision model-0430).

## New in 0.22.1

- `python -m fransys migrate-parts DIR` rewrites a schema 1 parts library to the 0.22 format (decision 0474). `DIR` is the library's folder (the one holding `library.toml` and `parts/`) or a folder above it, never `parts/`.
- A removed 0.22 name raises an error that names the new spelling and the row above, from one table that is deleted at the 0.23 tag (decision 0475).

## New in 0.22.3

- `d.unused(pc.x3[3], pc.x4_1)` declares a nested unit's boundary points, or a port, that the design leaves open on purpose (decision 0481). The unit's own `unused=` stays the unit's fact. It reverses the `add(unused=)` part of the 0.22 removal.
- Two ERROR codes check it: `UNUSED_NOT_BOUNDARY` and `UNUSED_POINT_WIRED`; a point listed twice raises an `AuthorError`.

## New in 0.22.2

- The per-channel engineering range returns as `.plc(...).scale(unit, raw=, eng=)`, written to the Wago rack XML exactly as in 0.21.2 (decision model-0425).
- Three ERROR codes check it: `SCALING_RANGE_INVALID`, `SCALING_NOT_ANALOGUE` and `SCALING_UNIT_EMPTY`.
