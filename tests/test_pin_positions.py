"""R283: no two placed symbols share a pin position on a page; the helper reports one that does."""

from types import SimpleNamespace
from typing import Any

import fransys as fr
from pin_positions import shared_pin_positions
from tests.field_cases.test_a_two_pole_breaker_on_two_rails_stands_in_one_column import _design
lazy import pytest


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


def test_the_rail_breaker_design_shares_no_pin_position(monkeypatch: pytest.MonkeyPatch) -> None:
    import fransys_el.lay_out_core as core

    seen: list[Any] = []
    real = core.write_layout

    def spy(laid: Any, *args: Any, **kwargs: Any) -> Any:
        seen.extend(
            x.placement.pages for x in (laid, *args, *kwargs.values()) if hasattr(x, "placement")
        )
        return real(laid, *args, **kwargs)

    monkeypatch.setattr(core, "write_layout", spy)
    fr.build(*_design())
    assert seen
    assert [shared_pin_positions(pages) for pages in seen] == [[] for _ in seen]
