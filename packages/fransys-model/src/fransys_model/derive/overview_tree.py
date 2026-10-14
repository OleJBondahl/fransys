"""The overview's parts tree: units, then the items they hold, strips last (O12, model-0198).

Every row prints relative to the unit that holds it, as the views do (`display_unit`). The page
nests the rows; it computes no name. Reached as `derive.overview_tree`.
"""

from typing import Any

from fransys_model.vocab.tables import items, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .designation import designation_refusal, printed_designation
from .kinds import item_kind
from .order import natural_key
from .overview import overview_graph
from .overview_levels import level_box_lines
from .rows import ItemKind, OverviewNode
from .rows_overview import TreeRow

__all__ = ["overview_tree"]

type _Key = tuple[str, Id[Any]]


def _unit_label(model: Model, unit: Id[Unit]) -> str:
    """The row text of a unit: its box text relative to the unit that holds it."""
    return " ".join(level_box_lines(model, unit, units(model)[unit].parent))


def _item_label(model: Model, node: OverviewNode) -> str:
    """The row text of an item: its designation in its own unit, else its description."""
    unit = items(model)[node.item].unit
    if node.designation is not None and designation_refusal(model, node.item, unit=unit) is None:
        return printed_designation(model, node.item, unit=unit)
    return node.designation if node.designation is not None else node.description


def _holder(model: Model, item: Id[Item]) -> _Key | None:
    """What the row of `item` hangs on: its parent item in the same unit, else its unit."""
    record = items(model)[item]
    if record.parent is not None and items(model)[record.parent].unit == record.unit:
        return ("item", record.parent)
    return None if record.unit is None else ("unit", record.unit)


class _Tree:
    """The rows being built, and the children of each row in display order."""

    def __init__(self, model: Model) -> None:
        self.model = model
        self.nodes = {n.item: n for n in overview_graph(model).nodes}
        self.kids: dict[_Key | None, list[_Key]] = {}
        self.rows: list[TreeRow] = []
        for unit in sorted(units(model), key=lambda u: natural_key(_unit_label(model, u))):
            up = units(model)[unit].parent
            self._add(None if up is None else ("unit", up), ("unit", unit))
        for strips in (False, True):
            for item in self.nodes:
                if (item_kind(model, item) is ItemKind.STRIP) is strips:
                    self._add(_holder(model, item), ("item", item))

    def _add(self, holder: _Key | None, child: _Key) -> None:
        self.kids.setdefault(holder, []).append(child)

    def _row(self, parent: int | None, child: _Key) -> TreeRow:
        kind, ident = child
        if kind == "unit":
            return TreeRow(
                parent=parent, unit=ident, item=None, label=_unit_label(self.model, ident)
            )
        label = _item_label(self.model, self.nodes[ident])
        return TreeRow(parent=parent, unit=None, item=ident, label=label)

    def walk(self, key: _Key | None, parent: int | None) -> None:
        """Append the rows under `key` in preorder."""
        for child in self.kids.get(key, []):
            index = len(self.rows)
            self.rows.append(self._row(parent, child))
            self.walk(child, index)


def overview_tree(model: Model) -> tuple[TreeRow, ...]:
    """The rows of the parts tree in display order, each naming its parent row by index."""
    tree = _Tree(model)
    tree.walk(None, None)
    return tuple(tree.rows)
