"""`geometry.meet`: closed and open meeting of spans, boxes and points (cleanup step 2, F1)."""

from fransys_layout.geometry import Box, boxes_meet, contains_point, meets


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


def test_boxes_meet_closed_takes_an_edge_or_a_corner_and_open_takes_neither() -> None:
    """Boxes that share an edge or a corner meet closed, not open, in either order."""
    a = Box(x=0, y=0, width=8, height=8)
    for b in (Box(x=8, y=0, width=8, height=8), Box(x=8, y=8, width=8, height=8)):
        assert boxes_meet(a, b, closed=True)
        assert boxes_meet(b, a, closed=True)
        assert not boxes_meet(a, b, closed=False)
    assert boxes_meet(a, Box(x=4, y=4, width=8, height=8), closed=False)
    assert not boxes_meet(a, Box(x=9, y=0, width=8, height=8), closed=True)


def test_contains_point_is_closed() -> None:
    """A point on an edge or a corner is inside; one outside is not."""
    box = Box(x=8, y=8, width=8, height=8)
    assert contains_point(box, 8, 8)
    assert contains_point(box, 16, 16)
    assert not contains_point(box, 17, 12)
    assert not contains_point(box, 12, 7)
