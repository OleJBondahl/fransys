"""The Bridge mark symbols: their drawn lines and their room, from the TOML data (pdf-0049)."""

from symdef import Line

from electrical_symbols import bridge_mark, bridge_mark_room


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


def test_the_tick_spans_two_mm_on_the_middle_of_its_room() -> None:
    assert bridge_mark_room("tick") == (2.0, 1.0)
    ((start, end),) = _lines("tick")
    assert end[0] - start[0] == 2.0
    assert start[1] == end[1] == 0.5
