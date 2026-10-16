"""The wiring terms of the score: crossings, bends, excess bends, length and detour.

One counter each. A crossing is counted once per point and per pair of nets: wires of one net
never cross each other, and routes of one net that share a trunk count once (baseline section 1).
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .outputs import SceneWire
    from .values import XY, Fan


MIN_POINTS = 2  # a polyline needs two vertices to be a wire


class Polyline(Protocol):
    """What the counters read of a wire; `Wire` and `SceneWire` both meet it."""

    @property
    def net(self) -> str: ...
    @property
    def page(self) -> int: ...
    @property
    def points(self) -> tuple[XY, ...]: ...


def _heading(a: XY, b: XY) -> tuple[int, int]:
    return ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))


def shape(points: tuple[XY, ...]) -> tuple[int, int, int, int]:
    """Bends, excess bends, length and Manhattan distance between the ends of one polyline."""
    dirs = [_heading(a, b) for a, b in pairwise(points) if a != b]
    bends = sum(1 for a, b in pairwise(dirs) if a != b)
    length = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in pairwise(points))
    (x0, y0), (x1, y1) = points[0], points[-1]
    if x0 == x1 or y0 == y1:
        need = 0
    else:  # an L needs 1 bend; ends leaving on the same axis need a Z, 2
        need = 2 if dirs and (dirs[0][0] == 0) == (dirs[-1][0] == 0) else 1
    return bends, max(0, bends - need), length, abs(x1 - x0) + abs(y1 - y0)


def bundles(fans: Iterable[Fan]) -> dict[str, str]:
    """Each member net of a bundle fan to the fan's id: the id its trunk wire carries."""
    return {net: fan.id for fan in fans if fan.lanes > 1 for net in fan.nets}


def crossing_points(
    wires: Sequence[Polyline], bundle_of: Mapping[str, str] | None = None
) -> set[tuple[int, int, str, str]]:
    """Distinct (x, y, horizontal net, vertical net) where a run passes straight across another.

    A member's drop never crosses its own bundle's trunk: `bundle_of` names that pair.
    """
    own = bundle_of or {}
    horizontal, vertical = [], []
    for wire in wires:
        for a, b in pairwise(wire.points):
            if a[1] == b[1] and a[0] != b[0]:
                horizontal.append((wire.net, a[1], min(a[0], b[0]), max(a[0], b[0])))
            elif a[0] == b[0] and a[1] != b[1]:
                vertical.append((wire.net, a[0], min(a[1], b[1]), max(a[1], b[1])))
    return {
        (x, y, hn, vn)
        for hn, y, left, right in horizontal
        for vn, x, top, bottom in vertical
        if hn != vn
        and own.get(hn) != vn
        and own.get(vn) != hn
        and left < x < right
        and top < y < bottom
    }


def crossings_on_page(wires: Sequence[Polyline], bundle_of: Mapping[str, str] | None = None) -> int:
    """The number of distinct crossings of one page's wires."""
    return len(crossing_points(wires, bundle_of))


def wiring(
    wires: tuple[SceneWire, ...], bundle_of: Mapping[str, str] | None = None
) -> dict[str, int]:
    """The five wiring terms over all wires of a scene."""
    total = {"crossings": 0, "bends": 0, "excess_bends": 0, "length_g": 0, "detour_g": 0}
    by_page: dict[int, list[SceneWire]] = defaultdict(list)
    for wire in wires:
        if len(wire.points) < MIN_POINTS:
            continue
        bends, excess, length, direct = shape(wire.points)
        total["bends"] += bends
        total["excess_bends"] += excess
        total["length_g"] += length
        total["detour_g"] += length - direct
        by_page[wire.page].append(wire)
    total["crossings"] = sum(crossings_on_page(tuple(page), bundle_of) for page in by_page.values())
    return total
