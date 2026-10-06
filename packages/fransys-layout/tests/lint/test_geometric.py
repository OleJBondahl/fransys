"""WP11 acceptance skeletons: `lint.geometric` (ROADMAP WP11, docs/design/lint.md 6.8).

Every code has an input that triggers it; the clean page triggers none.
"""

import dataclasses
import itertools
import re
from pathlib import Path

import pytest
from samples import SHEET, hid, page_plan, placed, through_geometry

from fransys_layout.geometry import (
    Box,
    Facing,
    LayoutError,
    Point,
    PortGeometry,
)
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import (
    ALL_CODES,
    OUT_OF_CONTENT_BOX,
    REDUNDANT_JOG,
    SYMBOL_OVERLAP,
    WIRE_NOT_ORTHOGONAL,
    WIRE_OVER_LABEL,
    WIRE_THROUGH_SYMBOL,
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
from fransys_model.kernel import Id, Severity


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


def test_a_clean_page_has_no_findings() -> None:
    """Two stacked symbols and one straight wire between their ports: nothing to report."""
    assert _codes(_layout(routes=(_wire(((104, 112), (104, 288))),))) == []


def test_a_diagonal_segment_is_reported() -> None:
    """A segment that changes x and y at once is `WIRE_NOT_ORTHOGONAL`."""
    assert _codes(_layout(routes=(_wire(((104, 112), (120, 288))),))) == [WIRE_NOT_ORTHOGONAL]


def test_a_wire_through_an_unrelated_symbol_is_reported() -> None:
    """Function 3 stands on the straight wire between 1 and 2."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    layout = _layout(functions=functions, routes=(_wire(((104, 112), (104, 288))),))
    findings = lint_geometry(layout, sheet=SHEET)
    assert [f.code for f in findings] == [WIRE_THROUGH_SYMBOL]
    assert hid("function", 3) in findings[0].subjects


def test_a_wire_over_a_label_is_reported() -> None:
    """A label box across the wire is `WIRE_OVER_LABEL`."""
    label = PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", 9),
        slot="tag",
        drawing_set=1,
        page=1,
        box=Box(x=96, y=196, width=32, height=8),
    )
    layout = _layout(routes=(_wire(((104, 112), (104, 288))),), labels=(label,))
    assert _codes(layout) == [WIRE_OVER_LABEL]


def test_a_jog_with_nothing_to_avoid_is_reported() -> None:
    """Out, over, back: a detour around empty space is `REDUNDANT_JOG`."""
    jog = _wire(((104, 112), (104, 160), (136, 160), (136, 200), (104, 200), (104, 288)))
    assert _codes(_layout(routes=(jog,))) == [REDUNDANT_JOG]


def test_a_jog_around_a_symbol_is_not_redundant() -> None:
    """The same detour with function 3 in the way is justified."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    jog = _wire(((104, 112), (104, 160), (168, 160), (168, 240), (104, 240), (104, 288)))
    assert _codes(_layout(functions=functions, routes=(jog,))) == []


def test_overlapping_keepout_boxes_are_reported() -> None:
    """Two symbols 16 G apart overlap: `SYMBOL_OVERLAP` naming both functions."""
    functions = (placed(1, x=104, y=96), placed(2, x=120, y=96, name="b"))
    findings = lint_geometry(_layout(functions=functions), sheet=SHEET)
    assert [f.code for f in findings] == [SYMBOL_OVERLAP]
    assert set(findings[0].subjects) == {hid("function", 1), hid("function", 2)}


def test_a_symbol_outside_the_content_box_is_reported() -> None:
    """A keep-out box past the right edge of the 1280 G sheet is `OUT_OF_CONTENT_BOX`."""
    functions = (placed(1, x=1272, y=96),)
    assert _codes(_layout(functions=functions)) == [OUT_OF_CONTENT_BOX]


def test_routes_of_two_nets_meeting_at_a_cell_are_not_chained_into_a_jog() -> None:
    """Net 1 turns at (104, 200) where net 2 passes: two wires, not one wire with a jog."""
    first = _wire(((104, 112), (104, 200), (40, 200)), number=1)
    second = _wire(((168, 200), (104, 200), (104, 288)), number=2)
    assert REDUNDANT_JOG not in _codes(_layout(routes=(first, second)))


def test_the_same_shape_on_one_net_is_a_jog() -> None:
    """The can-fail half: both pieces on net 1 form out, over, back."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    assert REDUNDANT_JOG in _codes(_layout(routes=(first, second)))


def test_a_label_inside_its_own_symbols_keepout_box_is_clean() -> None:
    """A tag in its slot overlaps its own keep-out box by definition: not a finding."""
    label = PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", 1),
        slot="tag",
        drawing_set=1,
        page=1,
        box=Box(x=120, y=92, width=32, height=8),
    )
    assert _codes(_layout(labels=(label,))) == []


_CODE_CONSTANT = re.compile(r'^([A-Z][A-Z_]+) = "([A-Z][A-Z_]+)"$', re.MULTILINE)


def test_every_code_constant_in_the_package_is_listed() -> None:
    """A module that defines a finding code `ALL_CODES` does not list fails this test."""
    package = Path(__file__).resolve().parents[2] / "src" / "fransys_layout"
    defined = {
        value
        for path in sorted(package.rglob("*.py"))
        for name, value in _CODE_CONSTANT.findall(path.read_text(encoding="utf-8"))
        if name == value
    }
    assert defined == set(ALL_CODES)
    assert list(ALL_CODES) == sorted(ALL_CODES)


def test_the_listing_check_can_fail() -> None:
    """The pattern does find a code constant, so an unlisted one would be caught."""
    assert _CODE_CONSTANT.findall('UNLISTED_CODE = "UNLISTED_CODE"\n') == [
        ("UNLISTED_CODE", "UNLISTED_CODE")
    ]


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


def test_a_route_with_two_diagonal_segments_is_one_finding_naming_the_route() -> None:
    """Two diagonal segments in one route are one finding, on the route's `(connection, a, b)`."""
    route = _wire(((104, 112), (120, 160), (120, 200), (136, 288)))
    assert _found(_layout(routes=(route,))) == [(WIRE_NOT_ORTHOGONAL, _route_ids(1))]


@pytest.mark.parametrize(
    "points",
    [
        pytest.param(((104, 112), (104, 160), (168, 160)), id="an L"),
        pytest.param(((104, 112), (104, 112), (104, 288)), id="a repeated point"),
        pytest.param(((104, 112), (104, 112)), id="two ports on one cell, the route [p, p]"),
    ],
)
def test_an_orthogonal_route_is_not_reported(points: tuple[tuple[int, int], ...]) -> None:
    """An L, a repeated point and the route `[p, p]` have no segment that turns x and y at once."""
    assert WIRE_NOT_ORTHOGONAL not in _codes(_layout(routes=(_wire(points),)))


def test_a_diagonal_segment_takes_part_in_no_other_check() -> None:
    """The diagonal runs near function 3 and a label; only its own code is reported."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    label = _label(9, Box(x=118, y=196, width=16, height=8))
    route = _wire(((104, 112), (136, 288)))
    assert _found(_layout(functions=functions, routes=(route,), labels=(label,))) == [
        (WIRE_NOT_ORTHOGONAL, _route_ids(1))
    ]


# --- WIRE_THROUGH_SYMBOL ---------------------------------------------------------------


def test_the_through_finding_names_the_route_and_the_function() -> None:
    """The finding's subjects are the route's `(connection, a, b)` and the function."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    layout = _layout(functions=functions, routes=(_wire(((104, 112), (104, 288))),))
    assert _found(layout) == [
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 3), hid("port", 12), hid("port", 21)),
        )
    ]


