"""Acceptance skeletons: `lint.coherence`.

The check exists because a label-keyed router once cross-wired two fans while the
geometric score improved. Each code has an input that triggers it.
"""

from coherence_helpers import DRAWN, NO_UNITS, layout_of, wire
from samples import connection, hid

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
)
from fransys_layout.stages import (
    LinkMarker,
    MarkerSide,
)


def _marker(side: MarkerSide, *, page: int, port: int) -> LinkMarker:
    """A marker at its port: 12 is `out` of function 1 (y = 96), 21 is `in` of function 2."""
    return LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", port),
        side=side,
        drawing_set=1,
        page=page,
        at=Point(x=104, y={12: 112, 21: 288}[port]),
        box=Box(x=104, y={12: 108, 21: 284}[port], width=24, height=8),
        partner_page=3 - page,
    )


def test_a_connection_drawn_twice_is_reported() -> None:
    """Exactly once: two routes for one conductor are as wrong as none."""
    route = wire(1, ((104, 112), (104, 288)))
    findings = check_coherence(
        layout_of(routes=(route, route)), (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS
    )
    assert [f.code for f in findings] == [CONNECTION_DRAWN_TWICE]
