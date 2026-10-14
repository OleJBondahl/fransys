"""LC1 (layout-0215): the parts of a column cut between its rows, and their keys.

A part is keyed by its column's key and its first row, so it sorts right after its column. A
wire across the cut turns back up the page, so `references.turned` draws it as a marker pair.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import Column

_ROW = "row"


def base_of(key: AuthoringKey) -> tuple[AuthoringKey, int]:
    """The key of the column a part was cut from, and the part's first row there."""
    if len(key) > 1 and key[-2] == _ROW and key[-1].isdigit():
        return key[:-2], int(key[-1])
    return key, 0


def row_part_key(key: AuthoringKey, first: int) -> AuthoringKey:
    """The key of the part starting at row `first`; a part cut again counts from its column."""
    base, at = base_of(key)
    return (*base, _ROW, f"{at + first:04d}")


def row_parts(column: Column, rows: Sequence[Sequence[int]]) -> tuple[Column, ...]:
    """`column` as one column per run of rows: the first keeps the key, each part from row 0."""
    found = []
    for n, part in enumerate(rows):
        renumber = {at: i for i, at in enumerate(part)}
        cells = tuple(
            replace(c, index=renumber[c.index]) for c in column.cells if c.index in renumber
        )
        key = column.key if n == 0 else row_part_key(column.key, part[0])
        found.append(replace(column, key=key, cells=cells))
    return tuple(found)


def share_spacing(
    spacing: Mapping[AuthoringKey, int], keys: Sequence[AuthoringKey], default: int
) -> dict[AuthoringKey, int]:
    """`spacing` with the parts of each cut column all at the narrowest one: one pitch down them."""
    parts: dict[AuthoringKey, list[AuthoringKey]] = {}
    for key in keys:
        parts.setdefault(base_of(key)[0], []).append(key)
    found = dict(spacing)
    for same in parts.values():
        if len(same) > 1 and (low := min(spacing.get(key, default) for key in same)) < default:
            found.update(dict.fromkeys(same, low))
    return found
