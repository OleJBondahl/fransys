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


def test_rule_1_wins_over_rule_2_when_both_ends_have_replica_pages_in_an_earlier_set() -> None:
    """Both ends are boundary functions of `_A`: each has a replica page in the top-level set 1
    (where rule 2 would find a page of each) and a home page in set 2. Rule 1 takes set 2."""
    pages_a, pages_b = [(1, 1), (2, 1)], [(1, 2), (2, 3)]
    set_units = {1: None, 2: _A}
    assert _cut(pages_a, pages_b, (_A, _A), set_units) == ((2, 1), (2, 3))
    # the twin: the same pages with ends of no one unit go to rule 2's first unit, the top level
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((1, 1), (1, 2))


@pytest.mark.parametrize(
    "set_units",
    [
        pytest.param({}, id="a-model-with-no-units"),
        pytest.param({1: None, 2: None}, id="every-set-at-the-top-level"),
    ],
)
def test_rule_1_with_no_unit_at_all_is_each_ends_earliest_page(set_units) -> None:
    """Ends of no unit in a model without units: byte-identical to the old rule."""
    pages_a, pages_b = [(2, 1), (1, 3)], [(2, 2), (1, 4)]
    assert _cut(pages_a, pages_b, (None, None), set_units) == _earliest(pages_a, pages_b)


def test_rule_1_the_top_level_counts_as_the_unit_of_two_unit_less_ends() -> None:
    """Two ends of no unit with replica pages in unit `_A`'s set 1 and pages in the top-level
    set 2: the top level is their unit, so the cut is on set 2."""
    pages_a, pages_b = [(1, 1), (2, 1)], [(1, 2), (2, 2)]
    assert _earliest(pages_a, pages_b) == ((1, 1), (1, 2))
    assert _cut(pages_a, pages_b, (None, None), {1: _A, 2: None}) == ((2, 1), (2, 2))


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


def test_rule_2_takes_the_unit_whose_first_drawing_set_is_earliest() -> None:
    """Units `_P` (sets 3 and 5) and `_Q` (set 4) each hold a page of each end: `_P` wins by its
    first set, 3, and the pages are its own, in set 5; not `_Q`'s, though `_Q`'s pages are earlier
    than `_P`'s."""
    set_units = {1: _A, 2: _B, 3: _P, 4: _Q, 5: _P}
    pages_a, pages_b = [(1, 1), (4, 1), (5, 1)], [(2, 1), (4, 2), (5, 2)]
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((5, 1), (5, 2))
    # the mirror: `_Q` first by its first set (3), and it is then the one taken, in its set 4;
    # a walk from the last set would take `_P`'s pages in set 5
    swapped = {1: _A, 2: _B, 3: _Q, 4: _Q, 5: _P}
    assert _cut(pages_a, pages_b, (_A, _B), swapped) == ((4, 1), (4, 2))


def test_rule_2_takes_each_ends_earliest_page_in_the_chosen_unit() -> None:
    """The parent's set has two pages of each end: the earliest of each, not the last."""
    set_units = {1: _A, 2: _B, 3: _P}
    pages_a, pages_b = [(3, 4), (1, 1), (3, 2)], [(2, 1), (3, 5), (3, 3)]
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((3, 2), (3, 3))


@pytest.mark.parametrize(
    "set_units",
    [
        pytest.param({1: None, 2: _A, 3: _B}, id="top-level-set-first"),
        pytest.param({1: _A, 2: _B, 3: None}, id="top-level-set-last"),
    ],
)
def test_rule_2_the_top_level_can_be_the_shared_unit(set_units) -> None:
    """Two top-level units' boundary functions meet on the top-level set's pages."""
    top = next(s for s, u in set_units.items() if u is None)
    home_a, home_b = (
        next(s for s, u in set_units.items() if u is _A),
        next(s for s, u in set_units.items() if u is _B),
    )
    pages_a, pages_b = [(top, 1), (home_a, 1)], [(top, 2), (home_b, 1)]
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((top, 1), (top, 2))


def test_rule_3_no_unit_holding_a_page_of_each_end_is_the_earliest_pages() -> None:
    """A wire bypassing the boundaries: `a` in `_A`'s sets only, `b` in `_B`'s: the earliest
    page of each, whatever order the pages are given in."""
    set_units = {1: _A, 2: _B, 3: _A}
    pages_a, pages_b = [(3, 1), (1, 2), (1, 1)], [(2, 2), (2, 1)]
    assert _cut(pages_a, pages_b, (_A, _B), set_units) == ((1, 1), (2, 1))


def test_an_end_with_no_page_in_its_own_units_sets_falls_through_to_rule_2() -> None:
    """Both ends name unit `_A`, but `a` has only a page in the top-level set 1, where `b` has
    one too: rule 1 has no page for `a`, rule 2 takes the top level."""
    pages_a, pages_b = [(1, 1)], [(2, 1), (1, 2)]
    assert _cut(pages_a, pages_b, (_A, _A), {1: None, 2: _A}) == ((1, 1), (1, 2))


def test_an_end_with_no_page_in_its_own_units_sets_falls_through_to_rule_3() -> None:
    """Both ends name unit `_A`, `a` has only a page in the top-level set, `b` only one in
    `_A`'s set: no unit holds both, so the earliest pages."""
    pages_a, pages_b = [(1, 1)], [(2, 1)]
    assert _cut(pages_a, pages_b, (_A, _A), {1: None, 2: _A}) == ((1, 1), (2, 1))


def test_an_own_unit_that_owns_no_drawing_set_falls_through() -> None:
    """The units are named by the ends but `set_units` has no set for them: rule 3."""
    pages_a, pages_b = [(2, 1), (1, 1)], [(2, 2)]
    assert _cut(pages_a, pages_b, (_A, _A), {1: None, 2: None}) == ((1, 1), (2, 2))
