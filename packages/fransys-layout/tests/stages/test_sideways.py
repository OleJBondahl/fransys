"""`sideways_ends`: which pin of a beside wire keeps its way and which leaves sideways."""

from samples import hid

from fransys_layout.geometry import Facing, Point
from fransys_layout.stages import PortRef
from fransys_layout.stages._sides import Edge, located
from fransys_layout.stages.sideways import sideways_ends
from fransys_layout.stages.space import End


def _ref(function: int) -> PortRef:
    return PortRef(function=hid("function", function), port=hid("port", function * 10))


def _pair(top_y: int, bottom_y: int) -> tuple[Edge, dict]:
    """A wire from a south pin at x 0 down to a north pin at x 64, `bottom_y - top_y` below."""
    edge = Edge(
        connection=hid("conductor", 1),
        physical_net=hid("net", 1),
        a=_ref(1),
        b=_ref(2),
        subjects=(),
    )
    ends = {
        located(edge.a): End(at=Point(x=0, y=top_y), facing=Facing.S),
        located(edge.b): End(at=Point(x=64, y=bottom_y), facing=Facing.N),
    }
    return edge, ends


def test_a_north_pin_one_grid_down_is_entered_from_above() -> None:
    """JOIN-VERTICAL: the south pin leaves sideways and the north pin keeps its way."""
    edge, ends = _pair(0, 8)
    found = sideways_ends(edge, ends)
    assert found[located(edge.a)].facing is Facing.E
    assert found[located(edge.b)].facing is Facing.N


def test_off_the_shallower_south_pin_keeps_its_way() -> None:
    """ROUTE-016: the fallback leaves the north pin sideways, as before JOIN-VERTICAL."""
    # UNDO: stages/sideways.py, drop `or not above` from the elif
    edge, ends = _pair(0, 8)
    found = sideways_ends(edge, ends, above=False)
    assert found[located(edge.a)].facing is Facing.S
    assert found[located(edge.b)].facing is Facing.W
