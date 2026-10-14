"""The diagram placer for a diagram of separate pieces: each placed alone, then packed in rows.

A piece shares no line with another, so each is placed by `place_diagram` and moved whole. The
`shape` is the caller's: pieces are packed to its aspect, never left in one row.
"""

from dataclasses import replace
lazy from collections.abc import Sequence

from fransys_layout.engines.diagram.columns import pieces
from fransys_layout.engines.diagram.pack import pack_rows
from fransys_layout.engines.diagram.place import place_diagram
from fransys_layout.engines.diagram.values import PlacedDiagram, PlacedSheet
from fransys_layout.engines.diagram.wrap import extent, wrapped
from fransys_layout.geometry import PAGE_PAD, WIRING_GRID, Point
lazy from fransys_layout.engines.diagram.values import DiagramFacts

PIECE_GAP = 2 * PAGE_PAD  # clear space between two packed pieces


def _split(facts: DiagramFacts) -> list[tuple[DiagramFacts, list[int]]]:
    """Each piece as facts of its own with the indexes of its lines in `facts.lines`."""
    ids = tuple(b.box for b in facts.boxes)
    joins = zip(facts.column, facts.column[1:], strict=False)  # one column is one piece
    parts = pieces(ids, [*((ln.a, ln.b) for ln in facts.lines), *joins])
    result = []
    for part in parts:
        members = set(part)
        idx = [i for i, ln in enumerate(facts.lines) if ln.a in members]
        boxes = tuple(b for b in facts.boxes if b.box in members)
        lines = tuple(facts.lines[i] for i in idx)
        column = tuple(c for c in facts.column if c in members)
        left = tuple(c for c in facts.left if c in members)
        result.append((replace(facts, boxes=boxes, lines=lines, column=column, left=left), idx))
    return result


def _moved(sheet: PlacedSheet, dx: int, dy: int) -> PlacedSheet:
    """`sheet` with everything moved by `(dx, dy)`."""
    boxes = tuple(
        replace(
            b,
            x=b.x + dx,
            y=b.y + dy,
            tabs=tuple(replace(t, y=t.y + dy) for t in b.tabs),
        )
        for b in sheet.boxes
    )
    lines = tuple(
        replace(
            ln,
            points=tuple(Point(x=p.x + dx, y=p.y + dy) for p in ln.points),
            text_x=ln.text_x + dx,
            text_y=ln.text_y + dy,
        )
        for ln in sheet.lines
    )
    return PlacedSheet(number=1, boxes=boxes, lines=lines, markers=())


def _down(value: int) -> int:
    return value - value % WIRING_GRID


def _slots(sheets: Sequence[PlacedSheet], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """The `(dx, dy)` that moves each sheet to its packed place, from its grid-snapped corner."""
    corners = [extent(s) for s in sheets]
    origin = [(_down(left), _down(top)) for left, top, _, _ in corners]
    sizes = [(r - ox, b - oy) for (_, _, r, b), (ox, oy) in zip(corners, origin, strict=True)]
    at = pack_rows(sizes, shape=shape, gap=PIECE_GAP)
    return [
        (PAGE_PAD + x - ox, PAGE_PAD + y - oy) for (x, y), (ox, oy) in zip(at, origin, strict=True)
    ]


def _merged(moved: Sequence[PlacedSheet], indexes: Sequence[Sequence[int]]) -> PlacedSheet:
    """One sheet of the moved pieces, its lines back in the order of the facts."""
    lines = [
        (i, ln)
        for m, idx in zip(moved, indexes, strict=True)
        for i, ln in zip(idx, m.lines, strict=True)
    ]
    return PlacedSheet(
        number=1,
        boxes=tuple(b for m in moved for b in m.boxes),
        lines=tuple(ln for _, ln in sorted(lines, key=lambda t: t[0])),
        markers=(),
    )


def place_packed(facts: DiagramFacts, shape: tuple[int, int]) -> PlacedDiagram | None:
    """The placed diagram of `facts` with its pieces packed in rows to `shape`.

    One piece is placed as it is. None when a piece cannot be placed or falls on more than one
    sheet: the pieces share one canvas, so no sheet is cut.
    """
    parts = _split(facts)
    placed = [place_diagram(part) for part, _ in parts]
    if any(p is None or len(p.sheets) != 1 for p in placed):
        return None
    width = shape[0] - 2 * PAGE_PAD
    sheets = [wrapped(p.sheets[0], width, facts.text_height) for p in placed if p is not None]
    if len(parts) == 1:
        return PlacedDiagram(unit=facts.unit, sheets=(sheets[0],))
    moved = [_moved(s, dx, dy) for s, (dx, dy) in zip(sheets, _slots(sheets, shape), strict=True)]
    return PlacedDiagram(unit=facts.unit, sheets=(_merged(moved, [idx for _, idx in parts]),))
