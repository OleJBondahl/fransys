"""S4: layout counts each drawing set's reference groups from its own decisions, derive numbers
the placed markers, and the two agree; the box widens when a count reaches three digits.

Layout's count is `references.digits._reference_groups` over the stage's markers; derive's is the
highest `drawing_text.reference_number` among the written markers of a set (a pure off stub is
no reference, D4).
"""

from collections import Counter, defaultdict
from dataclasses import replace
from functools import cache

import pytest
from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_model
from samples import PROFILE, SHEET, hid, page_plan

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.geometry import Box, Point
from fransys_layout.stages.references.digits import (
    Digits,
    SetDigits,
    _digit_widths,
    _reference_groups,
    set_digits,
)
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_layout.stages.types import LinkMarker, MarkerSide
from fransys_model.derive.drawing_text import _branches_of, heads_group, reference_number
from fransys_model.kernel import Model, freeze
from fransys_model.layout import DrawingSet, Page, StarKind, layout_of
from fransys_model.layout import LinkMarker as WrittenMarker

_NARROW_WIDTH_MM = 158


@cache
def _laid_out(name: str) -> tuple[tuple[LinkMarker, ...], Model]:
    """One cabinet golden laid out once: the stage's markers and the written model.

    Each test of this module over 1 s shares this one build per cabinet (the root CLAUDE.md's
    gate rule): a layout of the cabinet takes about a second.
    """
    if name == "narrow":
        model = narrow_model(_NARROW_WIDTH_MM)
    else:
        model = freeze(build_cabinet(second_location=name == "two_location"))
    results, _ = stage_results(model, read_inputs(model))
    return results.layout.markers, write_layout(model, results, write_keys(model))


def _counted(name: str) -> dict[int, int]:
    """Layout's own reference-group count per drawing set, from the stage's markers."""
    markers, _ = _laid_out(name)
    return {one: n for one, n in _reference_groups(markers).items() if n}


def _numbered(name: str) -> dict[int, int]:
    """Derive's highest `#n` per drawing set among the written markers, pure off stubs left out."""
    _, written = _laid_out(name)
    pages, sets = layout_of(written, Page), layout_of(written, DrawingSet)
    markers = layout_of(written, WrittenMarker)
    named = {one.partner for one in markers.values() if one.star is StarKind.BRANCH}
    found: dict[int, int] = defaultdict(int)
    for one in markers.values():
        if one.star is StarKind.OFF and one.id not in named:
            continue  # a pure off stub: no reference (D4)
        number = sets[pages[one.page].drawing_set].number
        found[number] = max(found[number], reference_number(written, one))
    return dict(found)


@pytest.mark.parametrize("name", ["house", "two_location", "narrow"])
def test_layout_counts_as_many_reference_groups_per_set_as_derive_numbers(name: str) -> None:
    """Per drawing set: layout's own group count equals derive's highest `#n`.

    Both ask `heads_group` (RR-O5, layout-0132), so this proves the one predicate, not two copies.
    """
    # CAN-FAIL: stages/references/digits.py `_reference_groups`: the predicate call put back as its
    #     old inline condition with one clause flipped (`side is OWNER` -> `USER`) fails here
    assert _counted(name) == _numbered(name)


@pytest.mark.parametrize("name", ["house", "two_location", "narrow"])
def test_no_branch_names_a_pure_off_stub(name: str) -> None:
    """Derive's `named` can only be true of a merged stub (a stage "ref"), never a pure one.

    A pure off stub is its own partner. So layout, which sees a merged stub as a "ref" end that
    heads its group anyway, gives `heads_group` no `named` for an "off" and counts what derive does.
    """
    # CAN-FAIL: derive/drawing_text.py `_branches_of`: `is StarKind.BRANCH` -> `in (BRANCH, OFF)`
    #     (an off stub names itself a hub) fails the pure-stub assert on the two-location cabinet
    _, written = _laid_out(name)
    hubs = _branches_of(written)
    for one in layout_of(written, WrittenMarker).values():
        if one.star is StarKind.OFF and one.partner == one.id:
            assert one.id not in hubs
    merged = [one for one in layout_of(written, WrittenMarker).values() if one.star is StarKind.OFF]
    assert (name == "two_location") == any(one.partner != one.id for one in merged)


def test_the_cabinets_have_reference_groups_to_count() -> None:
    """Guard: the equality above is not vacuous; the narrow cabinet holds four groups.

    One severed cut (its owner marker), two page-groups of one star net (a reference on each of
    two pages) and one turned reference pair (S12, M12: a net of two ports whose join turns
    back is a reference and a branch, not a wire).
    """
    markers, _ = _laid_out("narrow")
    kinds = Counter(one.star for one in markers if heads_group(one.star, one.side.value))
    assert kinds == {"": 1, "ref": 3}
    assert sum(_counted("narrow").values()) == 4


def _owner(n: int, drawing_set: int) -> LinkMarker:
    """The owner marker of severed cut `n` in `drawing_set`: one reference group."""
    return LinkMarker(
        connection=hid("conductor", n),
        port=hid("port", n),
        side=MarkerSide.OWNER,
        drawing_set=drawing_set,
        page=1,
        at=Point(x=0, y=0),
        box=Box(x=8, y=-4, width=40, height=8),
        partner_page=2,
    )


def test_ninety_nine_groups_keep_two_digits_and_a_hundred_widen() -> None:
    """`#99` and `p99` fit two digits; the 100th group (or sheet) needs a third, and a wider box."""
    # CAN-FAIL: stages/references/digits.py `digit_widths`: `len(str(group_count))` ->
    #     `len(str(group_count - 1))` (100 groups stay at two digits) fails the second assert
    assert _digit_widths(99, 99) == (2, 2)
    assert _digit_widths(100, 5) == (3, 2)
    assert _digit_widths(5, 100) == (2, 3)
    assert _digit_widths(0, 1) == (2, 2)
    assert reference_box_width(SHEET, PROFILE, digits=Digits(3, 2)) > reference_box_width(
        SHEET, PROFILE
    )


def test_a_set_of_a_hundred_groups_gets_three_digits_and_its_neighbour_two() -> None:
    """Set 1: 100 severed cuts on 2 pages; set 2: 99 cuts on 1 page. A user marker is no group."""
    # CAN-FAIL: stages/references/digits.py `set_digits`: `groups[one]` -> `groups[1]` (every set
    #     takes set 1's count) fails on set 2
    markers = [
        *(_owner(n, 1) for n in range(100)),
        *(_owner(n, 2) for n in range(100, 199)),
        replace(_owner(999, 2), side=MarkerSide.USER),
    ]
    plans = [
        replace(page_plan(("a",), number=n), drawing_set=s) for s, n in ((1, 1), (1, 2), (2, 1))
    ]
    assert _reference_groups(markers) == Counter({1: 100, 2: 99})
    assert set_digits(markers, plans, {}) == (
        SetDigits(drawing_set=1, refs=3, sheets=2, other_sets=1),
        SetDigits(drawing_set=2, refs=2, sheets=2, other_sets=1),
    )
