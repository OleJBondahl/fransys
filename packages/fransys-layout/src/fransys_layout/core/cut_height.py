"""The cut's height estimate: a column's height plus the G its fitted marker boxes reach (R508)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .flow_values import Column
    from .values import Options


def _reach(column: Column, options: Options, *, head: bool) -> int:
    """The G the fitted boxes of a column's head (up) or other (down) pins reach beyond them.

    A box equal to the plain marker's adds nothing: the cut counted it already.
    """
    cells = [c for lane in column.lanes for c in lane.cells]
    syms, heads = {c.sym for c in cells}, {(c.sym, c.top_pin) for c in cells}
    return max(
        (
            max(-b.y for o, b in views.items() if o in options.marker_vertical)
            if head
            else max(b.y + b.h for o, b in views.items() if o in options.marker_vertical)
            for (pin, _), views in options.marker_fit.items()
            if pin.sym in syms and ((pin.sym, pin.pin) in heads) is head and views != options.marker
        ),
        default=0,
    )


def lowered(height: int, columns: Iterable[Column], options: Options) -> int:
    """`height` plus the G the fitted boxes of `columns` reach above and below it."""
    cols = list(columns)
    up = max((_reach(c, options, head=True) for c in cols), default=0)
    down = max((_reach(c, options, head=False) for c in cols), default=0)
    return height + up + down
