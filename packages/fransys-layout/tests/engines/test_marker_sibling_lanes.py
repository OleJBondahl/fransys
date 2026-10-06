"""WIRE-X56 (decision layout-0054) in the markers' call: a box never covers a sibling port's lane.

A wire leaving port `2` of a function straight out must not run through the box of the marker
at port `1` of the same function. The markers' call (`place_markers`, S20) admits a place only
off every lane (`marker_row._lanes_beside`): the box stands one grid clear of it, with its stub
still over it, or beyond the lane with a lead (layout-0054). The router's test is closed (a step
that only touches a box edge is blocked), so a lane on the home box's edge counts.
"""

import dataclasses
from typing import TYPE_CHECKING

import pytest
from samples import PROFILE, hid

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Orientation,
    Point,
    PortGeometry,
    SymbolGeometry,
    overlaps,
)
from fransys_layout.stages import (
    DrawnFunction,
    DrawnPort,
    LinkMarker,
    MarkerSide,
    PlacedFunction,
    SheetFormat,
)
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers
from fransys_layout.stages.texts.place_texts import LABEL_UNPLACED

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

_SHEET = SheetFormat(
    name="invented sheet", content_width=400, content_height=400, frame_columns=8, frame_rows=6
)
_HALF = WIRING_GRID // 2  # layout-0054: a stub stands half a grid inside its box


def _two_ports(facing: Facing) -> SymbolGeometry:
    """Ports `a` at x=0 and `b` at x=16, both facing `facing` at y=16."""
    return SymbolGeometry(
        key="two-ports",
        poles=1,
        orientation=Orientation.R0,
        body=Box(x=-8, y=-16, width=40, height=32),
        keepout=Box(x=-8, y=-16, width=40, height=32),
        through=None,
        ports=(
            PortGeometry(name="a", at=Point(x=0, y=16), facing=facing),
            PortGeometry(name="b", at=Point(x=16, y=16), facing=facing),
        ),
        slots=(),
    )


def _function(facing: Facing) -> tuple[PlacedFunction, DrawnFunction]:
    """One function at (56, 56): port 1 at x=56 and port 2 at x=72, y=72, both facing `facing`."""
    geometry = _two_ports(facing)
    placed = PlacedFunction(
        function=hid("function", 1),
        drawing_set=1,
        page=1,
        column=("invented", "a"),
        at=Point(x=56, y=56),
        geometry=geometry,
    )
    drawn = DrawnFunction(
        function=hid("function", 1),
        item=hid("item", 1),
        key=("invented", "fn1"),
        kind="terminal",
        geometry=geometry,
        ports=(
            DrawnPort(port=hid("port", 11), symbol_port="a"),
            DrawnPort(port=hid("port", 12), symbol_port="b"),
        ),
        primary_in="a",
        primary_out="b",
        roles=kind_roles("terminal"),
    )
    return placed, drawn


def _marker(port: int, at: Point, box: Box) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", port),
        side=MarkerSide.USER,
        drawing_set=1,
        page=1,
        at=at,
        box=box,
        partner_page=2,
        star="branch",
    )


def _place(
    markers: tuple[LinkMarker, ...],
    functions: tuple[tuple[PlacedFunction, DrawnFunction], ...],
    sheet: SheetFormat = _SHEET,
) -> tuple[tuple[LinkMarker, ...], tuple[Finding, ...]]:
    """`place_markers` over `functions`: the markers as placed, and the findings."""
    return place_markers(
        markers,
        tuple(p for p, _ in functions),
        tuple(d for _, d in functions),
        MarkerRoom(
            columns=(),
            connections=(),
            joins=(),
            wired=frozenset(),
            sheet=sheet,
            profile=PROFILE,
        ),
    )


def _run_all(*markers: LinkMarker, facing: Facing = Facing.S) -> tuple[LinkMarker, ...]:
    found, findings = _place(markers, (_function(facing),))
    assert findings == ()
    return found


def _run(marker: LinkMarker, facing: Facing = Facing.S) -> LinkMarker:
    (found,) = _run_all(marker, facing=facing)
    return found


def _clear_of(box: Box, lane: int) -> bool:
    """Whether `lane` is a whole grid off the closed box, the router's own test."""
    return lane + WIRING_GRID <= box.x or box.x + box.width + WIRING_GRID <= lane


def _stub_over(marker: LinkMarker) -> bool:
    """Whether the stub is over the box with half a grid to spare at either end."""
    return marker.box.x + _HALF <= marker.at.x <= marker.box.x + marker.box.width - _HALF


