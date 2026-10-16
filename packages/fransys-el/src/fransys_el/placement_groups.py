"""The group a symbol is drawn in, and the label of a group node (design 2.1, hints C2)."""

from typing import TYPE_CHECKING

from fransys_model.derive import effective_placement, function_item, node_label
from fransys_model.layout import GroupHint, layout_of
from fransys_model.vocab import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Function

__all__ = ["group_of", "label_of"]


def label_of(model: Model, node: Id[AspectNode]) -> str:
    """The label of group node `node`, the name hints and `Sym.group` use."""
    return node_label(model, node)


def group_of(model: Model, function: Id[Function]) -> str | None:
    """The label of the group `function` is drawn in: its `GroupHint`, else its item's placement."""
    for hint in layout_of(model, GroupHint).values():
        if hint.function == function:
            return label_of(model, hint.group)
    node = effective_placement(model, function_item(model, function), Aspect.FUNCTION)
    return None if node is None else label_of(model, node)
