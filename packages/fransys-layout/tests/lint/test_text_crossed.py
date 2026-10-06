"""`TEXT_CROSSED_BY_ROUTE`: a link marker's stub through a text box (lint/_texts.py, lint.md 6.8).

A route through a label or marker box stays `WIRE_OVER_LABEL`; only the marker's stub, which
render draws and the layout does not store, is judged here. One defect, one finding.
"""

import dataclasses
import itertools

import pytest
from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import TEXT_CROSSED_BY_ROUTE, WIRE_OVER_LABEL
from fransys_layout.stages import (
    LabelKind,
    Layout,
    LinkMarker,
    MarkerSide,
    PlacedLabel,
    Route,
    RoutePoint,
)
from fransys_model.kernel import Id, Severity

_DOWN = Box(x=92, y=140, width=32, height=8)  # stub of a marker at (100, 100): x 100, y 100..140


def _marker(
    port: int,
    box: Box,
    at: Point,
    *,
    lead: bool = True,
    turn: Point | None = None,
) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 5),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=at,
        box=box,
        partner_page=2,
        lead=lead,
        turn=turn,
    )


def _down(port: int = 7, *, x: int = 100, page: int = 1) -> LinkMarker:
    """Marker `port` at `(x, 100)` whose box `_DOWN` (moved to `x`) lies below it."""
    box = Box(x=x - 8, y=140, width=32, height=8)
    return dataclasses.replace(_marker(port, box, Point(x=x, y=100)), page=page)


def _label(subject: int, box: Box, *, page: int = 1) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", subject),
        slot="tag",
        drawing_set=1,
        page=page,
        box=box,
    )


def _wire(points: tuple[tuple[int, int], ...]) -> Route:
    return Route(
        connection=hid("conductor", 1),
        physical_net=hid("net", 1),
        drawing_set=1,
        page=1,
        a=hid("port", 12),
        b=hid("port", 21),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(points)),
    )


def _layout(*, functions=(), routes=(), labels=(), markers=()) -> Layout:
    return Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=routes,
        decisions=(),
        markers=markers,
        labels=labels,
    )


def _found(layout: Layout) -> list[tuple[str, tuple[Id, ...]]]:
    return [(f.code, f.subjects) for f in lint_geometry(layout, sheet=SHEET)]


def _subjects(*ids: Id) -> tuple[Id, ...]:
    """Finding subjects are stored in `Id` order, each once."""
    return tuple(sorted(set(ids)))


def _crossed_by(marker: LinkMarker, subject: Id) -> list[tuple[str, tuple[Id, ...]]]:
    return [(TEXT_CROSSED_BY_ROUTE, _subjects(marker.connection, marker.port, subject))]


def test_a_marker_with_no_text_near_its_stub_has_no_finding() -> None:
    assert _found(_layout(markers=(_down(),))) == []


def test_a_stub_through_a_label_is_reported_with_the_three_subjects() -> None:
    marker = _down()
    label = _label(9, Box(x=90, y=110, width=20, height=8))
    layout = _layout(labels=(label,), markers=(marker,))
    assert _found(layout) == _crossed_by(marker, hid("function", 9))
    assert lint_geometry(layout, sheet=SHEET)[0].severity is Severity.WARNING


def test_a_stub_through_another_lead_markers_box_is_reported_with_its_port() -> None:
    marker = _down(7)
    other = _marker(8, Box(x=90, y=110, width=20, height=8), Point(x=90, y=200))
    assert _found(_layout(markers=(marker, other))) == _crossed_by(marker, hid("port", 8))


@pytest.mark.parametrize(
    ("lead", "expected"),
    [pytest.param(True, True, id="lead"), pytest.param(False, False, id="not a lead")],
)
def test_a_non_lead_markers_box_is_no_text(*, lead: bool, expected: bool) -> None:
    """A non-lead marker shares its lead's box, so the box is not counted as a text."""
    marker = _down(7)
    other = _marker(8, Box(x=90, y=110, width=20, height=8), Point(x=90, y=200), lead=lead)
    assert bool(_found(_layout(markers=(marker, other)))) is expected


def test_a_non_lead_markers_own_stub_still_crosses() -> None:
    marker = _marker(7, _DOWN, Point(x=100, y=100), lead=False)
    label = _label(9, Box(x=90, y=110, width=20, height=8))
    assert _found(_layout(labels=(label,), markers=(marker,))) == _crossed_by(
        marker, hid("function", 9)
    )


