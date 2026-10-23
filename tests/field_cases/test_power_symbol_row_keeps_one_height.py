"""Field case: a ground symbol on a plug pin whose lead points into a PLC output module's box.

The engineering shape: a board's connector with a plug mated to it, the plug standing below the
board, and under the plug a PLC output module drawn as a box with its channels on the north edge.
Plug pin 1 is wired to channel 1; plug pin 2 is on a DC supply's 0 V rail, so pin 2 draws the
ground symbol, and its lead points down into the module's box.

The bug (found on the pump cabinet with `hide_unused_pins` narrowing the box): the plug left only
the row gap above the box, less than the symbol's lead and body, so no lead length cleared the box,
`POWER_SYMBOL_UNPLACED` warned and the symbol sat on the box's edge. Any small row gap shows it,
and the case sets one.

Rule (decision layout-0117, owner's choice G1, 2026-10-06): a row of pins (one item's, or one mated
pair's) keeps one height. When a power symbol at any pin of the row would reach into the box the
row faces, the row and that box move apart by whole grids until the symbol clears. Leads stay
straight and get longer; no pin moves alone.
"""

from typing import TYPE_CHECKING

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_layout import generic_box_geometry, symbol_geometry
from fransys_layout.geometry import overlaps, translate
from fransys_model.layout import Orientation, PowerSymbol, layout_of

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_layout import SymbolGeometry


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(row_gap=16)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        module = d.device("K1", "DEMO-PLC-DO-2")
        plug = d.device("J1", "DEMO-CONN-2P")
        board = d.device("B1", "DEMO-IO-2X")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    d.detail.wire(plug.x1["1"], module.do_1["1"], wire=(BU, 0.5))
    d.detail.wire(plug.x1["2"], psu.output["-"], wire=(BU, 0.5))
    d.mate(plug, board.x1)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _geometry(one) -> SymbolGeometry:
    """The geometry the drawn symbol stands in: a generic box from its sides and offsets."""
    if one.key != "generic-box":
        return symbol_geometry(one.key, orientation=Orientation[one.orient])
    sides, offsets = dict(one.sides), dict(one.offsets)
    names = tuple(sides)
    return generic_box_geometry(
        names, tuple(sides[n] for n in names), offsets=tuple(offsets[n] for n in names)
    )


def _cells(model, tag):
    """The drawn cells of the item `tag`, as (cell, geometry, pin page x, pin page y).

    The pin is the port the cell's lead leaves from, else its `out` port.
    """
    found = []
    for cell in symbol_subjects(model):
        if cell.tag == tag:
            geo = _geometry(cell)
            (port,) = (p for p in geo.ports if p.name == (cell.leads or ("out",))[0])
            found.append((cell, geo, cell.x + port.at.x, cell.y + port.at.y))
    return found


def _keepout(cell, geo: SymbolGeometry):
    return translate(geo.keepout, dx=cell.x, dy=cell.y)


def test_the_ground_row_keeps_one_height(tmp_path: Path) -> None:
    """The ground clears its box; each pin row keeps one height and the leads stay straight."""
    result = _build(tmp_path)
    assert "POWER_SYMBOL_UNPLACED" not in {f.code for f in fr.check(result)}
    model = result.model
    k1, k1_geo, channel_x, channel_y = _cells(model, "K1")[0]
    box = _keepout(k1, k1_geo)
    grounds = [s for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"]
    jack = [s for s in grounds if (model.key_of(s.port) or ("",))[0] == "G/J1"]
    assert jack
    for one in jack:
        body = translate(
            symbol_geometry("ground", orientation=one.orientation).body, dx=one.x, dy=one.y
        )
        assert not overlaps(body, box)

    plug, board = _cells(model, "J1"), _cells(model, "B1")
    assert len({y for *_, y in plug}) == 1
    assert len({y for *_, y in board}) == 1
    for cell, geo, x, _ in board:
        (mate_cell, mate_geo, _, _) = next(one for one in plug if one[2] == x)
        mate_box, board_box = _keepout(mate_cell, mate_geo), _keepout(cell, geo)
        assert mate_box.y == board_box.y + board_box.height

    channel = (channel_x, channel_y)
    leads = [
        w
        for d in drawn_pages(model).values()
        for w in d.wires
        if channel in w.points and set(w.points) & {(x, y) for _, _, x, y in plug}
    ]
    (lead,) = leads
    (lead_x,) = {x for x, _ in lead.points}
    (pin_two_x,) = {x for _, _, x, _ in plug} - {lead_x}
    assert {one.x for one in jack} == {pin_two_x}
