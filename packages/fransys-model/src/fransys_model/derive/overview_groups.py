"""Which function group each box of a unit level belongs to, and the boxes the fold draws (O3).

A group is the topmost function node that is the opened unit's own (`own_nodes`), else the item's
effective function node. A nested unit joins the one group all its grouped items share. A strip
with a group folds into it; the strips with none form one box, "Terminal strips (n)".
"""

from typing import Any

from fransys_model.derive.facts.units import unit_items
from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import Aspect, ItemKind
from fransys_model.vocab.tables import aspect_nodes
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import own_nodes
from .lookups import effective_placement
from .order import natural_key
from .overview_levels import level_box
from .overview_names import node_lines
from .rows_overview import FoldBox
from .unit_nodes import chain_up
lazy from .rows import OverviewBox

__all__ = [
    "box_groups",
    "box_order_key",
    "fold_box",
    "fold_key",
    "group_box",
    "strips_box",
]


def _item_group(model: Model, unit: Id[Unit], item: Id[Item]) -> Id[AspectNode] | None:
    """`item`'s group in `unit`'s level: its topmost own function ancestor, else its own node."""
    nodes = aspect_nodes(model)
    chain = [
        node
        for node in chain_up(nodes, effective_placement(model, item, Aspect.FUNCTION))
        if nodes[node].aspect is Aspect.FUNCTION
    ]
    own = own_nodes(model, unit)
    return next((node for node in reversed(chain) if node in own), chain[0] if chain else None)


def box_groups(
    model: Model, unit: Id[Unit], boxes: tuple[OverviewBox, ...]
) -> dict[Id[Any], Id[AspectNode] | None]:
    """The group of each box of `unit`'s level; a unit box takes the one group its items share."""
    shared: dict[Id[Any], set[Id[AspectNode] | None]] = {}
    for item in sorted(unit_items(model, unit)):
        box = level_box(model, item, unit)
        if box is not None and box.kind == "unit":
            shared.setdefault(box, set()).add(_item_group(model, unit, item))
    found: dict[Id[Any], Id[AspectNode] | None] = {}
    for one in boxes:
        if one.kind is None:
            held = shared.get(one.box, set()) - {None}
            found[one.box] = next(iter(held)) if len(held) == 1 else None
        else:
            found[one.box] = _item_group(model, unit, one.box)
    return found


def fold_key(box: OverviewBox) -> OverviewRef:
    """The key of a box that stands on its own: a unit or an item."""
    if box.kind is None:
        return OverviewRef(kind=OverviewRefKind.UNIT, unit=box.box)
    return OverviewRef(kind=OverviewRefKind.ITEM, item=box.box)


def fold_box(box: OverviewBox) -> FoldBox:
    """A standing box as a fold box, with no counts."""
    return FoldBox(
        key=fold_key(box),
        lines=box.lines,
        tabs=box.tabs,
        dashed=box.dashed,
        item_kind=box.kind,
        terminals=box.terminals,
        items=0,
        units=0,
        strips=0,
        inner_lines=0,
    )


def group_box(
    model: Model, node: Id[AspectNode], members: list[OverviewBox], inner_lines: int
) -> FoldBox:
    """A function group as one box: its designation and name, its counts of what it holds."""
    return FoldBox(
        key=OverviewRef(kind=OverviewRefKind.GROUP, node=node),
        lines=node_lines(model, node),
        tabs=(),
        dashed=False,
        item_kind=None,
        terminals=sum(m.terminals for m in members),
        items=sum(m.kind is not None and m.kind is not ItemKind.STRIP for m in members),
        units=sum(m.kind is None for m in members),
        strips=sum(m.kind is ItemKind.STRIP for m in members),
        inner_lines=inner_lines,
    )


def strips_box(members: list[OverviewBox]) -> FoldBox:
    """The strips with no group as one box, "Terminal strips (n)" for `n` strips."""
    return FoldBox(
        key=OverviewRef(kind=OverviewRefKind.STRIPS),
        lines=(f"Terminal strips ({len(members)})",),
        tabs=(),
        dashed=False,
        item_kind=ItemKind.STRIP,
        terminals=sum(m.terminals for m in members),
        items=0,
        units=0,
        strips=len(members),
        inner_lines=0,
    )


def box_order_key(box: FoldBox) -> tuple[Any, ...]:
    """Fold boxes in text order: by the lines they print, then by kind."""
    return (tuple(natural_key(line) for line in box.lines), box.key.kind.value)