def test_the_same_page_without_the_function_in_the_way_is_clean() -> None:
    """The twin of the previous test: function 3 moved off the wire."""
    functions = (placed(1, x=104, y=96), placed(3, x=304, y=200), placed(2, x=104, y=304))
    assert _codes(_layout(functions=functions, routes=(_wire(((104, 112), (104, 288))),))) == []


@pytest.mark.parametrize(
    ("x", "expected"),
    [(152, []), (151, [WIRE_THROUGH_SYMBOL]), (96, []), (97, [WIRE_THROUGH_SYMBOL])],
    ids=["flush right", "1 G in from the right", "flush left", "1 G in from the left"],
)
def test_a_run_flush_with_a_border_is_not_through_it(x: int, expected: list[str]) -> None:
    """Function 3's keep-out box spans x 96 to 152; the interior test is strict."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    assert _codes(_layout(functions=functions, routes=(_wire(((x, 112), (x, 288))),))) == expected


@pytest.mark.parametrize(
    ("end", "expected"),
    [(184, []), (185, [WIRE_THROUGH_SYMBOL])],
    ids=["ends on the top border", "ends 1 G inside"],
)
def test_a_run_resting_its_end_on_a_border_is_not_through(end: int, expected: list[str]) -> None:
    """Function 3's keep-out box spans y 184 to 216."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    assert (
        _codes(_layout(functions=functions, routes=(_wire(((104, 112), (104, end))),))) == expected
    )


def test_one_finding_per_route_and_function_however_often_the_route_crosses_it() -> None:
    """Crossing function 3's box twice is one finding; crossing a second function adds one."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(4, x=104, y=248))
    twice = _wire(((60, 190), (200, 190), (200, 210), (80, 210)))
    assert _found(_layout(functions=functions, routes=(twice,))) == [
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 3), hid("port", 12), hid("port", 21)),
        )
    ]
    both = _wire(((104, 190), (104, 260)))
    assert _found(_layout(functions=functions, routes=(both,))) == [
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 3), hid("port", 12), hid("port", 21)),
        ),
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 4), hid("port", 12), hid("port", 21)),
        ),
    ]


def test_two_routes_through_one_function_are_two_findings() -> None:
    """One finding per (route, function) pair: two routes through one function are two."""
    functions = (placed(3, x=104, y=200),)
    routes = (_wire(((104, 190), (104, 210)), number=1), _wire(((110, 190), (110, 210)), number=2))
    assert [c for c, _ in _found(_layout(functions=functions, routes=routes))] == [
        WIRE_THROUGH_SYMBOL,
        WIRE_THROUGH_SYMBOL,
    ]


def test_a_repeated_point_inside_a_foreign_box_tests_nothing() -> None:
    """A zero-length segment has no interior to pass through; a real one does."""
    functions = (placed(3, x=104, y=200),)
    assert _codes(_layout(functions=functions, routes=(_wire(((104, 200), (104, 200))),))) == []
    assert _codes(_layout(functions=functions, routes=(_wire(((104, 200), (104, 240))),))) == [
        WIRE_THROUGH_SYMBOL
    ]


_LANES = [
    pytest.param(((200, 184), (200, 100)), ((200, 184), (200, 220)), id="N"),
    pytest.param(((200, 216), (200, 300)), ((200, 216), (200, 190)), id="S"),
    pytest.param(((216, 200), (300, 200)), ((216, 200), (190, 200)), id="E"),
    pytest.param(((184, 200), (100, 200)), ((184, 200), (210, 200)), id="W"),
]


@pytest.mark.parametrize("reverse", [False, True], ids=["from the port", "to the port"])
@pytest.mark.parametrize(("outward", "inward"), _LANES)
def test_a_run_on_an_endpoint_ports_outward_lane_is_exempt_and_the_inward_run_is_not(
    outward: tuple[tuple[int, int], ...], inward: tuple[tuple[int, int], ...], *, reverse: bool
) -> None:
    """A route may run out of a port through its own symbol's box, along the lane only."""

    def route(points: tuple[tuple[int, int], ...]) -> Route:
        return _wire(points[::-1] if reverse else points)

    assert _codes(_layout(functions=(_star(),), routes=(route(outward),))) == []
    assert _codes(_layout(functions=(_star(),), routes=(route(inward),))) == [WIRE_THROUGH_SYMBOL]


def test_a_sideways_run_from_a_port_is_not_on_its_lane() -> None:
    """The N port's lane is vertical: a horizontal run from it is through its own box."""
    route = _wire(((200, 184), (232, 184)))
    assert _codes(_layout(functions=(_star(),), routes=(route,))) == [WIRE_THROUGH_SYMBOL]


def test_a_vertex_at_a_port_is_not_an_end_of_the_route() -> None:
    """Only the first and last vertex name endpoint symbols: passing a port is crossing."""
    passing = _wire(((200, 100), (200, 184), (200, 300)))
    assert _codes(_layout(functions=(_star(),), routes=(passing,))) == [WIRE_THROUGH_SYMBOL]
    ending = _wire(((200, 100), (200, 184)))
    assert _codes(_layout(functions=(_star(),), routes=(ending,))) == []


@pytest.mark.parametrize(
    "out",
    [(240, 200), (200, 240), (160, 200), (200, 160)],
    ids=["E", "S", "W", "N"],
)
def test_several_ports_on_one_point_give_several_lanes(out: tuple[int, int]) -> None:
    """A junction dot has four ports at its centre: each direction leaves along its own lane."""
    assert _codes(_layout(functions=(_dot(),), routes=(_wire(((200, 200), out)),))) == []


def test_a_foreign_symbol_is_not_exempt_on_the_same_line() -> None:
    """The route ends at function 7's port; function 8's box on the same lane is still crossed."""
    other = placed(8, x=200, y=264)
    route = _wire(((200, 216), (200, 300)))
    assert _found(_layout(functions=(_star(), other), routes=(route,))) == [
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 8), hid("port", 12), hid("port", 21)),
        )
    ]


def test_a_run_on_a_ports_ray_is_exempt_only_when_the_route_ends_at_the_port() -> None:
    """The lane is the route's own: the same run on the N ray from (200, 180) is through the box.

    The run (200, 180) to (200, 100) lies wholly on the N port's ray but the route does not end
    at the port (200, 184), so the port is not one of its own ends.

    # UNDO: in `own_ends_at`, `if at in ends` becomes `if True` (the test finds nothing)
    """
    route = _wire(((200, 180), (200, 100)))
    assert _codes(_layout(functions=(_star(),), routes=(route,))) == [WIRE_THROUGH_SYMBOL]
    ending = _wire(((200, 184), (200, 100)))
    assert _codes(_layout(functions=(_star(),), routes=(ending,))) == []


# --- WIRE_OVER_LABEL -------------------------------------------------------------------


