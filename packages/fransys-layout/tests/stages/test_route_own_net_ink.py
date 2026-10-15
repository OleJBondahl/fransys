"""layout-0243: a marker's stub ink is no obstacle for wires of the marker's own net.

The invented plant: function 2 above function 1, one wire (net 1) between them; function 3's
marker stub runs along y 64 (a turned branch) from x 0 to its box at x 150, across that
wire. Function 3's port is wired by a second connection to function 4, on net 1 (own) or
net 2 (foreign).
"""

from dataclasses import replace

from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide


def _marker() -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", 31),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=0, y=100),
        turn=Point(x=0, y=64),
        box=Box(x=150, y=60, width=24, height=8),
        partner_page=2,
    )


def _rail(net: int) -> int:
    """The number of points of the wire 1-2 past the stub of a marker on net `net`."""
    stub_wire = replace(connection(2, 4, 3), physical_net=hid("net", net))
    routes, _ = route(
        (connection(1, 2, 1), stub_wire),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=104, y=32, name="b"),
            placed(3, x=304, y=208),
            placed(4, x=304, y=304),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        markers=(_marker(),),
        profile=PROFILE,
        sheet=SHEET,
    )
    (rail,) = (one for one in routes if one.connection == hid("conductor", 1))
    return len(rail.points)


def test_a_rail_past_its_own_markers_stub_runs_straight() -> None:
    """UNDO: stages/_edge_paths.py, `_search`: do not drop the shapes of the edge's own net."""
    assert _rail(1) == 2


def test_a_foreign_wire_past_the_same_stub_still_goes_round() -> None:
    assert _rail(2) > 2
