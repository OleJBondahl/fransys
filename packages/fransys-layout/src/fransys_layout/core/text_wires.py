"""Stage 8c: one wire label per labelled net per page, on the page grid (layout-0310).

`label_along` is general: a polyline, a size, the sides to try per run direction, an obstacle grid
and the trunk width give a free box or None. `label_nets` runs it for every net with a label size.
A trunk `lanes` wide, given to `label_along`, makes a label stand one cell past `band.band_extent`
on the +x or +y side and one cell off on the other; a trunk's lane lines are wires of their own.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from .band import band_extent, on_band_side
from .errors import CoreError
from .keys import natural_key
from .outputs import WireLabel
from .text_label_grid import page_grid, page_obstacles
from .values import XY, Box, Finding

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .occupancy import Occupancy
    from .outputs import Annotations, PagePlacement, Placement, Routes, Wire
    from .values import Net, Options, PlacementProblem, Size

FIX = "move the net's label, lengthen a run, or leave a side free"
Run = tuple[XY, XY]
Sides = Sequence[Sequence[str]]  # each: a run direction, then its sides in try order
HORIZONTAL = "horiz"
VERTICAL = "vert"


@dataclass(frozen=True, slots=True)
class Want:
    """What a label asks of a run: its size, the trunk width in lanes and the grid step."""

    size: Size
    lanes: int
    step: int


def length(run: Run) -> int:
    (x0, y0), (x1, y1) = run
    return abs(x1 - x0) + abs(y1 - y0)


def runs(points: Sequence[XY]) -> list[Run]:
    """The straight segments of a polyline, longest first, ties by first index."""
    return sorted((s for s in pairwise(points) if s[0] != s[1]), key=lambda s: -length(s))


def sides_of(sides: Sides, direction: str) -> Sequence[str]:
    """The sides to try for a run direction; a missing direction is an error naming the fix."""
    found = next((s[1:] for s in sides if s[0] == direction), None)
    if found is None:
        msg = f"Options.wire_label_sides has no entry for {direction!r} runs: add one"
        raise CoreError(msg)
    return found


def offsets(half: int, step: int) -> Iterator[int]:
    """0, +step, -step, +2 step, ... while the shift stays within half."""
    yield 0
    for k in range(1, half // step + 1):
        yield k * step
        yield -k * step


def stand(side: str, cell: int, lanes: int, extent: int, step: int) -> int:
    """The box edge across the run: one cell past the band on the E or S side, one off on W or N."""
    if on_band_side(side):
        return cell * step + band_extent(lanes, step)[1] + step
    return cell * step - extent


def candidate(run: Run, side: str, want: Want, shift: int) -> Box:
    """The box beside the run on `side`, centred on its middle plus `shift`."""
    (x0, y0), (x1, y1) = run
    size, step = want.size, want.step
    if y0 == y1:
        start = (min(x0, x1) + max(x0, x1)) // 2 + shift - size.w // 2
        y = stand(side, y0 // step, want.lanes, size.h, step)
        return Box(start // step * step, y, size.w, size.h)
    start = (min(y0, y1) + max(y0, y1)) // 2 + shift - size.h // 2
    x = stand(side, x0 // step, want.lanes, size.w, step)
    return Box(x, start // step * step, size.w, size.h)


def within(run: Run, box: Box) -> bool:
    """The box lies along the run, not past either end."""
    (x0, y0), (x1, y1) = run
    if y0 == y1:
        return min(x0, x1) <= box.x and box.x + box.w <= max(x0, x1)
    return min(y0, y1) <= box.y and box.y + box.h <= max(y0, y1)


def label_run(run: Run, want: Want, sides: Sides, occ: Occupancy) -> Box | None:
    """The first free box along one run: sides in order, then shifts nearest the middle first."""
    flat = run[0][1] == run[1][1]
    for side in sides_of(sides, HORIZONTAL if flat else VERTICAL):
        for shift in offsets(length(run) // 2, want.step):
            box = candidate(run, side, want, shift)
            if within(run, box) and occ.free(box):
                return box
    return None


def label_along(
    points: Sequence[XY], size: Size, sides: Sides, occupancy: Occupancy, lanes: int = 1
) -> Box | None:
    """The first free box for a label of `size` beside a run of the polyline, longest run first.

    `sides` lists, per run direction ("horiz", "vert"), the direction then its sides in try order.
    """
    want = Want(size, lanes, occupancy.step)
    for run in runs(points):
        box = label_run(run, want, sides, occupancy)
        if box is not None:
            return box
    return None


def longest(wire: Wire) -> int:
    """The length of the wire's longest run, for the order a net's wires are tried in."""
    return max((length(r) for r in runs(wire.points)), default=0)


def net_label(size: Size, wires: Sequence[Wire], options: Options, grid: Occupancy) -> Box | None:
    """The first free box on the net's wires, the wire with the longest run first."""
    ordered = sorted(enumerate(wires), key=lambda iw: (-longest(iw[1]), iw[0]))
    for _, wire in ordered:
        box = label_along(wire.points, size, options.wire_label_sides, grid)
        if box is not None:
            return box
    return None


def labelled_grid(
    page: PagePlacement,
    wires: Sequence[Wire],
    notes: Annotations,
    problem: PlacementProblem,
    options: Options,
) -> Occupancy:
    """The page grid of layout-0304 with P5B's labels of the page marked."""
    boxes = page_obstacles(page, notes.markers, notes.tables, options, notes.anchored)
    grid = page_grid(page, wires, boxes, problem.area, options)
    for annex in notes.annexes:
        if annex.page == page.page:
            grid.mark_box(annex.box)
    return grid


def label_page(
    page: int, wires: Sequence[Wire], nets: Sequence[Net], grid: Occupancy, options: Options
) -> tuple[list[WireLabel], list[Finding]]:
    """The wire labels of one page, nets in order, each winner marked for the nets after it."""
    out: list[WireLabel] = []
    findings: list[Finding] = []
    for net in nets:
        mine = [w for w in wires if w.net == net.id]
        if not mine or net.label is None:
            continue
        box = net_label(net.label, mine, options, grid)
        if box is None:
            text = f"label of net {net.id} on page {page} has no free place: {FIX}"
            findings.append(Finding("TEXT_OVERLAP", text, page, net.id))
            continue
        grid.mark_box(box)
        out.append(WireLabel(net.id, page, box))
    return out, findings


def label_nets(
    placement: Placement,
    routes: Routes,
    notes: Annotations,
    problem: PlacementProblem,
    options: Options,
) -> tuple[tuple[WireLabel, ...], tuple[Finding, ...]]:
    """One WireLabel per labelled net per page; `notes` holds the markers, tables and labels.

    A TEXT_OVERLAP finding names each net left with no free place. A net with no wire on a page
    gets neither a label nor a finding there.
    """
    wires = {r.page: r.wires for r in routes.pages}
    nets = sorted((n for n in problem.nets if n.label is not None), key=lambda n: natural_key(n.id))
    out: list[WireLabel] = []
    findings: list[Finding] = []
    for page in sorted(placement.pages, key=lambda p: p.page):
        on_page = wires.get(page.page, ())
        grid = labelled_grid(page, on_page, notes, problem, options)
        labels, found = label_page(page.page, on_page, nets, grid, options)
        out += labels
        findings += found
    return tuple(out), tuple(findings)
