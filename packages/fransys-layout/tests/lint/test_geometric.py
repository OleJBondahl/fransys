"""Acceptance skeletons for `lint.geometric`.

Every code has an input that triggers it; the clean page triggers none.
"""

import dataclasses
import re
from typing import TYPE_CHECKING

import pytest
from samples import SHEET, hid, page_plan, placed, through_geometry

from fransys_layout.geometry import (
    Box,
    Facing,
    Point,
    PortGeometry,
)
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import (
    OUT_OF_CONTENT_BOX,
)
from fransys_layout.stages import (
    LabelKind,
    Layout,
    LinkMarker,
    MarkerSide,
    PlacedFunction,
    PlacedLabel,
    Route,
    RoutePoint,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id

from fransys_model.kernel import Severity


def _wire(
    points: tuple[tuple[int, int], ...], *, number: int = 1, net: int | None = None, page: int = 1
) -> Route:
    return Route(
        connection=hid("conductor", number),
        physical_net=hid("net", number if net is None else net),
        drawing_set=1,
        page=page,
        a=hid("port", 12),
        b=hid("port", 21),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(points)),
    )


def _layout(*, functions=None, routes=(), labels=(), markers=()) -> Layout:
    if functions is None:
        functions = (placed(1, x=104, y=96), placed(2, x=104, y=304))
    return Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=routes,
        decisions=(),
        markers=markers,
        labels=labels,
    )


def _marker(port: int, box: Box, *, page: int = 1) -> LinkMarker:
    """A marker of port `port` whose box is `box`, at the box's top-left corner."""
    return LinkMarker(
        connection=hid("conductor", 5),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=page,
        at=Point(x=box.x, y=box.y),
        box=box,
        partner_page=2,
    )


def _codes(layout: Layout) -> list[str]:
    return [f.code for f in lint_geometry(layout, sheet=SHEET)]


_CODE_CONSTANT = re.compile(r'^([A-Z][A-Z_]+) = "([A-Z][A-Z_]+)"$', re.MULTILINE)


# --- helpers for the unit tests below --------------------------------------------------


def _label(
    subject: int, box: Box, *, page: int = 1, slot: str = "tag", kind: LabelKind = LabelKind.TAG
) -> PlacedLabel:
    return PlacedLabel(
        kind=kind, subject=hid("function", subject), slot=slot, drawing_set=1, page=page, box=box
    )


def _found(layout: Layout) -> list[tuple[str, tuple[Id, ...]]]:
    """Every finding as `(code, subjects)`, in the order the lint returned them."""
    return [(f.code, f.subjects) for f in lint_geometry(layout, sheet=SHEET)]


def _route_ids(number: int) -> tuple[Id, ...]:
    """The subjects of a finding about `_wire(number=number)`: conductor, then its two ports."""
    return (hid("conductor", number), hid("port", 12), hid("port", 21))


def _star() -> PlacedFunction:
    """Function 7 at (200, 200): one port on each side of a 64 G square keep-out box."""
    ports = (
        PortGeometry(name="n", at=Point(x=0, y=-16), facing=Facing.N),
        PortGeometry(name="e", at=Point(x=16, y=0), facing=Facing.E),
        PortGeometry(name="s", at=Point(x=0, y=16), facing=Facing.S),
        PortGeometry(name="w", at=Point(x=-16, y=0), facing=Facing.W),
    )
    geometry = dataclasses.replace(
        through_geometry(), ports=ports, keepout=Box(x=-32, y=-32, width=64, height=64)
    )
    return dataclasses.replace(placed(7, x=200, y=200), geometry=geometry)


def _dot() -> PlacedFunction:
    """Function 7 at (200, 200): all four ports on one point, as the library's junction dot."""
    ports = tuple(
        PortGeometry(name=facing.name.lower(), at=Point(x=0, y=0), facing=facing)
        for facing in Facing
    )
    geometry = dataclasses.replace(
        through_geometry(), ports=ports, keepout=Box(x=-8, y=-8, width=16, height=16)
    )
    return dataclasses.replace(placed(7, x=200, y=200), geometry=geometry)


def _tall(number: int, *, x: int, y: int) -> PlacedFunction:
    """A through symbol whose keep-out box reaches 16 G below its `out` port."""
    geometry = dataclasses.replace(
        through_geometry(), keepout=Box(x=-8, y=-16, width=56, height=48)
    )
    return dataclasses.replace(placed(number, x=x, y=y), geometry=geometry)


_JOG = ((104, 112), (104, 160), (136, 160), (136, 200), (104, 200), (104, 288))


# --- WIRE_NOT_ORTHOGONAL ---------------------------------------------------------------


# --- WIRE_THROUGH_SYMBOL ---------------------------------------------------------------


_LANES = [
    pytest.param(((200, 184), (200, 100)), ((200, 184), (200, 220)), id="N"),
    pytest.param(((200, 216), (200, 300)), ((200, 216), (200, 190)), id="S"),
    pytest.param(((216, 200), (300, 200)), ((216, 200), (190, 200)), id="E"),
    pytest.param(((184, 200), (100, 200)), ((184, 200), (210, 200)), id="W"),
]


# --- WIRE_OVER_LABEL -------------------------------------------------------------------


# --- link markers (decision layout-0019) -----------------------------------------------


_MARKER_BOX = Box(x=190, y=110, width=20, height=20)


# --- REDUNDANT_JOG ---------------------------------------------------------------------


