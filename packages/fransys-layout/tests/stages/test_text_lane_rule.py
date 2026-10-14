"""layout-0196: no text stands on a port's exit lane, its own function's included.

The invented plant: function 2 above function 1; function 2's `out` port (x = 104, facing S)
has its lane at y 48..56. Function 1's `in` port at (104, 80) carries a power symbol whose one
text, 15 wide by 8, has a single candidate, over that lane. With an unowned text there, the
router has no exempt lane for `out`, so the wire seals in (ROUTE_FAILED).
"""

from fransys_el import TEXTS
from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, placed

from fransys_layout.geometry import Box, Facing, Point, overlaps, port_page_at
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.labels import SlotFrame, port_lanes
from fransys_layout.stages.route import ROUTE_FAILED
from fransys_layout.stages.space import Shape, Space
from fransys_layout.stages.texts.candidates import TextKind
from fransys_layout.stages.texts.place_texts import Anchor, TextToPlace, place_texts
from fransys_layout.stages.texts.power import with_power_labels


def test_a_text_does_not_stand_on_its_own_functions_lane() -> None:
    """UNDO: stages/texts/place_texts.py, `place_texts`: `others` filters `shape.owner not in
    text.own` again, and the tag stands on its own function's lane."""
    own, home = hid("function", 1), Box(x=10, y=20, width=30, height=7)
    anchor = Anchor(box=Box(x=40, y=20, width=20, height=7), facing=Facing.W)
    text = TextToPlace(
        kind=TextKind.TAG,
        handle=own,
        position=Point(x=0, y=0),
        width=30,
        height=7,
        anchors=(anchor,),
        own=(own,),
    )
    lane = Shape(owner=own, box=Box(x=20, y=18, width=0, height=10))
    (found,), _ = place_texts((text,), Space(shapes=()), TEXTS, lanes=(lane,))
    assert found.box != home
    assert not overlaps(found.box, lane.box)


def _plant():
    above, below = placed(2, x=104, y=32, name="b"), placed(1, x=104, y=96)
    pin = port_page_at(below.at, below.geometry.ports[0])
    power = LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", 1),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=pin,
        box=Box(x=pin.x - 4, y=pin.y - 12, width=8, height=8),
        partner_page=2,
        symbol="power-supply",
        symbol_text="24V",
    )
    return above, below, power


def _route(reserved: tuple[Box, ...]):
    above, below, _ = _plant()
    far = placed(3, x=304, y=208, name="c")
    return route(
        (connection(1, 2, 3),),
        (),
        (below, above, far),
        (drawn(1), drawn(2), drawn(3)),
        reserved=reserved,
        profile=PROFILE,
        sheet=SHEET,
    )


def test_an_unowned_text_on_the_start_lane_seals_the_route_in() -> None:
    """The consumer shape on invented values: a 15 by 8 unowned box on the start's lane."""
    routes, findings = _route((Box(x=97, y=48, width=15, height=8),))
    assert [one.code for one in findings] == [ROUTE_FAILED]
    assert routes == ()


def test_a_power_text_leaves_another_ports_lane_and_the_wire_routes() -> None:
    """UNDO: stages/texts/power.py, `with_power_labels`: drop `lanes=port_lanes(placed)`; the
    text stands on function 2's lane, is held as a reserved box, and the route fails."""
    above, below, power = _plant()
    labels, _ = with_power_labels(
        (), (below, above), (power,), SlotFrame(content=None, profile=PROFILE), "power"
    )
    lanes = port_lanes((below, above))
    assert all(not overlaps(one.box, lane.box) for one in labels for lane in lanes)
    held = tuple(one.box for one in labels if not one.unplaced)
    routes, findings = _route(held)
    assert [one.code for one in findings] == []
    assert len(routes) == 1