def test_the_label_finding_names_the_route_and_the_label_subject() -> None:
    """The finding's subjects are the route's `(connection, a, b)` and the label's subject."""
    label = _label(9, Box(x=96, y=196, width=32, height=8))
    assert _found(_layout(routes=(_wire(((104, 112), (104, 288))),), labels=(label,))) == [
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("function", 9), hid("port", 12), hid("port", 21)),
        )
    ]


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(Box(x=96, y=196, width=32, height=8), [WIRE_OVER_LABEL], id="across"),
        pytest.param(Box(x=104, y=196, width=32, height=8), [], id="resting on it, right"),
        pytest.param(Box(x=72, y=196, width=32, height=8), [], id="resting on it, left"),
        pytest.param(Box(x=103, y=196, width=32, height=8), [WIRE_OVER_LABEL], id="1 G across"),
        pytest.param(
            Box(x=73, y=196, width=32, height=8), [WIRE_OVER_LABEL], id="1 G across, left"
        ),
        pytest.param(Box(x=96, y=288, width=32, height=8), [], id="beyond its lower end"),
        pytest.param(
            Box(x=96, y=287, width=32, height=8), [WIRE_OVER_LABEL], id="1 G past its end"
        ),
        pytest.param(Box(x=96, y=104, width=32, height=8), [], id="above its upper end"),
        pytest.param(
            Box(x=96, y=105, width=32, height=8), [WIRE_OVER_LABEL], id="reaches 1 G into the run"
        ),
        pytest.param(
            Box(x=96, y=113, width=32, height=8), [WIRE_OVER_LABEL], id="1 G into the run"
        ),
    ],
)
def test_a_label_is_over_a_wire_only_when_the_wire_crosses_its_interior(
    box: Box, expected: list[str]
) -> None:
    """Both axes are strict: resting on a wire or past its end is not over it.

    No symbols on the page: the boundary boxes probed here reach into the default pair's
    own bodies, which is `TEXT_OVERLAP`'s, not this check's.
    """
    layout = _layout(
        functions=(), routes=(_wire(((104, 112), (104, 288))),), labels=(_label(9, box),)
    )
    assert _codes(layout) == expected


def test_a_horizontal_run_is_tested_the_same_way() -> None:
    """A label resting on a horizontal run is clean; one across it is not."""
    route = _wire(((40, 200), (200, 200)))
    over = _label(9, Box(x=100, y=196, width=32, height=8))
    resting = _label(9, Box(x=100, y=192, width=32, height=8))
    assert _codes(_layout(routes=(route,), labels=(over,))) == [WIRE_OVER_LABEL]
    assert _codes(_layout(routes=(route,), labels=(resting,))) == []


def test_two_labels_of_one_subject_give_one_finding_and_two_subjects_give_two() -> None:
    """The finding is per (route, label subject) pair, so a subject's second label adds none."""
    route = _wire(((104, 112), (104, 288)))
    one = _label(9, Box(x=96, y=196, width=32, height=8))
    same = _label(9, Box(x=96, y=236, width=32, height=8), slot="value", kind=LabelKind.MARKING)
    other = _label(8, Box(x=96, y=236, width=32, height=8))
    assert _codes(_layout(routes=(route,), labels=(one, same))) == [WIRE_OVER_LABEL]
    assert _found(_layout(routes=(route,), labels=(one, other))) == [
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("function", 8), hid("port", 12), hid("port", 21)),
        ),
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("function", 9), hid("port", 12), hid("port", 21)),
        ),
    ]


def test_a_wire_labels_own_route_counts_like_any_other() -> None:
    """A wire label across its own route is over a wire; the subject repeats the connection once."""
    label = PlacedLabel(
        kind=LabelKind.WIRE,
        subject=hid("conductor", 1),
        slot="",
        drawing_set=1,
        page=1,
        box=Box(x=96, y=196, width=32, height=8),
    )
    assert _found(_layout(routes=(_wire(((104, 112), (104, 288))),), labels=(label,))) == [
        (WIRE_OVER_LABEL, _route_ids(1))
    ]


def test_a_label_on_another_page_is_not_over_this_pages_wire() -> None:
    """Pages never interact: the same label on the route's own page is over it."""
    route = _wire(((104, 112), (104, 288)))
    box = Box(x=96, y=196, width=32, height=8)
    assert _codes(_layout(routes=(route,), labels=(_label(9, box, page=2),))) == []
    assert _codes(_layout(routes=(route,), labels=(_label(9, box, page=1),))) == [WIRE_OVER_LABEL]


# --- link markers (decision layout-0019) -----------------------------------------------


def test_a_wire_over_a_marker_box_is_reported_with_the_markers_port() -> None:
    """A marker box across the wire is `WIRE_OVER_LABEL`; its subject is the marker's port."""
    marker = _marker(7, Box(x=96, y=196, width=32, height=8))
    layout = _layout(routes=(_wire(((104, 112), (104, 288))),), markers=(marker,))
    # subjects are stored in handle order: the conductor, then ports 7, 12 and 21
    assert _found(layout) == [
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("port", 7), hid("port", 12), hid("port", 21)),
        )
    ]


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(Box(x=96, y=196, width=32, height=8), [WIRE_OVER_LABEL], id="across"),
        pytest.param(Box(x=104, y=196, width=32, height=8), [], id="resting on the wire"),
        pytest.param(Box(x=112, y=196, width=32, height=8), [], id="beside"),
        pytest.param(Box(x=96, y=288, width=32, height=8), [], id="beyond its end"),
    ],
)
def test_a_marker_is_over_a_wire_only_when_the_wire_crosses_its_interior(
    box: Box, expected: list[str]
) -> None:
    """The label rule: both axes strict, so a box resting on the wire is not over it.

    No symbols on the page, for the same reason as the label version above.
    """
    layout = _layout(
        functions=(), routes=(_wire(((104, 112), (104, 288))),), markers=(_marker(7, box),)
    )
    assert _codes(layout) == expected


def test_a_marker_on_another_page_is_not_over_this_pages_wire() -> None:
    """Pages never interact: the same marker on the route's own page is over it."""
    route = _wire(((104, 112), (104, 288)))
    box = Box(x=96, y=196, width=32, height=8)
    assert _codes(_layout(routes=(route,), markers=(_marker(7, box, page=2),))) == []
    assert _codes(_layout(routes=(route,), markers=(_marker(7, box, page=1),))) == [WIRE_OVER_LABEL]


def test_a_marker_and_a_label_of_one_handle_on_one_route_give_one_finding() -> None:
    """The subject is the handle, as for two labels of one subject (6.8).

    The label and the marker sit at different boxes, both across the wire, so they are two
    texts of one subject (`WIRE_OVER_LABEL`'s dedup), not one text overlapping itself.
    """
    box = Box(x=96, y=196, width=32, height=8)
    other_box = Box(x=96, y=230, width=32, height=8)
    label = dataclasses.replace(_label(9, box), subject=hid("port", 7))
    layout = _layout(
        functions=(),
        routes=(_wire(((104, 112), (104, 288))),),
        labels=(label,),
        markers=(_marker(7, other_box),),
    )
    assert _codes(layout) == [WIRE_OVER_LABEL]


_MARKER_BOX = Box(x=190, y=110, width=20, height=20)