def test_a_marker_box_moves_off_a_sibling_ports_lane_and_keeps_its_stub() -> None:
    """The box at port 2 (x=72), 35 wide, centred, covers port 1's lane at x=56: it moves right.

    The nearest place that is a grid clear of the lane with the stub still over it is x=64. The
    box is a plain rectangle beside its stub (`shared_box`) at the same height.

    # UNDO: `_tier` builds no place at `lane.x + WIRING_GRID` (the nearest clear place is gone)
    """
    at = Point(x=72, y=72)
    box = Box(x=55, y=80, width=35, height=12)
    assert box.x < 56 < box.x + box.width  # the premise: the box covers the sibling's lane
    moved = _run(_marker(12, at, box))
    assert moved.box == Box(x=64, y=80, width=35, height=12)
    assert _clear_of(moved.box, 56)
    assert _stub_over(moved)
    assert moved.at == at
    assert moved.shared_box
    assert moved.lead


def test_a_marker_box_moves_left_when_the_sibling_is_to_its_right() -> None:
    """Port 1 (x=56) has its box over port 2's lane (x=72): the box moves left, off the lane.

    # UNDO: `_lanes_beside` drops the lanes of the marker's own function (no lane to the right)
    """
    at = Point(x=56, y=72)
    box = Box(x=45, y=80, width=35, height=12)
    assert box.x < 72 < box.x + box.width
    moved = _run(_marker(11, at, box))
    assert moved.box.x < box.x
    assert _clear_of(moved.box, 72)
    assert _stub_over(moved)
    assert moved.shared_box


def test_a_marker_box_moves_off_a_sibling_ports_lane_on_the_north_side() -> None:
    """A box above its port, over a sibling that leaves N (up) at x=56: it moves right too.

    # UNDO: `_meets` reads the lane's far end as the south one for a north lane
    """
    at = Point(x=72, y=72)
    box = Box(x=55, y=52, width=35, height=12)  # above the port: N
    moved = _run(_marker(12, at, box), facing=Facing.N)
    assert moved.box == Box(x=64, y=52, width=35, height=12)
    assert _clear_of(moved.box, 56)
    assert moved.shared_box


def test_a_marker_box_with_the_lane_on_its_left_edge_moves() -> None:
    """The router refuses a step that only touches a box edge, so a lane exactly on the edge
    is covered: the box at x=56..91 has port 1's lane (x=56) on its edge and moves right.

    # UNDO: `_on_lane` reads the home's closed test as an open one (`box.x < lane.x < ...`)
    """
    at = Point(x=72, y=72)
    box = Box(x=56, y=80, width=35, height=12)
    moved = _run(_marker(12, at, box))
    assert moved != _marker(12, at, box)
    assert moved.box.x == 64
    assert _clear_of(moved.box, 56)


def test_a_marker_box_with_the_lane_on_its_right_edge_moves() -> None:
    """The box at x=37..72 has port 2's lane (x=72) on its right edge: it moves left.

    # UNDO: as above, on the right-hand comparison
    """
    at = Point(x=56, y=72)
    box = Box(x=37, y=80, width=35, height=12)
    moved = _run(_marker(11, at, box))
    assert moved != _marker(11, at, box)
    assert moved.box.x < box.x
    assert _clear_of(moved.box, 72)
    assert _stub_over(moved)


def test_a_marker_box_clear_of_every_sibling_lane_stays_where_it_is() -> None:
    """A box already off the sibling's lane stays at its home (no arrow becomes a rectangle).

    # UNDO: `_place` reads every home as on a lane (`fits=False`): the box is re-placed
    """
    at = Point(x=72, y=72)
    box = Box(x=64, y=80, width=16, height=12)
    assert _run(_marker(12, at, box)) == _marker(12, at, box)


def test_a_marker_box_that_cannot_clear_the_lane_stays_and_is_reported() -> None:
    """A box wider than the room between the sibling's lane and the content box has no free
    place: it stays at its first candidate, drawn, and `LABEL_UNPLACED` names its port (S20).

    # UNDO: `_place` admits a place on a lane (`fits=True` always): no finding, a box on the lane
    """
    at = Point(x=72, y=72)
    box = Box(x=-100, y=80, width=400, height=12)
    marker = _marker(12, at, box)
    found, findings = _place((marker,), (_function(Facing.S),))
    assert found == (marker,)
    assert [(f.code, f.subjects) for f in findings] == [(LABEL_UNPLACED, (marker.port,))]


