"""R360: no anchored item overlaps a body, another anchored item or the frame, in the seven cases.

The demo skid and the six corpus designs are built as in `test_drawn_symbols_placed_by_core`; an
anchored item is a drawn symbol the core anchored (its place is in the layouts' anchored list) or a
power symbol. The OVERLAP finding of the drawing invariants (a WARNING with a stock per case) must
never name one. The pump-station case joins when its example is buildable here. The planted case
that proves the check can fail is in the field case
`test_a_power_symbol_beside_a_neighbour_stands_clear_of_it`.
"""

from functools import cache
from itertools import combinations

import pytest
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS, POWER_KEYS, _drawn_and_layouts

from fransys_layout.core import overlaps


@cache
def _anchored_overlaps(name: str) -> tuple[int, list[str]]:
    """(how many anchored items there are, each pair of bodies that meet with one anchored)."""
    drawn, _, sets = _drawn_and_layouts(name)
    anchored = {
        (pages[a.page].id, a.x, a.y, a.orient)
        for layout, pages in sets
        for a in layout.annotations.anchored
    }
    count, found = 0, []
    for page, drawing in drawn.items():
        held = [s for s in drawing.symbols if s.outline is not None]
        count += sum((page, s.x, s.y, s.orient) in anchored or s.key in POWER_KEYS for s in held)
        for a, b in combinations(held, 2):
            if not overlaps(a.outline, b.outline):
                continue
            if any((page, s.x, s.y, s.orient) in anchored or s.key in POWER_KEYS for s in (a, b)):
                found.append(f"{page}: {a.key} / {b.key}")
    return count, found


@pytest.mark.rule("PLACEMENT")
@pytest.mark.rule("POWER-NET")
@pytest.mark.parametrize("name", CASE_PARAMS)
def test_no_anchored_item_overlaps_in_a_case(name: str) -> None:
    assert _anchored_overlaps(name)[1] == []


@pytest.mark.private_input
def test_the_cases_hold_anchored_items_so_the_check_has_something_to_test() -> None:
    assert sum(_anchored_overlaps(name)[0] for name in BUILDS) > 0