@pytest.mark.parametrize(
    "at",
    [
        pytest.param((200, 184), id="its own port's ray"),
        pytest.param((200, 216), id="another port's ray"),
        pytest.param((150, 120), id="no placed port at marker.at"),
    ],
)
def test_a_wire_through_a_markers_box_is_reported_on_its_own_ports_ray_too(
    at: tuple[int, int],
) -> None:
    """No run is exempt: a box never stands on a drawn wire, its own pin's wire included.

    S20 M7, amended 2026-10-01 (4b6a's m7a: -X1:1's own wire ran through its turned box).
    The marker's port is the star's N port (200, 184), its S port (200, 216) or none; the
    route (200, 150) to (200, 100) lies on the N ray through `_MARKER_BOX`, and is reported
    in all three, with the marker's port in the subjects.

    # UNDO: restore the lane of the marker's own port through its own box in
    # `geometric._wires` (`crosses_unless_leaving`), failing the first case
    """
    marker = dataclasses.replace(_marker(9, _MARKER_BOX), at=Point(x=at[0], y=at[1]))
    route = _wire(((200, 150), (200, 100)))
    layout = _layout(functions=(_star(),), routes=(route,), markers=(marker,))
    over = [subjects for code, subjects in _found(layout) if code == WIRE_OVER_LABEL]
    assert len(over) == 1
    assert hid("port", 9) in over[0]


def test_two_markers_on_one_box_are_both_over_the_wire_through_it() -> None:
    """Markers 9 (the N port) and 8 (the S port) share `_MARKER_BOX`; a wire runs on the N ray.

    Each marker's port is a subject of its own finding.
    """
    north = dataclasses.replace(_marker(9, _MARKER_BOX), at=Point(x=200, y=184))
    south = dataclasses.replace(_marker(8, _MARKER_BOX), at=Point(x=200, y=216))
    route = _wire(((200, 150), (200, 100)))
    layout = _layout(functions=(_star(),), routes=(route,), markers=(north, south))
    over = [subjects for code, subjects in _found(layout) if code == WIRE_OVER_LABEL]
    assert len(over) == 2
    assert any(hid("port", 8) in subjects for subjects in over)
    assert any(hid("port", 9) in subjects for subjects in over)


