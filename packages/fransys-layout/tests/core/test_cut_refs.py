"""Stage 4's references and findings on hand-built problems: copies, P3, stubs, tall, spilled.

A page holds 1280 x 822 G inside the 16 G margins. Sizes are in G; the designation label is
Size(16, 8) everywhere (cut_fixtures).
"""

from __future__ import annotations

from dataclasses import replace
from itertools import accumulate, permutations
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import assume, given, reject, settings
from hypothesis import strategies as st
from options_fixtures import core_options

from fransys_layout.core import (
    Facts,
    PinRef,
    PlacementProblem,
    Size,
    Unit,
    build_flow,
    order_blocks,
)
from fransys_layout.core.blocks import assign_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.cut_bundle import leg_stubs
from fransys_layout.core.cut_ends import ReferenceLaneError, lane_ends
from fransys_layout.core.cut_ledger import account
from fransys_layout.core.cut_refs import _column_pin, across
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Attach, CrossLink, CutResult, Fan, FlowGraph
from fransys_layout.core.geometry import marker_box_at
from fransys_layout.core.outputs import Trunk
from fransys_layout.core.text_ends import MarkEnv, pinned_stand
from fransys_layout.core.unionfind import UnionFind
from fransys_layout.core.values import CutEnd, PagePlan, Ref, RefEnd, RefKind, RowPlan, StandClass

from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, chain, cut_of, elem, free, net, page_of, refs_of, side

# copies and the P3 check


