"""layout-0247: a wire no path off the markers' ink holds is drawn in the old room, with a note.

The invented plant: function 2 above function 1, one wire between them; function 3's marker
stub is a horizontal run across the whole sheet between the two, so every path crosses its ink.
"""

from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.route import ROUTE_NEAR_FLAG_STUB
from fransys_model.kernel import Severity


def _wall() -> LinkMarker:
    """A marker of function 3's port 31 whose stub runs along y 64 from x 0 to the box at 1400."""
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", 31),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=0, y=64),
        box=Box(x=1400, y=60, width=24, height=8),
        partner_page=2,
    )


def _route(*markers: LinkMarker):
    return route(
        (connection(1, 2, 1),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=32, name="b"), placed(3, x=304, y=208)),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        markers=markers,
        profile=PROFILE,
        sheet=SHEET,
    )


def test_a_wire_no_path_off_the_ink_holds_is_drawn_and_named() -> None:
    """UNDO: stages/route.py, `route`: drop the `failures.append(_near_ink(...))` line."""
    routes, findings = _route(_wall())
    assert len(routes) == 1
    (note,) = findings
    assert note.code == ROUTE_NEAR_FLAG_STUB
    assert note.severity is Severity.INFO
    assert note.subjects == (hid("conductor", 1),)
    assert note.message.startswith("p1.1: Fransys could not draw this cleanly")


def test_a_wire_with_a_path_off_the_ink_has_no_note() -> None:
    routes, findings = _route()
    assert len(routes) == 1
    assert findings == ()
