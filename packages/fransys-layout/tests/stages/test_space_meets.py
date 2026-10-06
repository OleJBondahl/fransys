"""`space._touches` against the old formula: every `open_ends` combination, both step directions."""

from itertools import product

from fransys_layout.geometry import Box
from fransys_layout.stages.space import _touches


def _old_meets(reach, open_ends, low, high):
    (one, other), (one_open, other_open) = reach, open_ends
    if one > other:
        one, other, one_open, other_open = other, one, other_open, one_open
    return (high > one if one_open else high >= one) and (
        low < other if other_open else low <= other
    )


def _old_touches(box, first, second, ends):
    open_ends = (first in ends, second in ends)
    if first[0] == second[0]:
        if not box.x <= first[0] <= box.x + box.width:
            return False
        return _old_meets((first[1], second[1]), open_ends, box.y, box.y + box.height)
    if not box.y <= first[1] <= box.y + box.height:
        return False
    return _old_meets((first[0], second[0]), open_ends, box.x, box.x + box.width)


def test_touches_matches_the_old_formula_for_every_end_and_direction() -> None:
    box = Box(x=4, y=4, width=4, height=4)
    coords = range(0, 13, 2)
    steps = [((c, a), (c, b)) for c, a, b in product(coords, coords, coords) if a != b]
    steps += [((a, c), (b, c)) for c, a, b in product(coords, coords, coords) if a != b]
    for first, second in steps:
        for ends in ((), (first,), (second,), (first, second)):
            assert _touches(box, first, second, frozenset(ends)) == _old_touches(
                box, first, second, frozenset(ends)
            ), (first, second, ends)
