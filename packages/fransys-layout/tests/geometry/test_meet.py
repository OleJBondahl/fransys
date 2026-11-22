"""`geometry.meet`: closed and open meeting of spans, boxes and points (cleanup step 2, F1)."""

from fransys_layout.geometry import Box, contains_point, meets


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


def test_contains_point_is_closed() -> None:
    """A point on an edge or a corner is inside; one outside is not."""
    box = Box(x=8, y=8, width=8, height=8)
    assert contains_point(box, 8, 8)
    assert contains_point(box, 16, 16)
    assert not contains_point(box, 17, 12)
    assert not contains_point(box, 12, 7)
