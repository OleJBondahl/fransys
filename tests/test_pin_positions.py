"""R283: no two placed symbols share a pin position on a page; the helper reports one that does."""

from types import SimpleNamespace

import fransys as fr
from pin_positions import shared_pin_positions
from tests.field_cases.test_a_two_pole_breaker_on_two_rails_stands_in_one_column import _design

from electrical_symbols import LIBRARY
from fransys_layout.drawing import Drawing, port_points


def _placed(sym: str, x: int, y: int) -> SimpleNamespace:
    return SimpleNamespace(
        sym=sym,
        pin_xy=(SimpleNamespace(pin="in", x=x, y=y), SimpleNamespace(pin="out", x=x, y=y + 40)),
    )


def test_two_symbols_on_one_pin_are_reported() -> None:
    page = SimpleNamespace(placed=(_placed("A", 10, 0), _placed("B", 10, 40)))
    assert shared_pin_positions([page]) == [(0, 10, 40, ("A", "B"))]


def test_symbols_apart_are_not_reported() -> None:
    page = SimpleNamespace(placed=(_placed("A", 10, 0), _placed("B", 10, 60)))
    assert shared_pin_positions([page]) == []


def _drawn_page(drawing: Drawing) -> SimpleNamespace:
    """A drawn page as the placed symbols the helper reads: each symbol's pin points in G."""
    return SimpleNamespace(
        placed=tuple(
            SimpleNamespace(
                sym=s.id,
                pin_xy=tuple(SimpleNamespace(x=x, y=y) for (x, y), _ in port_points(s, LIBRARY)),
            )
            for s in drawing.symbols
        )
    )


def test_the_rail_breaker_design_shares_no_pin_position() -> None:
    drawings = fr.build(*_design()).drawings.values()
    pages = [_drawn_page(d) for d in drawings]
    assert any(page.placed for page in pages)
    assert shared_pin_positions(pages) == []
