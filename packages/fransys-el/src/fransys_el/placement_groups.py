"""The group a symbol is drawn in, and the label of a group node (design 2.1, hints C2)."""

from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.derive import effective_placement, function_item, node_label
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached, render_id
from fransys_model.layout import GroupHint, layout_of
from fransys_model.vocab import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Function

__all__ = ["group_nodes", "group_of", "label_of"]


@digest_cached(DIGEST_CACHE_SIZE)
def _ambiguous(model: Model) -> frozenset[str]:
    """The labels that two or more aspect nodes carry (a unit's group and the design's)."""
    count = Counter(node_label(model, n) for n in group_nodes(model))
    return frozenset(label for label, n in count.items() if n > 1)


def label_of(model: Model, node: Id[AspectNode]) -> str:
    """The core text of group node `node`, the name hints and `Sym.group` use.

    The label, unless another aspect node has it too; then the label and the node's id text.
    """
    label = node_label(model, node)
    return f"{label} {render_id(node)}" if label in _ambiguous(model) else label


def group_nodes(model: Model) -> list[Id[AspectNode]]:
    """Every aspect node of the model: the nodes a page group can be."""
    return list(model.tables.get("aspect_node", {}))


def group_of(model: Model, function: Id[Function]) -> str | None:
    """The label of the group `function` is drawn in: its `GroupHint`, else its item's placement."""
    for hint in layout_of(model, GroupHint).values():
        if hint.function == function:
            return label_of(model, hint.group)
    node = effective_placement(model, function_item(model, function), Aspect.FUNCTION)
    return None if node is None else label_of(model, node)