# The jog of the first route starts at the route's own end cell (104, 112); the second starts
# one grid unit in, at (104, 120). Their straight runs are x = 104 from y 112 to 152 and from
# y 120 to 160.
_AT_THE_END = ((104, 112), (136, 112), (136, 152), (104, 152), (104, 288))
_ONE_IN = ((104, 112), (104, 120), (136, 120), (136, 160), (104, 160), (104, 288))


# --- SYMBOL_OVERLAP --------------------------------------------------------------------


# --- OUT_OF_CONTENT_BOX ----------------------------------------------------------------


_KEEPOUT = Box(x=-8, y=-16, width=56, height=32)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(Box(x=1248, y=100, width=32, height=8), [], id="flush right"),
        pytest.param(Box(x=1249, y=100, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past right"),
        pytest.param(Box(x=0, y=0, width=32, height=8), [], id="flush top left"),
        pytest.param(Box(x=-1, y=0, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past left"),
        pytest.param(Box(x=0, y=-1, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past top"),
        pytest.param(Box(x=0, y=878, width=32, height=8), [], id="flush bottom"),
        pytest.param(Box(x=0, y=879, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past bottom"),
    ],
)
def test_a_label_box_is_tested_against_the_content_box(box: Box, expected: list[str]) -> None:
    """A label flush with an edge is inside; one grid unit past it is not."""
    assert _codes(_layout(labels=(_label(9, box),))) == expected


# --- pages, faults and order -----------------------------------------------------------


def _busy() -> Layout:
    """A page that triggers every code at once, with a second page that adds nothing."""
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=104, y=304),
        placed(3, x=104, y=200),
        placed(4, x=120, y=96, name="b"),
        placed(5, x=1272, y=96),
        placed(6, x=104, y=96, page=2),
    )
    routes = (
        _wire(((104, 112), (104, 288)), number=1),
        _wire(((300, 112), (340, 160)), number=2),
        _wire(((400, 100), (400, 140), (432, 140), (432, 180), (400, 180), (400, 260)), number=3),
        _wire(((1300, 300), (1300, 400)), number=4),
        _wire(((104, 112), (104, 288)), number=5, page=2),
    )
    labels = (
        _label(9, Box(x=96, y=236, width=32, height=8)),
        _label(9, Box(x=400, y=236, width=32, height=8), page=2),
    )
    return _layout(functions=functions, routes=routes, labels=labels)


# --- edges the mutation sweep pointed at ------------------------------------------------


_GRAZING = [
    pytest.param(56, 184, 48, 184, id="a box left of the run"),
    pytest.param(112, 184, 120, 184, id="a box right of the run"),
    pytest.param(104, 144, 104, 136, id="a box above the run"),
    pytest.param(104, 216, 104, 224, id="a box below the run"),
]


_OFF_LANE = [
    pytest.param(((200, 184), (200, 100), (210, 100), (210, 184)), id="N"),
    pytest.param(((200, 216), (200, 300), (210, 300), (210, 216)), id="S"),
    pytest.param(((184, 200), (100, 200), (100, 210), (184, 210)), id="W"),
    pytest.param(((216, 200), (300, 200), (300, 210), (216, 210)), id="E"),
]


_RINGS = [
    pytest.param(
        ((104, 112), (104, 160), (136, 160), (136, 200)),
        ((136, 200), (104, 200), (104, 288), (104, 112)),
        id="closing after the middle leg",
    ),
    pytest.param(
        ((104, 112), (104, 160), (136, 160)),
        ((136, 160), (136, 200), (104, 200), (104, 288), (104, 112)),
        id="closing before the middle leg",
    ),
    pytest.param(
        ((104, 112), (104, 160), (120, 160)),
        ((120, 160), (136, 160), (136, 200), (104, 200), (104, 288), (104, 112)),
        id="closing in the middle of an arm",
    ),
]


# --- the printed sets (model-0201) -----------------------------------------------------


def _struck_and_outside() -> Layout:
    """A route over a label (`WIRE_OVER_LABEL`) and a label past the box (`OUT_OF_CONTENT_BOX`)."""
    return _layout(
        routes=(_wire(((200, 184), (200, 300))),),
        labels=(
            _label(8, Box(x=190, y=240, width=20, height=8)),
            _label(9, Box(x=1249, y=100, width=32, height=8)),
        ),
    )


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        pytest.param(None, ["OUT_OF_CONTENT_BOX", "WIRE_OVER_LABEL"], id="every set"),
        pytest.param(frozenset({1}), ["OUT_OF_CONTENT_BOX", "WIRE_OVER_LABEL"], id="set 1 printed"),
        pytest.param(frozenset({2}), ["OUT_OF_CONTENT_BOX"], id="set 1 not printed"),
    ],
)
def test_a_look_finding_skips_a_set_nobody_prints_but_a_geometry_finding_stays(
    printed: frozenset[int] | None, expected: list[str]
) -> None:
    found = lint_geometry(_struck_and_outside(), sheet=SHEET, printed=printed)
    assert [f.code for f in found] == expected


def test_an_unclearable_defect_is_info_and_a_clearable_one_stays_warning() -> None:
    """layout-0252: the stuck route is INFO; the label past the content box is a WARNING."""
    found = {f.code: f.severity for f in lint_geometry(_struck_and_outside(), sheet=SHEET)}
    assert found == {"OUT_OF_CONTENT_BOX": Severity.WARNING, "WIRE_OVER_LABEL": Severity.INFO}
