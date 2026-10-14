"""What an overview box or an open thing stands for, and the mode of a view (model-0198).

One reference type serves the records and the `derive` fold rows, so they key boxes alike.
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


_PLAIN = OverviewMode.PLAIN
_MODES = {
    (False, False): {_PLAIN, OverviewMode.LOCATION, OverviewMode.FIELDS},
    (True, False): {OverviewMode.GROUPS, OverviewMode.SEE_THROUGH, _PLAIN, OverviewMode.LANES},
    (True, True): {OverviewMode.SEE_THROUGH},
}
_OPEN = {
    OverviewRefKind.ITEM,
    OverviewRefKind.UNIT,
    OverviewRefKind.PLACE,
    OverviewRefKind.FIELDS,
}
_LEVEL = {OverviewRefKind.GROUP, OverviewRefKind.STRIPS}


def check_view(
    unit: Id[Unit] | None,
    level: OverviewRef | None,
    mode: OverviewMode,
    open_: OverviewRef | None,
    open_at: OverviewRef | None = None,
) -> None:
    """Refuse a (unit, level, mode) a level cannot have, and a level or open of a wrong kind.

    `open_at` is the inside box an opened stub hangs on; it needs an `open_` that is no strip.
    """
    if unit is None and level is not None:
        msg = "a group or strips level needs its unit"
        raise SchemaError(msg, kind="layout.overview_view")
    if level is not None and level.kind not in _LEVEL:
        msg = f"a view cannot open a {level.kind.value} as its level"
        raise SchemaError(msg, kind="layout.overview_view")
    if mode not in _MODES[(unit is not None, level is not None)]:
        msg = f"a level of unit {unit} opened as {level} has no mode {mode.value}"
        raise SchemaError(msg, kind="layout.overview_view")
    if open_ is not None and open_.kind not in _OPEN:
        msg = f"a view cannot hold a {open_.kind.value} open"
        raise SchemaError(msg, kind="layout.overview_view")
    _check_open_at(open_, open_at)


def _check_open_at(open_: OverviewRef | None, open_at: OverviewRef | None) -> None:
    """Refuse an inside box for an open that is no stub."""
    if open_at is not None and (open_ is None or open_.kind is OverviewRefKind.ITEM):
        msg = "a view's open box hangs on an inside box only for an opened stub"
        raise SchemaError(msg, kind="layout.overview_view")
