"""Stage 8b: one designation Label for each placed symbol, on its page grid (layout-0304).

The first pass takes, in natural order, the first candidate whose cells are free, else the one with
the fewest blocked cells, and marks it. Then the label with the most blocked cells moves to its best
candidate while that lowers its count (at most `ROUNDS` moves). A label left with blocked cells is
reported as TEXT_OVERLAP. The box is `Sym.label` at the corner: no text size is computed here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .keys import natural_key
from .outputs import Annotations, Label
from .text_label_cands import candidates
from .text_label_grid import page_grid, page_obstacles
from .values import XY, Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .occupancy import Occupancy
    from .outputs import PagePlacement, Placement, Routes
    from .values import Box, Options, PlacementProblem, Sym

ROUNDS = 50  # most descent moves on one page
FIX = "move the symbol, shorten the designation, or raise the row gap"


@dataclass(frozen=True, slots=True)
class PageLabels:
    """One page's labels and findings, the moves made and the cells held."""

    labels: tuple[Label, ...]
    findings: tuple[Finding, ...]
    rounds: int
    cells: int


class Cover:
    """The page grid plus the cells the labels hold; a cell is blocked by either."""

    def __init__(self, base: Occupancy) -> None:
        self.base = base
        self.held: Counter[XY] = Counter()
        self.choice: list[int] = []  # the candidate index each label stands at, in label order

    def cells(self, box: Box) -> list[XY]:
        step = self.base.step
        return [
            (i, j)
            for i in range(box.x // step, -(-(box.x + box.w) // step))
            for j in range(box.y // step, -(-(box.y + box.h) // step))
        ]

    def mark(self, box: Box) -> None:
        self.held.update(self.cells(box))

    def unmark(self, box: Box) -> None:
        self.held.subtract(self.cells(box))

    def blocked(self, box: Box) -> int:
        """The cells of the box that are hard, carry a wire or are held by another label."""
        b = self.base
        return sum(1 for c in self.cells(box) if c in b.hard or c in b.used or self.held[c] > 0)


def first_pass(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> None:
    """Natural order; each label takes its first free candidate, else its least blocked."""
    for options in cands:
        counts = [cover.blocked(box) for _, box in options]
        pick = counts.index(min(counts))
        cover.mark(options[pick][1])
        cover.choice.append(pick)


def own_counts(cover: Cover, boxes: Sequence[Box], held: Box) -> list[int]:
    """Blocked cells of each box with the label standing at `held` taken out."""
    cover.unmark(held)
    counts = [cover.blocked(box) for box in boxes]
    cover.mark(held)
    return counts


def improve(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> bool:
    """Move the most blocked label that has a better candidate; False when none has."""
    choice = cover.choice
    now = [
        own_counts(cover, [cands[i][choice[i]][1]], cands[i][choice[i]][1])[0]
        for i in range(len(cands))
    ]
    for i in sorted(range(len(cands)), key=lambda k: (-now[k], k)):
        if now[i] == 0:
            return False
        held = cands[i][choice[i]][1]
        counts = own_counts(cover, [box for _, box in cands[i]], held)
        best = counts.index(min(counts))
        if counts[best] < now[i]:
            cover.unmark(held)
            cover.mark(cands[i][best][1])
            choice[i] = best
            return True
    return False


def descend(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> int:
    """Moves made, at most ROUNDS."""
    for rounds in range(ROUNDS):
        if not improve(cover, cands):
            return rounds
    return ROUNDS


def label_page(
    page: PagePlacement, grid: Occupancy, syms: Mapping[str, Sym], options: Options
) -> PageLabels:
    """The labels of one page on its grid."""
    order = sorted(page.placed, key=lambda p: (natural_key(p.sym), p.sym))
    cands = [candidates(syms[p.sym], p, options) for p in order]
    cover = Cover(grid)
    first_pass(cover, cands)
    rounds = descend(cover, cands)
    labels, findings = [], []
    for p, options_, pick in zip(order, cands, cover.choice, strict=True):
        corner, box = options_[pick]
        labels.append(Label(p.sym, page.page, box, corner))
        left = own_counts(cover, [box], box)[0]
        if left:
            text = f"label of {p.sym} on page {page.page} has {left} blocked cells: {FIX}"
            findings.append(Finding("TEXT_OVERLAP", text, page.page, p.sym))
    return PageLabels(tuple(labels), tuple(findings), rounds, sum(cover.held.values()))


def label_run(
    placement: Placement,
    routes: Routes,
    notes: Annotations,
    problem: PlacementProblem,
    options: Options,
) -> list[PageLabels]:
    """label_page for every page in page order; `notes` holds the markers and tables."""
    syms = {s.id: s for s in problem.symbols}
    wires = {r.page: r.wires for r in routes.pages}
    out = []
    for page in sorted(placement.pages, key=lambda p: p.page):
        boxes = page_obstacles(page, notes.markers, notes.tables, options)
        grid = page_grid(page, wires.get(page.page, ()), boxes, problem.area, options.wiring_grid)
        out.append(label_page(page, grid, syms, options))
    return out


def label_pages(
    placement: Placement,
    routes: Routes,
    notes: Annotations,
    problem: PlacementProblem,
    options: Options,
) -> tuple[tuple[Label, ...], tuple[Finding, ...]]:
    """One designation Label per Placed per page; `notes` holds the markers and tables.

    A TEXT_OVERLAP finding names each label left with blocked cells.
    """
    runs = label_run(placement, routes, notes, problem, options)
    return (
        tuple(label for r in runs for label in r.labels),
        tuple(f for r in runs for f in r.findings),
    )