def test_a_wire_that_starts_behind_a_markers_port_is_over_its_box() -> None:
    """The run (200, 190) to (200, 100) passes the N port (200, 184) from behind.

    It also runs through the star's own box from the inside, so both findings show.
    """
    marker = dataclasses.replace(_marker(9, _MARKER_BOX), at=Point(x=200, y=184))
    route = _wire(((200, 190), (200, 100)))
    layout = _layout(functions=(_star(),), routes=(route,), markers=(marker,))
    assert _codes(layout) == [WIRE_OVER_LABEL, WIRE_THROUGH_SYMBOL]


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(Box(x=1248, y=100, width=32, height=8), [], id="flush right"),
        pytest.param(Box(x=1249, y=100, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past right"),
        pytest.param(Box(x=0, y=0, width=32, height=8), [], id="flush top left"),
        pytest.param(Box(x=-1, y=0, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past left"),
        pytest.param(Box(x=0, y=879, width=32, height=8), [OUT_OF_CONTENT_BOX], id="past bottom"),
    ],
)
def test_a_marker_box_is_tested_against_the_content_box(box: Box, expected: list[str]) -> None:
    """A marker flush with an edge is inside; one grid unit past it is not."""
    assert _codes(_layout(markers=(_marker(7, box),))) == expected


def test_the_content_finding_of_a_marker_names_its_port() -> None:
    marker = _marker(7, Box(x=1270, y=100, width=32, height=8))
    assert _found(_layout(markers=(marker,))) == [(OUT_OF_CONTENT_BOX, (hid("port", 7),))]


def test_a_page_with_only_a_marker_is_linted() -> None:
    """The marker alone puts its page in the run: it leaves the content box on page 3."""
    layout = _layout(
        functions=(), markers=(_marker(7, Box(x=1270, y=100, width=32, height=8), page=3),)
    )
    assert _codes(layout) == [OUT_OF_CONTENT_BOX]


# --- REDUNDANT_JOG ---------------------------------------------------------------------


def test_a_jog_names_every_route_of_its_joined_polyline() -> None:
    """Both pieces are on net 1 and meet at (136, 160): one polyline, one finding."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    assert _found(_layout(routes=(first, second))) == [
        (
            REDUNDANT_JOG,
            (
                hid("conductor", 1),
                hid("conductor", 2),
                hid("port", 12),
                hid("port", 21),
            ),
        )
    ]


def test_the_same_pieces_on_two_nets_are_two_wires_and_no_jog() -> None:
    """The twin of the one-net case: two physical nets are never chained."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=2)
    assert _codes(_layout(routes=(first, second))) == []


def test_pieces_of_one_net_on_two_pages_are_not_joined() -> None:
    """Routes join within a page only."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1, page=2)
    assert _codes(_layout(routes=(first, second))) == []


@pytest.mark.parametrize(
    "points",
    [
        pytest.param(_JOG, id="out, over, back"),
        pytest.param(
            ((104, 112), (104, 160), (72, 160), (72, 200), (104, 200), (104, 288)), id="mirrored"
        ),
        pytest.param(
            ((40, 200), (80, 200), (80, 232), (120, 232), (120, 200), (200, 200)),
            id="a bump on a horizontal wire",
        ),
        pytest.param(
            ((104, 112), (104, 160), (120, 160), (136, 160), (136, 200), (104, 200), (104, 288)),
            id="a vertex in the middle of an arm",
        ),
        pytest.param(
            ((104, 112), (104, 160), (136, 160), (136, 160), (136, 200), (104, 200), (104, 288)),
            id="a repeated point",
        ),
        pytest.param(
            (
                (104, 112),
                (104, 128),
                (136, 128),
                (136, 144),
                (104, 144),
                (104, 176),
                (136, 176),
                (136, 192),
                (104, 192),
                (104, 288),
            ),
            id="two jogs are one finding",
        ),
    ],
)
def test_a_jog_is_three_legs_that_leave_a_line_and_re_enter_it(
    points: tuple[tuple[int, int], ...],
) -> None:
    """Equal, opposite arms across a middle leg are a jog, however the route is spelled."""
    assert _found(_layout(routes=(_wire(points),))) == [(REDUNDANT_JOG, _route_ids(1))]


@pytest.mark.parametrize(
    "points",
    [
        pytest.param(
            ((104, 112), (104, 160), (136, 160), (136, 200), (120, 200), (120, 288)),
            id="arms of unequal length",
        ),
        pytest.param(
            ((104, 112), (104, 160), (136, 160), (136, 200), (168, 200), (168, 288)),
            id="a staircase",
        ),
        pytest.param(
            ((104, 112), (104, 160), (136, 160), (140, 200), (108, 200), (108, 288)),
            id="a diagonal in the middle",
        ),
        pytest.param(((104, 112), (104, 160), (168, 160), (168, 288)), id="an L"),
    ],
)
def test_what_does_not_return_to_its_line_is_not_a_jog(points: tuple[tuple[int, int], ...]) -> None:
    """Unequal arms, a staircase, a diagonal middle and an L are not jogs."""
    assert REDUNDANT_JOG not in _codes(_layout(routes=(_wire(points),)))


def test_a_grazed_box_blocks_the_straight_run_but_a_box_beside_it_does_not() -> None:
    """The router's closed test decides: a keep-out box that only touches the run blocks it.

    The box's right edge is on x = 104, the line the jog leaves and re-enters. The interior test
    would call the run free; the router could not have drawn it, so the detour is justified.
    """
    grazed = (placed(1, x=104, y=96), placed(3, x=56, y=184), placed(2, x=104, y=304))
    beside = (placed(1, x=104, y=96), placed(3, x=48, y=184), placed(2, x=104, y=304))
    route = _wire(_JOG)
    assert _codes(_layout(functions=grazed, routes=(route,))) == []
    assert _codes(_layout(functions=beside, routes=(route,))) == [REDUNDANT_JOG]


def test_a_label_box_blocks_the_straight_run_like_a_keepout_box() -> None:
    """A label box that only touches the straight run blocks it; one beside it does not."""
    route = _wire(_JOG)
    grazed = _label(9, Box(x=72, y=172, width=32, height=8))
    beside = _label(9, Box(x=64, y=172, width=32, height=8))
    assert _codes(_layout(routes=(route,), labels=(grazed,))) == []
    assert _codes(_layout(routes=(route,), labels=(beside,))) == [REDUNDANT_JOG]


def test_a_marker_box_on_the_straight_run_justifies_the_detour_and_one_off_it_does_not() -> None:
    """The router detours round a marker it was given as reserved; the lint agrees (layout-0028).

    The straight run of `_JOG` is x = 104 from y = 160 to 200. The marker box on it blocks
    it, so the jog is not redundant; the same box well beside it leaves the jog reported.
    """
    route = _wire(_JOG)
    on_the_run = _marker(33, Box(x=100, y=172, width=8, height=8))
    beside = _marker(33, Box(x=40, y=172, width=8, height=8))
    assert _found(_layout(routes=(route,), markers=(on_the_run,))) == []
    assert [c for c, _ in _found(_layout(routes=(route,), markers=(beside,)))] == [REDUNDANT_JOG]


def test_a_marker_box_blocks_the_straight_run_like_a_label_box() -> None:
    """A marker box that only touches the straight run blocks it; one beside it does not."""
    route = _wire(_JOG)
    grazed = _marker(33, Box(x=72, y=172, width=32, height=8))
    beside = _marker(33, Box(x=64, y=172, width=32, height=8))
    assert _codes(_layout(routes=(route,), markers=(grazed,))) == []
    assert _codes(_layout(routes=(route,), markers=(beside,))) == [REDUNDANT_JOG]


def test_a_marker_box_of_another_page_does_not_block_this_pages_straight_run() -> None:
    """The obstacles are those of the jog's own page."""
    on_the_run = _marker(33, Box(x=100, y=172, width=8, height=8), page=2)
    assert _codes(_layout(routes=(_wire(_JOG),), markers=(on_the_run,))) == [REDUNDANT_JOG]


def test_a_marker_box_across_a_keepout_box_is_not_a_symbol_overlap() -> None:
    """A marker box is an obstacle for the jog check only; two keep-out boxes are compared alone."""
    across = _marker(33, Box(x=90, y=90, width=32, height=16))
    assert SYMBOL_OVERLAP not in _codes(_layout(markers=(across,)))


def test_another_route_is_not_an_obstacle_to_the_straight_run() -> None:
    """A crossing costs the router a penalty and never a jog."""
    crossing = _wire(((60, 180), (90, 180), (150, 180)), number=2, net=2)
    assert [c for c, _ in _found(_layout(routes=(_wire(_JOG), crossing)))] == [REDUNDANT_JOG]


@pytest.mark.parametrize("reverse", [False, True], ids=["lane at the head", "lane at the tail"])
def test_a_jog_on_an_endpoint_ports_lane_is_redundant_across_the_joined_routes(
    *, reverse: bool
) -> None:
    """The straight run lies on function 1's lane, inside its tall keep-out box.

    The lane belongs to the first route's end; the jog is closed by the second route, so the
    lanes of every route of the polyline count. `reverse` stores both routes backwards, which
    walks the polyline from the other end.
    """
    functions = (_tall(1, x=104, y=96), placed(2, x=104, y=304))
    first = ((104, 112), (104, 120), (136, 120))
    second = ((136, 120), (136, 136), (104, 136), (104, 288))
    routes = (
        _wire(first[::-1] if reverse else first, number=1, net=1),
        _wire(second[::-1] if reverse else second, number=2, net=1),
    )
    assert REDUNDANT_JOG in _codes(_layout(functions=functions, routes=routes))


def test_the_same_jog_off_the_port_is_blocked_by_the_symbol() -> None:
    """Starting 4 G below the port, the route is not at function 1's port: no lane, no jog."""
    functions = (_tall(1, x=104, y=96), placed(2, x=104, y=304))
    route = _wire(((104, 116), (104, 120), (136, 120), (136, 136), (104, 136), (104, 288)))
    assert REDUNDANT_JOG not in _codes(_layout(functions=functions, routes=(route,)))


# The jog of the first route starts at the route's own end cell (104, 112); the second starts
# one grid unit in, at (104, 120). Their straight runs are x = 104 from y 112 to 152 and from
# y 120 to 160.
_AT_THE_END = ((104, 112), (136, 112), (136, 152), (104, 152), (104, 288))
_ONE_IN = ((104, 112), (104, 120), (136, 120), (136, 160), (104, 160), (104, 288))


@pytest.mark.parametrize(
    ("points", "box", "expected"),
    [
        pytest.param(
            _AT_THE_END, Box(x=88, y=104, width=32, height=8), True, id="on the route's end cell"
        ),
        pytest.param(
            _ONE_IN, Box(x=88, y=120, width=32, height=8), False, id="on a cell one unit in"
        ),
    ],
)
def test_a_box_edge_on_the_straights_own_end_cell_does_not_block_it_but_on_another_cell_does(
    points: tuple[tuple[int, int], ...], box: Box, *, expected: bool
) -> None:
    """The router leaves a route's end cell free (layout-0038's margin); the lint asks the same.

    The label box has an edge on the straight's first cell: its bottom edge on the end cell
    (104, 112), or its top edge on (104, 120), a cell that is not an end. Only the first is free.

    UNDO: in `_jogs._admitted`, `run_admitted` is given `frozenset()` for the end cells.
    """
    layout = _layout(routes=(_wire(points),), labels=(_label(9, box),))
    assert (REDUNDANT_JOG in _codes(layout)) is expected


@pytest.mark.parametrize(
    ("marker_at", "expected"),
    [
        pytest.param((104, 112), True, id="the marker of the route's own port"),
        pytest.param((104, 168), False, id="the marker of another port, on the same line"),
    ],
)
def test_a_straight_along_its_own_ports_marker_stub_lane_is_not_blocked_and_along_anothers_is(
    marker_at: tuple[int, int], *, expected: bool
) -> None:
    """A marker box is owned by its port, and only that port's lane goes through it (13.18).

    The marker box, y 120 to 128, lies across the straight x = 104, y 112 to 152. The marker at
    function 1's port (104, 112), which the route ends on, has a lane through it that the router
    would use. A marker of function 3's `in` port at (104, 168), which faces N along the same
    line but is not an end of the route, has none: the box blocks.

    UNDO: in `_segments.own_ends_at`, the marker's end is added whether or not `marker.at in ends`
    (case 2), or in `geometric._jogs` the marker's box is owned by `None` (case 1).
    """
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=184), placed(2, x=104, y=304))
    at = Point(x=marker_at[0], y=marker_at[1])
    marker = dataclasses.replace(_marker(12, Box(x=84, y=120, width=40, height=8)), at=at)
    layout = _layout(functions=functions, routes=(_wire(_AT_THE_END),), markers=(marker,))
    assert (REDUNDANT_JOG in _codes(layout)) is expected


