"""Hand-built problems and flows for the stage 2 tests: groups, cards, fans and hints.

A designation label is `Size(16, 8)` everywhere here. A column symbol is 16 wide; a reach
(left, right) makes the whole symbol that wide and hard, so no tag stagger lets like columns
stand closer (layout-0271): the draft's "narrow equals width". Every box has real pins.
"""

from __future__ import annotations

from dataclasses import replace
lazy from collections.abc import Sequence

from options_fixtures import core_options
from turn_fixtures import views_of

from fransys_layout.core import Box, Facts, Hints, PinRef, PlacementProblem, Size, Sym
from fransys_layout.core.values import (
    Attach,
    Block,
    BlockList,
    Cell,
    Column,
    CycleSplit,
    End,
    Fan,
    FlowGraph,
    Lane,
)

from .pack_fixtures import card as card_sym

AREA = Size(1312, 854)  # a page width of 1280 inside the 16 G margins
LABEL = Size(16, 8)


def sym(sid: str, group: str | None, unit: str = "", reach: tuple[int, int] | None = None) -> Sym:
    """A column symbol: 16 wide on its wire, or with reach (left, right) that wide all hard."""
    body = Box(-reach[0], 0, sum(reach), 32) if reach else Box(-8, 0, 16, 32)
    return Sym(
        sid,
        group,
        unit,
        LABEL,
        (),
        (),
        views=views_of(body, body, body, (), ("R0", "R180")),
    )


def box_sym(sid: str, group: str | None, pins: int, unit: str = "", north: int = 0) -> Sym:
    """A box with pins p1.. in marking order (the first `north` face north, the rest south)."""
    return replace(card_sym(sid, pins, north=north), group=group, unit=unit, label=LABEL)


def column(cid: str, *cells: str, pin: tuple[str, str] | None = None) -> Column:
    """One lane, head to foot; pin is a box pin at the head."""
    lane = Lane(tuple(Cell(s, "R0", None, None) for s in cells), 0)
    head = End("boxpin", pin=PinRef(*pin)) if pin else End("open")
    return Column(cid, (lane,), (head,), (End("open"),), 32 * len(cells), 16)


def fan(fid: str, *cols: str) -> Fan:
    """A fan whose legs are the given columns."""
    legs = tuple(Attach(c, 0, 0, PinRef("x", "p")) for c in cols)
    return Fan(fid, (f"net-{fid}",), (), legs, None, 1, "S")


def problem_of(
    syms: Sequence[Sym], hints: Hints | None = None, area: Size = AREA
) -> PlacementProblem:
    return PlacementProblem(area, tuple(syms), (), hints=hints or Hints(), facts=Facts())


def build(
    syms: Sequence[Sym],
    cols: Sequence[Column],
    fans: Sequence[Fan] = (),
    hints: Hints | None = None,
    area: Size = AREA,
) -> tuple[BlockList, ...]:
    """Stage 2 on a hand-built flow."""
    from fransys_layout.core.blocks import assign_blocks

    flow = FlowGraph(tuple(cols), tuple(fans), (), (), CycleSplit(0, 0, 0), ())
    return assign_blocks(
        flow,
        problem_of(syms, hints, area),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def flat(lists: Sequence[BlockList]) -> list[Block]:
    return [b for bl in lists for b in bl.blocks]


def by_anchor(lists: Sequence[BlockList]) -> dict[str, Block]:
    """The blocks keyed by what they stand on: the anchor box, else the first column."""
    return {b.anchor or b.columns[0]: b for b in flat(lists)}


def ids(lists: Sequence[BlockList]) -> list[str]:
    """What each block stands on, in order: the anchor box, else its first column."""
    return [b.anchor or b.columns[0] for b in flat(lists)]


def loose(*groups: str, reach: tuple[int, int] | None = None) -> tuple[list[Sym], list[Column]]:
    """Column ci holds symbol si of the i-th group: one free column block per group."""
    syms = [sym(f"s{i}", g, reach=reach) for i, g in enumerate(groups, 1)]
    return syms, [column(f"c{i}", f"s{i}") for i in range(1, len(groups) + 1)]


def shaped_box(
    reaches: Sequence[tuple[int, int]], *, reverse: bool = False, north: int = 0
) -> tuple[list[Sym], list[Column]]:
    """Box A1 (group PLC), column ci with symbol ki of reach (left, right) on pin pi.

    reverse puts column ci on pin p(n+1-i).
    """
    n = len(reaches)
    syms = [box_sym("A1", "PLC", n, north=north)]
    syms += [sym(f"k{i}", "CH", reach=r) for i, r in enumerate(reaches, 1)]
    cols = [
        column(f"c{i}", f"k{i}", pin=("A1", f"p{n + 1 - i if reverse else i}"))
        for i in range(1, n + 1)
    ]
    return syms, cols


def box_case(
    n: int, width: int, *, reverse: bool = False, north: int = 0
) -> tuple[list[Sym], list[Column]]:
    """Box A1 with n columns, each symbol's footprint width wide and centred on its wire."""
    return shaped_box([(width // 2, width // 2)] * n, reverse=reverse, north=north)