@pytest.mark.parametrize(
    "box",
    [
        pytest.param(Box(x=92, y=140, width=32, height=8), id="box below"),
        pytest.param(Box(x=92, y=52, width=32, height=8), id="box above"),
        pytest.param(Box(x=140, y=96, width=32, height=8), id="box right"),
        pytest.param(Box(x=28, y=96, width=32, height=8), id="box left"),
    ],
)
def test_a_markers_own_stub_never_crosses_its_own_box(box: Box) -> None:
    """The stub ends on its box's edge; a lone marker reports nothing, whichever side."""
    assert _found(_layout(markers=(_marker(7, box, Point(x=100, y=100)),))) == []


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(Box(x=90, y=110, width=20, height=8), True, id="across"),
        pytest.param(Box(x=100, y=110, width=20, height=8), False, id="left edge on the stub"),
        pytest.param(Box(x=80, y=110, width=20, height=8), False, id="right edge on the stub"),
        pytest.param(Box(x=90, y=80, width=20, height=20), False, id="bottom edge on the port"),
        pytest.param(Box(x=90, y=140, width=20, height=8), False, id="top edge on the stub end"),
        pytest.param(Box(x=90, y=139, width=20, height=8), True, id="one unit into the stub"),
        pytest.param(Box(x=90, y=101, width=20, height=8), True, id="one unit below the port"),
    ],
)
def test_a_stub_is_through_a_text_only_by_its_interior(box: Box, *, expected: bool) -> None:
    """Both axes strict, as for a route: edge contact is not through.

    Some of these boxes also sit over the marker's own box (`TEXT_OVERLAP`'s, not this
    check's), so only `TEXT_CROSSED_BY_ROUTE` is counted here.
    """
    found = [
        f
        for f in _found(_layout(labels=(_label(9, box),), markers=(_down(),)))
        if f[0] == TEXT_CROSSED_BY_ROUTE
    ]
    assert bool(found) is expected


@pytest.mark.parametrize(
    ("at", "box", "text"),
    [
        pytest.param(
            Point(x=100, y=100),
            Box(x=140, y=96, width=32, height=8),
            Box(x=110, y=96, width=8, height=8),
            id="box to the right",
        ),
        pytest.param(
            Point(x=200, y=100),
            Box(x=160, y=96, width=32, height=8),
            Box(x=194, y=96, width=4, height=8),
            id="box to the left",
        ),
        pytest.param(
            Point(x=100, y=200),
            Box(x=92, y=152, width=32, height=8),
            Box(x=96, y=170, width=8, height=8),
            id="box above",
        ),
    ],
)
def test_a_stub_crosses_in_every_direction(at: Point, box: Box, text: Box) -> None:
    marker = _marker(7, box, at)
    assert _found(_layout(labels=(_label(9, text),), markers=(marker,))) == _crossed_by(
        marker, hid("function", 9)
    )


def _turn_marker() -> LinkMarker:
    """S20 M7: port (100, 100) on a wire that runs south; the junction one grid on at (100, 108),
    the branch east to x 116, and the box vertical below the branch end, its near edge at 116."""
    return _marker(
        7, Box(x=112, y=116, width=8, height=32), Point(x=100, y=100), turn=Point(x=100, y=108)
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            Box(x=106, y=104, width=4, height=8), True, id="on the branch east of the dot"
        ),
        pytest.param(Box(x=114, y=110, width=4, height=4), True, id="on the stub after the bend"),
        pytest.param(Box(x=96, y=100, width=8, height=8), False, id="on the wire to the dot"),
        pytest.param(Box(x=106, y=100, width=4, height=8), False, id="branch rests on its edge"),
        pytest.param(Box(x=106, y=112, width=4, height=8), False, id="clear of the branch"),
    ],
)
def test_only_the_branch_and_stub_past_a_turn_are_a_crossing_the_wire_to_it_is_wire_over_label(
    text: Box, *, expected: bool
) -> None:
    """M7: the port-to-dot run is the wire (a route, `WIRE_OVER_LABEL`), render draws no stub
    there; the branch and the stub up to the box are the marker's, so a text on them is crossed."""
    marker = _turn_marker()
    found = _found(_layout(labels=(_label(9, text),), markers=(marker,)))
    assert found == (_crossed_by(marker, hid("function", 9)) if expected else [])


