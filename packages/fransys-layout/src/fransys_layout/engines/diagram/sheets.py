"""The diagram frame's sheets (BD5): columns placed left to right, a new sheet when needed.

A sheet ends after column `c` when column `c + 1` plus its trailing room would pass the right pad.
The next sheet starts at the cut's leading zone. A column that fits no sheet alone cannot be placed.
"""

lazy from collections.abc import Sequence

from fransys_layout.engines.diagram.sizes import PAGE_PAD
lazy from fransys_layout.engines.diagram.channels import Pair


def _next_x(sheet: Sequence[tuple[int, int]], widths: Sequence[int], pairs: Sequence[Pair]) -> int:
    """Where the column after the sheet's last one would start, in the channel's width."""
    last, x = sheet[-1]
    return x + widths[last] + pairs[last].width


def split_sheets(
    widths: Sequence[int], pairs: Sequence[Pair], sheet_width: int
) -> tuple[tuple[tuple[int, int], ...], ...] | None:
    """Each sheet's columns as (column index, x), or None when a column fits no sheet alone."""
    limit = sheet_width - PAGE_PAD
    sheets: list[list[tuple[int, int]]] = [[]]
    for c, width in enumerate(widths):
        x = _next_x(sheets[-1], widths, pairs) if sheets[-1] else PAGE_PAD
        if sheets[-1] and x + width + pairs[c].trail > limit:
            sheets.append([])
            x = pairs[c - 1].lead
        if x + width + pairs[c].trail > limit:
            return None
        sheets[-1].append((c, x))
    return tuple(tuple(s) for s in sheets)
