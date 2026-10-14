"""A strip opened on a folded level (O5): its terminals stand in the strip's place (model-0198).

The terminals are boxes of the level, in strip order, and each wire of theirs is a line or a stub
as the level draws any other. Reached through `derive.fold_level`.
"""

from typing import TYPE_CHECKING

from fransys_model.layout import OverviewRef, OverviewRefKind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .overview_levels import strip_view
from .rows import ItemKind
from .rows_overview import FoldBox

if TYPE_CHECKING:
    from .overview_conns import Conn, Through

__all__ = ["freed", "terminal_boxes", "terminal_ref"]


def terminal_ref(terminal: Id[Item]) -> OverviewRef:
    """The reference of a terminal box."""
    return OverviewRef(kind=OverviewRefKind.ITEM, item=terminal)


def terminal_boxes(model: Model, unit: Id[Unit], strip: Id[Item]) -> tuple[FoldBox, ...]:
    """The terminals of `strip` opened on `unit`'s level as boxes, in strip order."""
    return tuple(
        FoldBox(
            key=terminal_ref(t.item),
            lines=(t.label,),
            tabs=(),
            dashed=False,
            item_kind=ItemKind.TERMINAL,
            terminals=0,
            items=0,
            units=0,
            strips=0,
            inner_lines=0,
        )
        for t in strip_view(model, strip, unit).terminals
    )


def freed(
    conns: tuple[Conn, ...], passing: tuple[Through, ...], strip: Id[Item]
) -> tuple[tuple[Conn, ...], tuple[Through, ...]]:
    """The conns at the pass-through terminals of `strip`, and the passes that remain.

    An opened strip draws each of its terminals, so their wires are plain lines, not one pass.
    """
    gone = {one.terminal for one in passing if one.strip == strip}
    plain = tuple(c for c in conns if {c.a, c.b} & gone)
    return plain, tuple(one for one in passing if one.terminal not in gone)
