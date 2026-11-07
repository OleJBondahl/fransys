"""One clearance predicate: which keep boxes a probe box hits (layout-0394)."""

from __future__ import annotations

import pytest

from fransys_layout.core.clearance import Keep, clear, closed_cells, fan_own, own_end, reach, through, through_keeps
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.values import Box, PinRef


def _keep(box: Box, owner: str = "S1", node: str = "") -> Keep:
    return Keep(node=node, box=box, kind="sym", owner=owner)


@pytest.mark.parametrize(("hit", "miss"), [(Box(10, 0, 5, 5), Box(11, 0, 5, 5)), (Box(0, 10, 5, 5), Box(0, 11, 5, 5))])
def test_touch_is_a_hit_on_an_edge_and_not_past_it(hit: Box, miss: Box) -> None:
    assert clear(Box(0, 0, 10, 10), [_keep(hit)], {}) == (_keep(hit),)
    assert clear(Box(0, 0, 10, 10), [_keep(miss)], {}) == ()


def test_gap_widens_the_keep() -> None:
    keep = _keep(Box(11, 0, 5, 5))
    assert clear(Box(0, 0, 10, 10), [keep], {}, gap=2) == (keep,)


def test_own_skips_by_owner() -> None:
    keep = _keep(Box(10, 0, 5, 5), owner="A1")
    assert clear(Box(0, 0, 10, 10), [keep], {}, own={"A1"}) == ()
    assert clear(Box(0, 0, 10, 10), [keep], {}, own={"B2"}) == (keep,)


def test_zero_width_probe_inside_a_keep_hits() -> None:
    keep = _keep(Box(0, 0, 10, 10))
    assert clear(Box(3, 2, 0, 0), [keep], {}) == (keep,)


def test_zero_height_probe_on_a_keep_top_edge_hits() -> None:
    keep = _keep(Box(0, 10, 10, 5))
    assert clear(Box(2, 10, 4, 0), [keep], {}) == (keep,)
    assert clear(Box(2, 9, 4, 0), [keep], {}) == ()


def test_keep_with_node_adds_node_y() -> None:
    keep = _keep(Box(0, 2, 10, 5), node="row")
    y = {"row": 20}
    assert clear(Box(0, 25, 1, 1), [keep], y) == (keep,)
    assert clear(Box(0, 28, 1, 1), [keep], y) == ()


def test_result_keeps_input_order() -> None:
    first = _keep(Box(0, 0, 10, 10), owner="A")
    second = _keep(Box(2, 2, 3, 3), owner="B")
    third = _keep(Box(5, 5, 3, 3), owner="C")
    result = clear(Box(0, 0, 10, 10), [third, first, second], {})
    assert result == (third, first, second)


@pytest.mark.parametrize(
    ("start", "side", "gap", "expected"),
    [(12, "below", 0, 18), (12, "below", 3, 21), (25, "above", 0, 15), (25, "above", 3, 18), (40, "below", 0, 0), (5, "above", 0, 0)],
)
def test_reach_with_and_without_gap_and_clamped_at_zero_beyond_the_far_edge(start: int, side: str, gap: int, expected: int) -> None:
    assert reach(start, [_keep(Box(0, 10, 5, 20))], side, gap) == expected


def test_fan_own_is_the_attached_symbols() -> None:
    drive, leg = (
        Attach(None, 0, 0, PinRef("A1", "p"), net="n"),
        Attach("c", 0, 0, PinRef("B2", "q"), net="n"),
    )
    fan = Fan("f", ("n",), (drive,), (leg,), None, 1, "above")
    assert fan_own(fan) == frozenset({"A1", "B2"})


def test_fan_own_adds_the_cells_of_given_columns() -> None:
    fan = Fan("f", ("n",), (Attach(None, 0, 0, PinRef("A1", "p"), net="n"),), (), None, 1, "above")
    assert fan_own(fan, [["C1", "C2"], ["D1"]]) == frozenset({"A1", "C1", "C2", "D1"})


def test_closed_cells_include_the_far_edge_and_scale_with_the_pitch() -> None:
    """layout-0395, R535: the one home of the closed-edge cell range."""
    xs, ys = closed_cells(Box(16, 8, 16, 8), 8)
    assert (list(xs), list(ys)) == ([2, 3, 4], [1, 2])
    xs, ys = closed_cells(Box(3, 5, 0, 0))
    assert (list(xs), list(ys)) == ([3], [5])


def _wire_exempt(port: tuple[int, int], points: tuple[tuple[int, int], ...]) -> bool:
    return own_end(port, points[0]) or own_end(port, points[-1])


def test_own_end_exempts_a_wire_ending_at_the_port_point() -> None:
    assert _wire_exempt((4, 2), ((9, 9), (4, 2)))
    assert _wire_exempt((2, 2), ((2, 2), (9, 9)))


def test_own_end_does_not_exempt_a_wire_passing_through_the_port_point() -> None:
    assert not _wire_exempt((2, 2), ((0, 2), (2, 2), (9, 2)))


def test_own_end_does_not_exempt_a_foreign_point() -> None:
    assert not _wire_exempt((2, 2), ((1, 1), (3, 3)))


def _body() -> tuple[Keep, ...]:
    return (Keep("", Box(0, 0, 16, 16), "body", "T"),)


def test_a_run_meets_a_body_only_at_its_own_end_pin() -> None:
    body, pins = _body(), {"T": ((8, 0), (8, 16), (16, 16))}
    assert through_keeps(Box(8, 0, 0, 0), body, ((8, 0),), frozenset(), pins) == ()  # a point on its own pin
    assert through_keeps(Box(8, 0, 0, 16), body, ((8, 0), (8, 40)), frozenset({"T"}), pins) == body  # the interior
    assert through_keeps(Box(0, 16, 16, 0), body, ((0, 16),), frozenset(), pins) == body  # an edge run over the foreign pin (8, 16)
    assert through_keeps(Box(0, 16, 16, 0), body, ((16, 16),), frozenset(), {"T": ((16, 16),)}) == ()  # an edge run into its own pin
    assert through_keeps(Box(0, 16, 16, 0), body, ((0, 16),), frozenset(), {"T": ((8, 0),)}) == body  # the end is no pin of the body
    assert through_keeps(Box(16, 16, 8, 0), body, ((24, 16),), frozenset(), {"T": ((8, 0),)}) == ()  # a point on a foreign corner is looks (R1164)


def test_through_reads_a_diagonal_as_the_true_segment() -> None:
    box = Box(0, 0, 16, 16)
    assert through((-8, 8), (8, -8), box, (), ()) is False  # touches the corner (0, 0) only
    assert through((-4, 20), (20, -4), box, (), ())  # crosses the interior
    assert not through((-8, 20), (20, 24), box, (), ())  # clear of the body
    assert through((0, 0), (16, 16), box, (), ())  # along the diagonal
    assert through((-2, 6), (22, 6), box, (), ())  # orthogonal, through
    assert through((0, 16), (16, 16), box, (), ())  # along an edge, no pin
    assert not through((16, 16), (24, 16), box, (), ())  # a corner touch is looks


@pytest.mark.rule("BUNDLE-LEGS")
@pytest.mark.parametrize(("thin", "probe_w", "hit"), [(0, 5, 1), (1, 5, 1), (0, 10, 1), (0, 4, 0), (1, 4, 0)])
def test_thin_keep_hits_at_its_true_extent_at_gap_minus_one(thin: int, probe_w: int, hit: int) -> None:
    keep = _keep(Box(5, -3, thin, 20))
    assert clear(Box(0, 0, probe_w, 10), [keep], {}, gap=-1) == (keep,) * hit
