"""A placed sheet wider than its limit, wrapped into rows: a general technique over plain values.

The columns are cut into bands that fit `width`, each band is moved under the one before it, and a
line between two bands takes a fold route (`wrap_route`) round the rows' ends. A sheet that
cannot be wrapped (a line over more than one band, an end off a box's side, a route that touches
a box or crosses a line) comes back as it was.
"""

from collections import Counter
from dataclasses import dataclass, replace
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.overview.lanes.labels import label_at
from fransys_layout.engines.overview.sizes import tab_reach
from fransys_layout.engines.overview.wrap_route import clear, fold_points
from fransys_layout.geometry import WIRING_GRID as G
from fransys_layout.geometry import Facing, Point
lazy from fransys_layout.engines.overview.sheet_values import (
    Ident,
    PlacedBox,
    PlacedLine,
    PlacedSheet,
    PlacedTab,
)

MAX_TRACKS = 8  # the most lines that fold between two rows before the sheet stays as it is
INNER = -1  # a line inside one band

type Bounds = tuple[int, int, int, int]  # left, top, right, bottom


def _tab_x(box: PlacedBox, tab: PlacedTab) -> int:
    reach = tab_reach(tab.text_width)
    return box.x + box.width + reach if tab.side is Facing.E else box.x - reach


def _span(box: PlacedBox) -> tuple[int, int]:
    xs = (box.x, box.x + box.width, *(_tab_x(box, t) for t in box.tabs))
    return min(xs), max(xs)


def extent(sheet: PlacedSheet) -> Bounds:
    """The `(left, top, right, bottom)` of boxes, tabs and line points of `sheet`."""
    xs = [v for b in sheet.boxes for v in _span(b)] + [p.x for ln in sheet.lines for p in ln.points]
    ys = [v for b in sheet.boxes for v in (b.y, b.y + b.height)]
    ys += [p.y for ln in sheet.lines for p in ln.points]
    return min(xs), min(ys), max(xs), max(ys)


def _cut(boxes: Sequence[PlacedBox], limit: int) -> dict[int, int] | None:
    """The band of each box column (by its x), a band ending before it passes `limit`."""
    cols: dict[int, list[int]] = {}
    for box in boxes:
        left, right = _span(box)
        old = cols.setdefault(box.x, [left, right])
        cols[box.x] = [min(old[0], left), max(old[1], right)]
    band_of: dict[int, int] = {}
    band, start = 0, None
    for x, (left, right) in sorted(cols.items()):
        if start is None:
            start = left
        elif right - start > limit:
            band, start = band + 1, left
        if right - start > limit:
            return None
        band_of[x] = band
    return band_of


def _classify(
    sheet: PlacedSheet, band: Mapping[Ident, int], by_id: Mapping[Ident, PlacedBox]
) -> list[int] | None:
    """Per line `INNER` or the band it leaves; None for a line over two bands or off a side."""
    kinds = []
    for ln in sheet.lines:
        first, second = (ln.a, ln.b) if band[ln.a] <= band[ln.b] else (ln.b, ln.a)
        if band[first] == band[second]:
            kinds.append(INNER)
        elif band[second] - band[first] == 1 and _leaves_east(ln, by_id[first], by_id[second]):
            kinds.append(band[first])
        else:
            return None
    return kinds


def _leaves_east(ln: PlacedLine, first: PlacedBox, second: PlacedBox) -> bool:
    pts = ln.points if ln.a == first.box else ln.points[::-1]
    return pts[0].x == first.x + first.width and pts[-1].x == second.x


def _bounds(
    sheet: PlacedSheet, band: Mapping[Ident, int], kinds: Sequence[int], count: int
) -> list[Bounds]:
    """Each band's `(left, top, right, bottom)`: its boxes, tabs and the lines inside it."""
    xs: list[list[int]] = [[] for _ in range(count)]
    ys: list[list[int]] = [[] for _ in range(count)]
    for b in sheet.boxes:
        xs[band[b.box]] += _span(b)
        ys[band[b.box]] += (b.y, b.y + b.height)
    for ln, kind in zip(sheet.lines, kinds, strict=True):
        if kind == INNER:
            xs[band[ln.a]] += [p.x for p in ln.points]
            ys[band[ln.a]] += [p.y for p in ln.points]
    return [(min(x), min(y), max(x), max(y)) for x, y in zip(xs, ys, strict=True)]


def _offsets(
    bounds: Sequence[Bounds], folds: Mapping[int, int], left: int
) -> list[tuple[int, int]]:
    """Each band's move: to start at `left`, under the one before with room for its folds."""
    moves = []
    bottom = 0
    for k, (band_left, top, _, band_bottom) in enumerate(bounds):
        dy = 0 if k == 0 else bottom + (folds[k - 1] + 2) * G - top
        moves.append((left - band_left, dy))
        bottom = band_bottom + dy
    return moves


