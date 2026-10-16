"""render draws the two Bridge mark pieces from the symbols, in the rule pen (render-0021)."""

import fransys_render

from fransys_model.derive import BRIDGE_PIECE_KEYS
from fransys_model.derive.print_sizes import LINE_RULE_MM


def test_a_piece_is_drawn_per_key_at_its_symbols_size_in_the_rule_pen() -> None:
    pieces = fransys_render.bridge_pieces()
    assert set(pieces) == set(BRIDGE_PIECE_KEYS.values())
    line, tick = pieces[BRIDGE_PIECE_KEYS["line"]], pieces[BRIDGE_PIECE_KEYS["tick"]]
    assert (line.width_mm, line.height_mm) == (3.0, 1.0)
    assert (tick.width_mm, tick.height_mm) == (2.0, 1.0)
    for piece in pieces.values():
        assert f'stroke-width="{LINE_RULE_MM}"' in piece.svg
        assert piece.svg.startswith("<svg ")
