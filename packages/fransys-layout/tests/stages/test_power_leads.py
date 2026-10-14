"""D5 ruled 2026-10-02: a power symbol never touches another symbol; it takes a longer lead.

Two supply ends on neighbouring top pins, a pitch apart: their one-grid symbols (16 wide) would
share an edge, so the second takes the fewest whole grids that clear the first.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.texts.power import page_shapes
from fransys_layout.stages.texts.power_lead import (
    POWER_SYMBOL_UNPLACED,
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


def test_the_first_symbol_keeps_one_grid_and_the_next_takes_more() -> None:
    """UNDO: in `_led` return `marker` unchanged: the second keeps one grid."""
    first, second = _led(0, _PITCH)
    assert first.symbol_grids == 1
    assert second.symbol_grids > 1


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
    assert finding.severity == Severity.INFO
    assert finding.subjects == (marker.port,)
    assert "power-supply" in finding.message
    assert "+24" in finding.message


def test_page_shapes_draws_a_power_symbol_only_when_asked() -> None:
    """The lead search clears the page without the symbols; the text placer clears them too."""
    power = _end(1, 0)
    ordinary = replace(_end(2, 40), symbol="")
    without = page_shapes((power, ordinary), (), (), symbols=False)
    with_symbols = page_shapes((power, ordinary), (), (), symbols=True)
    assert {one.owner for one in without} == {ordinary.port}
    assert ordinary.box in {one.box for one in without}
    assert len(with_symbols) == len(without) + 2
    assert [one for one in with_symbols if one.owner is None] == list(with_symbols[len(without) :])
