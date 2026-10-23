"""`svg` draws a junction-dot `DrawnSymbol` through symdef, no element of its own (render-0025)."""

from fransys_el import style
from fransys_render.draw import svg
from test_draw import drawing, sym

from electrical_symbols import LIBRARY


def test_a_junction_dot_symbol_draws_the_librarys_circle_at_its_point() -> None:
    out = svg(drawing([sym(key="junction-dot", x=96, y=88)]), LIBRARY, style(LIBRARY))
    assert out.count("<circle") == 1
    assert 'class="junction"' not in out
    assert 'transform="translate(' in out
