"""Stage 4 fills the row and the pin of each arrow and tag end it plans (layout-0292)."""

from __future__ import annotations

import itertools
from dataclasses import replace
from fractions import Fraction

from fransys_layout.core import PinRef, order_blocks
from fransys_layout.core.cut import plan_unit
from fransys_layout.core.cut_costs import positions
from fransys_layout.core.cut_dp import RowState
from fransys_layout.core.cut_ends import Lanes, end_at, link_over_empty_rows, ref_pins
from fransys_layout.core.cut_refs import references
from fransys_layout.core.values import PlacementProblem, Ref, RefEnd, RefKind

from .cut_fixtures import cut_of, elem, free, net, refs_of, side
from .pipeline_fixtures import blocks_of, flow_of
from .solve_fixtures import ring_beside_a_tall_chain
from .test_fallbacks import OPTIONS

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


def _arrow(a: int, b: int) -> Ref:
    """An arrow of fan f:x from row `a` to row `b` of page 1."""
    return Ref("f:x", RefKind.ARROW, (RefEnd(1, None, None, a), RefEnd(1, None, None, b)))


def test_two_arrows_meeting_in_a_row_without_a_trunk_become_one() -> None:
    """layout-0337: the fan has a trunk in rows 0 and 2 only; row 1 holds none."""
    rows = {"f:x": frozenset({(1, 0), (1, 2)})}
    assert link_over_empty_rows([_arrow(0, 1), _arrow(1, 2)], rows) == [_arrow(0, 2)]


def test_an_arrow_left_with_an_end_in_a_row_without_a_trunk_is_dropped() -> None:
    rows = {"f:x": frozenset({(1, 0)})}
    assert link_over_empty_rows([_arrow(0, 1)], rows) == []
    assert link_over_empty_rows([_arrow(0, 1)], {"f:x": frozenset({(1, 0), (1, 1)})}) == [_arrow(0, 1)]


def _one_page_per_position(problem: PlacementProblem) -> tuple[dict[str, Lanes], list[Ref], list[int]]:
    """The lanes, the references, and the positions the net n3's own links stand at (not read from ref_pins)."""
    flow = flow_of(problem, OPTIONS)
    (unit,) = order_blocks(blocks_of(problem, OPTIONS), flow, OPTIONS)
    cut, _, _ = plan_unit(unit, (flow, problem, OPTIONS), frozenset())
    n = len(cut.seq)
    plan = [(i, i, RowState(Fraction(0), 0, 0, i, None)) for i in range(n)]
    pos = positions(cut.seq, cut.by_id)
    pins = ref_pins(flow, pos)
    truth = [pos[a.column or a.pin.sym] for ln in flow.cross_links if ln.net == "n3" for a in ln.ends]
    return pins, references(cut, plan, {i: i + 1 for i in range(n)}, frozenset(), pins), truth


def test_a_net_with_two_lost_links_gets_one_tag_lane_and_a_pin_on_every_end() -> None:
    """KI777-R1: a second source of one name must not overwrite the first's lane (a pinless tag end)."""
    base = ring_beside_a_tall_chain()
    n3 = next(n for n in base.nets if n.id == "n3")
    for lost in itertools.combinations(n3.pins, 2):
        tagged = tuple(replace(n, tagged=(lost,)) if n.id == "n3" else n for n in base.nets)
        pins, refs, truth = _one_page_per_position(replace(base, nets=tagged))
        for cut in range(min(truth), max(truth)):
            assert any(r.net == "n3" and r.ends[0].page <= cut + 1 and r.ends[1].page >= cut + 2 for r in refs), (lost, cut)
        assert len(pins["n3"]) == 1
        assert {p for _, p in pins["n3"][0]} == set(n3.pins), lost
        assert len({(r.net, r.kind, r.cut) for r in refs}) == len(refs), lost
        for ref in refs:
            for end in ref.ends:
                assert end.pin is not None, (lost, ref.net, ref.cut)  # marks refuses an end with no pin (text_markers._order)
                assert end.row is not None or ref.kind is not RefKind.ARROW, (lost, ref.net, ref.cut)  # and an arrow end with no row
        for name, lanes in pins.items():
            for lane in lanes:
                at = [i for i, _ in lane]
                for cut in range(min(at, default=0), max(at, default=0)):
                    spans = [r for r in refs if r.net == name and r.ends[0].page <= cut + 1 and r.ends[1].page >= cut + 2]
                    assert spans, (lost, name, cut)
