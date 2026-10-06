"""`geometry.meet`: closed and open meeting of spans, boxes and points (cleanup step 2, F1)."""

import itertools

from fransys_layout.geometry import Box, boxes_meet, contains_point, meets


def test_a_closed_span_test_counts_a_shared_end_and_an_open_one_does_not() -> None:
    """Spans that share only an end meet when closed and not when open."""
    assert meets((0, 8), (8, 16))
    assert meets((8, 16), (0, 8))
    assert not meets((0, 8), (8, 16), closed=False)
    assert not meets((0, 8), (9, 16))


def test_open_a_leaves_out_exactly_the_named_end() -> None:
    """Each of the four `open_a` combinations leaves out only its own ends of `a`."""
    low_touch, high_touch = (8, 16), (0, 8)  # `b` that shares only a's low end, only a's high end
    a = (8, 16)
    assert meets(a, high_touch)
    assert not meets(a, high_touch, open_a=(True, False))
    assert meets(a, high_touch, open_a=(False, True))
    a = (0, 8)
    assert meets(a, low_touch)
    assert not meets(a, low_touch, open_a=(False, True))
    assert meets(a, low_touch, open_a=(True, False))
    assert not meets(a, low_touch, open_a=(True, True))


def test_a_zero_length_span_inside_another_meets_it_open() -> None:
    """There is no emptiness guard: a point strictly inside a span meets it open."""
    assert meets((4, 4), (0, 8), closed=False)
    assert not meets((0, 0), (0, 8), closed=False)


def test_boxes_meet_closed_takes_an_edge_or_a_corner_and_open_takes_neither() -> None:
    """Boxes that share an edge or a corner meet closed, not open, in either order."""
    a = Box(x=0, y=0, width=8, height=8)
    for b in (Box(x=8, y=0, width=8, height=8), Box(x=8, y=8, width=8, height=8)):
        assert boxes_meet(a, b, closed=True)
        assert boxes_meet(b, a, closed=True)
        assert not boxes_meet(a, b, closed=False)
    assert boxes_meet(a, Box(x=4, y=4, width=8, height=8), closed=False)
    assert not boxes_meet(a, Box(x=9, y=0, width=8, height=8), closed=True)


def test_boxes_meet_gap_pads_the_first_box_then_tests_strictly() -> None:
    """`gap` grows `a` on every side: a box 8 away is out at gap 8 open, in at gap 9."""
    a = Box(x=0, y=0, width=8, height=8)
    b = Box(x=16, y=0, width=8, height=8)
    assert not boxes_meet(a, b, closed=False, gap=8)
    assert boxes_meet(a, b, closed=False, gap=9)
    assert boxes_meet(a, b, closed=True, gap=8)


def test_boxes_meet_agrees_with_a_cell_by_cell_oracle() -> None:
    """Over a small grid of non-empty boxes, closed and open agree with the point-set definition."""
    boxes = [
        Box(x=x, y=y, width=w, height=h)
        for x, y, w, h in itertools.product(range(3), range(3), range(1, 3), range(1, 3))
    ]
    for a, b in itertools.product(boxes[::5], boxes[::7]):
        shared_x = (max(a.x, b.x), min(a.x + a.width, b.x + b.width))
        shared_y = (max(a.y, b.y), min(a.y + a.height, b.y + b.height))
        assert boxes_meet(a, b, closed=True) == (
            shared_x[0] <= shared_x[1] and shared_y[0] <= shared_y[1]
        )
        assert boxes_meet(a, b, closed=False) == (
            shared_x[0] < shared_x[1] and shared_y[0] < shared_y[1]
        )


def test_contains_point_is_closed() -> None:
    """A point on an edge or a corner is inside; one outside is not."""
    box = Box(x=8, y=8, width=8, height=8)
    assert contains_point(box, 8, 8)
    assert contains_point(box, 16, 16)
    assert not contains_point(box, 17, 12)
    assert not contains_point(box, 12, 7)
