"""Stage 4's references and findings on hand-built problems: copies, P3, stubs, tall, spilled.

A page holds 1280 x 822 G inside the 16 G margins. Sizes are in G; the designation label is
Size(16, 8) everywhere (cut_fixtures).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import (
    Facts,
    Options,
    PinRef,
    PlacementProblem,
    Unit,
    build_flow,
    order_blocks,
)
from fransys_layout.core.blocks import assign_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.cut_refs import _column_pin
from fransys_layout.core.values import CutResult, Ref, RefEnd, RefKind

from .conftest import MARKER_BOX
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
    assert result.spec.reference_plan == (
        Ref("feed", RefKind.COPY, (RefEnd(2, "c:k1", PinRef("k2", "n")),)),
    )
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
            (RefEnd(2, "c:k1", PinRef("k2", "n")), RefEnd(3, "c:k1", PinRef("k3", "n"))),
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
        ),
    )
    assert [(f.code, f.page, f.subject) for f in result.spec.findings] == [
        ("HEAD_OFF_LEGS", 1, "f:feed")
    ]


def test_a_through_jumper_hub_is_not_copied() -> None:
    """A jumper j0 has two nodes, so it is no free-sided symbol: the arrow stays."""
    syms = [elem("j0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    result = cut_of(syms, [net("feed", "j0.n", "j0.s", "k1.n", "k2.n", "k3.n")])
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


def hub_case(
    widths: tuple[int, int, int], heights: tuple[int, int, int], *, free_hub: bool
) -> CutResult:
    """Trunk u (jumper j) joins k1, k2; trunk v (hub t) joins k2, k3; t is free-sided or not."""
    hub = free("t") if free_hub else elem("t")
    pins = ("t.e",) if free_hub else ("t.n", "t.s")
    cols = [elem(f"k{i}", w, h) for i, (w, h) in enumerate(zip(widths, heights, strict=True), 1)]
    return cut_of(
        [*cols, elem("j"), hub],
        [net("u", "k1.s", "k2.s", "j.n", "j.s"), net("v", *pins, "k2.n", "k3.n")],
    )


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
    assert free_sided.spec.reference_plan == (
        Ref("v", RefKind.COPY, (RefEnd(2, "c:k2", PinRef("k3", "n")),)),
    )


def test_a_row_wrap_through_the_trunk_of_a_free_sided_hub_is_not_priced_as_a_copy() -> None:
    """Short columns wrap inside one page, where v keeps its arrow pair, whatever the hub."""
    for free_hub in (False, True):
        (page,) = hub_case((600, 600, 600), (100, 210, 40), free_hub=free_hub).spec.pages
        assert [row.columns for row in page.rows] == [("c:k1",), ("c:k2", "c:k3")]


# stubs


def test_a_net_that_crosses_units_ends_in_a_stub_at_each_of_its_boundary_pins() -> None:
    """Net m joins x, y, z, one page each; boundary pins x.e (U1), z.e (U2) give two stub ends."""
    syms = [side(name, 700, 500) for name in "xyz"]
    facts = Facts(
        units=(Unit("U1", None, (PinRef("x", "e"),)), Unit("U2", None, (PinRef("z", "e"),)))
    )
    crossing = cut_of(syms, [net("m", "x.e", "y.e", "z.e", crosses_unit=True)], facts)
    assert page_of(crossing) == {"c:x": 1, "c:y": 2, "c:z": 3}
    assert refs_of(crossing, "stub") == [
        Ref(
            "m",
            RefKind.STUB,
            (RefEnd(1, None, PinRef("x", "e")), RefEnd(3, None, PinRef("z", "e"))),
        )
    ]
    plain = cut_of(syms, [net("m", "x.e", "y.e", "z.e")], facts)
    assert refs_of(plain, "stub") == []  # the flag is what asks for stubs
    assert plain.spec.pages == crossing.spec.pages  # stubs cost nothing and move nothing
    assert [r for r in crossing.spec.reference_plan if r.kind != "stub"] == list(
        plain.spec.reference_plan
    )


def test_a_crossing_net_with_no_boundary_pin_plans_no_stub() -> None:
    syms = [side(name, 700, 500) for name in "xyz"]
    result = cut_of(
        syms,
        [net("m", "x.e", "y.e", "z.e", crosses_unit=True)],
        Facts(units=(Unit("U1", None, ()),)),
    )
    assert refs_of(result, "stub") == []


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
    """Thirty cells 96 G wide and 32 G high stack to 1192 G: twenty fill the page, ten remain."""
    ids = [f"k{i:02d}" for i in range(30)]
    result = cut_of([elem(i, 96) for i in ids], chain(ids))
    top, bottom = result.flow.columns
    assert [len(c.lanes[0].cells) for c in (top, bottom)] == [20, 10]
    assert (top.height, bottom.height) == (20 * 32 + 19 * 8, 10 * 32 + 9 * 8)
    assert (top.width, bottom.width) == (96, 96)
    assert result.spec.reference_plan == (
        Ref(
            "x19",
            RefKind.TAG,
            (RefEnd(1, "c:k00#a", PinRef("k19", "s")), RefEnd(1, "c:k00#b", PinRef("k20", "n"))),
        ),
    )


def test_the_split_keeps_every_field_of_the_fan_and_block_it_rewrites() -> None:
    """The tail fan hangs from the foot of the tall column: it moves to the lower half."""
    ids = [f"k{i:02d}" for i in range(12)]
    syms = [*(elem(i, 40, 96) for i in ids), elem("w"), elem("y")]
    prob = PlacementProblem(AREA, tuple(syms), (*chain(ids), net("tail", "k11.s", "w.n", "y.n")))
    options = Options(marker=MARKER_BOX)
    flow = build_flow(prob, options)
    (tail,) = flow.fans
    flow = replace(flow, fans=(replace(tail, crossed=(("w1", (1, 0)),)),))
    lists = order_blocks(assign_blocks(flow, prob, options), flow, options)
    lists = tuple(
        replace(bl, blocks=tuple(replace(b, fixed_order=True) for b in bl.blocks)) for bl in lists
    )
    result = cut_pages(lists, flow, prob, options)
    (moved,) = result.flow.fans
    assert (moved.drivers[0].column, moved.drivers[0].cell) == ("c:k00#b", 11 - 7)
    assert moved.crossed == (("w1", (1, 0)),)
    before = next(b for bl in lists for b in bl.blocks if "c:k00" in b.columns)
    after = next(b for bl in result.blocks for b in bl.blocks if "c:k00#a" in b.columns)
    assert after.fixed_order
    assert replace(after, columns=before.columns) == before  # only the columns differ


# columns spilled off an overfull card


def overfull(height: int) -> CutResult:
    """Box A1 with forty columns of 64 G, one on each pin.

    More columns than the 1280 G page holds at their pitch: the blocks stage keeps what fits
    on the card and lets the rest leave it and stand free.
    """
    syms = [box_sym(40), *(elem(f"k{i}", 64, height, "CH") for i in range(1, 41))]
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
    (page,) = result.spec.pages
    assert any(set(card) <= set(row.columns) for row in page.rows)  # the card is never cut
    expected = [
        Ref(
            f"n{c[3:]}",
            RefKind.TAG,
            (RefEnd(1, c, PinRef(f"k{c[3:]}", "n")), RefEnd(1, None, PinRef("A1", f"p{c[3:]}"))),
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
    (column,) = [
        c for c in result.flow.columns if any(x.sym == "k1" for ln in c.lanes for x in ln.cells)
    ]
    with pytest.raises(
        ValueError,
        match=(
            r"cut: net m: spilled column c:k1 holds none of its pins; "
            r"a spilled tag is planned only for a column that holds a pin of the net"
        ),
    ):
        _column_pin(column, net("m", "k3.n", "k4.n"))
