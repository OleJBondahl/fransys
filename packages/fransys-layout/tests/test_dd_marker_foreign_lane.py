"""DD-CHAIN-LANE (layout-0076): a marker box never covers the lane of another function's port.

Function 1's `out` (facing S) stands straight above function 2's `in` (facing N, the marker's
port); the marker's box in the gap between them would stand across function 1's only exit lane.
The markers' call (`place_markers`, WIRE-X56 in S20) takes no place on that lane.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, drawn, hid, placed

from fransys_layout.geometry import WIRING_GRID, Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers
from fransys_model.kernel import Id

_SHEET = replace(SHEET, content_width=400, content_height=400)
_X = 96  # on the wiring grid
_AT = Point(x=_X, y=104)  # function 2's `in`, 16 above its origin at y=120
_BOX = Box(x=_X - 22, y=84, width=45, height=12)  # centred on the stub, in the gap under function 1
_DRAWN = (drawn(1), drawn(2))


def _marker(*, x: int = _X) -> LinkMarker:
    """A star reference above function 2's port `in`, its box centred over its stub."""
    return LinkMarker(
        connection=Id(kind="conductor", value="9" * 32),
        port=hid("port", 21),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=x, y=_AT.y),
        box=replace(_BOX, x=x - 22),
        partner_page=2,
        star="ref",
    )


def _placed(marker: LinkMarker, functions: tuple) -> LinkMarker:
    """The one marker after `place_markers` over `functions`, no finding."""
    found, findings = place_markers(
        (marker,),
        functions,
        _DRAWN,
        MarkerRoom(
            columns=(),
            connections=(),
            joins=(),
            wired=frozenset(),
            sheet=_SHEET,
            profile=PROFILE,
        ),
    )
    assert findings == ()
    return found[0]


def test_a_box_across_another_functions_lane_at_its_stub_moves_off_the_lane() -> None:
    """The lane is at the stub's own x: the box leaves the stub, one grid clear of the lane, the
    lane between box and stub, and a lead draws the stub to it (layout-0054).

    # UNDO: `_lanes_beside` keeps only the lanes of the marker's own function (the box stays
    # centred on the stub, across function 1's lane)
    """
    above = (placed(1, x=_X, y=40), placed(2, x=_X, y=120))
    moved = _placed(_marker(), above)
    assert moved != _marker()
    assert not moved.box.x - WIRING_GRID < _X < moved.box.x + moved.box.width + WIRING_GRID
    assert moved.at == _AT  # the port and so the stub stay
    assert (moved.box.y, moved.box.width, moved.box.height) == (_BOX.y, _BOX.width, _BOX.height)
    assert moved.shared_box
    assert moved.lead


def test_a_box_beside_another_functions_lane_is_left_alone() -> None:
    """Function 1 is not above the stub: its lane at x=96 misses a box over x=200.

    # UNDO: `_place` reads every home as on a lane (`fits=False`): the box is re-placed
    """
    marker = _marker(x=200)
    beside = (placed(1, x=_X, y=40), placed(2, x=200, y=120))
    assert _placed(marker, beside) == marker


def test_a_function_beyond_the_marker_own_function_sends_no_lane_through_the_box() -> None:
    """Function 1 stands below function 2: its `out` faces down, its `in` up into function 2.

    # UNDO: `_meets` reads a south lane as meeting a box above its start (function 1's `out`,
    # far below the box, then counts as a lane)
    """
    marker = _marker()
    below = (placed(2, x=_X, y=120), placed(1, x=_X, y=200))
    assert _placed(marker, below) == marker