def test_a_free_sided_hub_is_copied_onto_the_other_page_of_its_fan() -> None:
    """The hub t0 heads leg k1; legs k2 and k3 stand on page 2: page 2 draws t0 again, no arrow."""
    syms = [free("t0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    result = cut_of(syms, [net("feed", "t0.e", "k1.n", "k2.n", "k3.n")])
    assert page_of(result) == {"c:k1": 1, "c:k2": 2, "c:k3": 2}
    assert [(p.page, [r.columns for r in p.rows]) for p in result.spec.pages] == [
        (1, [("c:k1",)]),
        (2, [("c:k2", "c:k3")]),
    ]
    assert result.spec.reference_plan == (Ref("feed", RefKind.COPY, (RefEnd(2, "c:k1", PinRef("k2", "n")),)),)
    (finding,) = result.spec.findings
    assert (finding.code, finding.page, finding.subject) == (
        "HEAD_OFF_LEGS",
        1,
        "f:feed",
    )  # one leg with the head, two on page 2
    assert finding.text.startswith("f:feed")


def test_a_copy_has_one_end_for_each_page_beyond_the_hubs_own() -> None:
    """Three legs of 700 G each take a page; the hub is copied onto pages 2 and 3, P3 is silent."""
    syms = [free("t0"), *(elem(f"k{i}", 700, 400) for i in (1, 2, 3))]
    result = cut_of(syms, [net("feed", "t0.e", "k1.n", "k2.n", "k3.n")])
    assert page_of(result) == {"c:k1": 1, "c:k2": 2, "c:k3": 3}
    assert result.spec.reference_plan == (
        Ref(
            "feed",
            RefKind.COPY,
            (RefEnd(2, "c:k1", PinRef("k2", "n"), stand=StandClass.TRUNK_END), RefEnd(3, "c:k1", PinRef("k3", "n"), stand=StandClass.TRUNK_END)),
        ),
    )
    assert result.spec.findings == ()  # every page holds one leg: the head's page holds no fewer


def test_the_p3_check_is_silent_when_the_head_page_holds_the_most_legs() -> None:
    syms = [free("t0"), elem("k1", 500, 400), elem("k2", 500, 400), elem("k3", 900, 400)]
    result = cut_of(syms, [net("feed", "t0.e", "k1.n", "k2.n", "k3.n")])
    assert page_of(result) == {"c:k1": 1, "c:k2": 1, "c:k3": 2}
    assert [r.kind for r in result.spec.reference_plan] == ["copy"]
    assert result.spec.findings == ()


def test_a_fan_headed_by_a_driver_keeps_its_arrow_and_gets_the_finding() -> None:
    """No hub on the trunk: nothing to copy, the page cut stays an arrow pair, P3 still reports."""
    syms = [elem("d0", 500, 400), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    result = cut_of(syms, [net("feed", "d0.s", "k1.n", "k2.n", "k3.n")])
    assert page_of(result) == {"c:d0": 1, "c:k1": 1, "c:k2": 2, "c:k3": 2}
    assert result.spec.reference_plan == (
        Ref(
            "f:feed",
            RefKind.ARROW,
            (RefEnd(1, "c:k1", PinRef("k1", "n"), 0), RefEnd(2, "c:k2", PinRef("k2", "n"), 0)),
            1,
        ),
    )
    assert [(f.code, f.page, f.subject) for f in result.spec.findings] == [("HEAD_OFF_LEGS", 1, "f:feed")]


@pytest.mark.rule("PAGE-CUT")
@pytest.mark.parametrize("head", ["driver", "hub"])
@pytest.mark.parametrize("legs", [2, 3, 4])
@pytest.mark.parametrize("width", [700, 800])
def test_every_trunk_that_crosses_a_page_cut_has_an_end_of_a_reference_on_each_page_it_has_pins(head: str, legs: int, width: int) -> None:
    """Class: a trunk's pins on pages p and p+1 are joined by an arrow or copy with an end on each page."""
    first = [elem("d0", 500, 400)] if head == "driver" else [free("t0")]
    pin = "d0.s" if head == "driver" else "t0.e"
    syms = [*first, *(elem(f"k{i}", width, 400) for i in range(legs))]
    result = cut_of(syms, [net("feed", pin, *(f"k{i}.n" for i in range(legs)))])
    pages = sorted(set(page_of(result).values()))
    assert len(pages) > 1
    ended = {e.page for r in result.spec.reference_plan if r.kind in (RefKind.ARROW, RefKind.COPY) for e in r.ends}
    assert set(pages[1:]) <= ended
    assert head == "hub" or pages[0] in ended


def test_a_through_jumper_hub_is_not_copied() -> None:
    """A jumper j0 has two nodes, so it is no free-sided symbol: the arrow stays."""
    syms = [elem("j0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    result = cut_of(syms, [net("feed", "j0.n", "j0.s", "k1.n", "k2.n", "k3.n")], Facts(joined=((PinRef("j0", "n"), PinRef("j0", "s")),)))
    assert result.flow.fans[0].hub == "j0"
    assert [r.kind for r in result.spec.reference_plan] == ["arrow"]
    assert [f.code for f in result.spec.findings] == ["HEAD_OFF_LEGS"]


def test_a_row_wrap_inside_one_page_plans_no_copy_and_no_finding() -> None:
    """Twelve 150 G legs wrap to a second row of one page: the arrow pair stays, no page crossed."""
    legs = [f"l{i:02d}" for i in range(12)]
    result = cut_of(
        [free("t0"), *(elem(leg, 150) for leg in legs)],
        [net("bus", "t0.e", *(f"{leg}.n" for leg in legs))],
    )
    (page,) = result.spec.pages
    assert len(page.rows) == 2
    assert [r.kind for r in result.spec.reference_plan] == ["arrow"]
    assert result.spec.findings == ()


def hub_case(widths: tuple[int, int, int], heights: tuple[int, int, int], *, free_hub: bool) -> CutResult:
    """Trunk u (jumper j) joins k1, k2; trunk v (hub t) joins k2, k3; t is free-sided or not."""
    hub = free("t") if free_hub else elem("t")
    pins = ("t.e",) if free_hub else ("t.n", "t.s")
    cols = [elem(f"k{i}", w, h) for i, (w, h) in enumerate(zip(widths, heights, strict=True), 1)]
    joined = tuple((PinRef(s, "n"), PinRef(s, "s")) for s in ("j", "t") if s == "j" or not free_hub)
    return cut_of([*cols, elem("j"), hub], [net("u", "k1.s", "k2.s", "j.n", "j.s"), net("v", *pins, "k2.n", "k3.n")], Facts(joined=joined))


def test_the_cut_prefers_the_break_where_the_arrow_is_a_copy() -> None:
    """No page holds k1, k2 and k3 together, any two fit: the cut falls after k1 or after k2.

    Each break costs one arrow, so with a jumper hub on v the fills decide: after k1. A free-sided
    hub turns the break at v into a copy, which costs nothing: after k2, with the copy planned.
    """
    jumper = hub_case((600, 600, 200), (600, 600, 600), free_hub=False)
    assert page_of(jumper) == {"c:k1": 1, "c:k2": 2, "c:k3": 2}
    assert [(r.net, r.kind) for r in jumper.spec.reference_plan] == [("f:u", "arrow")]
    free_sided = hub_case((600, 600, 200), (600, 600, 600), free_hub=True)
    assert page_of(free_sided) == {"c:k1": 1, "c:k2": 1, "c:k3": 2}
    assert free_sided.spec.reference_plan == (Ref("v", RefKind.COPY, (RefEnd(2, "c:k2", PinRef("k3", "n"), stand=StandClass.TRUNK_END),)),)


def test_a_row_wrap_through_the_trunk_of_a_free_sided_hub_is_not_priced_as_a_copy() -> None:
    """Short columns wrap inside one page, where v keeps its arrow pair, whatever the hub."""
    for free_hub in (False, True):
        (page,) = hub_case((600, 600, 600), (100, 210, 40), free_hub=free_hub).spec.pages
        assert [row.columns for row in page.rows] == [("c:k1",), ("c:k2", "c:k3")]


# stubs

NO_FLOW = FlowGraph((), (), (), (), ())


def test_an_end_that_carries_an_arrow_gets_no_stub() -> None:
    """The same net, cut by the DP: every end already stands under an arrow, so none stubs too."""
    syms = [replace(side(n, 700, 500), unit=u) for n, u in zip("xyz", ("U1", "U3", "U2"), strict=True)]
    facts = Facts(
        units=(Unit("U1", None, (PinRef("x", "e"),)), Unit("U2", None, (PinRef("z", "e"),))),
    )
    result = cut_of(syms, [net("m", "x.e", "y.e", "z.e", crosses_unit=True)], facts)
    assert refs_of(result, "stub") == []
    arrows = refs_of(result, "arrow")
    assert {e.pin for r in arrows for e in r.ends} >= {PinRef("x", "e"), PinRef("z", "e")}


def test_a_copied_hub_end_on_a_page_cut_gets_no_stub_at_the_copied_end() -> None:
    """The copy of t0 on page 2 names k2.n, a boundary pin too: it carries the copy, no stub."""
    syms = [free("t0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    out = tuple((PinRef(k, "n"), PinRef("out", k)) for k in ("k2", "k3"))
    facts = _wired(*out, units=(Unit("U1", None, tuple(a for a, _ in out)),))
    syms = [replace(s, unit="U1") if s.id in ("k2", "k3") else s for s in syms]
    result = cut_of(syms, [net("feed", "t0.e", "k1.n", "k2.n", "k3.n", crosses_unit=True)], facts)
    (copy,) = refs_of(result, "copy")
    assert copy.ends == (RefEnd(2, "c:k1", PinRef("k2", "n")),)
    (stub,) = refs_of(result, "stub")
    assert [e.pin for e in stub.ends] == [PinRef("k3", "n")]  # k2.n is the copied end: no stub


def test_a_hub_with_boundary_pins_on_both_sides_is_cut_by_an_arrow_pair_not_copied() -> None:
    """R455: the copy of a unit's boundary terminal tells a reader nothing the arrow pair does."""
    syms = [free("t0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    facts = Facts(units=(Unit("U1", None, (PinRef("t0", "n"), PinRef("t0", "s"))),))
    result = cut_of(syms, [net("feed", "t0.e", "k1.n", "k2.n", "k3.n")], facts)
    assert page_of(result) == {"c:k1": 1, "c:k2": 2, "c:k3": 2}
    assert refs_of(result, "copy") == []
    assert {r.net for r in refs_of(result, "arrow")} == {"f:feed"}


# tall columns


def test_a_tall_column_is_cut_into_two_columns_with_one_planned_tag() -> None:
    """Twelve cells of 96 G stack to 1240 G on an 822 G page; the fold falls after cell 7."""
    ids = [f"k{i:02d}" for i in range(12)]
    result = cut_of([elem(i, 40, 96) for i in ids], chain(ids))
    top, bottom = result.flow.columns
    assert (top.id, bottom.id) == ("c:k00#a", "c:k00#b")
    assert ([c.sym for c in top.lanes[0].cells], [c.sym for c in bottom.lanes[0].cells]) == (
        ids[:7],
        ids[7:],
    )
    assert (top.height, bottom.height) == (
        7 * 96 + 6 * 8,
        5 * 96 + 4 * 8,
    )  # each half its own height: cells and 8 G wires
    assert (top.width, bottom.width) == (40, 40)
    assert result.blocks[0].blocks[0].columns == ("c:k00#a", "c:k00#b")
    assert result.spec.reference_plan == (
        Ref(
            "x6",
            RefKind.TAG,
            (RefEnd(1, "c:k00#a", PinRef("k06", "s")), RefEnd(1, "c:k00#b", PinRef("k07", "n"))),
        ),
    )
    (page,) = result.spec.pages
    assert [row.columns for row in page.rows] == [("c:k00#a", "c:k00#b")]


def test_thirty_cells_of_96_g_cut_without_error_into_two_columns() -> None:
    """Thirty cells 96 G wide and 32 G high stack to 1192 G: the tag at the cut holds 48 G, so eighteen fill the page and twelve remain."""
    ids = [f"k{i:02d}" for i in range(30)]
    result = cut_of([elem(i, 96) for i in ids], chain(ids))
    top, bottom = result.flow.columns
    assert [len(c.lanes[0].cells) for c in (top, bottom)] == [18, 12]
    assert (top.height, bottom.height) == (18 * 32 + 17 * 8, 12 * 32 + 11 * 8)
    assert (top.width, bottom.width) == (96, 96)
    assert result.spec.reference_plan == (
        Ref(
            "x17",
            RefKind.TAG,
            (RefEnd(1, "c:k00#a", PinRef("k17", "s")), RefEnd(1, "c:k00#b", PinRef("k18", "n"))),
        ),
    )


def test_the_split_keeps_every_field_of_the_fan_and_block_it_rewrites() -> None:
    """The tail fan hangs from the foot of the tall column: it moves to the lower half."""
    ids = [f"k{i:02d}" for i in range(12)]
    syms = [*(elem(i, 40, 96) for i in ids), elem("w"), elem("y")]
    prob = PlacementProblem(
        AREA,
        tuple(syms),
        (*chain(ids), net("tail", "k11.s", "w.n", "y.n")),
        facts=Facts(),
    )
    options = core_options(
        marker=MARKER,
    )
    flow = build_flow(prob, options)
    (tail,) = flow.fans
    flow = replace(flow, fans=(replace(tail, crossed=(("w1", (1, 0)),)),))
    lists = order_blocks(assign_blocks(flow, prob, options), flow, options)
    lists = tuple(replace(bl, blocks=tuple(replace(b, fixed_order=True) for b in bl.blocks)) for bl in lists)
    result = cut_pages(lists, flow, prob, options)
    (moved,) = result.flow.fans
    assert (moved.drivers[0].column, moved.drivers[0].cell) == ("c:k00#b", 11 - 7)
    assert moved.crossed == (("w1", (1, 0)),)
    before = next(b for bl in lists for b in bl.blocks if "c:k00" in b.columns)
    after = next(b for bl in result.blocks for b in bl.blocks if "c:k00#a" in b.columns)
    assert after.fixed_order
    assert after.height_est < before.height_est  # the block is as tall as its pieces
    assert replace(after, columns=before.columns, height_est=before.height_est) == before


# columns spilled off an overfull card


def overfull(height: int) -> CutResult:
    """Box A1 with forty columns of 64 G, one on each pin.

    More columns than the 1280 G page holds at their pitch: the blocks stage keeps what fits
    on the card and lets the rest leave it and stand free.
    """
    syms = [box_sym(40, 20), *(elem(f"k{i}", 64, height, "CH") for i in range(1, 41))]
    return cut_of(syms, [net(f"n{i}", f"A1.p{i}", f"k{i}.n") for i in range(1, 41)])


def spilled_of(result: CutResult) -> tuple[list[str], list[str]]:
    """The columns of the card of A1 and the columns that left it, as the blocks stage made them."""
    (unit,) = result.blocks
    card = [c for b in unit.blocks if b.kind == "card" for c in b.columns]
    return card, [c for b in unit.blocks if b.kind == "column" for c in b.columns]


def test_each_spilled_column_gets_one_tag_to_its_box_pin() -> None:
    result = overfull(32)
    card, spilled = spilled_of(result)
    assert spilled
    first, second = result.spec.pages  # PAGE-CUT: the overfull card is cut, the spill is page 2
    assert any(set(card) <= set(row.columns) for row in first.rows)  # the card is never cut
    assert {c for row in second.rows for c in row.columns} == set(spilled)
    expected = [
        Ref(
            f"n{c[3:]}",
            RefKind.TAG,
            (RefEnd(2, c, PinRef(f"k{c[3:]}", "n")), RefEnd(1, None, PinRef("A1", f"p{c[3:]}"))),
        )
        for c in spilled
    ]
    assert list(result.spec.reference_plan) == expected  # the columns of the card plan nothing


def test_a_spilled_tag_end_carries_the_page_of_its_own_side() -> None:
    """Columns 320 G tall fill the card's page: the free columns take page 2, the box pin stays."""
    result = overfull(320)
    card, spilled = spilled_of(result)
    where = page_of(result)
    assert {where[c] for c in card} == {1}
    assert {where[c] for c in spilled} == {2}
    tags = result.spec.reference_plan
    assert [t.net for t in tags] == [f"n{c[3:]}" for c in spilled]
    assert {(t.ends[0].page, t.ends[1].page) for t in tags} == {(2, 1)}


def test_a_spilled_column_holding_no_pin_of_the_net_raises_naming_the_net_column_and_fix() -> None:
    """Column k1-k2 holds no pin of net m (on k3 and k4): the spilled tag is refused."""
    syms = [elem("k1"), elem("k2"), elem("k3"), elem("k4")]
    result = cut_of(syms, [*chain(["k1", "k2"]), net("m", "k3.n", "k4.n")])
    (column,) = [c for c in result.flow.columns if any(x.sym == "k1" for ln in c.lanes for x in ln.cells)]
    with pytest.raises(
        CoreError,
        match=(
            r"cut: net m: spilled column c:k1 holds none of its pins; "
            r"a spilled tag is planned only for a column that holds a pin of the net"
        ),
    ):
        _column_pin(column, net("m", "k3.n", "k4.n"))


# the ledger: one carrier per required conductor (CUT-LEDGER CL1)


def _wired(*pairs: tuple[PinRef, PinRef], units: tuple[Unit, ...] = ()) -> Facts:
    """Facts whose required conductors are `pairs`, each known from both ends."""
    return Facts(units=units, far_ends=(*pairs, *((b, a) for a, b in pairs)), groups=tuple(pairs))


def _account(syms, nets, facts, planned=()):
    """`account` on the pages the cut gave, with `planned` as the arrows, tags and copies already made."""
    result = cut_of(syms, nets, facts)
    where = {c[2:]: p for c, p in page_of(result).items()}
    return account(PlacementProblem(AREA, tuple(syms), tuple(nets), facts), NO_FLOW, where, planned, result.spec.pages)


def _pair(size: int):
    """Units' boundary pins x.e and y.e, one conductor between them: one page when small, two when big."""
    syms = [replace(side(n, size, size), unit=u) for n, u in (("x", "U1"), ("y", "U2"))]
    x, y = PinRef("x", "e"), PinRef("y", "e")
    return syms, [net("m", "x.e", "y.e", crosses_unit=True)], _wired((x, y)), (x, y)


def test_a_conductor_wired_on_its_page_is_ink_and_gets_no_stub() -> None:
    syms, nets, facts, (x, y) = _pair(200)
    got = _account(syms, nets, facts)
    assert got.refs == ()
    assert got.ink == {(x, y), (y, x)}


def test_a_conductor_across_pages_has_a_stub_at_each_end() -> None:
    syms, nets, facts, (x, y) = _pair(700)
    got = _account(syms, nets, facts)
    assert got.ink == frozenset()
    assert {e.pin for r in got.refs for e in r.ends} == {x, y}


def test_a_conductor_to_a_pin_outside_the_problem_has_a_stub_at_its_near_pin() -> None:
    syms = [side("x", 300, 300), side("y", 300, 300)]
    x = PinRef("x", "e")
    got = _account(syms, [net("m", "x.e", "y.e")], _wired((x, PinRef("out", "e"))))
    assert got.refs == (Ref("m", RefKind.STUB, (RefEnd(1, None, x, far=(PinRef("out", "e"),)),)),)
    assert got.stubbed == {x}


def test_a_crossing_end_stands_at_a_trunk_end_by_its_fans_attachments_on_the_page_not_by_the_nets_pins() -> None:
    """KI-616: x and y attach one fan; z is a net pin of no fan, so its end stands at its pin."""
    syms = [side(n, 200, 200) for n in "xyz"]
    x, y, z = (PinRef(n, "e") for n in "xyz")
    outs = [PinRef(f"out{n}", "e") for n in "xyz"]
    fan = Fan("f", ("m",), (Attach(None, 0, 0, x, net="m"),), (Attach(None, 0, 0, y, net="m"),), None, 1, "S")
    problem = PlacementProblem(AREA, tuple(syms), (net("m", "x.e", "y.e", "z.e", crosses_unit=True),), _wired(*zip((x, y, z), outs, strict=True)))
    got = account(problem, replace(NO_FLOW, fans=(fan,)), dict.fromkeys("xyz", 1), (), ())
    assert {e.pin: e.stand for r in got.refs for e in r.ends} == {x: StandClass.TRUNK_END, y: StandClass.TRUNK_END, z: StandClass.PIN}


def test_a_pin_with_a_drawn_wire_and_a_conductor_out_of_the_problem_has_a_stub_for_the_outer_one() -> None:
    """KI-615: x is ink with y, and wired out of the set: a net crossing a unit still owes x one stub end naming the far pin."""
    syms = [side("x", 300, 300), side("y", 300, 300)]
    x, y, out = PinRef("x", "e"), PinRef("y", "e"), PinRef("out", "e")
    facts = replace(_wired((x, y)), far_ends=(*_wired((x, y)).far_ends, (x, out)))  # the set's groups hold the in-set pair only
    got = _account(syms, [net("m", "x.e", "y.e", crosses_unit=True)], facts)
    assert got.ink == {(x, y), (y, x)}
    assert [(e.pin, e.far) for r in got.refs for e in r.ends] == [(x, (out,))]


def test_a_stub_end_names_the_far_pin_of_every_undrawn_conductor_at_its_pin() -> None:
    """R1581: one stub end per pin, its `far` every far pin of the pin's undrawn conductors, in the order given."""
    syms = [side("x", 300, 300), side("y", 300, 300)]
    x = PinRef("x", "e")
    outs = (PinRef("out", "e"), PinRef("out", "f"))
    got = _account(syms, [net("m", "x.e", "y.e")], _wired((x, outs[0]), (x, outs[1])))
    (ref,) = got.refs
    (end,) = ref.ends
    assert (end.pin, end.far) == (x, outs)


def test_an_arrow_end_carries_its_pin_and_the_other_end_stubs() -> None:
    """An arrow on x.e cuts the wire there: x is carried, y on the same page is not drawn to it and stubs."""
    syms, nets, facts, (x, y) = _pair(200)
    arrow = Ref("m", RefKind.ARROW, (RefEnd(1, None, x),))
    got = _account(syms, nets, facts, (arrow,))
    assert got.ink == frozenset()
    assert [e.pin for r in got.refs for e in r.ends] == [y]


def test_an_arrow_with_both_ends_on_one_pin_cuts_it_like_a_lone_end() -> None:
    """CUT-COPY-ENDS: two arrow ends on x.e are one pin, so x.e is cut from y as a lone arrow end cuts it."""
    syms, nets, facts, (x, _y) = _pair(200)
    got = _account(syms, nets, facts, (Ref("m", RefKind.ARROW, (RefEnd(1, None, x), RefEnd(1, None, x))),))
    assert got.ink == frozenset()


def test_a_copy_end_keeps_its_same_page_neighbour_wire() -> None:
    """CUT-COPY-ENDS: a copy stands at x.e and its wire to y on that page is drawn, where an arrow there cuts it."""
    syms, nets, facts, (x, y) = _pair(200)
    got = _account(syms, nets, facts, (Ref("m", RefKind.COPY, (RefEnd(1, None, x),)),))
    assert got.ink == {(x, y), (y, x)}


def test_a_cut_end_pin_keeps_its_same_page_neighbour_wire() -> None:
    """R1008: x is tagged to z on another page, so (x, z) is severed; (x, y) on one page stays ink."""
    syms = [side("x", 200, 200), side("y", 200, 200), side("z", 1200, 700)]
    x, y, z = (PinRef(n, "e") for n in "xyz")
    nets = [net("m", "x.e", "y.e", "z.e")]
    tag = Ref("m", RefKind.TAG, (RefEnd(1, None, x), RefEnd(2, None, z)))
    got = _account(syms, nets, _wired((x, y), (x, z)), (tag,))
    assert got.ink == {(x, y), (y, x)}
    assert got.refs == ()


def _line_case(*lines: str):
    """One conductor to outside per symbol x, y, ..., each lone net cut at its pin on the given harness line."""
    syms = [side(n, 100, 100) for n in "xyz"[: len(lines)]]
    nets = [replace(net(f"m{i}", f"{s.id}.e"), cut=(CutEnd(PinRef(s.id, "e"), line),)) for i, (s, line) in enumerate(zip(syms, lines, strict=True))]
    return _account(syms, nets, _wired(*((PinRef(s.id, "e"), PinRef("out", s.id)) for s in syms)))


def test_cut_pins_of_one_line_or_of_no_line_each_end_in_their_own_stub() -> None:
    """R1151: a line pin whose lead stops short is not covered; no pin rides on a neighbour's stub."""
    assert [r.net for r in _line_case("W3/X1", "W3/X1", "W3/X1").refs] == ["m0", "m1", "m2"]
    assert [r.net for r in _line_case("W3/X1", "W4/X1", "").refs] == ["m0", "m1", "m2"]


def test_a_required_pin_that_is_on_no_net_raises_naming_it() -> None:
    syms = [side("x", 100, 100), side("y", 100, 100)]
    with pytest.raises(CoreError, match=r"a pin of a required group has no ink and no reference: x q"):
        _account(syms, [net("m", "y.e")], _wired((PinRef("x", "q"), PinRef("out", "q"))))


def test_every_row_piece_of_a_net_on_one_page_gets_a_stub_naming_a_pin_outside_it() -> None:
    """R676: twelve 150 G legs wrap to two rows; each row is a drawn piece and carries a stub at a pin wired to the other row."""
    legs = [f"l{i:02d}" for i in range(12)]
    syms = [free("t0"), *(elem(leg, 150) for leg in legs)]
    names = ["t0.e", *(f"{leg}.n" for leg in legs)]
    pins = [PinRef(*n.split(".")) for n in names]
    facts = Facts(far_ends=tuple(pr for p in pins[1:] for pr in ((pins[0], p), (p, pins[0]))), groups=(tuple(pins),))
    nets = [net("bus", *names)]
    (page,) = cut_of(syms, nets, facts).spec.pages
    row_of = {c[2:]: r for r, row in enumerate(page.rows) for c in row.columns}
    flow = cut_of(syms, nets, facts).flow
    got = account(PlacementProblem(AREA, tuple(syms), tuple(nets), facts), flow, dict.fromkeys(row_of, page.page), (), (page,))
    assert {row_of[p.sym] for p in got.stubbed} == {0, 1}


def _legs_of(far: tuple[tuple[PinRef, PinRef], ...], ink: set[tuple[PinRef, PinRef]], *, fanned: bool = True) -> tuple[list[Ref], list[Ref]]:
    """`_legs` on a fan pin x.e (in no fan when not `fanned`) with a lead stub: `far` its conductors, `ink` the ones drawn."""
    from fransys_layout.core.cut_ledger import _legs
    from fransys_layout.core.flow_values import Attach, Fan
    from fransys_layout.core.values import PagePlan, RowPlan

    x = PinRef("x", "e")
    fan = Fan("f", ("m",), (Attach("c:x", 0, 0, x, net="m"),), (), None, 1, "H")
    page = PagePlan(1, "", (RowPlan(("c:x",), ()),), ())
    problem = PlacementProblem(AREA, (side("x", 40, 40),), (net("m", "x.e", "y.e"),), Facts(far_ends=far))
    made = [Ref("m", RefKind.STUB, (RefEnd(1, None, x),))]
    flow: Any = SimpleNamespace(fans=[fan] if fanned else [])
    return _legs(problem, flow, {"x": 1, "y": 1, "z": 2, "c:x": 1}, [page], (ink, made))


def test_a_fan_pin_drawn_to_every_far_end_keeps_no_stub_and_no_leg() -> None:
    """MARKER-FREE-SIDE (R1301): a one-sided pin carries no marker; its undrawn conductors get a leg each, a pin with none gets none."""
    x, y, z = PinRef("x", "e"), PinRef("y", "e"), PinRef("z", "e")
    assert _legs_of(((x, y),), {(x, y)}) == ([], [])
    kept, legs = _legs_of(((x, y), (x, z)), {(x, y)})
    assert kept == []
    assert [r.ends[0].pin for r in legs] == [x]
    kept, legs = _legs_of(((x, z),), set())
    assert kept == []
    assert [r.ends[0].pin for r in legs] == [x]
    assert _legs_of((), set()) == ([], [])  # a pin with no conductor gets no leg (R1308, R1541)
    kept, legs = _legs_of(((x, y), (x, z)), {(x, y)}, fanned=False)  # el-0108: in no fan it has no leg, so its stub stays
    assert [e.pin for r in kept for e in r.ends] == [x]
    assert legs == []


def _leg(pin: str) -> RefEnd:
    return RefEnd(1, "C1", PinRef("K1", pin), 0, StandClass.LEG)


def test_a_bundle_of_legs_on_one_page_is_one_stub_that_lists_every_pin_it_ends() -> None:
    """BUNDLE (R1319): one end stands for the bundle and names the other pins' conductors."""
    pins = [PinRef("K1", n) for n in "123"]
    ends = [_leg(p.pin) for p in pins]
    far = {p: {(2, "B1")} for p in pins}
    (stub,) = leg_stubs(ends, far, {p: f"n{p.pin}" for p in pins})
    assert (stub.ends[0].pin, stub.ends[0].also) == (pins[0], (pins[1], pins[2]))


def test_legs_that_leave_to_one_far_device_outside_the_set_are_one_bundle() -> None:
    """KI-615: a far end in no page of the set is page 0, so pins wired to one outside device bundle like those of one far page."""
    from fransys_layout.core.cut_ledger import _far_pages

    pins = [PinRef("K1", n) for n in "12"]
    out = PinRef("far", "e")
    far = _far_pages(tuple((p, out) for p in pins), set(), {"K1": 1})
    assert far == {p: {(0, "far")} for p in pins}
    (stub,) = leg_stubs([_leg(p.pin) for p in pins], far, {p: f"n{p.pin}" for p in pins})
    assert stub.ends[0].also == (pins[1],)


def test_legs_that_leave_to_different_far_devices_are_a_stub_each() -> None:
    pins = [PinRef("K1", n) for n in "12"]
    ends = [_leg(p.pin) for p in pins]
    far = {pins[0]: {(2, "B1")}, pins[1]: {(2, "B2")}}
    stubs = leg_stubs(ends, far, {p: f"n{p.pin}" for p in pins})
    assert [r.ends[0].also for r in stubs] == [(), ()]


def test_a_tagged_link_gets_its_tag_unless_every_pin_is_already_a_planned_end() -> None:
    """layout-0508: a lost link with a pin no planned reference ends still needs its tag; one fully referenced does not."""
    a, b = PinRef("a", "p"), PinRef("b", "p")
    flow: Any = SimpleNamespace(cross_links=[CrossLink("n", tuple(Attach(None, 0, 0, p, net="n") for p in (a, b)), tagged=True)])
    where = {"a": 1, "b": 1}
    whole = [Ref("n", RefKind.TAG, (RefEnd(1, None, a), RefEnd(1, None, b)))]
    part = [Ref("n", RefKind.STUB, (RefEnd(1, None, a),))]
    assert across(flow, where, whole) == []
    assert [(r.net, r.kind, [e.pin for e in r.ends]) for r in across(flow, where, part)] == [("n", RefKind.TAG, [a, b])]


def test_a_boundary_pin_with_a_drawn_and_an_undrawn_conductor_is_stubbed() -> None:
    """el-0108: x.e is wired to y on its page and leaves the unit to a pin outside the problem; the drawn wire does not carry the one that leaves."""
    syms, nets, _, (x, y) = _pair(200)
    facts = Facts(units=(Unit("U1", None, (x,)),), far_ends=((x, y), (y, x), (x, PinRef("out", "e"))), groups=((x, y),))
    got = _account(syms, nets, facts)
    assert got.ink == {(x, y), (y, x)}
    assert x in got.stubbed


def test_a_piece_whose_references_pair_among_themselves_is_joined_to_the_rest_by_one_pair_not_a_stub() -> None:
    """BANK-PIECES-JOINED (R1711, layout-0508 A21): a 4-pin link over three pages, tagged a-b and c-d, with b and c on page 2 in
    different rows and no wire between them: the pieces {a, b} and {c, d} are both touched by a tag and neither is ended, so the ledger
    hands the loop one join pair with an end in each piece and plans no stub. Red when `_made` asks "a reference stands at this pin"."""
    syms = [side(n, 100, 100) for n in "abcd"]
    a, b, c, d = (PinRef(n, "e") for n in "abcd")
    facts = Facts(units=(), far_ends=((a, b), (b, a), (c, d), (d, c)), groups=((a, b, c, d),))
    planned = (Ref("m", RefKind.TAG, (RefEnd(1, None, a), RefEnd(2, None, b))), Ref("m", RefKind.TAG, (RefEnd(2, None, c), RefEnd(3, None, d))))
    pages = (
        PagePlan(1, "U1", (RowPlan(("a",), ("a",)),), ()),
        PagePlan(2, "U1", (RowPlan(("b",), ("b",)), RowPlan(("c",), ("c",))), ()),
        PagePlan(3, "U1", (RowPlan(("d",), ("d",)),), ()),
    )
    got = account(
        PlacementProblem(AREA, tuple(syms), (net("m", "a.e", "b.e", "c.e", "d.e"),), facts), NO_FLOW, {"a": 1, "b": 2, "c": 2, "d": 3}, planned, pages
    )
    assert got.refs == ()
    ((net_id, (near, far)),) = got.unjoined
    assert net_id == "m"
    assert {near, far} & {a, b}
    assert {near, far} & {c, d}


def _copy_account(*, fanned: bool):
    """`account` on a and b, a required pair on two pages: a COPY stands at c (a's page, wired to a) and at b, a tag at a; b has ink to d."""
    from fransys_layout.core.flow_values import Attach, Fan

    syms = [side(n, 100, 100) for n in "abczd"]
    a, b, c, z, d = (PinRef(n, "e") for n in "abczd")
    facts = Facts(units=(), far_ends=((a, b), (b, a), (a, c), (c, a), (b, d), (d, b)), groups=((a, b),))
    planned = (
        Ref("m", RefKind.COPY, (RefEnd(1, None, c), RefEnd(2, None, b))),
        Ref("m", RefKind.TAG, (RefEnd(1, None, a), RefEnd(1, None, z))),
    )
    pages = (
        PagePlan(1, "U1", (RowPlan(("a", "c", "z"), ("a", "c", "z")),), ()),
        PagePlan(2, "U1", (RowPlan(("c:b", "d"), ("c:b", "d")),), ()),
    )
    problem = PlacementProblem(AREA, tuple(syms), (net("m", "a.e", "b.e", "c.e", "z.e", "d.e"),), facts)
    fan = Fan("f", ("m",), (Attach("c:b", 0, 0, b, net="m"),), (), None, 1, "H")
    flow: Any = SimpleNamespace(fans=[fan] if fanned else [], columns=(), cross_links=())
    return account(problem, flow, {"a": 1, "c": 1, "z": 1, "b": 2, "c:b": 2, "d": 2}, planned, pages), (a, b)


def test_a_copy_joins_no_pins_so_a_group_whose_ends_it_touches_is_joined_by_a_pair() -> None:
    """KI-710 (R1819, CL1): a copy covers its own conductor to its hub, so a is not joined to b: a is touched by a tag, so the ledger
    hands the loop one join pair a-b."""
    got, (a, b) = _copy_account(fanned=False)
    assert [pair for _, pair in got.unjoined] == [(a, b)]


def test_a_pin_the_loop_joins_gets_no_leg_for_the_conductor_the_join_carries() -> None:
    """KI-710 (R1819): b is a fan pin with ink to d and the undrawn conductor to a; the loop's pair a-b carries it, so no leg stands at b."""
    got, (_, b) = _copy_account(fanned=True)
    assert got.unjoined
    assert not [r for r in got.refs if r.kind is RefKind.STUB and b in {e.pin for e in r.ends}]


def test_a_pieces_marked_pin_is_the_same_in_every_order_of_its_pins() -> None:
    """BANK-PIECES-JOINED (R1717): the pin a piece is marked at follows the far-end order the model gives, not the order of the group's pins."""
    from itertools import permutations

    from fransys_layout.core.cut_pieces import hole_pin

    a, b, c, out = (PinRef(n, "e") for n in ("a", "b", "c", "out"))
    far_ends = ((b, out), (a, out), (c, out))
    net_of = {a: "m", b: "m", c: "m"}
    assert {hole_pin(list(order), far_ends, net_of) for order in permutations((a, b, c))} == {b}


def test_a_lane_passes_its_net_through_a_cell_and_between_cells_so_the_ledger_sees_the_pins_joined() -> None:
    """layout-0508 A21: a terminal cell's two pins on one net and the lane wire to the cell below are drawn together: no join, no stub."""
    from fransys_layout.core.cut_pieces import trunked
    from fransys_layout.core.flow_values import Cell

    terminal, relay = PinRef("x1", "n"), PinRef("k1", "in")
    lane: Any = SimpleNamespace(cells=(Cell("x1", "R0", "n", "s"), Cell("k1", "R0", "in", "out")))
    flow: Any = SimpleNamespace(fans=(), cross_links=(), columns=(SimpleNamespace(id="c", lanes=(lane,)),))
    net_of = {terminal: "n", PinRef("x1", "s"): "n", relay: "n", PinRef("k1", "out"): "m"}
    pairs = trunked(flow, {"c": 1}, net_of)
    assert (terminal, PinRef("x1", "s")) in pairs
    assert (PinRef("x1", "s"), relay) in pairs
    assert not any(relay in pair and PinRef("k1", "out") in pair for pair in pairs)  # two nets through one cell join nothing
    assert trunked(flow, {}, net_of) == set()  # a column on no page of this cut draws no lane


def test_a_bundles_lanes_are_tied_per_net_so_one_lanes_tag_never_carries_the_other_lane() -> None:
    """R1902 (CL1): the pins of two lanes of one fan on one page share no wire; a plain fan's attachments still share its trunk."""
    from fransys_layout.core.cut_pieces import trunked

    def fan(lanes: int) -> Any:
        attach = [Attach("c", ln, 0, PinRef(f"s{ln}", "p"), net=f"n{ln}") for ln in range(2)]
        return Fan("f", ("n0", "n1"), tuple(attach), (), None, lanes, "S")

    pins = (PinRef("s0", "p"), PinRef("s1", "p"))
    where = {"c": 1}
    for lanes, tied in ((2, False), (1, True)):
        flow: Any = SimpleNamespace(fans=(fan(lanes),), cross_links=(), columns=())
        assert ((pins[0], pins[1]) in trunked(flow, where, {})) is tied


def test_an_arrow_joins_each_lane_it_stands_for_to_that_lanes_pin_at_the_other_end() -> None:
    """R1902 (CL1): with the per-net tie of a bundle, the arrow's `also` pins are the only link of a second lane across the cut."""
    from fransys_layout.core.cut_pieces import pairs

    a1, b1, a2, b2 = (PinRef(n, "p") for n in ("a1", "b1", "a2", "b2"))
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c", a1, also=(b1,)), RefEnd(2, "c", a2, also=(b2,))), cut=0)
    got = pairs([ref], {a1: "n0", a2: "n0", b1: "n1", b2: "n1"})
    assert (b1, b2) in got
    assert (a1, a2) in got
    assert (a1, b2) not in got


@st.composite
def _fan_cuts(draw: st.DrawFn) -> tuple[list[int], list[int], list[int], list[int]]:
    """A two-lane fan over a sequence cut into pages and rows: each position's page, row and lane, and the two hubs."""
    size = draw(st.integers(4, 9))
    steps = st.lists(st.integers(0, 1), min_size=size - 1, max_size=size - 1)
    page = list(accumulate(draw(steps), initial=0))
    row: list[int] = [0]
    for new_page, new_row in zip(draw(steps), draw(steps), strict=True):
        row.append(0 if new_page else row[-1] + new_row)
    lane_of = draw(st.lists(st.integers(0, 1), min_size=size, max_size=size))
    assume(lane_of.count(0) > 1 and lane_of.count(1) > 1)
    hubs = [draw(st.sampled_from([i for i in range(size) if lane_of[i] == k])) for k in (0, 1)]
    return page, row, lane_of, hubs


def _drawn(acc: Any, planned: list[Ref], lane_of: list[int], spot: list[tuple[int, int]]) -> tuple[UnionFind, set[PinRef]]:
    """The drawn pieces: ink, a lane's trunk ink per (page, row), arrow ends, equal-lane `also` and join pairs; the pins a reference carries."""
    uf, carried = UnionFind(), set[PinRef]()
    for i, j in permutations(range(len(spot)), 2):
        if spot[i] == spot[j] and lane_of[i] == lane_of[j]:
            uf.union(f"{PinRef(f's{i}', 'e')}", f"{PinRef(f's{j}', 'e')}")
    for a, b in [*acc.ink, *(pair for _, pair in acc.unjoined)]:
        uf.union(f"{a}", f"{b}")
    for ref in planned:
        for a, b in permutations(ref.ends, 2):
            uf.union(f"{a.pin}", f"{b.pin}")
            for p, q in ((p, q) for p in a.also for q in b.also if lane_of[int(p.sym[1:])] == lane_of[int(q.sym[1:])]):
                uf.union(f"{p}", f"{q}")
    for ref in (*acc.refs, *planned):
        carried |= {p for e in ref.ends for p in (e.pin, *e.also) if p}
    return uf, carried


@given(_fan_cuts())
@settings(deadline=None, max_examples=300)
def test_every_conductor_of_a_cut_fan_is_drawn_whole_or_carried_at_both_ends_by_a_reference(case: Any) -> None:
    """KI-767 guard (R1938): the oracle is the drawn pieces (ink, a lane's trunk ink per page and row, arrow ends)."""
    page, row, lane_of, hubs = case
    size = len(page)
    pin = [PinRef(f"s{i}", "e") for i in range(size)]
    lanes = tuple(tuple((i, pin[i]) for i in range(size) if lane_of[i] == k) for k in (0, 1))
    conductors = [(pin[i], pin[hubs[lane_of[i]]]) for i in range(size) if i != hubs[lane_of[i]]]
    facts = Facts(far_ends=(*conductors, *((b, a) for a, b in conductors)), groups=tuple(conductors))
    nets = [net(f"n{k}", *(f"s{i}.e" for i in range(size) if lane_of[i] == k)) for k in (0, 1)]
    attach = [Attach(None, 0, 0, pin[i], lane_of[i], net=f"n{lane_of[i]}") for i in range(size)]
    fan = Fan("f", ("n0", "n1"), tuple(attach[h] for h in hubs), tuple(a for i, a in enumerate(attach) if i not in hubs), None, 2, "S")
    planned = []
    for b in (b for b in range(size - 1) if (page[b], row[b]) != (page[b + 1], row[b + 1])):
        try:
            ends = lane_ends("f", lanes, ((b, f"s{b}"), (b + 1, f"s{b + 1}")), dict(enumerate(page)), dict(enumerate(row)))
        except ReferenceLaneError:
            reject()
        if ends:
            planned.append(Ref(f"n{lane_of[b]}", RefKind.ARROW, ends, b))
    plan = tuple(
        PagePlan(p, "U1", tuple(RowPlan(tuple(f"s{i}" for i in range(size) if (page[i], row[i]) == (p, r)), ()) for r in sorted(set(row))), ())
        for p in sorted(set(page))
    )
    problem = PlacementProblem(AREA, tuple(side(f"s{i}", 100, 100) for i in range(size)), tuple(nets), facts)
    acc = account(problem, replace(NO_FLOW, fans=(fan,)), {f"s{i}": page[i] for i in range(size)}, planned, plan)
    drawn, carried = _drawn(acc, planned, lane_of, list(zip(page, row, strict=True)))
    for a, b in conductors:
        assert drawn.same(f"{a}", f"{b}") or (a in carried and b in carried), (a, b)


def _stub_env(lane_ends: tuple[tuple[int, int] | None, ...]) -> tuple[MarkEnv, Ref, list[RefEnd]]:
    """A page with one trunk of a 2-lane bundle, no leg lines, and a LEG and a TRUNK_END stub end at each pole's pin."""
    pins = [PinRef(f"s{k}", "p") for k in (0, 1)]
    attach = tuple(Attach(None, 0, k, pins[k], k, net=f"n{k}") for k in (0, 1))
    fan = Fan("f", ("n0", "n1"), (), attach, None, 2, "S")
    trunk = Trunk("f", 1, 256, 498, 530, 2, 0, lane_ends)
    options = core_options(marker=MARKER, marker_vertical=frozenset({"R90", "R270", "MR90", "MR270"}), marker_above="R270", marker_below="R90")
    env = MarkEnv(options, Size(1312, 854), {}, {}, {(1, "f"): (trunk,)}, {"f": fan})
    ref = Ref("n0", RefKind.STUB, ())
    ends = [RefEnd(1, None, p, row=0, stand=st_) for st_ in (StandClass.LEG, StandClass.TRUNK_END) for p in pins]
    return env, ref, ends


def test_a_bundled_stub_with_no_leg_line_stands_on_its_own_poles_lane_end() -> None:
    """P2 (R1938): lane_ends ((498, 498), (530, 530)) and no leg line: pole 0's stub abuts x=498, pole 1's x=530."""
    env, ref, ends = _stub_env(((498, 498), (530, 530)))
    for end in ends:
        assert end.pin is not None
        pole = int(end.pin.sym[1:])
        ref = replace(ref, net=f"n{pole}")
        stand = pinned_stand(env, ref, end)
        assert marker_box_at(stand.x, stand.y, env.options, stand.orient).x == (498, 530)[pole], end


def test_a_bundled_stub_whose_pole_has_no_lane_end_raises_naming_the_stub_and_the_pole() -> None:
    env, ref, ends = _stub_env(((498, 498), None))
    with pytest.raises(CoreError, match=r"pole 1 of the bundle has no lane end for the stub at s1.p"):
        pinned_stand(env, replace(ref, net="n1"), ends[1])
