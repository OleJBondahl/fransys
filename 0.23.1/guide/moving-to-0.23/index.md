# Moving to 0.23

This page lists what 0.23 adds, what stays refused for now, and the known issues you can meet. No call changes from 0.22.9: no name is added to or removed from the API, and no call needs a new spelling.

## New in 0.23.1

- A PLC channel's signal name and description print in the PLC list only, never at the pins. The pins draw as in 0.23.0. For `.plc(..., description=)` see `moving-to-0.22.md`, New in 0.23.1.

## New in 0.23.0

- By-others outlines: `unit-outline-by-others` draws a unit that others supply as a dashed outline, and `connector-head` is the symbol for a connector head. Both are `electrical_symbols` symbols.
- `WIDER_THAN_PAGE` and `PAGE_OVERFLOW` name the drawing set, the PDF page, the row and its devices, so you can find the overflow.
- A two-pole switch with a pin turned to the far side draws it as a cross-link; before, a second lane could claim the pin.

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