def test_a_marker_box_another_marker_box_blocks_takes_the_next_free_place() -> None:
    """Marker 11 stands first (the port nearer the left) at x=90..110, over its own stub's lane
    side; marker 12's nearest clear place (x=64..99) meets that box, so the greedy walk takes the
    next free place (S20): the same place one tier out, a box height further down, its stub
    running down the clear x=72. The other box stays.

    # UNDO: `place_texts` admits a place that overlaps a box already placed (x=64..99 at tier 0)
    """
    marker = _marker(12, Point(x=72, y=72), Box(x=55, y=80, width=35, height=12))
    other = _marker(11, Point(x=56, y=72), Box(x=90, y=80, width=20, height=12))
    found = _run_all(marker, other)
    assert found[1] == other
    assert not overlaps(found[0].box, found[1].box)
    assert found[0].box == Box(x=64, y=92, width=35, height=12)
    assert found[0].stub_extra == marker.stub_extra + marker.box.height  # one tier out
    assert _clear_of(found[0].box, 56)
    assert _stub_over(found[0])
    assert found[0].shared_box


def test_a_shared_marker_box_is_left_alone() -> None:
    """A box already shared (a C21 run's, `shared_box`) has one place, where it stands.

    # UNDO: `_row` drops `marker.shared_box or` from its one-place test (the box is moved)
    """
    at = Point(x=72, y=72)
    shared = dataclasses.replace(
        _marker(12, at, Box(x=55, y=80, width=35, height=12)), shared_box=True
    )
    assert _run(shared) == shared


def test_a_north_marker_is_left_alone_when_the_sibling_leaves_south() -> None:
    """Only a sibling leaving on the marker's own side has a lane through its box: the box
    above port 2 is not moved by port 1's S wire, which runs away from it.

    # UNDO: `_meets` reads a south lane as meeting a box above its start
    """
    at = Point(x=72, y=72)
    marker = _marker(12, at, Box(x=55, y=52, width=35, height=12))  # above the port: N
    assert _run(marker, facing=Facing.S) == marker


def test_a_south_marker_is_left_alone_when_the_sibling_leaves_north() -> None:
    """The mirror: the box below port 2 is not moved by port 1's N wire.

    # UNDO: as above
    """
    at = Point(x=72, y=72)
    marker = _marker(12, at, Box(x=55, y=80, width=35, height=12))  # below the port: S
    assert _run(marker, facing=Facing.N) == marker


def _motor(number: int, x: int) -> tuple[PlacedFunction, DrawnFunction]:
    """Function `number` at (x, 56): ports `number*10+1` at x and `number*10+2` at x+16 (S)."""
    placed, drawn = _function(Facing.S)
    placed = dataclasses.replace(placed, function=hid("function", number), at=Point(x=x, y=56))
    ports = (
        DrawnPort(port=hid("port", number * 10 + 1), symbol_port="a"),
        DrawnPort(port=hid("port", number * 10 + 2), symbol_port="b"),
    )
    return placed, dataclasses.replace(drawn, function=hid("function", number), ports=ports)


def _run_motors(
    markers: tuple[LinkMarker, ...], *xs: int, width: int = 400
) -> tuple[tuple[LinkMarker, ...], tuple[Finding, ...]]:
    """`place_markers` over motors at `xs` (numbered from 1) on a `width` wide page."""
    sheet = dataclasses.replace(_SHEET, content_width=width)
    return _place(markers, tuple(_motor(n, x) for n, x in enumerate(xs, start=1)), sheet)


def _wide_box_at_the_left_edge() -> LinkMarker:
    """Motor 1 at x=16: port 11 (x=16) has a lone 85 G box, centred, past the left edge; the
    sibling port 12 sends a wire down its lane at x=32 (the pump station's U and W)."""
    return _marker(11, Point(x=16, y=72), Box(x=-26, y=80, width=85, height=12))


