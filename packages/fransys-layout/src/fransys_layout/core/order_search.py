"""Stage 3, the exact search: branch and bound over column orders, natural order first.

Split from `order` to keep both modules small. It reads column ids only through the position they
stand in, never their text.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

Span = tuple[
    frozenset[str], bool
]  # columns a fan or cross-link touches here; True for a cross-link
Before = dict[str, frozenset[str]]  # a column -> the columns that must stand before it


class Search:
    """Branch and bound over column orders in natural order: the first order of least cost wins.

    A leaf must cost less than `bound`; a prefix is charged what no later column can undo, and one
    repeating an earlier prefix at no lower cost is dropped. After `budget` nodes the best stands.
    """

    def __init__(
        self, cols: Sequence[str], spans: Sequence[Span], before: Before, bound: int, budget: int
    ) -> None:
        index = {c: i for i, c in enumerate(cols)}
        self.cols = list(cols)
        self.n = len(cols)
        self.m = len(spans)
        self.size = [len(members) for members, _ in spans]
        self.link = [int(link) for _, link in spans]
        self.of = [tuple(s for s, (members, _) in enumerate(spans) if c in members) for c in cols]
        self.need = [sum(1 << index[p] for p in before[c]) for c in cols]
        self._chain_twins(before)
        self._reset(bound, budget)

    def _reset(self, bound: int, budget: int) -> None:
        self.lo = [-1] * self.m  # position where a span began, -1 before
        self.cnt = [0] * self.m  # columns of a span placed so far
        self.prefix: list[int] = []
        self.seen: dict[tuple[int, tuple[int, ...]], int] = {}
        self.best = bound
        self.budget = budget
        self.found: list[int] | None = None
        self.nodes = 0

    def _chain_twins(self, before: Before) -> None:
        """Twin columns (same spans and predecessors, no successor) keep natural order."""
        waited = set().union(*before.values())
        groups: dict[tuple[tuple[int, ...], int], list[int]] = {}
        for i, c in enumerate(self.cols):
            if c not in waited:
                groups.setdefault((self.of[i], self.need[i]), []).append(i)
        for twins in groups.values():
            for a, b in pairwise(twins):
                self.need[b] |= 1 << a

    def run(self) -> list[str] | None:
        self.place(0, 0)
        return None if self.found is None else [self.cols[i] for i in self.found]

    def place(self, placed: int, cost: int) -> None:
        if self.nodes >= self.budget:
            return
        self.nodes += 1
        k = len(self.prefix)
        if k == self.n:
            self.best, self.found = cost, list(self.prefix)
            return
        for c in range(self.n):
            if placed >> c & 1 or self.need[c] & ~placed:
                continue
            total = cost + self.step(c, k)
            if total < self.best and self.fresh(placed | 1 << c, total):
                self.prefix.append(c)
                self.place(placed | 1 << c, total)
                self.prefix.pop()
            self.undo(c)

    def step(self, c: int, k: int) -> int:
        """Put column c at position k; the cost it adds."""
        mine = self.of[c]
        added = self._open_cost(mine)
        for s in mine:
            if self.cnt[s] == 0:
                self.lo[s] = k
            self.cnt[s] += 1
        closed = (s for s in mine if self.cnt[s] == self.size[s])
        return added + sum(self._interleaves(s) for s in closed)

    def _open_cost(self, mine: tuple[int, ...]) -> int:
        """Foreign columns, and a cross-link's between-end columns, that stand inside open spans."""
        added = 0
        for s in range(self.m):
            if self.lo[s] >= 0 and self.cnt[s] < self.size[s]:  # open before this column
                if s not in mine:
                    added += 1 + self.link[s]
                elif self.cnt[s] + 1 < self.size[s]:
                    added += self.link[s]
        return added

    def _interleaves(self, s: int) -> int:
        """Spans begun after span s that are still open when s closes interleave with it."""
        return sum(
            1 for t in range(self.m) if self.lo[t] > self.lo[s] and self.cnt[t] < self.size[t]
        )

    def undo(self, c: int) -> None:
        for s in self.of[c]:
            self.cnt[s] -= 1
            if self.cnt[s] == 0:
                self.lo[s] = -1

    def fresh(self, placed: int, cost: int) -> bool:
        """False when an earlier prefix with the same columns and open-span order cost no more."""
        zipped = zip(self.lo, self.cnt, self.size, strict=True)
        opened = [lo for lo, cnt, size in zipped if lo >= 0 and cnt < size]
        rank = {v: i for i, v in enumerate(sorted(set(opened)))}
        key = (placed, tuple(rank[v] for v in opened))
        if cost >= self.seen.get(key, cost + 1):
            return False
        self.seen[key] = cost
        return True


def exact_search(
    natural: Sequence[str],
    spans: Sequence[Span],
    before: Before,
    seed: tuple[list[str], int],
    budget: int,
) -> list[str]:
    """Branch and bound over at most `budget` nodes, bounded by the cost of `seed`.

    `seed` is an order already found and its cost: it stands when no leaf is reached, and a search
    that finishes gives the same answer without it.
    """
    order, cost = seed
    found = Search(natural, spans, before, cost + 1, budget).run()
    return order if found is None else found
