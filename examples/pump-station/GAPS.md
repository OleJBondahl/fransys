# Gaps

The places where this example is not drawn or authored the way a real cabinet would be, because
Fransys, at the pinned v0.13.3 line, cannot say it yet. Open gaps come first, then the closed ones
with the version that closed them. Evidence is in the three `out/` folders: `out/cabinet/` (the
cabinet unit's set), `out/board/` (the relay board's) and `out/all/` (everything, with the system
document). A `wires.csv` row lists its two ends in the model's id order, so its order can
flip when an authoring key changes. `fr.check` on this build holds 0 ERROR and three WARNING, the
layout warnings of G29.

## Open

- **G5.** `fr.check` gives 5 `SYMBOL_DEFAULTED` (info), all `supply` functions drawn as a labelled
  box: the controller's `system` and `field`, `-DI1`'s `power`, `-DO1` and `-T1`.

- **G6.** The fuse links in `-Fn1` are child items with no function (`3NW8004-1`, six in
  `out/all/EX-1-v1.1-bom.csv`, `F11; F21`). The aux blocks on `-Qn1` no longer carry a tag of their
  own: they are floating children and print the contactor's designation (`-Q11:53/NO`).

- **G7.** The motors `-M1`, `-M2` and their cables `-W11`, `-W21` sit at `+EXT`, outside the
  cabinet unit, so no cabinet page draws them. They are named in the `-X3` terminal list
  (cabinet page 11) and in the cable stubs of the pump pages (pages 5 and 6). The system document
  draws the cables and their motor ends (`out/all/EX-1-v1.1.pdf` pages 4 and 5). The motors
  themselves as symbols wait for the system block diagram.

- **G8.** The overload relay `-Bn2` direct-mounts and prints no input terminals. The part file
  `overload-relay-lrd08.toml` authors the IEC 60445 inputs `1/L1`, `3/L2`, `5/L3` so the wire from
  the contactor has a port to land on (`parts/README.md` records that they are not printed).

- **G14.** Text overlap between link-marker boxes and wire-end labels is reported by no finding.
  Not re-read on the whole v0.5.1 build; the pages rendered for this round (3, 4 and 5) show none.

- **G17.** Functions of items with no unit (the switch `+EXT-K1`, the harness plugs, the motors,
  `+EXT-X0`) are drawn on no schematic page. They are named in text: the cable drawings, the
  cable list and BOM of the system document, the `-X3` list and the stubs on the cabinet pages.
  The block diagram is the fix.

- **G20.** The contactor and its aux block each carry a NC contact (`aux_nc` 21/22, `nc` 61/62)
  that this design leaves unwired. The part files keep them, because a part file is the catalogue
  part. At 0.5.1 each drew alone as `LONE_CELL` (WARNING); the pin no longer reports it, and they
  show as `PORT_UNCONNECTED` (INFO). `tests/test_unit_identity.py` allows no `LONE_CELL`.

- **G21.** `inspect.signature(d.dc_supply)` raises `NameError: Design` on Python 3.15; at v0.6.0
  `inspect.signature(fr.build)` works. The annotation names a type the module does not import,
  which 3.15's lazy annotations expose. Found by calling `inspect.signature`
  on the surface; nothing in this build fails.

- **G22.** The power symbols of the `24V` and `GND` rails (declared by `dc_supply`) are drawn on
  module ports, such as the `24V` and ground symbols on `-DI1` and `-DO1` (page 4), but not at
  the open ends of the `-X2` terminal wires on the pump and supply pages. An observation on the
  v0.5.1 layout, not a finding.

- **G29.** Three layout warnings remain (`POWER_SYMBOL_UNPLACED`; `SYMBOL_OVERLAP` is 0 since v0.11.0), all on
  the pump's 24 V auxiliary-contact pins. v0.6.1: the -J1:3 ground placed (layout-0117).

## Closed

