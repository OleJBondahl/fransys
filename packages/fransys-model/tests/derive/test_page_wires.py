"""`page_wires` counts every conductor line of a page: routes, fan-out legs, power leads.

Model-0254. Built on stand-in records: the function reads only `page`, `points` and `legs`.
"""

import sys
from decimal import Decimal
from types import SimpleNamespace as Stand
from typing import Any

import pytest

from fransys_model.derive import page_wires
from fransys_model.kernel import Id
from fransys_model.layout import HarnessFanOut, Page, Route, RoutePoint

_PAGE = Id(kind="layout.page", value="p")


def _pts(*xy: tuple[int, int]) -> list[RoutePoint]:
    return [RoutePoint(index=i, x=x, y=y) for i, (x, y) in enumerate(xy)]


@pytest.fixture
def lines(monkeypatch: pytest.MonkeyPatch) -> Stand:
    """The records `page_wires` reads, patched in; the test fills `routes` and `fans`."""
    home = sys.modules["fransys_model.derive.page_wires"]  # the package name holds the function

    held = Stand(routes=[], fans=[])
    kinds: dict[type, Any] = {
        Page: {_PAGE: Stand(sheet_format="f")},
        Route: lambda: dict(enumerate(held.routes)),
        HarnessFanOut: lambda: dict(enumerate(held.fans)),
    }

    def layout_of(_model: object, kind: type) -> Any:
        found = kinds[kind]
        return found() if callable(found) else found

    monkeypatch.setattr(home, "layout_of", layout_of)
    monkeypatch.setattr(home, "sheet_format_of", lambda _m, _f: Stand(module_mm=Decimal(8)))
    return held


def _row(lead_grids: dict) -> tuple[int, Decimal]:
    model: Any = Stand()  # a stand-in model: `layout_of` is patched
    row = page_wires(model, lead_grids)[_PAGE]
    return row.bends, row.length_mm


def test_a_route_a_fan_out_leg_and_a_power_lead_all_count(lines: Stand) -> None:
    lines.routes = [Stand(page=_PAGE, points=_pts((0, 0), (10, 0)))]
    lines.fans = [
        Stand(
            page=_PAGE,
            legs=[
                Stand(points=_pts((0, 0), (3, 0), (3, 4))),  # one bend, 7 long
                Stand(points=_pts((0, 0), (3, 4))),  # a slant, 5 long
            ],
        )
    ]
    assert _row({_PAGE: 6}) == (1, Decimal(28))


@pytest.mark.usefixtures("lines")
def test_a_page_with_only_a_power_lead_has_its_length_and_no_bend() -> None:
    assert _row({_PAGE: 6}) == (0, Decimal(6))
