"""P5-G plants: a card with no column stands in a row of a page, placed by its wiring (layout-0288).

A box wired by fan trunks alone is a card block with `columns=()` (layout-0283). Stage 3 seats it
immediately after the fan block that most trunks end at it from (ties: natural key of the block
id), or, with no such block, in a row of its own at the end of its unit. Stage 4 cuts it like any
block.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Hints, order_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.cut_guard import unplaced

from .blocks_fixtures import box_sym
from .conftest import MARKER
from .flow_builders import elem, free, net, problem
from .pipeline_fixtures import blocks_of, cut_of, flow_of, placed_of
from .test_box_blocks import chain_shape

if TYPE_CHECKING:
    from fransys_layout.core.values import CutResult, PlacementProblem


def _sym(sid: str, group: str):
    return free(sid, group=group)


def two_fans(ends_a: int, ends_b: int, *, a_first: bool = True) -> PlacementProblem:
    """Box K with trunk ends on fan A (A1, A2) and fan B (B1, B2): ends_a and ends_b pins each.

    a_first False reverses the group order, so the block list stands [B, A] while natural key
    still ranks A first.
    """
    pins = [f"K.p{i}" for i in range(1, ends_a + ends_b + 1)]
    syms = [
        box_sym("K", "PLC", ends_a + ends_b),
        *(_sym(t, "GA") for t in ("A1", "A2")),
        *(_sym(t, "GB") for t in ("B1", "B2")),
    ]
    nets = [
        net("ta", *pins[:ends_a], "A1.e", "A2.e"),
        net("tb", *pins[ends_a:], "B1.e", "B2.e"),
    ]
    hints = Hints(group_order=("GA", "GB") if a_first else ("GB", "GA"))
    return problem(syms, nets, hints)


def _seated(prob: PlacementProblem) -> list[str]:
    """Stage 3's block ids for the problem's one unit, in order."""
    opts = core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    lists = order_blocks(blocks_of(prob, opts), flow_of(prob, opts), opts)
    return [b.id for bl in lists for b in bl.blocks]


def _rows(result: CutResult, block: str) -> list[tuple[int, tuple[str, ...]]]:
    """(page, the row's blocks) of every row the block stands in."""
    return [(p.page, r.blocks) for p in result.spec.pages for r in p.rows if block in r.blocks]


def test_a_card_stands_after_the_fan_block_with_most_trunks_ending_at_it() -> None:
    prob = two_fans(1, 2, a_first=True)
    result = cut_of(prob)
    assert result.spec.findings == ()  # BLOCK_NOT_PLACED would name card:K
    assert _seated(prob) == ["fan:c:A1", "fan:c:B1", "card:K"]
    assert len(_rows(result, "card:K")) == 1


def test_the_majority_beats_block_order_and_natural_key() -> None:
    """The majority block wins whether it is later (A) or earlier (B) in block order."""
    ids = _seated(two_fans(2, 1, a_first=False))
    assert ids == ["fan:c:B1", "fan:c:A1", "card:K"]
    ids = _seated(two_fans(1, 2, a_first=False))
    assert ids == ["fan:c:B1", "card:K", "fan:c:A1"]


def test_equal_trunk_counts_go_to_the_smaller_natural_key_not_the_first_in_order() -> None:
    """The list stands [B, A] but A ranks first by natural key, so the card follows A."""
    prob = two_fans(1, 1, a_first=False)
    assert _seated(prob) == ["fan:c:B1", "fan:c:A1", "card:K"]
    assert len(_rows(cut_of(prob), "card:K")) == 1


def foot_shape() -> PlacementProblem:
    """Box B met only by the foot of a column whose head is on box A: no trunk, no box hop."""
    syms = [box_sym("A", "PLC", 1), box_sym("B", "PLC", 1), elem("E")]
    return problem(syms, [net("n1", "A.p1", "E.n"), net("n2", "E.s", "B.p1")])


def test_a_card_with_no_trunk_and_no_hop_gets_a_row_of_its_own_at_the_end() -> None:
    result = cut_of(foot_shape())
    assert _rows(result, "card:B") == [(1, ("card:B",))]
    assert [r.blocks for r in result.spec.pages[0].rows][-1] == ("card:B",)
    assert [f.code for f in result.spec.findings] == []


def test_a_refused_chain_box_is_seated_and_drawn_not_dropped() -> None:
    """R348: a refused chain (pins do not face) degrades to a drawing: every box has a row."""
    result = cut_of(chain_shape())
    placed = {b for p in result.spec.pages for r in p.rows for b in r.blocks}
    assert placed == {f"card:A{i}" for i in (1, 2, 3)}
    assert "CHAIN_NOT_DRAWN" not in {f.code for f in result.spec.findings}


OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def _page_w(prob: PlacementProblem) -> int:
    return prob.area.w - 2 * OPTIONS.margin.w


def test_the_guard_names_a_block_in_no_row() -> None:
    """A lone card left unseated (stage 3 skipped) is BLOCK_NOT_PLACED, naming block and stage."""
    prob = two_fans(1, 2)
    flow = flow_of(prob)
    lists = blocks_of(prob)  # stage 3 not run: the card keeps seat "none"
    found = unplaced(
        lists,
        cut_pages(
            lists,
            flow,
            prob,
            OPTIONS,
        ).spec.pages,
        _page_w(prob),
        OPTIONS,
    )
    assert [(f.code, f.subject) for f in found] == [("BLOCK_NOT_PLACED", "card:K")]
    assert "stage 4" in found[0].text


def test_the_guard_flags_a_whole_block_in_two_rows() -> None:
    prob = two_fans(1, 2)
    result = cut_of(prob)
    page = result.spec.pages[0]
    twice = replace(page, rows=(*page.rows, page.rows[-1]))
    found = unplaced(result.blocks, (twice,), _page_w(prob), OPTIONS)
    assert [(f.code, f.subject) for f in found] == [("BLOCK_NOT_PLACED", "card:K")]


def test_a_split_fan_is_no_finding() -> None:
    """A single-lane fan cut across rows stands in several rows and is fine."""
    prob = problem(
        [free(f"T{i}") for i in range(120)], [net("t", *(f"T{i}.e" for i in range(120)))]
    )
    result = cut_of(prob)
    assert len(result.spec.pages[0].rows) > 1
    assert result.spec.findings == ()


def test_every_seated_card_is_placed_on_its_page() -> None:
    """Stage 5 places the box of each plant once, on the page its row is on."""
    for prob, box in (
        (two_fans(1, 2), "K"),
        (two_fans(1, 1, a_first=False), "K"),
        (foot_shape(), "B"),
    ):
        pages = [pg for pg in placed_of(prob).pages if any(s.sym == box for s in pg.placed)]
        assert [pg.page for pg in pages] == [1], box
