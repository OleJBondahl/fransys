"""D5 ruled 2026-10-02: a power symbol never touches another symbol; it takes a longer lead.

Two supply ends on neighbouring top pins, a pitch apart: their one-grid symbols (16 wide) would
share an edge, so the second takes the fewest whole grids that clear the first.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.texts.power import power_place
from fransys_layout.stages.texts.power_lead import (
    MOST_GRIDS,
    POWER_SYMBOL_UNPLACED,
    _crosses,
    _touches,
    with_power_leads,
)
from fransys_model.kernel import Severity

_PITCH = 16


def _end(port: int, x: int) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", port),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=x, y=0),
        box=Box(x=x - 4, y=-20, width=8, height=8),
        partner_page=2,
        symbol="power-supply",
        symbol_text="+24",
    )


def _led(*xs: int) -> tuple[LinkMarker, ...]:
    return with_power_leads(tuple(_end(n, x) for n, x in enumerate(xs, 1)), (), ())[0]


def test_neighbouring_supply_symbols_touch_no_other_symbol() -> None:
    """UNDO: in `_clear` drop the `taken` boxes from the touch test: all three keep one grid."""
    bodies = [power_place(one).body for one in _led(0, _PITCH, 2 * _PITCH)]
    assert len(bodies) == 3
    for i, body in enumerate(bodies):
        assert all(not _touches(body, other) for other in bodies[i + 1 :])


def test_the_first_symbol_keeps_one_grid_and_the_next_takes_more() -> None:
    """UNDO: in `_led` return `marker` unchanged: the second keeps one grid."""
    first, second = _led(0, _PITCH)
    assert first.symbol_grids == 1
    assert second.symbol_grids > 1


def test_a_lone_symbol_keeps_the_one_grid_lead() -> None:
    """UNDO: start `_led`'s range at 2: a lone symbol gets a longer lead for nothing."""
    assert [one.symbol_grids for one in _led(0)] == [1]


def _crowd() -> LinkMarker:
    """A reference of another port whose box covers the whole page: no lead clears a symbol."""
    return replace(_end(99, 0), symbol="", box=Box(x=-1000, y=-1000, width=2000, height=2000))


def test_a_symbol_no_lead_clears_keeps_one_grid_and_raises_a_warning() -> None:
    """UNDO: in `with_power_leads` drop `findings.extend(...)`: the crowded symbol is silent."""
    marker = _end(1, 0)
    (led, _), found = with_power_leads((marker, _crowd()), (), ())
    assert led.symbol_grids == 1
    (finding,) = found
    assert finding.code == POWER_SYMBOL_UNPLACED
    assert finding.severity == Severity.WARNING
    assert finding.subjects == (marker.port,)
    assert "power-supply" in finding.message
    assert "+24" in finding.message


def test_a_symbol_a_lead_clears_raises_no_finding() -> None:
    """UNDO: in `with_power_leads` make `clear` always falsy: every symbol warns for nothing."""
    assert with_power_leads((_end(1, 0), _end(2, _PITCH)), (), ())[1] == ()


def test_the_body_relation_is_closed_and_the_lead_relation_open() -> None:
    """UNDO: in `_crosses` call `boxes_meet(a, b, closed=True)`: edge-sharing boxes now cross."""
    a, edge, inside = (
        Box(x=0, y=0, width=8, height=8),
        Box(x=8, y=0, width=8, height=8),
        Box(x=4, y=4, width=8, height=8),
    )
    assert _touches(a, edge)
    assert not _crosses(a, edge)
    assert _touches(a, inside)
    assert _crosses(a, inside)


def test_a_symbol_no_lead_clears_keeps_one_grid_and_the_warning_names_the_most_grids() -> None:
    """UNDO: set `MOST_GRIDS` to 1 in the code: the warning text names 1, not 12."""
    wall = replace(_end(9, 0), symbol="", box=Box(x=-500, y=-500, width=1000, height=1000))
    found, findings = with_power_leads((_end(1, 0), wall), (), ())
    marker = found[0]
    assert MOST_GRIDS == 12
    assert marker.symbol_grids == 1
    assert [f.code for f in findings] == [POWER_SYMBOL_UNPLACED]
    assert f"up to {MOST_GRIDS} grids" in findings[0].message