def test_a_straight_along_its_own_ports_lane_past_the_lanes_far_end_is_not_blocked() -> None:
    """Function 1's `out` port lane ends one step past its keep-out, at y 136; the straight goes on.

    The straight x = 104, y 120 to 160 is longer than the lane, and no lane contains it. Each
    step that touches the keep-out is inside it, so the router could have drawn it, and the
    old unbounded ray freed it too: the finding is the same before and after (layout-0083).

    UNDO: in `_jogs._admitted`, `run_admitted` becomes `step_admitted` (the whole run in one call).
    """
    functions = (_tall(1, x=104, y=96), placed(2, x=104, y=304))
    layout = _layout(functions=functions, routes=(_wire(_ONE_IN),))
    assert REDUNDANT_JOG in _codes(layout)


def test_three_route_ends_at_one_point_join_nothing() -> None:
    """Exactly two ends join; a third at the same point makes a junction."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    third = _wire(((136, 160), (136, 180)), number=3, net=1)
    assert _codes(_layout(routes=(first, second, third))) == []
    assert _codes(_layout(routes=(first, second))) == [REDUNDANT_JOG]


def test_two_ports_on_one_cell_count_as_two_ends_there() -> None:
    """The route [p, p] puts two ends at p, so the two real routes are a junction, not a chain."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    coincident = _wire(((136, 160), (136, 160)), number=3, net=1)
    assert _codes(_layout(routes=(first, second, coincident))) == []


def test_an_end_landing_inside_another_routes_segment_joins_nothing() -> None:
    """A T is not a chain: only ends meeting ends join."""
    first = _wire(((104, 112), (104, 160), (168, 160)), number=1, net=1)
    second = _wire(((136, 160), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    assert _codes(_layout(routes=(first, second))) == []


@pytest.mark.parametrize(
    "numbers",
    list(itertools.permutations((1, 2, 3))),
    ids=lambda numbers: "".join(str(n) for n in numbers),
)
def test_a_chain_of_three_is_found_whatever_the_handle_order(numbers: tuple[int, int, int]) -> None:
    """A, B, C are joined end to end; the middle route B is stored backwards."""
    a, b, c = numbers
    first = _wire(((104, 112), (104, 160)), number=a, net=1)
    middle = _wire(((136, 200), (136, 160), (104, 160)), number=b, net=1)
    last = _wire(((136, 200), (104, 200), (104, 288)), number=c, net=1)
    (finding,) = lint_geometry(_layout(routes=(first, middle, last)), sheet=SHEET)
    assert finding.code == REDUNDANT_JOG
    assert finding.subjects == (
        hid("conductor", 1),
        hid("conductor", 2),
        hid("conductor", 3),
        hid("port", 12),
        hid("port", 21),
    )


def test_a_ring_of_two_routes_between_the_same_ports_is_judged_once() -> None:
    """Two conductors on one net between the same two ports join at both ends."""
    straight = _wire(((104, 112), (104, 288)), number=1, net=1)
    jogged = _wire(_JOG, number=2, net=1)
    other = _wire(((104, 112), (104, 288)), number=3, net=1)
    assert _found(_layout(routes=(straight, jogged))) == [
        (
            REDUNDANT_JOG,
            (hid("conductor", 1), hid("conductor", 2), hid("port", 12), hid("port", 21)),
        )
    ]
    assert _codes(_layout(routes=(straight, other))) == []


# --- SYMBOL_OVERLAP --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("x", "expected"),
    [(160, []), (159, [SYMBOL_OVERLAP])],
    ids=["keep-out boxes share an edge", "1 G of overlap"],
)
def test_keepout_boxes_that_share_only_an_edge_do_not_overlap(x: int, expected: list[str]) -> None:
    """Function 1's box spans x 96 to 152, so function 2 at x = 160 starts at 152."""
    assert _codes(_layout(functions=(placed(1, x=104, y=96), placed(2, x=x, y=96)))) == expected


def test_an_overlapping_pair_is_named_in_handle_order_once() -> None:
    """Three mutually overlapping symbols are three pairs, each named in handle order."""
    functions = (placed(3, x=104, y=96), placed(1, x=120, y=96), placed(2, x=112, y=96))
    assert _found(_layout(functions=functions)) == [
        (SYMBOL_OVERLAP, (hid("function", 1), hid("function", 2))),
        (SYMBOL_OVERLAP, (hid("function", 1), hid("function", 3))),
        (SYMBOL_OVERLAP, (hid("function", 2), hid("function", 3))),
    ]


def test_symbols_of_different_pages_never_overlap_and_one_function_may_be_on_two_pages() -> None:
    """A terminal drawn on two pages is not a fault, and pages do not overlap one another."""
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=104, y=96, page=2),
        placed(1, x=104, y=96, page=2),
    )
    assert _found(_layout(functions=functions)) == [
        (SYMBOL_OVERLAP, (hid("function", 1), hid("function", 2)))
    ]
    assert _codes(_layout(functions=(placed(1, x=104, y=96), placed(1, x=104, y=96, page=2)))) == []


def test_one_function_placed_twice_on_one_page_is_a_fault() -> None:
    """Two placements of one function on one page raise `LayoutError`."""
    functions = (placed(1, x=104, y=96), placed(2, x=104, y=200), placed(1, x=104, y=304))
    with pytest.raises(LayoutError):
        lint_geometry(_layout(functions=functions), sheet=SHEET)
    apart = (placed(1, x=104, y=96), placed(2, x=104, y=200), placed(1, x=104, y=304, page=2))
    assert _codes(_layout(functions=apart)) == []


def test_a_label_in_a_foreign_keepout_box_is_not_a_symbol_overlap() -> None:
    """The lint never compares a label with a keep-out box: `labels` refuses a foreign one."""
    foreign = _label(2, Box(x=120, y=92, width=32, height=8))
    assert _codes(_layout(labels=(foreign,))) == []


# --- OUT_OF_CONTENT_BOX ----------------------------------------------------------------


_KEEPOUT = Box(x=-8, y=-16, width=56, height=32)


@pytest.mark.parametrize(
    ("x", "y", "keepout", "expected"),
    [
        pytest.param(1232, 96, _KEEPOUT, [], id="flush with the right edge"),
        pytest.param(
            1232,
            96,
            dataclasses.replace(_KEEPOUT, width=57),
            [OUT_OF_CONTENT_BOX],
            id="1 G past the right edge",
        ),
        pytest.param(8, 96, _KEEPOUT, [], id="flush with the left edge"),
        pytest.param(
            8,
            96,
            dataclasses.replace(_KEEPOUT, x=-9, width=57),
            [OUT_OF_CONTENT_BOX],
            id="1 G past the left edge",
        ),
        pytest.param(104, 16, _KEEPOUT, [], id="flush with the top edge"),
        pytest.param(
            104,
            16,
            dataclasses.replace(_KEEPOUT, y=-17, height=33),
            [OUT_OF_CONTENT_BOX],
            id="1 G past the top edge",
        ),
        pytest.param(
            104, 872, dataclasses.replace(_KEEPOUT, height=30), [], id="flush with the bottom edge"
        ),
        pytest.param(
            104,
            872,
            dataclasses.replace(_KEEPOUT, height=31),
            [OUT_OF_CONTENT_BOX],
            id="1 G past the bottom edge",
        ),
    ],
)
def test_a_keepout_box_flush_with_the_content_box_is_inside_it(
    x: int, y: int, keepout: Box, expected: list[str]
) -> None:
    """Origins stay on the wiring grid; the 1 G offset is in the keep-out box.

    The content box is 1280 x 886 and its bottom edge is not on the grid, so the bottom
    cases shorten the box from 32 G to 30 G instead of moving the origin.
    """
    geometry = dataclasses.replace(through_geometry(), keepout=keepout)
    box_at = dataclasses.replace(placed(1, x=x, y=y), geometry=geometry)
    assert _codes(_layout(functions=(box_at,))) == expected


