"""Field case: two columns of two stacked contact tables each reserve room for the taller stack.
The bug: the first table is pushed below the A2 star marker, a push the reserve does not count, so the room is 36 grid units short.
Open: strict xfail until a later golden-lane order moves the first table (stacking per layout-0170)."""

from typing import Any

import fransys as fr
import pytest
from _contact_tables import table_body_g, table_symbols
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

PADDING = 2  # the profile's marker padding: the reserve may exceed a stack by one of it


def _chain(d: Any, first: int, live: Any, rail: Any, lamps: Any) -> None:
    """Two relays in series from `live` to the rail, each with a contact feeding its lamp."""
    ks = [d.device(f"K{first + i}", "DEMO-RLY-2CO-24") for i in range(2)]
    ps = [d.device(f"P{first + i}", "DEMO-LAMP-24") for i in range(2)]
    d.series(live.inner, ks[0].coil["A1"], wire=(BU, 0.5))
    d.series(ks[0].coil["A2"], ks[1].coil["A1"], wire=(BU, 0.5))
    d.series(ks[1].coil["A2"], rail, wire=(BU, 0.5))
    for k, p, end in zip(ks, ps, lamps, strict=True):
        d.series(k.co_1["14"], p.lamp["1"], wire=(BU, 0.5))
        d.series(p.lamp["2"], end, wire=(BU, 0.5))


def _built(chains: int) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Relay group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 8).run("R", 8, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        _chain(d, 1, live[1], rail[2].outer, (rail[4].outer, rail[5].outer))
        if chains == 2:
            _chain(d, 3, live[2], rail[3].outer, (rail[6].outer, rail[7].outer))
    return fr.build(d, unit_document(cab))


@pytest.fixture(scope="module")
def got() -> fr.BuildResult:
    """The two-chain circuit, built once."""
    return _built(chains=2)


def _spare_room(built: fr.BuildResult) -> list[int]:
    """Per stack column: the page room below its tallest stack's bottom (>= 0 holds)."""
    (drawing,) = drawn_pages(built.model).values()
    stacks: dict[int, int] = {}
    for t in table_symbols(built.model):
        stacks[t.x] = max(stacks.get(t.x, 0), table_body_g(t)[3])
    return [drawing.area.h - bottom for bottom in stacks.values()]


def test_the_room_reserved_below_the_row_holds_the_tallest_stack(got: fr.BuildResult) -> None:
    """Each column's reserve holds its stack, the first table pushed below the A2 marker (0171).

    `contact_images` pushes the first table below the ground symbol under the foot coil's A2;
    the reserve counts that push (it was 36 short, 472 against 508), and no more than the stack.
    """
    spare = _spare_room(got)
    assert len(spare) == 2
    assert all(0 <= one <= PADDING for one in spare)
