"""M2 (owner 2026-10-07, layout-0149): a terminal wired only to a pin of another block stays at
that pin, and its own block's page does not show it.

Block B holds a switch wired to terminal X1:2, and terminal X1:1; block A holds relay K1, whose
coil pin carries the only wire of X1:1. A page break gives each block its own page. The rule it
rests on is V4 (owner 2026-10-02, layout-0099): a pin wired to a non-rail terminal shows it.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items


def _placed() -> dict[str, list[tuple[int, int, int]]]:
    """`(page, x, y)` of every placement, by the printed designation of its item."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    with d.function("GB", "Block B") as block_b:
        switch = d.device("S1", "DEMO-SWITCH-2P")
        into_a, beside = strip[1], strip[2]
        d.wire(switch.sw["B"], beside.outer, wire=(BU, 0.5))
    with d.function("GA", "Block A") as block_a:
        relay = d.device("K1", "DEMO-RLY-2CO-24")
        d.wire(into_a, relay.coil["A1"], wire=(BU, 0.5))
    d.layout.break_before(block_b)
    d.layout.break_before(block_a)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    name = {i.id: fr.derive.printed_designation(model, i.id) for i in items(model).values()}
    placed: dict[str, list[tuple[int, int, int]]] = {}
    for p in results.layout.placed:
        placed.setdefault(name[functions(model)[p.function].item], []).append(
            (p.page, p.at.x, p.at.y)
        )
    return placed


def test_a_terminal_wired_only_into_another_block_stays_at_that_pin() -> None:
    placed = _placed()
    (relay_page, relay_x, relay_y) = placed["-K1"][0]
    (at_pin,) = placed["-X1:1"]
    assert at_pin[:2] == (relay_page, relay_x)
    assert at_pin[2] < relay_y
    (switch_page, *_) = placed["-S1"][0]
    assert switch_page != relay_page
    assert [p for p, _x, _y in placed["-X1:2"]] == [switch_page]