def test_the_content_finding_names_the_function_the_label_subject_and_the_route() -> None:
    """A symbol, a label and a route outside the content box are three findings.

    The label sits clear of the symbol's own body (`TEXT_OVERLAP`'s), still out of content.
    """
    layout = _layout(
        functions=(placed(1, x=1272, y=96),),
        routes=(_wire(((104, 112), (1300, 112), (1300, 288))),),
        labels=(_label(9, Box(x=1270, y=300, width=32, height=8)),),
    )
    assert _found(layout) == [
        (OUT_OF_CONTENT_BOX, (hid("conductor", 1), hid("port", 12), hid("port", 21))),
        (OUT_OF_CONTENT_BOX, (hid("function", 1),)),
        (OUT_OF_CONTENT_BOX, (hid("function", 9),)),
    ]


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


@pytest.mark.parametrize(
    ("vertex", "expected"),
    [
        pytest.param((1280, 112), [], id="on the right edge"),
        pytest.param((1281, 112), [OUT_OF_CONTENT_BOX], id="past the right edge"),
        pytest.param((0, 112), [], id="on the left edge"),
        pytest.param((-1, 112), [OUT_OF_CONTENT_BOX], id="past the left edge"),
        pytest.param((104, 886), [], id="on the bottom edge"),
        pytest.param((104, 887), [OUT_OF_CONTENT_BOX], id="past the bottom edge"),
        pytest.param((104, 0), [], id="on the top edge"),
        pytest.param((104, -1), [OUT_OF_CONTENT_BOX], id="past the top edge"),
    ],
)
def test_a_route_is_outside_when_any_vertex_is_outside(
    vertex: tuple[int, int], expected: list[str]
) -> None:
    """The vertex is in the middle of the route, so its ends are not what decides."""
    route = _wire(((104, 112), vertex, (104, 288)))
    assert [c for c in _codes(_layout(routes=(route,))) if c == OUT_OF_CONTENT_BOX] == expected


# --- pages, faults and order -----------------------------------------------------------


def test_routes_labels_and_symbols_of_different_pages_never_interact() -> None:
    """A route on page 2 does not pass through the symbol on page 1."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    on_page_2 = _wire(((104, 112), (104, 288)), page=2)
    assert _codes(_layout(functions=functions, routes=(on_page_2,))) == []
    assert _codes(_layout(functions=functions, routes=(_wire(((104, 112), (104, 288))),))) == [
        WIRE_THROUGH_SYMBOL
    ]


def test_a_page_with_no_plan_is_not_a_fault() -> None:
    """`Layout.pages` is not read: a placed function on an unplanned page is linted."""
    layout = dataclasses.replace(_layout(functions=(placed(1, x=1272, y=96),)), pages=())
    assert _codes(layout) == [OUT_OF_CONTENT_BOX]


def test_a_route_with_fewer_than_two_points_is_a_fault() -> None:
    """One point raises `LayoutError`; the two-point route `[p, p]` does not."""
    with pytest.raises(LayoutError):
        lint_geometry(_layout(routes=(_wire(((104, 112),)),)), sheet=SHEET)
    assert _codes(_layout(routes=(_wire(((104, 112), (104, 112))),))) == []


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


def test_a_busy_page_reports_each_code_once_in_code_and_subject_order() -> None:
    """One page that triggers all six codes gives them sorted by `(code, subjects)`."""
    assert _found(_busy()) == [
        (OUT_OF_CONTENT_BOX, (hid("conductor", 4), hid("port", 12), hid("port", 21))),
        (OUT_OF_CONTENT_BOX, (hid("function", 5),)),
        (REDUNDANT_JOG, _route_ids(3)),
        (SYMBOL_OVERLAP, (hid("function", 1), hid("function", 4))),
        (WIRE_NOT_ORTHOGONAL, _route_ids(2)),
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("function", 9), hid("port", 12), hid("port", 21)),
        ),
        (
            WIRE_THROUGH_SYMBOL,
            (hid("conductor", 1), hid("function", 3), hid("port", 12), hid("port", 21)),
        ),
    ]


def test_every_geometric_finding_is_a_warning_with_a_message() -> None:
    """Every geometric code is `WARNING` and every finding says what is wrong."""
    findings = lint_geometry(_busy(), sheet=SHEET)
    assert {f.code for f in findings} == {
        OUT_OF_CONTENT_BOX,
        REDUNDANT_JOG,
        SYMBOL_OVERLAP,
        WIRE_NOT_ORTHOGONAL,
        WIRE_OVER_LABEL,
        WIRE_THROUGH_SYMBOL,
    }
    assert {f.severity for f in findings} == {Severity.WARNING}
    assert all(f.message for f in findings)


def test_the_result_is_equal_under_every_input_order() -> None:
    """Routes, functions and labels in any order give one list of findings."""
    busy = _busy()
    expected = lint_geometry(busy, sheet=SHEET)
    for routes in itertools.permutations(busy.routes):
        shuffled = dataclasses.replace(
            busy,
            routes=routes,
            placed=busy.placed[::-1],
            labels=busy.labels[::-1],
        )
        assert lint_geometry(shuffled, sheet=SHEET) == expected


def test_a_chain_is_found_whatever_the_order_of_its_routes_in_the_layout() -> None:
    """The order of `Layout.routes` does not change the findings."""
    first = _wire(((104, 112), (104, 160)), number=1, net=1)
    middle = _wire(((136, 200), (136, 160), (104, 160)), number=2, net=1)
    last = _wire(((136, 200), (104, 200), (104, 288)), number=3, net=1)
    expected = lint_geometry(_layout(routes=(first, middle, last)), sheet=SHEET)
    assert len(expected) == 1
    for routes in itertools.permutations((first, middle, last)):
        assert lint_geometry(_layout(routes=routes), sheet=SHEET) == expected


# --- edges the mutation sweep pointed at ------------------------------------------------


@pytest.mark.parametrize(
    ("start", "expected"),
    [(216, []), (215, [WIRE_THROUGH_SYMBOL])],
    ids=["starts on the bottom border", "starts 1 G inside"],
)
def test_a_run_starting_on_a_bottom_border_is_not_through(start: int, expected: list[str]) -> None:
    """Function 3's keep-out box spans y 184 to 216."""
    functions = (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304))
    route = _wire(((104, start), (104, 288)))
    assert _codes(_layout(functions=functions, routes=(route,))) == expected


