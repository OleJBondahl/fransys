"""A pin wired inside a black-box board refuses with PLACEMENT_PROBLEM, never crashes the layout.

The shape: a PLC output card sits under a rack board; one of its channel pins is wired to a coil.
A board is a black box on the cabinet page, so the pin has no symbol to land on.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BU


def test_a_channel_pin_wired_under_a_board_is_a_placement_problem() -> None:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    rack = d.device("R1", "DEMO-PCB-IO")
    card = d.device("DO1", "DEMO-PLC-DO-2", parent=rack, position=1)
    relay = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(card.do_1["1"], relay.coil["A1"], wire=(BU, 0.5))
    d.series(card.do_2["2"], relay.coil["A2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    expect_codes(result, "PLACEMENT_PROBLEM")
    codes = {f.code: f for f in fr.check(result)}
    assert "black box" in codes["PLACEMENT_PROBLEM"].message
