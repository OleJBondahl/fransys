"""The page's one obstacle index: hard boxes and wire marks on the wiring grid.

A cell is hard (a box) or carries wires as (net, axis). The exact runs of the same wires are kept
beside the cells, so `collinear` and `columns_used` read the marks, not the wires again.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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
    """Cells that are hard or used by wires, per net and axis, and the exact runs of those wires."""

    cols: int
    rows: int
    step: int
    hard: set[XY] = field(default_factory=set)
    used: dict[XY, list[tuple[str, str]]] = field(default_factory=dict)
    runs: dict[tuple[bool, int], list[Run]] = field(default_factory=lambda: defaultdict(list))
    ends: dict[XY, list[str]] = field(default_factory=dict)

    def mark_box(self, box: Box) -> None:
        lo, hi = box.x // self.step, -(-(box.x + box.w) // self.step)
        top, bottom = box.y // self.step, -(-(box.y + box.h) // self.step)
        self.hard.update((i, j) for i in range(lo, hi) for j in range(top, bottom))

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

    def blocked(self, cell: XY, axis: str, net: str) -> bool:
        """A hard box, another net's wire on the same axis, or another net's end or corner."""
        return (
            cell in self.hard
            or self.touched(cell, net)
            or any(o != net and a == axis for o, a in self.used.get(cell, ()))
        )

    def touched(self, cell: XY, net: str, skip: frozenset[str] = frozenset()) -> bool:
        """Another net (not in `skip`) has an end or a corner in the cell (R391)."""
        return any(n != net and n not in skip for n in self.ends.get(cell, ()))

    def foreign(self, cell: XY, net: str, skip: frozenset[str] = frozenset()) -> bool:
        """Another net's wire is in the cell: a path may cross it straight, never end or turn."""
        return any(o != net and o not in skip for o, _ in self.used.get(cell, ()))

    def crossing(self, cell: XY, axis: str, net: str) -> int:
        """The wires of other nets on the other axis in the cell."""
        return sum(1 for o, a in self.used.get(cell, ()) if o != net and a != axis)

    def touches(self, net: str, points: Sequence[XY], skip: frozenset[str] = frozenset()) -> bool:
        """The polyline meets a net not in `skip`: an end or corner on it, or a run along it."""
        step = self.step
        if any(self.foreign((x // step, y // step), net, skip) for x, y in points):
            return True
        for a, b in pairwise(points):
            axis = "h" if a[1] == b[1] else "v"
            for cell in cells_between(a, b, step):
                if self.touched(cell, net, skip) or any(
                    o != net and o not in skip and k == axis for o, k in self.used.get(cell, ())
                ):
                    return True
        return False

    def free(self, box: Box) -> bool:
        """No cell of the box is hard or carries a wire."""
        lo, hi = box.x // self.step, -(-(box.x + box.w) // self.step)
        top, bottom = box.y // self.step, -(-(box.y + box.h) // self.step)
        return all(
            (i, j) not in self.hard and (i, j) not in self.used
            for i in range(lo, hi)
            for j in range(top, bottom)
        )

    def collinear(self) -> int:
        """Pairs of runs of different nets on one line that share more than a point."""
        return sum(
            1
            for row in self.runs.values()
            for i, a in enumerate(row)
            for b in row[i + 1 :]
            if a[2] != b[2] and max(a[0], b[0]) < min(a[1], b[1])
        )

    def columns_used(self, gap: Gap) -> int:
        """Distinct x of the vertical runs strictly inside the gap, within its band when set."""
        banded = gap.y0 is not None and gap.y1 is not None
        top, bottom = (gap.y0, gap.y1) if banded else (-INF, INF)
        return len(
            {
                x
                for (horizontal, x), row in self.runs.items()
                if not horizontal
                and gap.x0 < x < gap.x1
                and any(lo <= bottom and hi >= top for lo, hi, _ in row)
            }
        )
