"""`stages.cutpages.cut_pages`: which pages a severed conductor's cut uses (decision layout-0078).

Pages are `(drawing_set, page)`. Each case names the naive answer, each end's earliest page, and
asserts the rule's answer differs from it, so a `cut_pages` that fell back to the earliest pages
fails the case.
"""

import pytest
from samples import hid

from fransys_layout.stages import cut_pages

_A, _B, _P, _Q = (hid("unit", n) for n in (1, 2, 3, 4))


def _earliest(pages_a, pages_b):
    """The answer the rule replaced: each end's earliest page anywhere."""
    return min(pages_a), min(pages_b)


def _cut(pages_a, pages_b, own_units, set_units):
    return cut_pages(pages_a, pages_b, own_units=own_units, set_units=set_units)


def test_rule_1_a_boundary_end_and_its_peer_of_one_unit_cut_in_that_units_pages() -> None:
    """Case (b): end `a` is a boundary function with a replica page in the top-level set 1 that
    is earlier than its home page in unit `_A`'s set 2; its peer `b` lives in set 2 only."""
    pages_a, pages_b = [(2, 1), (1, 1)], [(2, 3)]
    assert _earliest(pages_a, pages_b) == ((1, 1), (2, 3))
    assert _cut(pages_a, pages_b, (_A, _A), {1: None, 2: _A}) == ((2, 1), (2, 3))


@pytest.mark.parametrize(
    "set_units",
    [
        pytest.param({1: _A, 2: _B, 3: _P}, id="parent-set-numbered-after-its-units-sets"),
        pytest.param({1: _P, 2: _A, 3: _B}, id="parent-set-numbered-before-its-units-sets"),
    ],
)
def test_rule_2_two_units_ends_meeting_in_their_parent_cut_in_the_parents_pages(set_units) -> None:
    """Ends of units `_A` and `_B`, each with a home page in its own set and a black-box replica
    in the parent `_P`'s set: the parent's pages, whichever set number the parent has. With the
    parent last, each end's earliest page is its home page, which the old rule took."""
    home_a, home_b = (
        next(s for s, u in set_units.items() if u is _A),
        next(s for s, u in set_units.items() if u is _B),
    )
    parent = next(s for s, u in set_units.items() if u is _P)
    pages_a, pages_b = [(parent, 1), (home_a, 1)], [(parent, 2), (home_b, 1)]
    if parent > home_a:
        assert _earliest(pages_a, pages_b) == ((home_a, 1), (home_b, 1))
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((parent, 1), (parent, 2))


def test_rule_3_no_unit_holding_a_page_of_each_end_is_the_earliest_pages() -> None:
    """A wire bypassing the boundaries: `a` in `_A`'s sets only, `b` in `_B`'s: the earliest
    page of each, whatever order the pages are given in."""
    set_units = {1: _A, 2: _B, 3: _A}
    pages_a, pages_b = [(3, 1), (1, 2), (1, 1)], [(2, 2), (2, 1)]
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((1, 1), (2, 1))
