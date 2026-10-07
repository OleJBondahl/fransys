"""HA-D2 probe 6: a harness fan-out leg is exempt from `WIRE_NOT_ORTHOGONAL` by kind.

The lint reads `Layout.routes` only. A `HarnessFanOut` is a model record, not a `Route`, so
its oblique legs are never checked; the same points written as a `Route` are.
"""

from pathlib import Path

from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Point
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import WIRE_NOT_ORTHOGONAL
from fransys_layout.stages import Layout, Route, RoutePoint
from fransys_model.kernel import Id
from fransys_model.layout import FanLeg, HarnessFanOut
from fransys_model.layout import RoutePoint as ModelPoint

_OBLIQUE = ((0, 0), (8, 5))


def _fan_out() -> HarnessFanOut:
    leg = FanLeg(
        index=0,
        conductor=hid("conductor", 1),
        points=tuple(ModelPoint(index=i, x=x, y=y) for i, (x, y) in enumerate(_OBLIQUE)),
    )
    return HarnessFanOut(
        id=Id(kind="layout.harness_fan_out", value="c" * 32),
        key=("harness", "fan"),
        page=hid("layout.page", 1),
        harness=hid("item", 1),
        branch=1,
        x=0,
        y=0,
        legs=(leg,),
        produced_by="test",
    )


def _layout(routes: tuple[Route, ...] = ()) -> Layout:
    return Layout(
        pages=(page_plan(("a",)),),
        placed=(placed(1, x=104, y=96), placed(2, x=104, y=304)),
        routes=routes,
        decisions=(),
        markers=(),
        labels=(),
    )


def _codes(layout: Layout) -> list[str]:
    return [f.code for f in lint_geometry(layout, sheet=SHEET)]


def test_oblique_fan_out_legs_give_no_wire_not_orthogonal() -> None:
    """A fan-out with an oblique leg and no `Route` gives no finding."""
    fan = _fan_out()
    assert fan.legs[0].points[1].x != fan.legs[0].points[0].x
    assert fan.legs[0].points[1].y != fan.legs[0].points[0].y
    assert WIRE_NOT_ORTHOGONAL not in _codes(_layout())


def test_the_same_oblique_points_as_a_route_give_the_finding() -> None:
    """Control: the oblique points written as a `Route` are `WIRE_NOT_ORTHOGONAL`."""
    route = Route(
        connection=hid("conductor", 1),
        physical_net=hid("net", 1),
        drawing_set=1,
        page=1,
        a=hid("port", 12),
        b=hid("port", 21),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(_OBLIQUE)),
    )
    assert _codes(_layout((route,))) == [WIRE_NOT_ORTHOGONAL]


def test_lint_code_does_not_read_fan_outs() -> None:
    """No lint module names `HarnessFanOut`, `FanLeg` or `harness_fan_out`."""
    lint_dir = Path(__file__).parents[2] / "src" / "fransys_layout" / "lint"
    text = "".join(path.read_text() for path in lint_dir.glob("*.py"))
    assert not any(name in text for name in ("HarnessFanOut", "FanLeg", "harness_fan_out"))
