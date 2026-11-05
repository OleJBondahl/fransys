"""The page's one obstacle index: hard boxes and wire marks on the wiring grid.

A cell is hard (a box, with the symbols that own it) or carries wires as (net, axis). The exact
runs of the same wires are kept beside the cells, so `collinear` and `columns_used` read the marks,
not the wires again.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

from .clearance import closed_cells

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .outputs import Gap
    from .values import XY, Box

Run = tuple[int, int, str]
INF = 1 << 60


def cells_between(a: XY, b: XY, step: int) -> list[XY]:
    """The grid cells a straight run from a to b covers, both ends included."""
    (x0, y0), (x1, y1) = a, b
    if y0 == y1:
        return [(i, y0 // step) for i in range(min(x0, x1) // step, max(x0, x1) // step + 1)]
    return [(x0 // step, j) for j in range(min(y0, y1) // step, max(y0, y1) // step + 1)]


@dataclass(slots=True)
class Occupancy:
    """Cells that are hard or used by wires, per net and axis, the exact runs of those wires.

    Also the history cost a negotiated search adds: per cell and axis, it outlives `remove_net`.
    """

    cols: int
    rows: int
    step: int
    hard: dict[XY, frozenset[str]] = field(default_factory=dict)
    used: dict[XY, list[tuple[str, str]]] = field(default_factory=dict)
    runs: dict[tuple[bool, int], list[Run]] = field(default_factory=lambda: defaultdict(list))
    ends: dict[XY, list[str]] = field(default_factory=dict)
    admitted: dict[XY, set[tuple[str, str]]] = field(default_factory=dict)
    history: dict[tuple[XY, str], int] = field(default_factory=dict)
    share_cost: int = 0  # above 0 a path may share a present cell and pays for it

    def _harden(self, cells: Iterable[XY], owners: frozenset[str]) -> None:
        for cell in cells:
            self.hard[cell] = self.hard.get(cell, frozenset()) | owners

    def _cells(self, box: Box) -> list[XY]:
        s = self.step
        return [(i, j) for i in range(box.x // s, -(-(box.x + box.w) // s)) for j in range(box.y // s, -(-(box.y + box.h) // s))]

    def mark_box(self, box: Box, owners: frozenset[str] = frozenset()) -> None:
        self._harden(self._cells(box), owners)

    def mark_closed(self, box: Box, owners: frozenset[str] = frozenset()) -> None:
        """Hard cells of the box with its far edges included, as `clearance` and el count (R535).

        A wire of a symbol in `owners` may enter them (R-A); `admit` opens one cell.
        """
        xs, ys = closed_cells(box, self.step)
        self._harden(((i, j) for i in xs for j in ys), owners)

    def admit(self, cell: XY, owner: str, net: str) -> None:
        """A wire of `net` that belongs to `owner` may enter the hard `cell` of its pin (R-A)."""
        self._harden((cell,), frozenset())
        self.admitted.setdefault(cell, set()).add((owner, net))

    def mark_wire(self, net: str, points: Sequence[XY]) -> None:
        for p in points:
            self.ends.setdefault((p[0] // self.step, p[1] // self.step), []).append(net)
        for a, b in pairwise(points):
            axis = "h" if a[1] == b[1] else "v"
            for cell in cells_between(a, b, self.step):
                self.used.setdefault(cell, []).append((net, axis))
            if a[1] == b[1] and a[0] != b[0]:
                self.runs[(True, a[1])].append((min(a[0], b[0]), max(a[0], b[0]), net))
            elif a[0] == b[0] and a[1] != b[1]:
                self.runs[(False, a[0])].append((min(a[1], b[1]), max(a[1], b[1]), net))

    def unmark_wire(self, net: str, points: Sequence[XY]) -> None:
        """Reverse `mark_wire` for one point list; the net's other wires and its pin ends stay.

        A mark `remove_net` took off with its link (a net holding a rise and a link) is already gone.
        """
        for p in points:
            cell = (p[0] // self.step, p[1] // self.step)
            if net in self.ends.get(cell, ()):
                self.ends[cell].remove(net)
                if not self.ends[cell]:
                    del self.ends[cell]
        for a, b in pairwise(points):
            self._unmark_run(net, a, b)

    def _unmark_run(self, net: str, a: XY, b: XY) -> None:
        axis = "h" if a[1] == b[1] else "v"
        for cell in cells_between(a, b, self.step):
            if (net, axis) in self.used.get(cell, ()):
                self.used[cell].remove((net, axis))
                if not self.used[cell]:
                    del self.used[cell]
        if a[1] == b[1] and a[0] != b[0]:
            self._drop_run((True, a[1]), (min(a[0], b[0]), max(a[0], b[0]), net))
        elif a[0] == b[0] and a[1] != b[1]:
            self._drop_run((False, a[0]), (min(a[1], b[1]), max(a[1], b[1]), net))

    def _drop_run(self, key: tuple[bool, int], run: tuple[int, int, str]) -> None:
        if run in self.runs[key]:
            self.runs[key].remove(run)

    def mark_end(self, net: str, point: XY) -> None:
        """A port end of `net` at `point`: no other net's wire may end, turn or run on it (R472)."""
        self.ends.setdefault((point[0] // self.step, point[1] // self.step), []).append(net)

    def remove_net(self, net: str) -> None:
        for cell in list(self.used):
            self.used[cell] = [u for u in self.used[cell] if u[0] != net]
            if not self.used[cell]:
                del self.used[cell]
        for cell in list(self.ends):
            self.ends[cell] = [n for n in self.ends[cell] if n != net]
            if not self.ends[cell]:
                del self.ends[cell]
        for key in list(self.runs):
            self.runs[key] = [r for r in self.runs[key] if r[2] != net]

    def add_history(self, cell: XY, axis: str, amount: int) -> None:
        """Add `amount` to the cost of entering the cell on the axis; `remove_net` keeps it."""
        self.history[(cell, axis)] = self.history.get((cell, axis), 0) + amount

    def present(self, cell: XY, axis: str, net: str) -> int:
        """The wires of other nets on the same axis in the cell."""
        return sum(1 for o, a in self.used.get(cell, ()) if o != net and a == axis)

    def blocked(self, cell: XY, axis: str, net: str, own: frozenset[str] = frozenset()) -> bool:
        """A hard box none of `own` owns, another net's wire on the same axis, or its end.

        In a soft round (`share_cost` above 0) only the boxes and the port ends stay blocked.
        """
        if cell in self.hard and not self.hard[cell] & own and not self._admits(cell, net, own):
            return True
        if self.share_cost:
            return self.port_end(cell, net)
        return self.touched(cell, net) or self.present(cell, axis, net) > 0

    def port_end(self, cell: XY, net: str) -> bool:
        """An end of another net with no wire of its own in the cell: a port end (R472)."""
        wired = {o for o, _ in self.used.get(cell, ())}
        return any(n != net and n not in wired for n in self.ends.get(cell, ()))

    def contested(self, cell: XY, axis: str, net: str) -> int:
        """What a soft round prices in the cell: other nets' wires on the axis and their ends."""
        return self.present(cell, axis, net) + sum(1 for n in self.ends.get(cell, ()) if n != net)

    def _admits(self, cell: XY, net: str, own: frozenset[str]) -> bool:
        return any((o, net) in self.admitted.get(cell, ()) for o in own)

    def touched(self, cell: XY, net: str, skip: frozenset[str] = frozenset()) -> bool:
        """Another net (not in `skip`) has an end or a corner in the cell (R391)."""
        return any(n != net and n not in skip for n in self.ends.get(cell, ()))

    def foreign(self, cell: XY, net: str, skip: frozenset[str] = frozenset()) -> bool:
        """Another net's wire is in the cell: a path may cross it straight, never end or turn."""
        return any(o != net and o not in skip for o, _ in self.used.get(cell, ()))

    def crossing(self, cell: XY, axis: str, net: str) -> int:
        """The wires of other nets on the other axis in the cell."""
        return sum(1 for o, a in self.used.get(cell, ()) if o != net and a != axis)

    def conflicts(self, net: str, points: Sequence[XY], skip: frozenset[str] = frozenset()) -> list[tuple[XY, str]]:
        """Where the polyline meets a net not in `skip` (R391), as (cell, axis).

        An end or corner on its wire lists both axes; a run along it or through its end, the run's.
        """
        step = self.step
        out: list[tuple[XY, str]] = []
        for x, y in points:
            cell = (x // step, y // step)
            if self.foreign(cell, net, skip):
                out += [(cell, "h"), (cell, "v")]
        for a, b in pairwise(points):
            axis = "h" if a[1] == b[1] else "v"
            out += [
                (cell, axis)
                for cell in cells_between(a, b, step)
                if self.touched(cell, net, skip) or any(o != net and o not in skip and k == axis for o, k in self.used.get(cell, ()))
            ]
        return out

    def free(self, box: Box) -> bool:
        """No cell of the box is hard or carries a wire."""
        return all(c not in self.hard and c not in self.used for c in self._cells(box))

    def collinear(self) -> int:
        """Pairs of runs of different nets on one line that share more than a point."""
        return sum(
            1 for row in self.runs.values() for i, a in enumerate(row) for b in row[i + 1 :] if a[2] != b[2] and max(a[0], b[0]) < min(a[1], b[1])
        )

    def columns_used(self, gap: Gap) -> int:
        """Tracks the gap must hold: the nets with a vertical run strictly inside it (R391: one net per column), never fewer than their distinct x."""
        banded = gap.y0 is not None and gap.y1 is not None
        top, bottom = (gap.y0, gap.y1) if banded else (-INF, INF)
        hits = [
            (x, net)
            for (horizontal, x), row in self.runs.items()
            if not horizontal and gap.x0 < x < gap.x1
            for lo, hi, net in row
            if lo <= bottom and hi >= top
        ]
        return max(len({x for x, _ in hits}), len({net for _, net in hits}))
