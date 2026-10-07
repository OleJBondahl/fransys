"""layout-0142: the first slot call holds a power end's marker box and stub, not its symbol.

The lead, so the symbol's place, is set from the first labels (D5): at that call a power end has
only a reservation, and an ordinary end is held as drawn.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.firstlabels import _held
from fransys_layout.stages.texts.marker_row import stub_boxes
from fransys_layout.stages.texts.power import power_place, power_reserved


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


def test_a_power_end_reserves_its_box_and_stub_and_an_ordinary_end_nothing() -> None:
    """UNDO: in `power_reserved` drop `*stub_boxes(m)`: the stub is left out."""
    power, plain = _end(1, 0), replace(_end(2, 40), symbol="")
    assert power_reserved((power, plain)) == (power.box, *stub_boxes(power))


def test_the_first_call_holds_ordinary_ends_drawn_and_power_ends_reserved() -> None:
    """UNDO: in `_held` drop `power_reserved(markers)`: the power end's box is not held."""
    power, plain = _end(1, 0), replace(_end(2, 40), symbol="")
    held = _held((power, plain))
    assert {plain.box, *stub_boxes(plain), power.box, *stub_boxes(power)} == set(held)
    assert power_place(power).body not in held
