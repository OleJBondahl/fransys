"""R544/R545: every end of one reference names a pin of one lane of its fan (layout-0405)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fransys_layout.core import PinRef
from fransys_layout.core.cut_ends import ReferenceLaneError, lane_ends
from fransys_layout.core.cut_refs import references
from fransys_layout.core.values import RefKind

STATE = SimpleNamespace(prev=None, start=0)
PLAN: Any = [(0, 1, STATE), (2, 3, STATE)]
PAGE = {0: 1, 1: 1, 2: 2, 3: 2}
A = ((0, PinRef("A1", "p")), (2, PinRef("A2", "p")))
B = ((1, PinRef("B1", "p")), (3, PinRef("B2", "p")))


def _cut() -> Any:
    """Four columns; the page cut after position 1 crosses fan f:x."""
    bounds = [SimpleNamespace(fans=("f:x",) if b == 1 else (), nets=()) for b in range(3)]
    return SimpleNamespace(bounds=bounds, seq=[SimpleNamespace(column=f"c{i}") for i in range(4)])


def _pin_ends(lanes: tuple[Any, ...]) -> tuple[PinRef | None, ...] | None:
    arrows = [r for r in references(_cut(), PLAN, PAGE, frozenset(), {"f:x": lanes}) if r.kind is RefKind.ARROW]
    return tuple(e.pin for e in arrows[0].ends) if arrows else None


def test_both_ends_of_an_arrow_name_pins_of_one_lane() -> None:
    """The cut falls after B1: the nearest pins are B1 and A2, two lanes (R544 L1)."""
    first, second = _pin_ends((A, B)) or (None, None)
    assert first
    assert second
    assert first.sym[0] == second.sym[0] == "A"


def test_the_first_lane_in_the_fans_order_wins() -> None:
    assert _pin_ends((B, A)) == (PinRef("B1", "p"), PinRef("B2", "p"))


def test_a_lane_without_a_pin_on_both_pages_is_skipped() -> None:
    lone = ((0, PinRef("C1", "p")), (1, PinRef("C2", "p")))
    assert _pin_ends((lone, B, A)) == (PinRef("B1", "p"), PinRef("B2", "p"))


def test_a_cut_no_lane_crosses_plans_no_arrow() -> None:
    """Lane A ends before the cut, lane B starts after it (R547)."""
    before, after = ((0, PinRef("A1", "p")), (1, PinRef("A2", "p"))), ((2, PinRef("B1", "p")),)
    assert _pin_ends((before, after)) is None


def test_a_trunk_through_a_page_with_no_tap_names_no_pin_there() -> None:
    lane = ((0, PinRef("A1", "p")), (3, PinRef("A2", "p")))
    page = {0: 1, 1: 1, 2: 2, 3: 3}
    ends = lane_ends("f:x", (lane,), ((1, "c1"), (2, "c2")), page, {0: 0, 1: 0, 2: 0, 3: 0})
    assert [e.pin for e in ends] == [PinRef("A1", "p"), None]


def test_lanes_that_split_the_end_pages_between_them_raise_naming_the_fan() -> None:
    """Cut after position 2, ends on pages 3 and 4: lane X taps page 3, lane Y taps page 4."""
    page = {0: 1, 1: 2, 2: 3, 3: 4, 4: 4, 5: 5}
    plan: Any = [(0, 2, STATE), (3, 5, STATE)]
    bounds = [SimpleNamespace(fans=("f:x",) if b == 2 else (), nets=()) for b in range(5)]
    cut: Any = SimpleNamespace(bounds=bounds, seq=[SimpleNamespace(column=f"c{i}") for i in range(6)])
    x = ((2, PinRef("X1", "p")), (5, PinRef("X2", "p")))
    y = ((0, PinRef("Y1", "p")), (3, PinRef("Y2", "p")))
    with pytest.raises(ReferenceLaneError, match=r"reference f:x: lanes cross the cut"):
        references(cut, plan, page, frozenset(), {"f:x": (x, y)})


def test_a_reference_carries_the_cut_that_planned_it() -> None:
    """R550: Marker.ref comes from Ref.cut, so two cuts of one fan are two references."""
    refs = references(_cut(), PLAN, PAGE, frozenset(), {"f:x": (A,)})
    assert [r.cut for r in refs if r.kind is RefKind.ARROW] == [1]


def test_an_arrow_end_lists_the_pin_of_each_other_crossing_lane_on_its_page_in_also() -> None:
    """R1682: the one marker stands for every crossing lane, so its end names their pins."""
    ends = lane_ends("f:x", (A, B), ((1, "c1"), (2, "c2")), PAGE, {0: 0, 1: 0, 2: 0, 3: 0})
    assert [e.also for e in ends] == [(PinRef("B1", "p"),), (PinRef("B2", "p"),)]
