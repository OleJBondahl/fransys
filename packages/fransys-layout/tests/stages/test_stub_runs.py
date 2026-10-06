"""`stages.stub_runs.functions_through`: the one rule behind placement's refusal and the lint (M9).

A south marker at (0, 0) with its box at y 40..48: its stub is the run (0, 0) to (0, 40).
"""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.stub_runs import functions_through, stub_runs

_OWN, _FOREIGN = hid("function", 1), hid("function", 2)
_MARKER = LinkMarker(
    connection=hid("connection", 1),
    port=hid("port", 1),
    side=MarkerSide.OWNER,
    drawing_set=1,
    page=1,
    at=Point(x=0, y=0),
    box=Box(x=-12, y=40, width=24, height=8),
    partner_page=2,
)
_OWN_PORTS = {_OWN: (Point(x=0, y=0),)}


def _through(body: Box, *ports: Point) -> tuple:
    """The foreign functions the stub runs through, the foreign one's body and ports as given."""
    bodies = {_OWN: Box(x=-5, y=-10, width=10, height=10), _FOREIGN: body}
    return functions_through(_MARKER, bodies, {**_OWN_PORTS, _FOREIGN: ports})


def test_a_stub_through_a_foreign_bodys_interior_runs_through_it() -> None:
    """UNDO: `crosses` replaced by `False` in `functions_through`, and the body is not found."""
    assert _through(Box(x=-5, y=10, width=10, height=10)) == (_FOREIGN,)


def test_a_stub_past_a_foreign_body_runs_through_nothing() -> None:
    assert _through(Box(x=5, y=10, width=10, height=10)) == ()


def test_a_stub_over_a_foreign_port_runs_through_its_function() -> None:
    """UNDO: `_on` replaced by `False`, and the port on the stub is not found."""
    assert _through(Box(x=5, y=10, width=10, height=10), Point(x=0, y=30)) == (_FOREIGN,)


def test_the_markers_own_function_is_never_foreign() -> None:
    """UNDO: `own` emptied in `functions_through`, and the own body above the port is found."""
    bodies = {_OWN: Box(x=-5, y=-10, width=10, height=20)}
    assert functions_through(_MARKER, bodies, _OWN_PORTS) == ()


def test_a_south_markers_stub_is_one_run_from_its_port_to_its_box() -> None:
    """UNDO: `_run_to_box` returns `None`, and the stub is no run."""
    assert [(r.x, r.y, r.to_x, r.to_y) for r in stub_runs(_MARKER)] == [(0, 0, 0, 40)]