@pytest.mark.parametrize(
    ("box", "text", "expected"),
    [
        pytest.param(
            Box(x=40, y=80, width=85, height=12),
            Box(x=20, y=76, width=8, height=8),
            True,
            id="south: a text on the lead",
        ),
        pytest.param(
            Box(x=40, y=80, width=85, height=12),
            Box(x=10, y=74, width=12, height=4),
            True,
            id="south: a text on the stub",
        ),
        pytest.param(
            Box(x=40, y=80, width=85, height=12),
            Box(x=20, y=82, width=8, height=8),
            False,
            id="south: a text below the lead",
        ),
        pytest.param(
            Box(x=40, y=44, width=85, height=12),
            Box(x=20, y=52, width=8, height=8),
            True,
            id="north: a text on the lead",
        ),
        pytest.param(
            Box(x=40, y=44, width=85, height=12),
            Box(x=20, y=46, width=8, height=4),
            False,
            id="north: a text above the lead",
        ),
    ],
)
def test_the_stub_and_lead_of_a_box_beyond_a_lane_are_checked(
    box: Box, text: Box, *, expected: bool
) -> None:
    """D14, layout-0054: a box beside its stub (its x span does not hold the stub) is drawn with
    a stub from the port to the box's near edge level and a lead along that edge to the near
    corner (render `_shared_box_glyph`): the port (16, 72) has the box 40 G right of it, below
    (near edge y=80) or above (near edge y=56).
    """
    marker = _marker(7, box, Point(x=16, y=72))
    found = _found(_layout(labels=(_label(9, text),), markers=(marker,)))
    assert found == (_crossed_by(marker, hid("function", 9)) if expected else [])


def test_the_lead_of_a_non_lead_marker_is_not_drawn_and_not_checked() -> None:
    """Render draws the lead with the box, from the lead marker only: the stub of a marker that
    is not one still crosses, the lead does not exist."""
    box = Box(x=40, y=80, width=85, height=12)
    marker = _marker(7, box, Point(x=16, y=72), lead=False)
    on_lead = _label(9, Box(x=20, y=76, width=8, height=8))
    assert _found(_layout(labels=(on_lead,), markers=(marker,))) == []


def test_a_text_on_another_page_is_not_crossed() -> None:
    box = Box(x=90, y=110, width=20, height=8)
    assert _found(_layout(labels=(_label(9, box, page=2),), markers=(_down(),))) == []
    assert _found(_layout(labels=(_label(9, box, page=1),), markers=(_down(),))) != []


def test_a_marker_on_another_page_does_not_cross_this_pages_text() -> None:
    box = Box(x=90, y=110, width=20, height=8)
    assert _found(_layout(labels=(_label(9, box),), markers=(_down(page=2),))) == []


def test_the_findings_do_not_depend_on_the_order_of_the_markers() -> None:
    markers = (_down(7, x=100), _down(8, x=300), _down(9, x=500))
    labels = (
        _label(20, Box(x=290, y=110, width=20, height=8)),
        _label(21, Box(x=490, y=110, width=20, height=8)),
        _label(22, Box(x=90, y=110, width=20, height=8)),
    )
    expected = _found(_layout(labels=labels, markers=markers))
    assert len(expected) == 3
    assert expected == sorted(expected)
    for order in itertools.permutations(markers):
        assert _found(_layout(labels=labels[::-1], markers=order)) == expected


# --- the split with WIRE_OVER_LABEL -----------------------------------------------------


def _split_layout(*, with_stub: bool = True) -> Layout:
    """One route through label 9, and (when asked) one marker stub through label 10."""
    return _layout(
        functions=(placed(1, x=104, y=96), placed(2, x=104, y=304)),
        routes=(_wire(((104, 112), (104, 288))),),
        labels=(
            _label(9, Box(x=96, y=196, width=32, height=8)),
            _label(10, Box(x=296, y=110, width=16, height=8)),
        ),
        markers=(_marker(7, Box(x=292, y=140, width=32, height=8), Point(x=300, y=100)),)
        if with_stub
        else (),
    )


def test_a_route_and_a_stub_each_give_their_own_code_once() -> None:
    found = _found(_split_layout())
    over = [subjects for code, subjects in found if code == WIRE_OVER_LABEL]
    crossed = [subjects for code, subjects in found if code == TEXT_CROSSED_BY_ROUTE]
    assert [code for code, _ in found] == sorted([WIRE_OVER_LABEL, TEXT_CROSSED_BY_ROUTE])
    assert over == [
        _subjects(hid("conductor", 1), hid("port", 12), hid("port", 21), hid("function", 9))
    ]
    assert crossed == [_subjects(hid("conductor", 5), hid("port", 7), hid("function", 10))]


def test_a_route_alone_is_never_text_crossed() -> None:
    """Guards against the two codes reporting one defect: a route is `WIRE_OVER_LABEL` only."""
    assert [code for code, _ in _found(_split_layout(with_stub=False))] == [WIRE_OVER_LABEL]
