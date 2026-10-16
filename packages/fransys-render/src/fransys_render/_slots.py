"""One entry draws a symdef symbol from plain values (render-0014); none is computed here."""

from typing import TYPE_CHECKING, Literal

from symdef import stretch, table, wire

from electrical_symbols import G_PER_MODULE
from fransys_model.derive.grid_mm import grid_to_mm

from ._numbers import format_decimal
from ._symbol_geometry import _turned
from ._symbols import symbol_body

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from decimal import Decimal

    from symdef import Library
    from symdef.model import Symbol

    from fransys_model.layout import Orientation, SheetFormat

__all__ = ["draw_symbol"]

Axis = Literal["x", "y"]


def _modules(grid: float) -> float:
    """A grid value as module units: the unit change symdef asks for, nothing more."""
    return grid / G_PER_MODULE


def _stretched(
    symbol: Symbol,
    lengths: Mapping[Axis, int],
    offsets: Mapping[Axis, Mapping[str, int]],
) -> Symbol:
    """`stretch` on x, then on y, by the lengths and port offsets the record carries."""
    for axis in ("x", "y"):
        if axis in lengths:
            placed = {port: _modules(at) for port, at in offsets.get(axis, {}).items()}
            symbol = stretch(symbol, axis, _modules(lengths[axis]), placed or None)
    return symbol


def _built(  # noqa: PLR0913 -- the record's fields, one keyword each
    library: Library,
    key: str,
    *,
    points: Sequence[tuple[int, int]] | None,
    n: int | None,
    axis: Axis | None,
    head: str | None,
    lengths: Mapping[Axis, int],
    offsets: Mapping[Axis, Mapping[str, int]],
) -> Symbol:
    """The symbol as symdef builds it from the values, before orientation."""
    if points is not None:
        return wire(library, key, [(_modules(x), _modules(y)) for x, y in points])
    symbol = library.get(key)
    if n is not None and axis is not None:
        symbol = table(symbol, n, axis, head=None if head is None else library.get(head))
    return _stretched(symbol, lengths, offsets)


def draw_symbol(  # noqa: PLR0913 -- the record's fields, one keyword each
    library: Library,
    key: str,
    *,
    sheet: SheetFormat,
    at: tuple[int, int],
    font_mm: Decimal,
    orientation: Orientation,
    points: Sequence[tuple[int, int]] | None = None,
    n: int | None = None,
    axis: Axis | None = None,
    head: str | None = None,
    lengths: Mapping[Axis, int] | None = None,
    offsets: Mapping[Axis, Mapping[str, int]] | None = None,
    texts: Mapping[str, str] | None = None,
    tint: str | None = None,
) -> str:
    """`<g>` for symbol `key` (or wire style `key` through `points`), placed at `at` in G.

    `table`, `stretch` (x, then y) and `orient` run on the values as given. `texts` (slot id to
    string) is drawn by symdef, which also rejects an unknown or a missing required slot.
    """
    symbol = _built(
        library,
        key,
        points=points,
        n=n,
        axis=axis,
        head=head,
        lengths=lengths or {},
        offsets=offsets or {},
    )
    body = symbol_body(
        _turned(symbol, orientation),
        sheet.module_mm,
        font_mm,
        tint,
        texts=texts,
        required_slots=library.required_slots,
    )
    x_mm = grid_to_mm(sheet.content_x_mm, at[0], sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, at[1], sheet.module_mm)
    return f'<g transform="translate({format_decimal(x_mm)},{format_decimal(y_mm)})">{body}</g>'
