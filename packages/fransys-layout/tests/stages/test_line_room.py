"""`stages.line_room` (layout-0158): a line's pins keep room for its fan, run and stub."""

from types import SimpleNamespace
from typing import Any

from samples import PROFILE, hid, through_geometry

from fransys_layout.geometry import WIRING_GRID, snap_up
from fransys_layout.stages.line_draw import FAN_GRIDS
from fransys_layout.stages.line_room import MAX_TIERS, line_room
from fransys_layout.stages.line_trunk import LEAVE_GRIDS

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


def _row(count: int):
    """`count` first-row cells, each with a line end on its `in` port."""
    ids = [hid("function", n) for n in range(1, count + 1)]
    drawn = {
        one: SimpleNamespace(ports=(SimpleNamespace(port=_PORT, symbol_port="in"),)) for one in ids
    }
    cells = [[[SimpleNamespace(function=one, geometry=through_geometry())]] for one in ids]
    return cells, drawn, {(one, _PORT) for one in ids}


def test_each_further_cell_with_a_line_end_reserves_one_tier_up_to_two() -> None:
    """Three or more further cells reserve exactly `MAX_TIERS` tiers more than one cell does.

    UNDO: `MAX_TIERS` is 3 (or the cap is dropped), and a fifth cell reserves a third tier;
    uncapped, the room broke tests/test_harness_fix.py[study].
    """
    tier = snap_up(WIRING_GRID + PROFILE.text_height + 2 * PROFILE.marker_padding)
    lifts = []
    for count in (1, 2, 3, 4, 6):
        page, drawn, ends = _row(count)
        lifts.append(line_room(page, drawn, ends, PROFILE)[0])
    one, two, three, four, six = lifts
    assert [two - one, three - one] == [tier, 2 * tier]
    assert four == six == three
    assert MAX_TIERS == 2
