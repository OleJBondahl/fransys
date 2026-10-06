"""D2 (layout deep dive), EF-A1 part 4a: a multi-pole function with only some poles wired.

Same method as `test_dd_columns.py`: small invented designs on `examples/demo-parts`, read back
through the laid-out `SymbolPlacement` records and the findings of `fr.build`.
"""

import dataclasses
from itertools import combinations

from dd_chain_fixtures import contactor_with_pole_one_wired, placed, terminal_key
from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import Orientation, overlaps, symbol_geometry, translate
from fransys_layout.stages import Cell, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

MAIN = ("K1", "fn", "main")


def _x_range(model, key: tuple[str, ...]) -> tuple[object, int, int]:
    """The body's (page, left, right) of the function keyed `key` (a follower lane shows no tag)."""
    p = placed(model, *key)
    orientation = Orientation(p.orientation.value)
    box = symbol_geometry(p.symbol, poles=p.poles, orientation=orientation).body
    return p.page, p.x + box.x, p.x + box.x + box.width


def test_a_multi_pole_function_with_only_pole_one_wired_stands_in_its_wired_poles_column() -> None:
    """D2: XA:1 - K1:main.1..2 - XB:1 is one column; K1's unwired poles 2 and 3 open no other."""
    # UNDO: _chain_walk.py `drop_unwired_poles`: the line that drops a single unwired non-terminal
    # pole's chain when its function has a pole in a longer chain (fails until that line exists)
    model = contactor_with_pole_one_wired(relays=False).model
    main = placed(model, *MAIN)
    above, below = placed(model, *terminal_key("XA", 1)), placed(model, *terminal_key("XB", 1))
    assert above.x == main.x == below.x
    assert above.y < main.y < below.y
    in_column = [
        functions(model)[p.function].key
        for p in layout_of(model, SymbolPlacement).values()
        if p.x == main.x
    ]
    assert sorted(in_column) == sorted([MAIN, terminal_key("XA", 1), terminal_key("XB", 1)])


def test_a_contactor_beside_two_relays_has_no_overlap_and_no_unplaced_label() -> None:
    """D2: K1 (pole 1 wired) beside K2, K3 (2CO): no keep-out shares interior, every label fits."""
    # UNDO: stages/chains.py: the `drop_unwired_poles` call removed AND place.py `_lane_offsets`:
    # `max(cell.lane * pitch, packed)` -> `cell.lane * pitch`; either alone still passes (the
    # next test guards the place.py change alone)
    result = contactor_with_pole_one_wired(relays=True)
    codes = [f.code for f in result.findings]
    assert "SYMBOL_OVERLAP" not in codes
    assert "LABEL_UNPLACED" not in codes
    keys = [MAIN, ("K2", "fn", "coil"), ("K3", "fn", "coil")]
    ranges = {key: _x_range(result.model, key) for key in keys}
    same_page = [(a, b) for a, b in combinations(keys, 2) if ranges[a][0] == ranges[b][0]]
    assert len(same_page) >= 1  # pages differ between bodies: only a shared page can overlap
    for a, b in same_page:
        (_, a0, a1), (_, b0, b1) = ranges[a], ranges[b]
        assert a1 <= b0 or b1 <= a0, f"{a} {ranges[a]} overlaps {b} {ranges[b]}"


def test_a_cell_in_the_lane_after_a_multi_pole_cell_stands_clear_of_its_poles() -> None:
    """D2: a 3-pole cell in lane 0 has its keep-out over lanes 0-2; lane 1's cell starts beyond."""
    # UNDO: place.py `_lane_offsets`: `max(cell.lane * pitch, packed)` -> `cell.lane * pitch`
    three_pole = dataclasses.replace(
        drawn(1),
        geometry=symbol_geometry("make-contact", poles=3),
        primary_in="1.in",
        primary_out="1.out",
    )
    cells = tuple(Cell(function=hid("function", n), index=0, lane=n - 1) for n in (1, 2))
    lane_row = dataclasses.replace(column("a", (1,)), cells=cells)
    placed_cells, _ = place(
        page_plan(("a",)),
        (lane_row,),
        (three_pole, drawn(2)),
        PageStacking(profile=PROFILE, sheet=SHEET),
    )
    boxes = [
        translate(p.geometry.keepout, dx=p.at.x, dy=p.at.y)
        for p in sorted(placed_cells, key=lambda p: p.function)
    ]
    assert len(boxes) == 2
    assert boxes[1].x >= boxes[0].x + boxes[0].width
    assert not overlaps(*boxes)
