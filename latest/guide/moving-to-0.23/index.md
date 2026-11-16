# Moving to 0.23

This page lists what 0.23 adds, what stays refused for now, and the known issues you can meet. Each 0.23 release has its own section below, newest first. Read the BREAKING lines first: they need a change in your part files, calls or stored releases.

## New in 0.23.22

- A position in another PDF leads with that document's short code: `-A2 p7:6C` for a unit document (the unit's designation), `SYS p7:6C` for the system document. The code of the system document is the `[words]` key `system_document_code` (default `SYS`). Another document keeps its scope path. No call gains a keyword.
- With `hide_pe` set, two terminal annexes on a by-others system-document page are no longer left out (KI-1010 closed).
- A shared pole turns once, so the second lane's wired pin no longer faces away from its symbol (KI-753 closed). A fan tap whose rise finds no path is refused alone: the trunk and the other taps stay drawn (KI-991 closed). A crossing lane is no longer dropped from both ends of an arrow at a row cut (KI-992 closed).
- A card box clears the end cell of every lane of its attached column, so it no longer draws inside a longer lane.
- A page holds more cards: the cut forecasts only the flags that stack, so columns that fit the page are no longer folded onto the next (KI-973 closed). A bank of 16 relays takes one page, not two.
- A fallback reference pair stands with the room it asked for (KI-1004 closed).
- A position switch's tag slot stands above its roller and adds no left reach.

## New in 0.23.21

- BREAKING: a stored model of schema 32 or older is refused; the front-page record now holds the diagram sheet count (schema 33). Rebuild stored releases with `fr.release`.
- By-others sets print on the system drawing with no setting on your side: a by-others device wired to one unit no longer appears on that unit's PDF. The system document now holds a schematic section, and a reference into it reads `<design title> p<n>:<cell>`.
- Also in 0.23.20: a page title and its title-page index row name only the groups drawn on that page. A group reached only through a copy or stub keeps its own page's title (KI-986).
- BREAKING: a design that declares a SYSTEM document must set `d.project(...)`, because its heading and the where-texts into it print the project title. 0.23.20 built such a design without a project title; this release refuses it with `SYSTEM_DOCUMENT_NO_PROJECT`.
- A design with by-others devices needs a SYSTEM document, or its by-others set raises `UNPRINTED_SET`.

- `drawn_with=` on `d.device`, `d.terminal_strip`, `d.cable`, `d.harness` and `d.rack` puts a by-others item, and everything under a by-others root, on a unit's PDF: `d.device("M9", None, external=True, pins=("U", "V", "W"), drawn_with=skid)`. It needs `external=True` and a wire to the unit, or the build reports `DRAWN_WITH_UNIT_UNWIRED`. BREAKING: a stored model of schema 33 or older is refused (schema 34); rebuild stored releases with `fr.release`.

## New in 0.23.20

- Page references are right on an A2 cover with a long revision table. 0.23.19 counted its cover pages at A3 and printed every reference one page late.
- The number of extra cover pages depends on the paper: a long revision table flows over more cover pages at A3 than at A2.

## New in 0.23.19

- A cover no longer stops a build: COVER_OVERFLOW is gone. 0.23.18 refused a cover whose revision history had grown (KI-985 closed).
- The revision table stays at the foot of the cover while it fits. Else it follows the text and continues on further cover pages, its header repeated.
- Page numbers and page references count the extra cover pages.
- The notes of 0.23.3 to 0.23.18 are now on this page, one section per release.

## New in 0.23.18

- A join between pins at one level draws as a jog with a dot, not a jumper with no conductor behind it. 0.23.16 and 0.23.17 drew such a join wrongly (KI-737 closed).
- Known issue: a chain or hub can be drawn as ink with no conductor behind it. No shipped check counts it yet.

## New in 0.23.17

- BREAKING: the schema 1 part-file migration is removed: `migrate-parts` and `fransys_parts.migrate` are gone. Rewrite part files to schema 2 with 0.23.16's `migrate-parts` before you upgrade.
- BREAKING: a stored model of schema 31 or older is refused; a box side now writes `source_row` as null (schema 32). Rebuild stored releases with `fr.release`.
- `series(parallel, parallel)` joins the members as a star from the first member of the earlier group, not a cycle. The wire list drops one conductor per latch (KI-976).
- A refused set is refused once: its output steps do not run and it is not checked a second time (KI-799 closed).
- A card's pin pitch is its own pin spacing; the pitch floor is gone.
- Known issue: see 0.23.18 (a chain or hub drawn with no conductor behind it).

## New in 0.23.16

- BREAKING: a protecting device whose conductive link joins pins with no side fails with `PART_POLE_WITHOUT_SIDE` (ERROR). State `side = "line"` or `side = "load"` on each pole pin; for an MCB, pins 1 and 3 are line, 2 and 4 load.
- BREAKING: a fused terminal part that names `symbol=` is refused. Its protective link chooses the symbol, so delete the line. A terminal with a protective link draws as a fused terminal.
- BREAKING: a BOM lists a terminal strip once, not each of its terminals. Read the strip, not its terminals, when you build on the BOM rows.
- BREAKING: a terminal alone in its run, or a gap wider than one pitch from its neighbour, prints its full designation.
- The aspect is refdef's `Aspect` (stored model schema 31); rebuild stored releases.
- A fed end always stands at its last stand, so a refused slot no longer drops a conductor and no connection is missing on the drawing.
- A card keeps only the pieces of a cut column that meet its pins, so no row passes the page. Drawn tags and arrows are the box of their own text.
- A reference marker whose lead would cross a symbol body is not placed there. `WIDER_THAN_PAGE` now names splitting the device or paper A2 as the fix.
- A board that shares a unit is refused with a fix text.

