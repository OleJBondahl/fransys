"""The Bridge mark symbols: their drawn lines and their room, from the TOML data (pdf-0049)."""

import pytest
from symdef import Line

from electrical_symbols import bridge_mark, bridge_mark_room
from electrical_symbols.sheet import slot_box_mm


def _lines(piece: str) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    symbol = bridge_mark(piece)  # ty: ignore[invalid-argument-type] -- the test passes a literal
    return [
        ((float(e.start.x), float(e.start.y)), (float(e.end.x), float(e.end.y)))
        for e in symbol.elements
        if isinstance(e, Line)
    ]


def test_the_line_is_one_vertical_line_on_the_middle_of_a_three_mm_lane() -> None:
    assert bridge_mark_room("line") == (3.0, 1.0)
    ((start, end),) = _lines("line")
    assert start == (1.5, 0.0)
    assert end == (1.5, 1.0)


@pytest.mark.parametrize("piece", ["line", "tick"])
def test_the_room_is_the_union_of_the_slot_boxes(piece: str) -> None:
    symbol = bridge_mark(piece)  # ty: ignore[invalid-argument-type] -- the test passes a literal
    boxes = [slot_box_mm(symbol, one.id) for one in symbol.slots]
    left = min(x for x, _, _, _ in boxes)
    top = min(y for _, y, _, _ in boxes)
    right = max(x + w for x, _, w, _ in boxes)
    bottom = max(y + h for _, y, _, h in boxes)
    assert bridge_mark_room(piece) == (right - left, bottom - top)  # ty: ignore[invalid-argument-type] -- the test passes a literal


def test_the_tick_spans_two_mm_on_the_middle_of_its_room() -> None:
    assert bridge_mark_room("tick") == (2.0, 1.0)
    ((start, end),) = _lines("tick")
    assert end[0] - start[0] == 2.0
    assert start[1] == end[1] == 0.5
