"""Field case: a ground symbol on a plug pin, its lead pointing into a PLC output module's box, keeps its row's height.
The bug: a small row gap left no room for the symbol, so it sat on the box edge.
Fixed by layout-0117 (owner's choice G1): a row and its box move apart by whole grids until the symbol clears."""

from typing import TYPE_CHECKING

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_layout import generic_box_geometry, symbol_geometry
from fransys_layout.geometry import overlaps, translate
from fransys_model.layout import Orientation, PowerSymbol, layout_of

if TYPE_CHECKING:
    from fransys_layout import SymbolGeometry


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        module = d.device("K1", "DEMO-PLC-DO-2")
        plug = d.device("J1", "DEMO-CONN-2P")
        board = d.device("B1", "DEMO-IO-2X")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    d.series(plug.x1["1"], module.do_1["1"], wire=(BU, 0.5))
    d.series(plug.x1["2"], psu.output["-"], wire=(BU, 0.5))
    d.series(plug.x1["1"], board.x1["1"], wire=(BU, 0.5))
    d.series(plug.x1["2"], board.x1["2"], wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _geometry(one) -> SymbolGeometry:
    """The geometry the drawn symbol stands in: a generic box from its sides and offsets."""
    if one.key != "generic-box":
        return symbol_geometry(one.key, orientation=Orientation[one.orient])
    sides, offsets = dict(one.sides), dict(one.offsets)
    names = tuple(sides)
    return generic_box_geometry(names, tuple(sides[n] for n in names), offsets=tuple(offsets[n] for n in names))


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


def test_the_ground_row_keeps_one_height() -> None:
    """The ground clears its box; each pin row keeps one height and the leads stay straight."""
    result = _build()
    model = result.model
    k1, k1_geo, channel_x, channel_y = _cells(model, "K1")[0]
    box = _keepout(k1, k1_geo)
    grounds = [s for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"]
    jack = [s for s in grounds if (model.key_of(s.port) or ("",))[0] == "G/J1"]
    assert jack
    for one in jack:
        body = translate(symbol_geometry("ground", orientation=one.orientation).body, dx=one.x, dy=one.y)
        assert not overlaps(body, box)

    plug, board = _cells(model, "J1"), _cells(model, "B1")
    assert len({y for *_, y in plug}) == 1
    assert len({y for *_, y in board}) == 1
    for cell, geo, x, _ in board:
        (mate_cell, mate_geo, _, _) = next(one for one in plug if one[2] == x)
        mate_box, board_box = _keepout(mate_cell, mate_geo), _keepout(cell, geo)
        assert mate_box.y == board_box.y + board_box.height

    channel = (channel_x, channel_y)
    leads = [w for d in drawn_pages(model).values() for w in d.wires if channel in w.points and set(w.points) & {(x, y) for _, _, x, y in plug}]
    (lead,) = leads
    (lead_x,) = {x for x, _ in lead.points}
    (pin_two_x,) = {x for _, _, x, _ in plug} - {lead_x}
    assert {one.x for one in jack} == {pin_two_x}
