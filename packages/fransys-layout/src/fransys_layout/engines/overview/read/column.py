"""An open strip's column (OVERVIEW O5, A18): its terminals in strip order, and who stands left.

The order is the terminal table's, `derive.strip_view`. A wire's far box stands left of the
column, a cable's right: the strip's inside on one side, the field on the other.
"""

from fransys_layout.engines.overview.read.values import box_ident
from fransys_model.derive import strip_view
from fransys_model.layout import BoxKey, OverviewRef, OverviewRefKind
lazy from fransys_layout.engines.overview.read.values import BoxSpec, Ident, LineSpec
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit


def _left(lines: tuple[LineSpec, ...], column: frozenset[Ident]) -> tuple[Ident, ...]:
    """The boxes beside the column that stand left: those a wire of it reaches, in line order."""
    ends = [(ln.a, ln.b, ln.kind) for ln in lines if (ln.a in column) != (ln.b in column)]
    side: dict[Ident, bool] = {}
    for a, b, kind in ends:
        side.setdefault(b if a in column else a, kind != "cable")
    return tuple(box for box, is_left in side.items() if is_left)


def open_column(
    model: Model,
    unit: Id[Unit] | None,
    open_: OverviewRef | None,
    specs: tuple[tuple[BoxSpec, ...], tuple[LineSpec, ...]],
) -> tuple[tuple[Ident, ...], tuple[Ident, ...]]:
    """The `(column, left)` options of a view with a strip open; empty for any other view."""
    if unit is None or open_ is None or open_.item is None:
        return (), ()
    boxes, lines = specs
    drawn = {b.box for b in boxes}
    terminals = (
        box_ident(BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=t.item)))
        for t in strip_view(model, open_.item, unit).terminals
    )
    column = tuple(b for b in terminals if b in drawn)
    return column, _left(lines, frozenset(column))