## New in 0.23.15

- A lost conductor lays no trunk, so the three pair-return `CONNECTION_NOT_DRAWN` findings of 0.23.14 are gone.

## New in 0.23.14

- A transformer box, or any symbol whose pins share one chain, no longer fails layout with a cycle error (`PLACEMENT_PROBLEM`).
- Known issue: three pair-return `CONNECTION_NOT_DRAWN` findings are not fixed yet. 0.23.15 fixes them.

## New in 0.23.13

- The by-others frame prints no "by others" text by default. A corner text option comes later.

## New in 0.23.12

- BREAKING: `d.item` and `d.device` refuse a terminal part. The error names `d.terminal_strip`.
- A part's function may state `box_side = "top"` or `"bottom"`, and every pin of it keeps that side. The stored model schema is 29; rebuild stored releases.
- A part chooses the transformer-box symbol, a transformer sign in the psu box, through its `symbol`.
- The fan page draws the wires of an overload's poles; they stay separate drawn nets.
- Known issue KI-874: a starter's side tap is not fixed yet.

## New in 0.23.11

- BREAKING: a port names its physical connector pin with `connector = "j3.1"` in a part file. The stored model schema is 28; rebuild stored releases.
- `hide_pe` leaves out every conductor on the PE net, however it is joined. An earth-joined PE strip that is no declared rail no longer raises a false `CONNECTION_NOT_DRAWN` ERROR.

## New in 0.23.10

- BREAKING: a connector facet in a part file takes `poles`, where it took `pincount`. `pincount` is no longer a key and has no alias; repin your part files.
- A lost link's net keeps one tag lane with a pin on every end, so the layout CoreError that this case raised is gone (KI-777, KI-838 and KI-642 closed).
- A pole's two pins are consecutive on its lane (KI-837 closed).
- External roots are framed with the dashed by-others outline.

## New in 0.23.9

- 0.23.9 was tagged but not published. 0.23.10 carries its content: read the 0.23.10 section for the `poles` rename and the layout fixes.

## New in 0.23.8

- A page cut by height gives each lane it holds one head and one foot, which removes a crash in the join step (KI-836).
- A check now verifies that every drawn reference reads back to its target.
- A poles link rule from elecdef 0.7.0 applies: a link that joins a line pin and a load pin is a set of poles.
- Known issue KI-777: still open, see 0.23.7.

## New in 0.23.7

- The 0.23.5 change to page cutting is withdrawn, because it moved the layout error of KI-777 to a later step. Drawings return to their 0.23.4 form.
- Known issue KI-777: a layout CoreError can occur on the net of a lost link. It is fixed in 0.23.10.

## New in 0.23.6

- With `"ring_out"` in `[export] reports`, `fr.write` writes one ring-out sheet for every PDF document that has drawings, not only for each unit. `ring_out_skip` leaves named document presets without a sheet. See `settings.md`.
- Known issue KI-777: see 0.23.7.

## New in 0.23.5

- A ring-out core row's mm2 is its cable's gauge, read from the cable list row.
- A page cut reads the placed row measure. This is withdrawn in 0.23.7.
- Known issue KI-777: see 0.23.7.

## New in 0.23.4

- BREAKING: `DrawnRow.height_g` and `width_g` are now `height` and `width`; see the section below. Findings print the true G distance, and the guide says to divide by 8 once for millimetres.
- A set whose layout refused returns its pages and rows, so drawn checks can run on it. `fr.write` still refuses.
- A new export kind `ring_out` writes a ring-out sheet for each unit document. It is off by default.
- A page routed again with equal inputs is reused, which speeds up large builds (KI-815 closed).
- Known issue KI-777: see 0.23.7.

## New in 0.23.3

- A far end whose home set failed layout is judged by its drawn copies, so it no longer raises a false missing connection (KI-812).
- Two views of one power pin count as one piece, which removes a false `CONNECTION_NOT_DRAWN` on a power net (KI-813).
- A drawn set is checked exactly when its drawing is complete, so a failed set does not hide findings on the others.
- `HARNESS_WIRE_MISMATCH` compares each cable block with the harness-wire rows.
- Known issue KI-777: see 0.23.7.

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

## A fused terminal part names no symbol

- A fused terminal part no longer names `symbol=`. Its protective link chooses the symbol. Delete the line.

## A supply net behind a fuse prints the fuse

- A supply net behind a fuse or breaker prints its supply name and the tag of the nearest protective device, such as `24V -F2`. The net at the supply keeps `24V`. Two nets that share one name, with no unique protective device between them, raise `RAIL_IDENTITY_SHARED`: put a fuse or breaker between them.

## `DrawnRow.height_g` and `width_g` are now `height` and `width`

- A `Drawing` is in layout units, one eighth of a G, and its rows were always in that unit, so the `_g` suffix was wrong. Rename `row.height_g` to `row.height` and `row.width_g` to `row.width`; the values are the same. An A3 page's `area.w` is 1312.
- A build with a layout ERROR now returns its pages and rows in `result.drawings`, so you can see why; `fr.write` still refuses it.
