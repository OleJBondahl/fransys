"""What an overview box or an open thing stands for, the mode of a view and a box's key (model-0198).

One reference type serves the `derive` fold rows and the overview engine, so they key boxes alike.
"""

from enum import Enum

from fransys_model.kernel import Id, SchemaError, register_enum, value
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit


@register_enum
class OverviewRefKind(Enum):
    """What a reference names: a unit, an item, a group, the strips box, a place or fields."""

    UNIT = "unit"
    ITEM = "item"
    GROUP = "group"
    STRIPS = "strips"
    PLACE = "place"
    FIELDS = "fields"


@register_enum
class OverviewMode(Enum):
    """How a view draws its level: the system, a unit or a function group (O3, O9, O16)."""

    PLAIN = "plain"
    GROUPS = "groups"
    SEE_THROUGH = "see_through"
    LANES = "lanes"
    LOCATION = "location"
    FIELDS = "fields"


_FIELD = {
    OverviewRefKind.UNIT: "unit",
    OverviewRefKind.FIELDS: "unit",
    OverviewRefKind.ITEM: "item",
    OverviewRefKind.GROUP: "node",
    OverviewRefKind.PLACE: "node",
}


@value
class OverviewRef:
    """A unit, an item, a function group, the strips box, a place or a unit's field devices.

    `unit` is set for `UNIT` and `FIELDS`, `item` for `ITEM`, `node` for `GROUP` and `PLACE`;
    `STRIPS` holds none. A `PLACE` with no `node` stands for the boxes in no place.
    """

    kind: OverviewRefKind
    unit: Id[Unit] | None = None
    item: Id[Item] | None = None
    node: Id[AspectNode] | None = None

    def __post_init__(self) -> None:
        """Require the one id the kind names and none of the others."""
        named = _FIELD.get(self.kind)
        held = {n for n in ("unit", "item", "node") if getattr(self, n) is not None}
        if held != ({named} if named else set()) and self.kind is not OverviewRefKind.PLACE:
            msg = f"a {self.kind.value} reference holds only its {named or 'no'} id"
            raise SchemaError(msg, kind="layout.overview_box")
        if self.kind is OverviewRefKind.PLACE and held - {"node"}:
            msg = "a place reference holds only a node"
            raise SchemaError(msg, kind="layout.overview_box")


def ref_token(ref: OverviewRef) -> str:
    """A reference as text: its kind and its one id (`-` for none)."""
    held = ref.unit or ref.item or ref.node
    return f"{ref.kind.value}:{'-' if held is None else held.value}"


@value
class BoxKey:
    """The identity of a box in a view: what it stands for and, for a stub, the box it hangs on."""

    ref: OverviewRef
    at: OverviewRef | None = None

    @property
    def token(self) -> str:
        """The box as text: its reference, then `@` and the reference of the box it hangs on."""
        base = ref_token(self.ref)
        return base if self.at is None else f"{base}@{ref_token(self.at)}"
