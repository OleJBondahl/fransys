"""Field case: a ground symbol on a plug pin, its lead pointing into a PLC output module's box, keeps its row's height.
The bug: a small row gap left no room for the symbol, so it sat on the box edge.
Fixed by layout-0117 (owner's choice G1): a row and its box move apart by whole grids until the symbol clears."""

from functools import cache

import fransys as fr
from _drawn_facts import box_boxes, pin_turn, symbol_boxes, symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from electrical_symbols import GENERIC_BOX_KEY
from fransys_layout.geometry import overlaps, translate
from fransys_model.layout import PowerSymbol, layout_of


@cache
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


def _keepout(cell):
    """The keep-out of the drawn symbol `cell` on its page: a generic box from its sides and offsets, else its library symbol."""
    if cell.key == GENERIC_BOX_KEY:
        names = tuple(dict(cell.sides))
        box = box_boxes(names, tuple(dict(cell.sides)[n] for n in names), tuple(dict(cell.offsets)[n] for n in names))[1]
    else:
        box = symbol_boxes(cell.key, poles=cell.poles, orient=cell.orient)[1]
    return translate(box, dx=cell.x, dy=cell.y)


def _cells(model, tag):
    """The drawn cells of the item `tag`, as (cell, pin page x, pin page y).

    The pin is the port the cell's lead leaves from, else its `out` port.
    """
    found = []
    for cell in symbol_subjects(model):
        if cell.tag == tag:
            port = (cell.leads or ("out",))[0]
            if cell.key == GENERIC_BOX_KEY:
                found.append((cell, cell.x + dict(cell.offsets)[port], cell.y))
            else:
                at = pin_turn(cell.key, port, poles=cell.poles, orient=cell.orient)
                found.append((cell, cell.x + at.dx, cell.y + at.dy))
    return found


def test_the_ground_clears_its_box() -> None:
    """The ground on the plug's pin stands clear of the output module's box."""
    model = _build().model
    k1, _, _ = _cells(model, "K1")[0]
    box = _keepout(k1)
    grounds = [s for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"]
    jack = [s for s in grounds if (model.key_of(s.port) or ("",))[0] == "G/J1"]
    assert jack
    for one in jack:
        body = translate(symbol_boxes("ground", orient=one.orientation.name)[0], dx=one.x, dy=one.y)
        assert not overlaps(body, box)


def test_the_ground_row_keeps_one_height() -> None:
    """Each pin row keeps one height and the leads stay straight."""
    model = _build().model
    _, channel_x, channel_y = _cells(model, "K1")[0]
    jack = [s for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground" and (model.key_of(s.port) or ("",))[0] == "G/J1"]
    plug, board = _cells(model, "J1"), _cells(model, "B1")
    assert len({y for *_, y in plug}) == 1
    assert len({y for *_, y in board}) == 1
    for cell, x, _ in board:
        (mate_cell, _, _) = next(one for one in plug if one[1] == x)
        mate_box, board_box = _keepout(mate_cell), _keepout(cell)
        assert mate_box.y == board_box.y + board_box.height

    channel = (channel_x, channel_y)
    leads = [w for d in drawn_pages(model).values() for w in d.wires if channel in w.points and set(w.points) & {(x, y) for _, x, y in plug}]
    (lead,) = leads
    (lead_x,) = {x for x, _ in lead.points}
    (pin_two_x,) = {x for _, x, _ in plug} - {lead_x}
    assert {one.x for one in jack} == {pin_two_x}
