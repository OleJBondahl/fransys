"""`lead_ends`: hand-made placements, no model and no engine."""

from samples import connection, drawn, hid, through_geometry

from fransys_layout.geometry import Point
from fransys_layout.stages.box_leads import lead_ends
from fransys_layout.stages.types import PlacedFunction

DRAWN = (drawn(1), drawn(2))


def placed(number: int, x: int, *, page: int = 1) -> PlacedFunction:
    return PlacedFunction(
        function=hid("function", number),
        drawing_set=1,
        page=page,
        column=("invented", f"fn{number}"),
        at=Point(x=x, y=96),
        geometry=through_geometry(),
    )


def test_view_leads_to_far_in_port_on_same_page():
    found = lead_ends(
        (connection(1, 1, 2),), (placed(1, 96), placed(2, 200)), DRAWN, {hid("function", 1)}
    )
    assert found == {(hid("function", 1), 1, 1): (Point(x=200, y=80),)}


def test_far_end_listed_as_a_gives_its_out_port():
    found = lead_ends(
        (connection(1, 1, 2),), (placed(1, 96), placed(2, 200)), DRAWN, {hid("function", 2)}
    )
    assert found == {(hid("function", 2), 1, 1): (Point(x=96, y=112),)}


def test_conductor_between_two_views_gives_no_entry():
    found = lead_ends(
        (connection(1, 1, 2),),
        (placed(1, 96), placed(2, 200)),
        DRAWN,
        {hid("function", 1), hid("function", 2)},
    )
    assert found == {}


def test_far_function_only_on_page_2_gives_no_entry_for_page_1():
    found = lead_ends(
        (connection(1, 1, 2),),
        (placed(1, 96, page=1), placed(2, 200, page=2)),
        DRAWN,
        {hid("function", 1)},
    )
    assert found == {}


def test_view_on_both_pages_leads_only_where_far_function_stands():
    found = lead_ends(
        (connection(1, 1, 2),),
        (placed(1, 96, page=1), placed(1, 96, page=2), placed(2, 200, page=2)),
        DRAWN,
        {hid("function", 1)},
    )
    assert found == {(hid("function", 1), 1, 2): (Point(x=200, y=80),)}
