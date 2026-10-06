"""S20 (layout-0090): `place_markers`, settle's four marker moves as D3's placer rules.

Hand-made values: the through symbol (`in` 16 above its origin facing N, `out` 16 below facing
S, on x = 0). Each rule has a twin in which its cause is absent.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, connection, drawn, hid, placed

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, overlaps, translate
from fransys_layout.stages import Cell, Column, LinkMarker, MarkerSide, Role
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
from fransys_layout.stages.texts.marker_lanes import Lane, reach_of
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers, stub_boxes
from fransys_layout.stages.texts.place_texts import LABEL_UNPLACED
from fransys_layout.stages.texts.stand import star_turns, start_tier, tier_offset

_PORT = hid("port", 22)  # function 2's `out`
_AT = Point(x=104, y=112)


def _marker(star: str, *, port: int = 22, at: Point = _AT, width: int = 20) -> LinkMarker:
    """A marker at `port`, its box centred below its stub (facing S)."""
    return LinkMarker(
        connection=hid("conductor", port),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=at,
        box=Box(x=at.x - width // 2, y=at.y, width=width, height=12),
        partner_page=2,
        star=star,
    )


def _column(*, side: bool) -> Column:
    """Functions 2 and 1 in one column; function 1 is a side element when `side` is set."""
    return Column(
        key=("invented", "a"),
        cells=(
            Cell(function=hid("function", 2), index=0),
            Cell(function=hid("function", 1), index=0, side=side),
        ),
        group=None,
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )


def _placed(markers: tuple[LinkMarker, ...], placements: tuple, **options) -> tuple:
    """`place_markers` over `placements` of functions 1 and 2 on page 1."""
    return place_markers(
        markers,
        placements,
        (drawn(1), drawn(2)),
        MarkerRoom(
            columns=options.get("columns", ()),
            connections=options.get("connections", ()),
            joins=options.get("joins", ()),
            wired=options.get("wired", frozenset()),
            sheet=options.get("sheet", SHEET),
            profile=PROFILE,
        ),
    )


_ABOVE = (placed(2, x=104, y=96), placed(1, x=104, y=0))  # as `test_settle.py` stood them


def test_further_puts_a_star_marker_at_a_joined_port_one_box_height_out() -> None:
    """I4 Q1 as S14's n-th-out candidate: function 1 is a side element joined at port 22, so the
    marker's first place is one tier out, one box height (12, ADDENDUM 10 point 3; settle moved
    it one grid). Twin: no side element, the marker stays at its home."""
    start = _marker("branch")
    options = {"connections": (connection(1, 2, 1),)}
    (moved,), findings = _placed((start,), _ABOVE, columns=(_column(side=True),), **options)
    assert moved.box == replace(start.box, y=start.box.y + start.box.height)
    assert moved.stub_extra == start.box.height
    assert findings == ()
    (kept,), _ = _placed((start,), _ABOVE, columns=(_column(side=False),), **options)
    assert kept == start


def test_a_star_reference_on_a_wired_port_takes_its_one_turned_place() -> None:
    """S20 M7 (layout-0053): a wire ends at port 22 where the reference stands, so every place
    over the wired point is refused and the turned box is its one place: a junction one grid out,
    a branch east, the box vertical on the branch end (a whole number of grids out) and starting
    one grid beyond it, its near edge at least a grid from the pin's own wire, and the fewest
    grids that achieve it. Twin: not wired, it stays."""
    wired = frozenset({(_PORT, 1, 1)})
    (moved,), findings = _placed((_marker("ref"),), _ABOVE, wired=wired)
    box, end_x = moved.box, moved.box.x + moved.box.width // 2
    assert moved.turn == Point(x=_AT.x, y=_AT.y + WIRING_GRID)
    assert moved.vertical
    assert (box.width, box.height) == (12, 20)  # the one-line box, turned
    assert box.y == moved.turn.y + WIRING_GRID
    assert (end_x - _AT.x) % WIRING_GRID == 0
    assert box.x - _AT.x >= WIRING_GRID
    assert box.x - WIRING_GRID - _AT.x < WIRING_GRID  # one grid fewer would stand too close
    assert findings == ()
    (kept,), _ = _placed((_marker("ref"),), _ABOVE)
    assert kept == _marker("ref")


def test_two_markers_whose_homes_overlap_stand_apart_each_over_its_own_stub() -> None:
    """R7 B4's stagger as the greedy walk: the second marker's home overlaps the first's box, so
    it takes the next free place: no two boxes overlap, each stub stays over its own box and runs
    through no other box. Twin: far apart, both stay at home."""
    near = (placed(1, x=40, y=96), placed(2, x=56, y=96))
    first = _marker("branch", port=12, at=Point(x=40, y=112), width=30)
    second = _marker("branch", port=22, at=Point(x=56, y=112), width=30)
    assert overlaps(first.box, second.box)
    (one, two), findings = _placed((first, second), near)
    assert findings == ()
    assert one == first
    assert two != second
    assert not overlaps(one.box, two.box)
    for mine, other in ((one, two), (two, one)):
        assert mine.box.x <= mine.at.x <= mine.box.x + mine.box.width
        assert not any(overlaps(stub, other.box) for stub in stub_boxes(mine))
    far = (placed(1, x=40, y=96), placed(2, x=400, y=96))
    apart = replace(second, at=Point(x=400, y=112), box=replace(second.box, x=385))
    assert _placed((first, apart), far)[0] == (first, apart)


def test_a_box_across_a_wired_lane_at_its_stub_leaves_it_one_grid_clear() -> None:
    """WIRE-X56 (layout-0076): function 1's `out` stands straight above function 2's `in`, the
    marker's port, and its lane runs down through the box: no place over the stub is off that
    lane, so the box takes a place beyond it with a lead, one grid clear. Twin: function 1
    stands beside, its lane misses the box, and the box stays."""
    x, at = 96, Point(x=96, y=104)
    marker = replace(
        _marker("ref", port=21, at=at, width=45), box=Box(x=x - 22, y=84, width=45, height=12)
    )
    above = (placed(1, x=x, y=40), placed(2, x=x, y=120))
    (moved,), findings = _placed((marker,), above)
    assert findings == ()
    assert not moved.box.x - WIRING_GRID < x < moved.box.x + moved.box.width + WIRING_GRID
    assert (moved.at, moved.box.y) == (at, marker.box.y)
    assert moved.shared_box
    assert moved.lead
    beside = (placed(1, x=x, y=40), placed(2, x=200, y=120))
    alone = replace(marker, at=Point(x=200, y=104), box=replace(marker.box, x=178))
    assert _placed((alone,), beside)[0] == (alone,)


def test_a_box_across_the_left_content_edge_stands_against_it() -> None:
    """D14 M2 (layout-0068): the home crosses the content box's left edge, so the box stands
    against it, its stub still over it and half a grid inside. Twin: well inside, it stays."""
    marker = _marker("branch", port=22, at=Point(x=8, y=112))
    (moved,), findings = _placed((marker,), (placed(2, x=8, y=96),))
    assert findings == ()
    assert moved.box.x == 0
    assert moved.box.x + WIRING_GRID // 2 <= moved.at.x <= moved.box.x + moved.box.width
    assert moved.shared_box
    inside = _marker("branch", port=22, at=Point(x=200, y=112))
    assert _placed((inside,), (placed(2, x=200, y=96),))[0] == (inside,)


def test_two_one_place_boxes_over_each_other_leave_one_unplaced_and_both_drawn() -> None:
    """Two C21 run boxes, one place each, overlap: the second has no free place, so it stands
    at its one place with one `LABEL_UNPLACED`, never dropped."""
    near = (placed(1, x=40, y=96), placed(2, x=56, y=96))
    first = replace(_marker("off", port=12, at=Point(x=40, y=112), width=30), shared_box=True)
    second = replace(_marker("off", port=22, at=Point(x=56, y=112), width=30), shared_box=True)
    assert overlaps(first.box, second.box)
    found, findings = _placed((first, second), near)
    assert found == (first, second)
    assert [one.code for one in findings] == [LABEL_UNPLACED]


def test_a_marker_box_never_walks_down_through_the_next_symbol_on_its_line() -> None:
    """S20 tally 8b: function 2's `out` (the marker's port) has function 1 straight below it.
    The `in` lane of function 1 shuts every tier of the gap; a tier past it would stand over
    function 1's body, where the port's own lane ends. The box takes a place beside the lane in
    the gap instead. Twin: nothing below, the walk ends where the box leaves the content box and
    the box stays at its home."""
    # UNDO: stages/texts/marker_row.py `_row`: `_within_lane(base.box, own)` -> `True`
    marker = _marker("branch", port=22, at=Point(x=104, y=112), width=20)
    below = (placed(2, x=104, y=96), placed(1, x=104, y=200))
    (moved,), findings = _placed((marker,), below)
    body = translate(drawn(1).geometry.body, dx=104, dy=200)
    assert findings == ()
    assert moved.box.y + moved.box.height <= body.y
    assert not overlaps(moved.box, body)
    alone = _placed((marker,), (placed(2, x=104, y=96),))[0]
    assert alone == (marker,)


def _join(*ports: int, page: int = 1) -> JoinedRun:
    """A joined run on page `page` over the `out` ports of functions `ports`, in column order."""
    ends = tuple(JoinedEnd(column=("invented", "a"), port=hid("port", n * 10 + 2)) for n in ports)
    return JoinedRun(drawing_set=1, page=page, ends=ends)


def test_a_marker_box_never_stands_on_a_joined_run_s_wire() -> None:
    """S20: functions 1 and 2 stand side by side and `references` joined their `out` ports on one
    y; the marker of port 12 has its home box over that wire, so it takes the next free place:
    placed (no `LABEL_UNPLACED`), clear of the run. Twin: no join, or a join on another page,
    it stays at home."""
    # UNDO: stages/texts/marker_row.py `place_markers`: `Space(shapes=...)` -> `Space(shapes=()`
    #     (the home then stays on the wire)
    beside = (placed(1, x=40, y=96), placed(2, x=200, y=96))
    marker = _marker("branch", port=12, at=Point(x=40, y=112), width=60)
    wire = Box(x=40 + WIRING_GRID // 2, y=111, width=160 - WIRING_GRID, height=2)
    assert overlaps(marker.box, wire)
    (moved,), findings = _placed((marker,), beside, joins=(_join(1, 2),))
    assert findings == ()
    assert moved != marker
    assert not overlaps(moved.box, wire)
    assert _placed((marker,), beside)[0] == (marker,)
    assert _placed((marker,), beside, joins=(_join(1, 2, page=2),))[0] == (marker,)


def test_a_one_place_box_across_a_corridor_is_refused_it() -> None:
    """S20: a C21 run box has one place, no lane read; function 2 `out` over function 1 `in` is a
    corridor, and the box standing on it has no free place: it stays with one `LABEL_UNPLACED`.
    Twin: no connection, no corridor, no finding."""
    # UNDO: stages/labels.py `decided_runs`: `found = list(corridors(...))` -> `found = []`
    below = (placed(2, x=104, y=96), placed(1, x=104, y=200))
    marker = replace(_marker("off", port=22, width=20), shared_box=True)
    found, findings = _placed((marker,), below, connections=(connection(1, 2, 1),))
    assert found == (marker,)
    assert [one.code for one in findings] == [LABEL_UNPLACED]
    assert _placed((marker,), below)[1] == ()


def test_start_tier_and_offset_are_the_one_rule_for_the_joined_star_text() -> None:
    """`stand.start_tier` and `tier_offset`: tier 1 only for a star text, joined, not escaped.

    The escapes are a turned text and a C21 run's shared box. The offset is one box length per
    tier, down for a south facing and up for a north one.
    """
    # UNDO: stages/texts/stand.py `start_tier`: `return 0`
    assert start_tier(star="ref", joined=True, escaped=False) == 1
    assert start_tier(star="off", joined=True, escaped=False) == 1
    assert start_tier(star="ref", joined=False, escaped=False) == 0
    assert start_tier(star="", joined=True, escaped=False) == 0
    assert start_tier(star="ref", joined=True, escaped=True) == 0
    assert tier_offset(1, 12, south=True) == 12
    assert tier_offset(1, 12, south=False) == -12
    assert tier_offset(0, 12, south=True) == 0
    assert tier_offset(2, 12, south=False) == -24
    assert [star_turns("ref", terminal=True), star_turns("off", terminal=False)] == [True, True]
    assert [star_turns("off", terminal=True), star_turns("", terminal=False)] == [False, False]


def test_a_lane_reach_holds_its_x_and_its_y_extent_low_to_high() -> None:
    """`reach_of`: a south lane and a north lane both read their extent low first.

    A north lane ends above its port, so y > end: the extent is (end, y), never (y, end).
    """
    # UNDO: stages/texts/marker_lanes.py `reach_of`: `(lane.x, lane.y, lane.end)` for the extent
    south = Lane(function=hid("function", 1), port=_PORT, x=8, y=10, facing=Facing.S, end=50)
    north = replace(south, x=9, y=40, facing=Facing.N, end=-5)
    assert reach_of((south, north)) == ((8, 10, 50), (9, -5, 40))
