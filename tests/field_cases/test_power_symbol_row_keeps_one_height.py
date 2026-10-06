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
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import overlaps, symbol_geometry, translate
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.layout import PowerSymbol, Route, layout_of
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path


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
    d.wire(plug.x1["1"], module.do_1["1"], wire=(BU, 0.5))
    d.wire(plug.x1["2"], psu.output["-"], wire=(BU, 0.5))
    d.mate(plug, board.x1)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _cells(model, results, tag):
    """The placed cells of the item `tag`, as (cell, port page x, port page y) per port."""
    (item,) = (one.id for one in items(model).values() if one.tag == tag)
    own = {p.id for p in ports(model).values() if functions(model)[p.function].item == item}
    return [
        (cell, cell.at.x + port.at.x, cell.at.y + port.at.y)
        for cell in results.layout.placed
        if cell.function in own
        for port in cell.geometry.ports
    ]


def test_the_ground_row_keeps_one_height(tmp_path: Path) -> None:
    """The ground clears its box; each pin row keeps one height and the leads stay straight."""
    result = _build(tmp_path)
    assert "POWER_SYMBOL_UNPLACED" not in {f.code for f in fr.check(result)}
    model = result.model
    results, _ = stage_results(model, read_inputs(model))
    (k1,) = (one.id for one in items(model).values() if one.tag == "K1")
    own = {f.id for f in functions(model).values() if f.item == k1} | {k1}
    (box,) = (placed_keepout(one) for one in results.layout.placed if one.function in own)
    grounds = [s for s in layout_of(model, PowerSymbol).values() if s.symbol == "ground"]
    jack = [s for s in grounds if "G/J1" in s.key]
    assert jack
    for one in jack:
        body = translate(
            symbol_geometry("ground", orientation=one.orientation).body, dx=one.x, dy=one.y
        )
        assert not overlaps(body, box)

    plug, board = _cells(model, results, "J1"), _cells(model, results, "B1")
    assert len({y for _, _, y in plug}) == 1
    assert len({y for _, _, y in board}) == 1
    for cell, x, _ in board:
        (mate,) = (one for one, px, _ in plug if px == x)
        assert placed_keepout(mate).y == placed_keepout(cell).y + placed_keepout(cell).height

    (lead,) = (
        r
        for r in layout_of(model, Route).values()
        if ports(model)[r.a].key[0] == "G/J1" and ports(model)[r.b].key[0] == "G/K1"
    )
    (lead_x,) = {p.x for p in lead.points}
    (pin_two_x,) = {x for _, x, _ in plug} - {lead_x}
    assert {one.x for one in jack} == {pin_two_x}
