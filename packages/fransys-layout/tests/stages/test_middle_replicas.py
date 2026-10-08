"""HL11: a middle unit's no-line interfaces' replicas, split by edge, measured and placed."""

from fractions import Fraction

from samples import hid, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages.edges import InterfaceEdge
from fransys_layout.stages.middle import MiddleGroup, MiddleInterface, MiddleUnit
from fransys_layout.stages.middle_replicas import (
    replica_height,
    replica_places,
    replica_width,
    replicas,
)
from fransys_model.derive import natural_key

UNIT = hid("unit", 1)
J1, J2, J3 = (hid("function", n) for n in (1, 2, 3))
# a placed sample's keep-out is 56 wide and 32 high, from (-8, -16) about its `at`
WIDE, HIGH = 56, 32


def _interface(function, views, *, line: bool) -> MiddleInterface:
    designation = f"-U1-{function.value[-1]}"
    edge = InterfaceEdge(
        function, designation, natural_key(designation), None, line=line, share=Fraction(0)
    )
    return MiddleInterface(
        edge=edge,
        views=tuple(views),
        plug=None,
        plug_views=(),
        lines=(),
        plug_lines=(),
        far=frozenset(),
        conductors=frozenset(),
    )


def _group() -> MiddleGroup:
    """J1 (top, no line) views 10 and 11; J2 (bottom, no line) view 12; J3 has a line, view 13."""
    interfaces = (
        _interface(J1, [hid("function", 10), hid("function", 11)], line=False),
        _interface(J2, [hid("function", 12)], line=False),
        _interface(J3, [hid("function", 13)], line=True),
    )
    return MiddleGroup(
        unit=MiddleUnit(UNIT, interfaces, frozenset()), top=frozenset({J1, J3}), reach={}
    )


def test_replicas_split_the_no_line_views_by_their_interfaces_edge() -> None:
    """HL11: 10 and 11 are the top edge's, 12 the bottom's; 13 (a line) and 14 (none's) are out.

    UNDO: drop `if not one.edge.line` in `replicas`, and view 13 joins the top edge.
    """
    page = [placed(n, x=0, y=0) for n in (10, 11, 12, 13, 14)]
    top, bottom = replicas(_group(), page)
    assert [one.function for one in top] == [hid("function", 10), hid("function", 11)]
    assert [one.function for one in bottom] == [hid("function", 12)]


def test_replica_width_sums_each_keepout_width_plus_a_gap() -> None:
    """HL11: two replicas and a gap of 8 are 2 * (56 + 8); no replica, nothing.

    UNDO: `replica_width` leaves the `+ gap` out.
    """
    edge = [placed(10, x=0, y=0), placed(11, x=0, y=0)]
    assert replica_width(edge, 8) == 2 * (WIDE + 8)
    assert replica_width([], 8) == 0


def test_replica_height_is_the_tallest_keepout_and_zero_for_none() -> None:
    """HL11: the keep-outs are all 32 high; an empty edge is 0.

    UNDO: `replica_height` returns the first replica's height times the count.
    """
    assert replica_height([placed(10, x=0, y=0), placed(11, x=0, y=0)]) == HIGH
    assert replica_height([]) == 0


def test_top_replicas_stand_a_grid_below_the_frames_top_side_by_side_from_x() -> None:
    """HL11: the keep-outs start at frame.y + 8, the first at x 100, the next a width and gap on.

    UNDO: place the top replicas at `frame.y` instead of `frame.y + WIRING_GRID`.
    """
    frame = Box(x=0, y=40, width=400, height=200)
    edge = [placed(11, x=304, y=904), placed(10, x=24, y=504)]
    found = replica_places(edge, frame, 100, 8, top=True)
    # keep-out origin is `at` minus (8, 16); the move in x is snapped up to the grid
    # (layout-0164), so each `at` stays on it: 24 + snap_up(100 - 16), 304 + snap_up(164 - 296)
    assert found == {
        hid("function", 10): Point(x=112, y=40 + 8 + 16),
        hid("function", 11): Point(x=176, y=40 + 8 + 16),
    }


def test_bottom_replicas_stand_a_grid_above_the_frames_bottom_side() -> None:
    """HL11: the keep-outs end at frame.y + height - 8, so start 32 above that.

    UNDO: place the bottom replicas with the top rule.
    """
    frame = Box(x=0, y=40, width=400, height=200)
    found = replica_places([placed(10, x=24, y=504)], frame, 100, 8, top=False)
    assert found == {hid("function", 10): Point(x=112, y=40 + 200 - 8 - HIGH + 16)}


def test_a_replica_moves_by_whole_grids_so_its_ports_stay_on_the_wiring_grid() -> None:
    """layout-0164: a keep-out off the grid about `at` (text overhang) must not shift `at` off it.

    UNDO: `replica_places` moves `at` by `x - keepout.x` without snapping it up.
    """
    frame = Box(x=0, y=40, width=400, height=200)
    one = placed(10, x=24, y=504)
    found = replica_places([one], frame, 20, 8, top=True)  # 20 - 16 = 4: not a grid
    assert (found[hid("function", 10)].x - one.at.x) % 8 == 0
