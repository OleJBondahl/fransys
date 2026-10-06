"""D5 step 6: where a power end's symbol stands, and how it is turned (R7, A5).

The symbol's port point lies exactly one wiring grid from the pin along the pin's facing, and the
symbol is turned so its own port faces back at the pin: render's lead (a straight wiring grid from
the symbol's port along the port's facing) then ends on the pin and never bends. Four pin
facings times the three symbols.
"""

from dataclasses import replace

import pytest
from samples import hid

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, symbol_geometry
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.texts.power import _pin_facing, power_place, power_places

PIN = Point(x=160, y=200)
SYMBOLS = ("power-supply", "ground", "protective-earth")
# the pin's facing, the box a reference marker leaves there (above, below, beside) and the step
# one wiring grid out along that facing
SIDES = {
    Facing.N: (Box(x=PIN.x - 8, y=PIN.y - 40, width=16, height=24), (0, -1)),
    Facing.S: (Box(x=PIN.x - 8, y=PIN.y + 16, width=16, height=24), (0, 1)),
    Facing.E: (Box(x=PIN.x + 16, y=PIN.y - 8, width=40, height=16), (1, 0)),
    Facing.W: (Box(x=PIN.x - 56, y=PIN.y - 8, width=40, height=16), (-1, 0)),
}
BACK = {Facing.N: Facing.S, Facing.S: Facing.N, Facing.E: Facing.W, Facing.W: Facing.E}


def _end(symbol: str, facing: Facing, *, text: str = "+24") -> LinkMarker:
    return LinkMarker(
        connection=hid("conn", 1),
        port=hid("port", 1),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=PIN,
        box=SIDES[facing][0],
        partner_page=2,
        star="ref",
        symbol=symbol,
        symbol_text=text,
    )


@pytest.mark.parametrize("facing", list(SIDES))
@pytest.mark.parametrize("symbol", SYMBOLS)
def test_the_port_point_is_one_wiring_grid_from_the_pin_along_its_facing(
    symbol: str, facing: Facing
) -> None:
    """UNDO: in `power_place` use `2 * WIRING_GRID`: the port point lands two grids out."""
    place = power_place(_end(symbol, facing))
    port = symbol_geometry(symbol, orientation=place.orientation).ports[0]
    dx, dy = SIDES[facing][1]
    assert Point(x=place.at.x + port.at.x, y=place.at.y + port.at.y) == Point(
        x=PIN.x + dx * WIRING_GRID, y=PIN.y + dy * WIRING_GRID
    )


@pytest.mark.parametrize("facing", list(SIDES))
@pytest.mark.parametrize("symbol", SYMBOLS)
def test_the_symbols_port_faces_back_at_the_pin(symbol: str, facing: Facing) -> None:
    """A5: the lead is never bent. UNDO: in `turned` pick the first turn (always R0)."""
    place = power_place(_end(symbol, facing))
    port = symbol_geometry(symbol, orientation=place.orientation).ports[0]
    assert place.facing is facing
    assert port.facing is BACK[facing]


@pytest.mark.parametrize("facing", list(SIDES))
def test_the_orientation_differs_by_side_for_one_symbol(facing: Facing) -> None:
    """The ground symbol needs a different turn for each of the four sides.

    UNDO: in `turned` return `symbol_geometry(symbol)`: three sides then keep R0.
    """
    turns = {side: power_place(_end("ground", side)).orientation for side in SIDES}
    assert len(set(turns.values())) == len(SIDES)
    assert power_place(_end("ground", facing)).orientation is turns[facing]


@pytest.mark.parametrize("facing", list(SIDES))
def test_the_pin_facing_is_read_from_the_marker_box(facing: Facing) -> None:
    """UNDO: in `pin_facing` return `Facing.N` for a box below the pin."""
    assert _pin_facing(_end("ground", facing)) is facing


def test_the_body_is_the_oriented_symbols_body_at_its_origin() -> None:
    """UNDO: in `power_place` leave `body` at the origin (no `translate`)."""
    place = power_place(_end("power-supply", Facing.N))
    body = symbol_geometry("power-supply", orientation=place.orientation).body
    assert (place.body.x, place.body.y) == (place.at.x + body.x, place.at.y + body.y)
    assert (place.body.width, place.body.height) == (body.width, body.height)


def test_several_ends_of_one_port_on_one_page_are_one_symbol() -> None:
    """UNDO: in `power_places` drop the `not in found` test: two symbols on one pin."""
    first, second = _end("ground", Facing.S, text=""), _end("ground", Facing.S, text="")
    assert len(power_places((first, second))) == 1
    reference = replace(first, symbol="", symbol_text="")
    assert power_places((reference,)) == ()
