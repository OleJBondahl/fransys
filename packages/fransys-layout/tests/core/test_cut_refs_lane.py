"""R544/R545: every end of one reference names a pin of one lane of its fan (layout-0405)."""

from __future__ import annotations

from contextlib import suppress
from itertools import accumulate
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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


def test_an_arrow_end_drops_a_lane_whose_pins_on_its_page_all_lie_on_the_other_side_of_the_cut() -> None:
    """R1902, R1904: lane L has its only page-2 pin past the cut, so the end before it does not name L (BUNDLE-ARROW)."""
    runs_on = ((0, PinRef("A1", "p")), (1, PinRef("A2", "p")), (3, PinRef("A3", "p")))
    late = ((0, PinRef("L1", "p")), (3, PinRef("L2", "p")))
    ends = lane_ends("f:x", (runs_on, late), ((1, "c1"), (2, "c2")), {0: 1, 1: 2, 2: 2, 3: 2}, {0: 0, 1: 0, 2: 1, 3: 1})
    assert [e.also for e in ends] == [(), ()]


def test_an_arrow_end_keeps_a_lane_with_no_pin_on_its_page() -> None:
    """R1904: a lane that only passes a page is named as before, by the end whose page holds its pin."""
    runs_on = ((0, PinRef("A1", "p")), (2, PinRef("A2", "p")))
    skips = ((1, PinRef("L1", "p")), (3, PinRef("L2", "p")))
    ends = lane_ends("f:x", (runs_on, skips), ((1, "c1"), (2, "c2")), {0: 1, 1: 1, 2: 2, 3: 3}, {0: 0, 1: 0, 2: 0, 3: 0})
    assert [e.also for e in ends] == [(PinRef("L1", "p"),), ()]


@st.composite
def _lane_cuts(draw: st.DrawFn) -> tuple[tuple[Any, ...], dict[int, int], dict[int, int], int]:
    """Two or three lanes with pins at random positions, random monotone pages and rows, and a boundary."""
    size = draw(st.integers(4, 9))
    page = list(accumulate(draw(st.lists(st.integers(0, 1), min_size=size - 1, max_size=size - 1)), initial=0))
    row = list(accumulate(draw(st.lists(st.integers(0, 1), min_size=size - 1, max_size=size - 1)), initial=0))
    at = st.lists(st.integers(0, size - 1), min_size=2, max_size=4, unique=True)
    lanes = tuple(tuple((i, PinRef(f"L{k}_{i}", "p")) for i in sorted(draw(at))) for k in range(draw(st.integers(2, 3))))
    return lanes, dict(enumerate(page)), dict(enumerate(row)), draw(st.integers(0, size - 2))


def _stands(lane: Any, at: int, cut: int, page_of: dict[int, int]) -> bool:
    return any(page_of[i] == page_of[at] and (i <= cut) == (at <= cut) for i, _ in lane)


@given(_lane_cuts())
@settings(deadline=None, max_examples=300)
def test_an_arrow_names_a_lane_and_pins_that_stand_on_each_ends_page_and_side_where_any_crossing_lane_does(case: Any) -> None:
    """CUT-ROOT P1 (R1926): where a crossing lane has a pin on an end's page and side, the arrow's lane and each `also` pin stand there."""
    lanes, page_of, row_of, cut = case
    lane_of = {pin: ln for ln in lanes for _, pin in ln}
    where = {pin: i for ln in lanes for i, pin in ln}
    crossing = [ln for ln in lanes if min(i for i, _ in ln) <= cut < max(i for i, _ in ln)]
    with suppress(ReferenceLaneError):
        ends = lane_ends("f:x", lanes, ((cut, "c0"), (cut + 1, "c1")), page_of, row_of)
        for end, at in zip(ends, (cut, cut + 1), strict=False):  # no crossing lane: no ends
            assert end.pin is None or page_of[where[end.pin]] == page_of[at]
            if any(_stands(ln, at, cut, page_of) for ln in crossing) and end.pin:
                assert _stands(lane_of[end.pin], at, cut, page_of)
                assert (where[end.pin] <= cut) == (at <= cut)
            for pin in end.also:
                assert page_of[where[pin]] == page_of[at]
                assert (where[pin] <= cut) == (at <= cut)


def _lane(pins: str) -> Any:
    return tuple((int(p[1]), PinRef(p, "p")) for p in pins.split())


_FAN, _NONE = frozenset({"f:x"}), frozenset()


@pytest.mark.rule("BUNDLE-ARROW")
@pytest.mark.parametrize(
    ("lanes", "copy", "arrows"),
    [
        (("A0 A1 A2", "B0 B3 B4"), _FAN, []),
        (("A0 A1 A2", "B0 B3 B4"), _NONE, [(0, ("A0", "A1")), (2, ("B3", "B3"))]),
        (("B0 B3",), _NONE, [(2, ("B0", "B3"))]),  # valve, lamp 15+19
        (("B0 B3",), _FAN, []),
        (("B2 B5",), _NONE, [(4, ("B2", "B5"))]),  # mcc
        (("B0 B2 B3",), _FAN, [(2, ("B2", "B3"))]),
    ],
)
def test_a_copied_fan_has_no_arrow_whose_end_lies_on_another_page(lanes: tuple[str, ...], copy: frozenset[str], arrows: list[Any]) -> None:
    """R2252: a copied fan's arrows join one page, so a row cut counts only the pins on its own page (layout-0592)."""
    row0 = SimpleNamespace(prev=None, start=1)
    plan: Any = [(0, 0, STATE), (1, 4, SimpleNamespace(prev=row0, start=3)), (5, 5, SimpleNamespace(prev=None, start=5))]
    cut: Any = SimpleNamespace(
        bounds=[SimpleNamespace(fans=("f:x",), nets=()) for _ in range(5)], seq=[SimpleNamespace(column=f"c{i}") for i in range(6)]
    )
    refs = references(cut, plan, {0: 1, 1: 2, 2: 2, 3: 2, 4: 2, 5: 3}, copy, {"f:x": tuple(map(_lane, lanes))})
    assert [(r.cut, tuple(e.pin.sym for e in r.ends if e.pin)) for r in refs if r.kind is RefKind.ARROW] == arrows