def test_a_lone_box_at_the_edge_that_would_cover_a_sibling_lane_takes_the_place_beyond_it() -> None:
    """D14 and D15 (layout-0068): the box centred on its stub (x=16) crosses the left edge.
    Standing against the edge (x=0..85) covers the sibling's lane (x=32), and no place left of the
    lane keeps the stub under an 85 G box, in any tier. After the last tier it takes
    layout-0054's place beyond the lane: one grid clear of it (x=40), inside the content box, the
    stub left of the box with a lead from the stub's end.

    # UNDO: `_beyond` builds no place (`return []`): the box stays at x=-26 and is reported
    """
    marker = _wide_box_at_the_left_edge()
    (moved,), findings = _run_motors((marker,), 16)
    assert marker.box.x < 0  # the premise: it crosses the edge
    assert moved.box == Box(x=40, y=80, width=85, height=12)  # lane 32 + one grid, same size
    assert _clear_of(moved.box, 32)
    assert moved.at == marker.at  # the port and its stub stay
    assert moved.at.x < moved.box.x  # the stub is left of the box: it needs a lead
    assert moved.shared_box
    assert moved.lead
    assert findings == ()


def test_a_lone_box_at_the_right_edge_takes_the_place_beyond_the_lane_to_its_left() -> None:
    """The mirror: motor at x=368, port 12 (x=384) has the 85 G box past the right edge, its
    sibling's lane at x=368 to its left. The place beyond the lane is left of it: x=275..360.

    # UNDO: as above
    """
    marker = _marker(12, Point(x=384, y=72), Box(x=342, y=80, width=85, height=12))
    assert marker.box.x + marker.box.width > 400
    (moved,), findings = _run_motors((marker,), 368)
    assert moved.box == Box(x=275, y=80, width=85, height=12)
    assert _clear_of(moved.box, 368)
    assert moved.box.x + moved.box.width < moved.at.x  # the stub is right of the box
    assert moved.shared_box
    assert moved.lead
    assert findings == ()


def test_a_lone_box_with_no_free_span_beyond_the_lane_stays_and_is_reported() -> None:
    """D14: the page is 100 G wide: x=40 leaves an 85 G box 25 G past the edge, and the other
    side of the stub has no room. The box stays at its first candidate with `LABEL_UNPLACED`.

    # UNDO: `_beyond` drops its `x <= room.width - box.width` bound (x=40..125 is taken)
    """
    marker = _wide_box_at_the_left_edge()
    found, findings = _run_motors((marker,), 16, width=100)
    assert found == (marker,)
    assert [(f.code, f.subjects) for f in findings] == [(LABEL_UNPLACED, (marker.port,))]


def test_a_place_beyond_the_lane_that_meets_another_marker_box_is_not_taken() -> None:
    """Another marker's box, placed first (its port is further left), stands at x=100..185 with
    its stub off to the left (one place, a lead box): the wide box's place beyond the lane
    (x=40..125) would meet it. The wide box stays at its first candidate, reported, and the
    other box is where it was.

    # UNDO: `place_texts` admits a place that overlaps a box already placed
    """
    marker = _wide_box_at_the_left_edge()
    other = _marker(99, Point(x=8, y=72), Box(x=100, y=80, width=85, height=12))  # no lane
    found, findings = _run_motors((marker, other), 16)
    assert found == (marker, other)
    assert [(f.code, f.subjects) for f in findings] == [(LABEL_UNPLACED, (marker.port,))]


@pytest.mark.parametrize("width", [400, 200])
def test_two_lone_boxes_over_two_motors_lanes_are_placed_clear_of_every_lane_and_each_other(
    width: int,
) -> None:
    """The pump station's page: motor 1 at x=16 (lane 32) and motor 2 at x=136 (lane 152), both
    with an 85 G box over the port at the left of the pair. The first, placed first, takes the
    place beyond its lane, x=40..125. The second's nearest place clear of its lane (x=59..144)
    meets that box, so the greedy walk takes it one tier out (S20), at y=92, its stub running
    down x=136 clear of the first box. No box covers a lane, none meets another, and none is
    reported, on a page 400 wide and on one 200 wide (where the greedy walk never moves the
    first box for the second).

    # UNDO: `_tier` builds no tier beyond the first (`while True` stops after tier 0): the
    # second has no place and is reported
    """
    first = _marker(11, Point(x=16, y=72), Box(x=-26, y=80, width=85, height=12))
    second = _marker(21, Point(x=136, y=72), Box(x=93, y=80, width=85, height=12))
    found, findings = _run_motors((first, second), 16, 136, width=width)
    assert [m.box for m in found] == [
        Box(x=40, y=80, width=85, height=12),
        Box(x=59, y=92, width=85, height=12),
    ]
    assert found[1].stub_extra == second.stub_extra + second.box.height
    assert _clear_of(found[0].box, 32)
    assert _clear_of(found[1].box, 152)
    assert not overlaps(found[0].box, found[1].box)
    assert all(m.shared_box and m.lead for m in found)
    assert findings == ()