def _shift(point: Point, move: tuple[int, int]) -> Point:
    return Point(x=point.x + move[0], y=point.y + move[1])


def _moved_box(box: PlacedBox, move: tuple[int, int]) -> PlacedBox:
    tabs = tuple(replace(t, y=t.y + move[1]) for t in box.tabs)
    return replace(box, x=box.x + move[0], y=box.y + move[1], tabs=tabs)


def _moved_line(ln: PlacedLine, move: tuple[int, int]) -> PlacedLine:
    points = tuple(_shift(p, move) for p in ln.points)
    return replace(ln, points=points, text_x=ln.text_x + move[0], text_y=ln.text_y + move[1])


@dataclass(frozen=True)
class _Plan:
    """Where each box goes: its band, each band's bounds and move, the folds per boundary."""

    band: Mapping[Ident, int]
    bounds: list[Bounds]
    moves: list[tuple[int, int]]
    folds: Counter[int]
    left: int


def _oriented(ln: PlacedLine, band: Mapping[Ident, int]) -> tuple[Point, ...]:
    """The points of `ln` from its end in the earlier band to its end in the later one."""
    return ln.points if band[ln.a] < band[ln.b] else ln.points[::-1]


def _tracks(sheet: PlacedSheet, kinds: Sequence[int], band: Mapping[Ident, int]) -> dict[int, int]:
    """Each folded line's track at its boundary: the lowest start takes the innermost."""
    at: dict[int, int] = {}
    for k in {kd for kd in kinds if kd != INNER}:
        idx = [i for i, kd in enumerate(kinds) if kd == k]
        idx.sort(key=lambda i: -_oriented(sheet.lines[i], band)[0].y)
        at.update({i: t for t, i in enumerate(idx)})
    return at


def _folded(ln: PlacedLine, k: int, track: int, plan: _Plan, text_height: int) -> PlacedLine:
    """`ln` as its fold route round the end of band `k` and the start of band `k + 1`."""
    pts = _oriented(ln, plan.band)
    count = plan.folds[k]
    _, _, right, bottom = plan.bounds[k]
    points = fold_points(
        _shift(pts[0], plan.moves[k]),
        _shift(pts[-1], plan.moves[k + 1]),
        right=right + plan.moves[k][0] + (track + 1) * G,
        left=plan.left - (count - track) * G,
        track=bottom + plan.moves[k][1] + (track + 1) * G,
    )
    x, y = label_at(points, text_height)
    return replace(ln, points=points, text_x=x, text_y=y)


def _plan(sheet: PlacedSheet, width: int, tracks: int) -> tuple[_Plan, list[int]] | None:
    """The bands of `sheet` for folds of at most `tracks` lines a boundary, or None if none fit."""
    left = extent(sheet)[0] + (tracks + 1) * G
    band_of = _cut(sheet.boxes, width - 2 * (tracks + 1) * G)
    if band_of is None:
        return None
    band = {b.box: band_of[b.x] for b in sheet.boxes}
    kinds = _classify(sheet, band, {b.box: b for b in sheet.boxes})
    if kinds is None or sheet.markers or sheet.texts:
        return None
    folds = Counter(kd for kd in kinds if kd != INNER)
    if max(folds.values(), default=0) > tracks:
        return None
    bounds = _bounds(sheet, band, kinds, max(band.values()) + 1)
    return _Plan(band, bounds, _offsets(bounds, folds, left), folds, left), kinds


def _wrap_with(
    sheet: PlacedSheet, plan: _Plan, kinds: Sequence[int], text_height: int
) -> PlacedSheet:
    """`sheet` moved by `plan`, its bridging lines folded."""
    at = _tracks(sheet, kinds, plan.band)
    boxes = tuple(_moved_box(b, plan.moves[plan.band[b.box]]) for b in sheet.boxes)
    lines = tuple(
        _moved_line(ln, plan.moves[plan.band[ln.a]])
        if kd == INNER
        else _folded(ln, kd, at[i], plan, text_height)
        for i, (ln, kd) in enumerate(zip(sheet.lines, kinds, strict=True))
    )
    return replace(sheet, boxes=boxes, lines=lines)


def wrapped(sheet: PlacedSheet, width: int, text_height: int) -> PlacedSheet:
    """`sheet` as it is when no wider than `width`, else wrapped into rows of that width."""
    left, _, right, _ = extent(sheet)
    if right - left <= width:
        return sheet
    for tracks in range(1, MAX_TRACKS + 1):
        found = _plan(sheet, width, tracks)
        if found is None:
            continue
        made = _wrap_with(sheet, *found, text_height)
        new_left, _, new_right, _ = extent(made)
        folded = [ln.points for ln, kd in zip(made.lines, found[1], strict=True) if kd != INNER]
        if new_right - new_left <= width and clear(
            folded, made.boxes, [ln.points for ln in made.lines]
        ):
            return made
    return sheet