def test_the_first_and_last_vertex_of_a_longer_route_name_its_endpoint_symbols() -> None:
    """Both ends leave function 7 along a lane, at the ends of a route of six points."""
    out_and_in = _wire(((200, 184), (200, 100), (300, 100), (300, 300), (200, 300), (200, 216)))
    assert _codes(_layout(functions=(_star(),), routes=(out_and_in,))) == []
    into_north = _wire(((300, 300), (200, 300), (200, 216)))
    assert _codes(_layout(functions=(_star(),), routes=(into_north,))) == []
    out_of_north = _wire(((200, 184), (200, 100), (300, 100)))
    assert _codes(_layout(functions=(_star(),), routes=(out_of_north,))) == []


def test_a_label_across_one_run_of_a_longer_route_is_over_the_wire() -> None:
    """The label crosses the vertical run only; the horizontal run is clear of it."""
    route = _wire(((104, 112), (104, 240), (200, 240)))
    label = _label(9, Box(x=96, y=196, width=32, height=8))
    assert _found(_layout(routes=(route,), labels=(label,))) == [
        (
            WIRE_OVER_LABEL,
            (hid("conductor", 1), hid("function", 9), hid("port", 12), hid("port", 21)),
        )
    ]


_GRAZING = [
    pytest.param(56, 184, 48, 184, id="a box left of the run"),
    pytest.param(112, 184, 120, 184, id="a box right of the run"),
    pytest.param(104, 144, 104, 136, id="a box above the run"),
    pytest.param(104, 216, 104, 224, id="a box below the run"),
]


@pytest.mark.parametrize(("x", "y", "free_x", "free_y"), _GRAZING)
def test_a_box_touching_the_straight_run_on_any_side_blocks_it_and_one_grid_unit_away_does_not(
    x: int, y: int, free_x: int, free_y: int
) -> None:
    """The straight run is x = 104 from y 160 to 200; the closed test counts every touch."""
    route = _wire(_JOG)
    base = (placed(1, x=104, y=96), placed(2, x=104, y=304))
    touching = _layout(functions=(*base, placed(3, x=x, y=y)), routes=(route,))
    apart = _layout(functions=(*base, placed(3, x=free_x, y=free_y)), routes=(route,))
    assert REDUNDANT_JOG not in _codes(touching)
    assert REDUNDANT_JOG in _codes(apart)


def test_a_page_with_only_a_route_or_only_a_label_is_linted() -> None:
    """Pages come from the routes and labels too, not from the placed functions alone."""
    diagonal = _wire(((104, 112), (136, 288)), page=2)
    assert _found(_layout(functions=(), routes=(diagonal,))) == [
        (WIRE_NOT_ORTHOGONAL, _route_ids(1))
    ]
    outside = _label(9, Box(x=1270, y=100, width=32, height=8), page=3)
    assert _found(_layout(functions=(), labels=(outside,))) == [
        (OUT_OF_CONTENT_BOX, (hid("function", 9),))
    ]


_OFF_LANE = [
    pytest.param(((200, 184), (200, 100), (210, 100), (210, 184)), id="N"),
    pytest.param(((200, 216), (200, 300), (210, 300), (210, 216)), id="S"),
    pytest.param(((184, 200), (100, 200), (100, 210), (184, 210)), id="W"),
    pytest.param(((216, 200), (300, 200), (300, 210), (216, 210)), id="E"),
]


@pytest.mark.parametrize("points", _OFF_LANE)
def test_a_run_beside_the_lane_line_is_not_on_the_lane(points: tuple[tuple[int, int], ...]) -> None:
    """The route leaves along the lane and comes back 10 G beside it, through its own box."""
    assert _codes(_layout(functions=(_star(),), routes=(_wire(points),))) == [WIRE_THROUGH_SYMBOL]


def test_ends_that_share_only_one_coordinate_do_not_meet() -> None:
    """Route 1 ends at (136, 160); a route on the same net starting on the same y or x is apart."""
    first = _wire(((104, 112), (104, 160), (136, 160)), number=1, net=1)
    same_y = _wire(((168, 160), (168, 200), (136, 200), (136, 288)), number=2, net=1)
    same_x = _wire(((136, 180), (136, 200), (104, 200), (104, 288)), number=2, net=1)
    assert _codes(_layout(routes=(first, same_y))) == []
    assert _codes(_layout(routes=(first, same_x))) == []


def test_a_chain_of_four_routes_is_one_polyline() -> None:
    """The jog spans the second, third and fourth piece of one wire drawn as four."""
    pieces = (
        ((104, 112), (104, 160)),
        ((104, 160), (136, 160)),
        ((136, 160), (136, 200)),
        ((136, 200), (104, 200), (104, 288)),
    )
    routes = tuple(_wire(points, number=n, net=1) for n, points in enumerate(pieces, start=1))
    (finding,) = lint_geometry(_layout(routes=routes), sheet=SHEET)
    assert finding.code == REDUNDANT_JOG
    assert finding.subjects == (
        hid("conductor", 1),
        hid("conductor", 2),
        hid("conductor", 3),
        hid("conductor", 4),
        hid("port", 12),
        hid("port", 21),
    )


def test_a_polyline_that_is_not_joined_to_a_plain_one_is_judged_alone() -> None:
    """Two routes of one net that share no end: only the jogged one is named."""
    plain = _wire(((300, 112), (300, 288)), number=1, net=1)
    jogged = _wire(_JOG, number=2, net=1)
    assert _found(_layout(routes=(plain, jogged))) == [(REDUNDANT_JOG, _route_ids(2))]


@pytest.mark.parametrize(
    "points",
    [
        pytest.param(
            ((104, 112), (104, 160), (136, 160), (128, 160), (136, 160), (136, 200), (104, 200)),
            id="a horizontal spur on an arm",
        ),
        pytest.param(
            ((40, 200), (80, 200), (80, 232), (80, 224), (80, 232), (120, 232), (120, 200)),
            id="a vertical spur on an arm",
        ),
    ],
)
def test_a_spur_that_doubles_back_is_not_merged_into_the_leg_before_it(
    points: tuple[tuple[int, int], ...],
) -> None:
    """Legs merge only when they go on in one direction: E, W, E is three legs and no jog."""
    assert REDUNDANT_JOG not in _codes(_layout(routes=(_wire(points),)))


def test_a_jog_that_is_the_whole_route_is_found() -> None:
    """Three legs and one triple: the jog is both the first and the last of the route."""
    route = _wire(((300, 112), (332, 112), (332, 152), (300, 152)))
    assert _found(_layout(routes=(route,))) == [(REDUNDANT_JOG, _route_ids(1))]


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


@pytest.mark.parametrize(("out", "back"), _RINGS)
@pytest.mark.parametrize("swap", [False, True], ids=["low handle first", "low handle second"])
def test_a_ring_is_judged_whole_wherever_it_is_cut(
    out: tuple[tuple[int, int], ...], back: tuple[tuple[int, int], ...], *, swap: bool
) -> None:
    """Two routes of one net joined at both ends: the jog is found however the ring is cut."""
    routes = (
        _wire(out, number=2 if swap else 1, net=1),
        _wire(back, number=1 if swap else 2, net=1),
    )
    for order in itertools.permutations(routes):
        assert _found(_layout(routes=order)) == [
            (
                REDUNDANT_JOG,
                (hid("conductor", 1), hid("conductor", 2), hid("port", 12), hid("port", 21)),
            )
        ]
