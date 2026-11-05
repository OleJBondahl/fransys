"""POWER-NET (R538, owner 2026-10-02 'no 180 bending'): an anchored power symbol continues its pin.

Over the seven cases of `test_drawn_symbols_placed_by_core`, each anchored power symbol's lead runs
from its owner's pin away from the owner's body, on the side the pin stands on (the pin's own
"""

from functools import cache

import pytest
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS, POWER_KEYS, _drawn_and_layouts


def _heading(body, pin) -> tuple[int, int]:
    """The unit direction away from the body on the edge the pin stands on."""
    x, y = pin
    if y <= body.y:
        return (0, -1)
    if y >= body.y + body.h:
        return (0, 1)
    return (-1, 0) if x <= body.x else (1, 0)


@cache
def _bent(name: str) -> tuple[int, list[str]]:
    """(how many anchored power symbols there are, each that does not continue its pin)."""
    drawn, _, sets = _drawn_and_layouts(name)
    power = {(page, s.x, s.y, s.orient) for page, drawing in drawn.items() for s in drawing.symbols if s.key in POWER_KEYS}
    found: list[str] = []
    count = 0
    for layout, pages in sets:
        placed = {(p.page, p.sym): p for pg in layout.placement.pages for p in pg.placed}
        for a in layout.annotations.anchored:
            if (pages[a.page].id, a.x, a.y, a.orient) not in power:
                continue
            count += 1
            at = placed[(a.page, a.sym)]
            (px, py), (qx, qy) = a.lead
            want = _heading(at.body, (px, py))
            got = ((qx > px) - (qx < px), (qy > py) - (qy < py))
            if got != want:
                found.append(f"{pages[a.page].id}: {a.sym}.{a.pin} leads {got}, pin faces {want}")
    return count, found


@pytest.mark.rule("POWER-NET")
@pytest.mark.parametrize("name", CASE_PARAMS)
def test_every_anchored_power_symbol_continues_its_pins_direction(name: str) -> None:
    assert _bent(name)[1] == []


@pytest.mark.private_input
def test_the_cases_hold_anchored_power_symbols_so_the_check_has_something_to_test() -> None:
    assert sum(_bent(name)[0] for name in BUILDS) > 0


def test_the_heading_of_a_pin_is_the_side_of_the_body_it_stands_on() -> None:
    from fransys_layout.core.values import Box

    body = Box(0, 0, 20, 40)
    assert _heading(body, (10, 0)) == (0, -1)
    assert _heading(body, (10, 40)) == (0, 1)
    assert _heading(body, (0, 20)) == (-1, 0)
    assert _heading(body, (20, 20)) == (1, 0)
