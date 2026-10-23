"""The cover the annex stage places on: a page grid plus the cells the annexes hold (layout-0304).

The first pass takes, in the order given, the first candidate whose cells are free, else the one
with the fewest blocked cells, and marks it. Then the annex with the most blocked cells moves to
its best candidate while that lowers its count (at most `ROUNDS` moves).
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .values import XY, Box

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .occupancy import Occupancy
    from .values import Size

ROUNDS = 50  # most descent moves on one page


def on_outline(box: Box, body: Box) -> bool:
    """True when `box` meets the outline of `body`: touches or crosses it, not strictly inside."""
    meets = (
        box.x <= body.x + body.w
        and body.x <= box.x + box.w
        and box.y <= body.y + body.h
        and body.y <= box.y + box.h
    )
    inside = (
        body.x < box.x
        and box.x + box.w < body.x + body.w
        and body.y < box.y
        and box.y + box.h < body.y + body.h
    )
    return meets and not inside


class Cover:
    """The page grid plus the cells the labels hold; a cell is blocked by either."""

    def __init__(
        self,
        base: Occupancy,
        gap: int = 0,
        bounds: Size | None = None,
        owns: Sequence[Box] = (),
        outlines: Sequence[Box] = (),
    ) -> None:
        self.base = base
        self.owns = tuple(owns)  # the body of each annex, in annex order
        self.outlines = tuple(set(outlines or owns))  # every body outline of the page
        self.gap = gap  # a label keeps this far from every wire (Options.label_gap)
        self.bounds = bounds  # the content box: a label stands inside it
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

    def outside(self, box: Box) -> int:
        """The cells of the box that lie past the content box."""
        if self.bounds is None:
            return 0
        step, area = self.base.step, self.bounds
        return sum(
            1
            for i, j in self.cells(box)
            if min(i, j) < 0 or (i + 1) * step > area.w or (j + 1) * step > area.h
        )

    def wires_in(self, box: Box) -> int:
        """The exact wire runs that pass through `box`, their ends and sides not touching it."""
        count = 0
        for (horizontal, at), runs in self.base.runs.items():
            lo, hi = (box.y, box.y + box.h) if horizontal else (box.x, box.x + box.w)
            if not lo < at < hi:
                continue
            a, z = (box.x, box.x + box.w) if horizontal else (box.y, box.y + box.h)
            count += sum(1 for r0, r1, _ in runs if r0 < z and r1 > a)
        return count

    def near_wires(self, box: Box) -> int:
        """The wire runs within `gap` of the box that do not cross it."""
        gap = self.gap
        if gap == 0:
            return 0
        wide = Box(box.x - gap, box.y - gap, box.w + 2 * gap, box.h + 2 * gap)
        return self.wires_in(wide) - self.wires_in(box)

    def on_outlines(self, box: Box, own: Box | None = None) -> int:
        """The body outlines, other than `own` (its symbol's body), that the box touches or crosses.

        A designation stands clear of every drawn line (CORE-TEXTS ruling 100.2).
        """
        return sum(1 for o in self.outlines if o != own and on_outline(box, o))

    def own_of(self, index: int) -> Box | None:
        """The body of label `index`; None for a cover built without bodies."""
        return self.owns[index] if index < len(self.owns) else None

    def blocked(self, box: Box, own: Box | None = None) -> int:
        """Blocked cells: hard, wired, held by a label or outside the content box, plus near wires.

        A wire closer than `gap` counts one, so a label keeps its distance from it; an outline
        touched counts one.
        """
        b = self.base
        cells = {c for c in self.cells(box) if c in b.hard or c in b.used or self.held[c] > 0}
        return len(cells) + self.outside(box) + self.near_wires(box) + self.on_outlines(box, own)


def first_pass(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> None:
    """In the order given; each annex takes its first free candidate, else its least blocked."""
    for i, options in enumerate(cands):
        own = cover.own_of(i)
        counts = [cover.blocked(box, own) for _, box in options]
        pick = counts.index(min(counts))
        cover.mark(options[pick][1])
        cover.choice.append(pick)


def own_counts(cover: Cover, boxes: Sequence[Box], held: Box, index: int) -> list[int]:
    """Blocked cells of each box of label `index` with that label standing at `held` taken out."""
    cover.unmark(held)
    own = cover.own_of(index)
    counts = [cover.blocked(box, own) for box in boxes]
    cover.mark(held)
    return counts


def improve(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> bool:
    """Move the most blocked label that has a better candidate; False when none has."""
    choice = cover.choice
    now = [
        own_counts(cover, [cands[i][choice[i]][1]], cands[i][choice[i]][1], i)[0]
        for i in range(len(cands))
    ]
    for i in sorted(range(len(cands)), key=lambda k: (-now[k], k)):
        if now[i] == 0:
            return False
        held = cands[i][choice[i]][1]
        counts = own_counts(cover, [box for _, box in cands[i]], held, i)
        best = counts.index(min(counts))
        if counts[best] < now[i]:
            cover.unmark(held)
            cover.mark(cands[i][best][1])
            choice[i] = best
            return True
    return False


def promote(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> bool:
    """Move a label with no blocked cell to an earlier candidate that is also free (I8.3)."""
    choice = cover.choice
    for i, options in enumerate(cands):
        held = options[choice[i]][1]
        counts = own_counts(cover, [box for _, box in options], held, i)
        if counts[choice[i]] == 0 and 0 in counts[: choice[i]]:
            cover.unmark(held)
            cover.mark(options[counts.index(0)][1])
            choice[i] = counts.index(0)
            return True
    return False


def descend(cover: Cover, cands: Sequence[Sequence[tuple[str, Box]]]) -> int:
    """Moves made, at most ROUNDS."""
    for rounds in range(ROUNDS):
        if not (improve(cover, cands) or promote(cover, cands)):
            return rounds
    return ROUNDS
