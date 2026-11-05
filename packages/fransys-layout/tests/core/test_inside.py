"""`inside`: a box lies within the page area, touching no edge (R360, R372, R751)."""

import pytest

from fransys_layout.core import Box, Size, inside

AREA = Size(100, 80)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        (Box(0, 0, 100, 80), False),
        (Box(1, 1, 98, 78), True),
        (Box(10, 10, 20, 20), True),
        (Box(-1, 0, 10, 10), False),
        (Box(0, -1, 10, 10), False),
        (Box(91, 0, 10, 10), False),
        (Box(0, 71, 10, 10), False),
    ],
)
def test_a_box_is_inside_only_when_all_four_edges_are(box: Box, expected) -> None:
    assert inside(box, AREA) is expected


@pytest.mark.parametrize(("edge", "expected"), [("open", False), ("closed", True)])
def test_a_box_touching_the_edge_is_inside_only_when_closed(edge, expected) -> None:
    assert inside(Box(0, 0, 100, 80), AREA, edge=edge) is expected
