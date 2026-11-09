# Moving to 0.23

This page lists what 0.23 adds, what stays refused for now, and the known issues you can meet. No call changes from 0.22.9: no name is added to or removed from the API, and no call needs a new spelling.

## New in 0.23.2

- After a layout ERROR in one drawing set, the drawn-page checks (CONNECTION_NOT_DRAWN, OVERLAP and the rest) still run on the other sets; 0.23.1 skipped them all. The ERROR says its set is not drawn. `fr.write` still refuses.

## New in 0.23.1

- A PLC channel's signal name and description print in the PLC list only, never at the pins. The pins draw as in 0.23.0. For `.plc(..., description=)` see `moving-to-0.22.md`, New in 0.23.1.

## New in 0.23.0

- By-others outlines: `unit-outline-by-others` draws a unit that others supply as a dashed outline, and `connector-head` is the symbol for a connector head. Both are `electrical_symbols` symbols.
- `WIDER_THAN_PAGE` and `PAGE_OVERFLOW` name the drawing set, the PDF page, the row and its devices, so you can find the overflow.
- A two-pole switch with a pin turned to the far side draws it as a cross-link; before, a second lane could claim the pin.

## Part-file key renamed

- A port of a role function names its physical connector pin with `connector = "j3.1"`. Its list text is the connector's pin; the stored model schema is 28, so rebuild every release with this build.
- A part function may state `box_side = "top"` or `"bottom"` to put its pins on that side of its box. The stored model schema is 29, so rebuild every release with this build.
- `[function.connector]` states `poles = 4` where it stated `pincount = 4`. A part file that still says `pincount` is refused with `FIELD_UNKNOWN` (ERROR); there is no alias. `poles` below 1 is refused with `FIELD_TYPE`, in elecdef's words. `gender` keeps its spelling.
- A stored model of schema 26 or older is refused, and the message says to rebuild the release with `fr.release`. Nothing is migrated. The listing version is now 10; a stored listing of version 6 to 9 still reads.

## Still refused, for now

- Mated connectors, PCB board documents and harness lines raise an ERROR. A board unit draws as an ordinary unit.
- A terminal with more than two pins raises an ERROR.
- A cable screen connection (`core(SH, ...)`, `spare(SH, at=...)`) raises `SCREEN_DISABLED`; the cable heading still prints "shielded".

## Known issues in 0.23.0

- KI-745: a side tag marker can be left unplaced (`MARKER_UNPLACED`) on a large page of many circuits. A fix is in progress and ships in the release after it lands.
- KI-749: `CONNECTION_NOT_DRAWN` or `MARKER_UNPLACED` on a page that also has `PAGE_OVERFLOW`. Fix the overflow first; the others follow it.
- KI-757: a wide marker on a page that does not overflow can leave `CONNECTION_NOT_DRAWN`.
- KI-759: a very large two-pole switch fan (24 or more chains per pole) can leave `CONNECTION_NOT_DRAWN` and `DANGLING_WIRE_END`.
- KI-762: a hub alone on a page or in a short row can lose a tag pair (`MARKER_UNPLACED`), and a `CONNECTION_NOT_DRAWN` can follow. A fix is in progress and ships in the release after it lands.
- KI-746, KI-747: a tag or `WHERE` marker text can overlap a wire or a slot text (`OVERLAP`, looks only).
- KI-748: the `OVERLAP` message does not name both elements yet.

## A supply net behind a fuse prints the fuse

- A supply net behind a fuse or breaker prints its supply name and the tag of the nearest protective device, such as `24V -F2`. The net at the supply keeps `24V`. Two nets that share one name, with no unique protective device between them, raise `RAIL_IDENTITY_SHARED`: put a fuse or breaker between them.

## `DrawnRow.height_g` and `width_g` are now `height` and `width`

- A `Drawing` is in layout units, one eighth of a G, and its rows were always in that unit, so the `_g` suffix was wrong. Rename `row.height_g` to `row.height` and `row.width_g` to `row.width`; the values are the same. An A3 page's `area.w` is 1312.
- A build with a layout ERROR now returns its pages and rows in `result.drawings`, so you can see why; `fr.write` still refuses it.
