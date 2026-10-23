"""A card's edges (E4) and spill, by the row's own width (P1.4 C, layout-0279)."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core.blocks_card import CardEdges, card_edges, overfull, pin_order
from fransys_layout.core.pack_row import RowSpec, row_width, solve_row
from fransys_layout.core.rowspec import one_row
from fransys_layout.core.values import Column, CycleSplit, FlowGraph, Size
lazy from fransys_layout.core.sym_values import Sym

from .blocks_fixtures import AREA, box_case, problem_of, shaped_box
from .pack_fixtures import card_block

PAGE = (
    AREA.w
    - 2
    * core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    ).margin.w
)


def edges_of(syms: list[Sym], cols: list[Column], area: Size = AREA) -> tuple[CardEdges, FlowGraph]:
    flow = FlowGraph(tuple(cols), (), (), (), CycleSplit(0, 0, 0), ())
    got = card_edges(
        "A1",
        [c.id for c in cols],
        flow,
        problem_of(syms, area=area),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    return got, flow


def spec_of(
    syms: list[Sym], flow: FlowGraph, edges: CardEdges, area: Size = AREA, extra: str = ""
) -> RowSpec:
    """The one row of the card that keeps the non-spilled columns (plus one spilled, `extra`)."""
    keep = [c.id for c in flow.columns if c.id not in edges.spilled or c.id == extra]
    box = syms[0].box
    assert box is not None
    kept = tuple(pin_order(keep, {c.id: c for c in flow.columns}, box))
    block = card_block("A1", kept, edges.pin_edges)
    return one_row(
        kept,
        (block,),
        flow,
        problem_of(syms, area=area),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def width_of(syms: list[Sym], flow: FlowGraph, edges: CardEdges) -> int:
    return row_width(spec_of(syms, flow, edges))


def test_two_edges_by_halves_at_sixteen_94_g_columns() -> None:
    """Sixteen 94 G columns do not fit one edge (natural: over the page); a half of 8 does."""
    syms, cols = box_case(16, 94, north=8)
    got, flow = edges_of(syms, cols)
    assert dict(got.pin_edges) == {f"p{i}": "N" if i <= 8 else "S" for i in range(1, 17)}
    assert got.spilled == ()
    assert width_of(syms, flow, got) == 822  # the draft's 816, here by row_width
    natural = CardEdges(tuple((f"p{i}", "S") for i in range(1, 17)), ())
    assert width_of(syms, flow, natural) > PAGE


def test_one_edge_at_sixteen_66_g_columns() -> None:
    """Sixteen 66 G columns fit the natural edge; the card keeps it and every pin on it."""
    syms, cols = box_case(16, 66)
    got, flow = edges_of(syms, cols)
    assert {e for _, e in got.pin_edges} == {"S"}
    assert got.spilled == ()
    assert width_of(syms, flow, got) == 1266 <= PAGE


def test_card_overfull_spills_the_columns_beyond_an_edge() -> None:
    """Forty 64 G columns: an edge keeps 17, the last three columns of each half spill."""
    syms, cols = box_case(40, 64, north=20)
    got, flow = edges_of(syms, cols)
    assert set(got.spilled) == {"c18", "c19", "c20", "c38", "c39", "c40"}
    assert dict(got.pin_edges)["p20"] == "N"  # every pin keeps its edge
    assert dict(got.pin_edges)["p21"] == "S"
    assert len(got.pin_edges) == 40
    assert width_of(syms, flow, got) == 32 + 16 * 72 + 3 * 16 + 16  # the draft's 1248, unchanged
    found = overfull("A1", got.spilled, 40)
    assert (found.code, found.subject) == ("CARD_OVERFULL", "A1")


def test_card_overfull_spills_in_pin_order_not_column_order() -> None:
    """c(41-i) stands on pin pi: c40 on p1 is wide and costs N one more column than S loses."""
    syms, cols = shaped_box([(32, 32)] * 39 + [(50, 50)], reverse=True, north=20)
    got, flow = edges_of(syms, cols)
    assert got.spilled == ("c24", "c23", "c22", "c21", "c3", "c2", "c1")  # pin order p17.., p38..
    assert "c40" not in got.spilled
    assert width_of(syms, flow, got) <= PAGE


def test_edge_capacity_is_the_row_width_stage_5_gives_the_edge() -> None:
    """At the kept width the page holds the card; one page G less and one column per edge goes."""
    syms, cols = box_case(40, 64, north=20)
    need = 1248
    for page, kept in ((need, 34), (need - 1, 32)):
        area = Size(
            page
            + 2
            * core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                driver_first=True,
                arrow_sides=("E", "W"),
            ).margin.w,
            AREA.h,
        )
        got, flow = edges_of(syms, cols, area)
        assert len(cols) - len(got.spilled) == kept
        spec = spec_of(syms, flow, got, area)
        assert solve_row(spec, area.w)[1] == 0  # stage 5 sees no overflow
        over = spec_of(syms, flow, got, area, extra=got.spilled[0])
        assert solve_row(over, area.w)[1] > 0  # one more column overflows


@pytest.mark.parametrize(("n", "width"), [(16, 94), (16, 66), (40, 64), (40, 70), (70, 16)])
def test_every_kept_card_fits_a_row_of_its_own(n: int, width: int) -> None:
    syms, cols = box_case(n, width, north=(n + 1) // 2)
    got, flow = edges_of(syms, cols)
    assert width_of(syms, flow, got) <= PAGE


def test_a_twenty_channel_card_at_16_g_pitch_fits() -> None:
    """The README gap "a 20-channel card at 16 G pitch finds no feasible cut" is closed for stage 2:
    the card keeps the natural edge and every column, and fits one row of its own."""
    syms, cols = box_case(20, 16)
    got, flow = edges_of(syms, cols)
    assert got.spilled == ()
    assert {e for _, e in got.pin_edges} == {"S"}
    assert width_of(syms, flow, got) <= PAGE
