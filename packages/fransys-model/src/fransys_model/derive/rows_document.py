"""The row shape of `derive.document_scope`: what one document selects from its model (model-0268).

It sits beside `rows.py` (model-0199); the selections are ids and `HarnessCable` rows.
"""

from fransys_model.kernel import Id, value
from fransys_model.layout import DrawingSet
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit

from .bom import TOP_LEVEL, TopLevelScope
from .rows import HarnessCable

__all__ = ["DocumentScope"]


@value
class DocumentScope:
    """The selections one `Document` makes, each read once from its subject.

    - `unit`: `document_unit`, the unit every reading uses; the `SYSTEM` preset has none.
    - `cables`: the `HarnessCable`s the drawings show (`SYSTEM`: the top-level ones, a unit: its
      own, an item: its cable children, a location: none); `harnesses`: the harness items with
      single wires the drawings add.
    - `bom_location`, `bom_item` and `top_level` make `bom_scope`, the scope `bom_lines` takes:
      the unit, else `TOP_LEVEL` for the system, else the location, else the item.
    - `bom_without`: the harness items a location document does not draw, with all they own;
      `bom_lines` leaves them out (`without=`) and `connector_items` omits them.
    - `drawing_sets`: the drawing sets this document prints, each set printed by exactly one
      document (`set_printers`): a unit's, the nested undocumented units', the fed items' ones.
    - `strips`: the terminal strips a terminal list covers; `connector_items`: the items a
      connector list covers for a unit or a location; `boards`: a board document's board.
    """

    unit: Id[Unit] | None
    cables: tuple[HarnessCable, ...]
    harnesses: tuple[Id[Item], ...]
    bom_location: Id[AspectNode] | None
    bom_item: Id[Item] | None
    bom_without: tuple[Id[Item], ...]
    top_level: bool
    strips: tuple[Id[Item], ...]
    connector_items: tuple[Id[Item], ...]
    boards: tuple[Id[Item], ...]
    drawing_sets: tuple[Id[DrawingSet], ...] = ()

    @property
    def bom_scope(self) -> Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None:
        """The scope `bom_lines` takes (see the class)."""
        if (unit := self.unit) is not None:
            return unit
        if self.top_level:
            return TOP_LEVEL
        return self.bom_location if self.bom_location is not None else self.bom_item
