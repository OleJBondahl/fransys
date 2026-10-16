"""Stage 4 fills the row and the pin of each arrow and tag end it plans (layout-0292)."""

from __future__ import annotations

from fransys_layout.core import PinRef, RefEnd, RefKind
from fransys_layout.core.cut_ends import end_at

from .cut_fixtures import cut_of, elem, free, net, refs_of, side

PAGE = {0: 1, 1: 1, 2: 1, 3: 2}
ROW = {0: 0, 1: 0, 2: 1, 3: 0}


PLACED = ((0, PinRef("A", "p")), (3, PinRef("B", "p")), (3, PinRef("B", "q")))


def test_an_end_names_the_pin_of_its_page_nearest_its_position() -> None:
    end = end_at(2, "c2", PLACED, PAGE, ROW)
    assert end == RefEnd(1, "c2", PinRef("A", "p"), 1)


def test_an_end_on_a_page_with_no_pin_of_the_reference_names_none() -> None:
    placed = ((3, PinRef("B", "p")),)
    assert end_at(1, "c1", placed, PAGE, ROW).pin is None


def test_equal_distances_break_by_natural_key() -> None:
    placed = ((1, PinRef("A", "p10")), (1, PinRef("A", "p9")))
    assert end_at(1, "c1", placed, PAGE, ROW).pin == PinRef("A", "p9")


def test_a_two_pin_net_cut_by_a_page_gives_each_end_its_own_pin_and_row() -> None:
    result = cut_of([side("k1", 700, 400), side("k2", 700, 400)], [net("x", "k1.e", "k2.e")])
    (tag,) = refs_of(result, RefKind.TAG)
    assert tag.ends == (
        RefEnd(1, "c:k1", PinRef("k1", "e"), 0),
        RefEnd(2, "c:k2", PinRef("k2", "e"), 0),
    )


def test_a_row_wrapped_fan_gives_its_arrows_the_rows_they_stand_in() -> None:
    legs = [f"l{i:02d}" for i in range(12)]
    result = cut_of(
        [free("t0"), *(elem(leg, 150) for leg in legs)],
        [net("bus", "t0.e", *(f"{leg}.n" for leg in legs))],
    )
    (arrow,) = refs_of(result, RefKind.ARROW)
    assert [e.row for e in arrow.ends] == [0, 1]
    assert all(e.pin is not None for e in arrow.ends)