- **G2.** The overload relay `-Bn2` plugs onto the contactor `-Qn1`'s output blades. Closed at
  v0.6.0: `mounted_on=contactor.main` writes the mount links, and no wire joins them.
- **G9.** The WAGO 750 rack's power-jumper contacts carry the field supply from module to module.
  Closed at v0.6.0: `u.busbar(controller.field["+"], module.power["24V"])` and its 0 V twin.
- **G15.** Every PE terminal bonds to the mounting rail through its own foot. Closed at v0.6.0:
  `u.rail_bond(incoming_pe, pe)` replaces the two PE bonding wires.
- **G3.** `+EXT-X0` and the switch `+EXT-K1` are parts owned by others. Closed at v0.3.1 by the
  external flag: `d.strip("X0", at=ext, external=True)` and `d.item("1085039", tag="K1", at=ext,
  external=True)`. The BOM has no line for the switch, and the `-W1` drawing marks its `+EXT-X0`
  end "by others".

- **G4.** Schema 1 had no field for rated current or coil voltage. Closed at the pinned v0.5.1:
  part files carry `[rating]`, `[function.rating]` and `[function.operating]`, and the rating
  validator reads them. Fuse class and motor power are still appended to the part's description
  (`fuse-link-3nw8004-1.toml`, `motor-1le1003-0eb42-2aa4.toml`). Parts whose datasheet could not
  be read carry no rating and limit nothing; `parts/README.md` says which.

- **G10.** A part file whose port matched no symbol port linted clean and then raised in layout.
  Closed at v0.2.0: `fr.build` reports `SYMBOL_PORT_MISSING` at the part file's line.

- **G13.** 54 `OUT_OF_CONTENT_BOX` warnings at v0.2.1. Closed at v0.3.1.

- **G16.** The controller's unused second RJ45 port read as `UNIT_CONNECTOR_DANGLING`. Closed at
  v0.3.0: `cab.boundary(controller.fn("x2"))` then `cab.unused(controller.fn("x2"))`; `unused`
  alone reads `UNUSED_CONTRADICTED`.

- **G18.** The mate of `-W3-J2` with the switch was shown nowhere. Closed at v0.3.0 by the stub
  `-W3 <- +EXT-K1:1 2 3 4 5 6 7 8` on the "WAGO PLC" page (page 4); `tests/test_stubs.py` fails
  if it goes.

- **G19.** The running lamps drew with `PAGE_OVERFULL` and `ROUTE_FAILED` on pre-release builds.
  Closed at v0.3.0. The lamps now run from the contactor's aux block, not from a coupling relay.

- **G23.** At 0.6 the strip surface had no per-terminal part. Closed at v0.6.0 for PE:
  `terminal_strip(..., pe=P.P_2002_1207)` gives the `-X1`, `-X0` and `-X3` PE terminals the
  green-yellow ground block again. The N terminals of `-X1` and `-X0` still take the strip's one
  grey part, where 0.5.1 had a blue one.
- **G24.** The upstream strip `-X0` was not marked "by others". Closed at v0.6.0:
  `d.terminal_strip(..., external=True)`.
- **G25.** `Earthing.IT` was not exported to consumers. Closed at v0.6.0 (`earthing=fr.IT`); this
  supply stays earthed, the default, as the real feed is.
- **G26.** A device with two functions could not take `interface=True`. Closed at v0.6.0: the
  controller takes `interface=("x1",), unused=("x2",)`, and `build.py` makes no private call.
- **G27.** A nested unit instance took no place or function group. Closed at v0.6.0:
  `u.add(relay_board, "U2")` takes a function group; the board sits in the `=PLC` group. Since
  CU7 (2026-10-06) the cabinet is a unit with no place, so the instance names none.
- **G28.** The 3LD2054 part's three links had no `rest` state; at 0.6 that read as three lint
  errors. They now carry `rest = "open"` in the part file.
