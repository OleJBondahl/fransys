"""Band alignment inputs (R7 B7, A9, layout-0061): who takes part in a band, its shared top."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .place import _Cell


def _participants(page: Sequence[Any]) -> dict[tuple[str, object, int], list[tuple[int, int]]]:
    """The topmost row of each band per column, keyed by (band, role, poles) (C13(b))."""
    found: dict[tuple[str, object, int], list[tuple[int, int]]] = {}
    for column, rows in enumerate(page):
        seen: set[str] = set()
        for index, row in enumerate(rows):
            band = row[0].band
            if band is None or band in seen:
                continue
            seen.add(band)
            # C13(b): the role, and the circuit width (poles across the row's lanes): a
            # 3-pole power row never aligns a single control contact
            poles = sum(cell.geometry.poles for cell in row if not cell.side)
            found.setdefault((band, row[0].role, poles), []).append((column, index))
    return found


def _band_top(
    page: Sequence[list[list[_Cell]]],
    members: Sequence[tuple[int, int]],
    stacked: Mapping[tuple[int, int], int],
) -> int:
    """The lowest current top among `members` that is at least their deepest need, else the need."""
    need = max(stacked[m] for m in members)
    tops = sorted(
        t for t in (min(cell.top for cell in page[c][i]) for c, i in members) if t >= need
    )
    return tops[0] if tops else need


def _cascade_bottom(rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]) -> int:
    """The column's lowest keep-out bottom if `_cascade` lowered `rows[start]` to `top`."""
    floor, bottom = top, max(cell.bottom for row in rows for cell in row)
    for index in range(start, len(rows)):
        row = rows[index]
        row_top = min(cell.top for cell in row)
        if row_top >= floor:
            return bottom
        shift = floor - row_top
        bottom = max(bottom, max(cell.bottom for cell in row) + shift)
        floor = max(cell.bottom for cell in row) + shift + gaps[index]
    return bottom
