"""`stages.line_room` (HL18, layout-0158): a line's pins keep room for its fan, run and stub."""

from types import SimpleNamespace
from typing import Any

from samples import PROFILE, hid, through_geometry

from fransys_layout.geometry import WIRING_GRID
from fransys_layout.stages.line_draw import FAN_GRIDS, LEAVE_GRIDS
from fransys_layout.stages.line_room import line_room

_F = hid("function", 1)
_PORT = hid("port", 1)
_DRAWN: dict[Any, Any] = {
    _F: SimpleNamespace(ports=(SimpleNamespace(port=_PORT, symbol_port="in"),))
}


def _page():
    cell = SimpleNamespace(function=_F, geometry=through_geometry())
    return [[[cell]]]


def test_a_first_row_pin_that_ends_a_line_keeps_the_fan_the_run_and_the_stub_above() -> None:
    """`in` faces N on the keep-out's top edge: the room is fan + run + a grid + the stub box.

    UNDO: `line_room` returns `(0, 0)`, and the leaving line's stub crosses the frame.
    """
    stub = WIRING_GRID + PROFILE.text_height + 2 * PROFILE.marker_padding
    lift, sink = line_room(_page(), _DRAWN, {(_F, _PORT)}, PROFILE)
    assert lift >= (FAN_GRIDS + LEAVE_GRIDS) * WIRING_GRID + stub
    assert lift % WIRING_GRID == 0
    assert sink == 0


def test_a_pin_that_ends_no_line_keeps_no_room() -> None:
    assert line_room(_page(), _DRAWN, set(), PROFILE) == (0, 0)
