"""Where a subject counts on a view: its nearest drawn ancestor box, or the line it names.

A finding's or a diff row's subject need not be drawn on a view. It counts on its nearest drawn
ancestor box (the item's parents, its strip box, its group, its field box, then its units
outward). A subject with no drawn ancestor is left out of that view (overview-0010).
"""

from typing import Any, cast

from fransys_model.kernel import parent_chain
from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import Aspect, SubjectKind
from fransys_model.vocab.tables import conductors, functions, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function, Item, Port, Unit

from .facts.subjects import subject_kind
from .kinds import item_role
from .lookups import effective_placement, item_of_port, unit_chain
from .overview_field import field_devices
from .overview_location import location_fold
lazy from .rows_overview_view import ViewBox, ViewRows

__all__ = ["place_members", "subject_marks", "view_lookup"]

type RefKey = tuple[str, Id[Any] | None]
type Subject = Id[Item] | Id[Unit] | Id[Port] | Id[Function] | Id[Conductor]
_ENDS = 2


def _ref_key(ref: OverviewRef) -> RefKey:
    """A box reference as `(kind, id)`; the id is the item, unit or aspect node it names."""
    if ref.item is not None:
        return (ref.kind.value, ref.item)
    return (ref.kind.value, ref.unit if ref.unit is not None else ref.node)


def place_members(model: Model, box: ViewBox) -> tuple[Id[Item] | Id[Unit], ...] | None:
    """The units and items a place box of the location fold holds, else `None`."""
    ref = box.key.ref
    fold = location_fold(model)
    if ref.kind is not OverviewRefKind.PLACE or box.key.at is not None or fold is None:
        return None
    place = next(b for b in fold.boxes if b.place == ref.node)
    return cast("tuple[Id[Item] | Id[Unit], ...]", tuple(place.boxes))


def view_lookup(model: Model, rows: ViewRows) -> dict[RefKey, int]:
    """Each drawn box's index by its reference; a place box also by each member it holds."""
    found: dict[RefKey, int] = {}
    for index, box in enumerate(rows.boxes):
        if box.key.at is not None:
            continue
        found.setdefault(_ref_key(box.key.ref), index)
        for member in place_members(model, box) or ():
            found.setdefault((subject_kind(member).value, member), index)
    return found


def _unit_keys(model: Model, unit: Id[Unit] | None) -> list[RefKey]:
    """The unit boxes from `unit` outward."""
    return [] if unit is None else [("unit", one) for one in unit_chain(model, unit)]


def _item_keys(model: Model, item: Id[Item], view_unit: Id[Unit] | None) -> list[RefKey]:
    """The boxes that can hold `item`, nearest first; `view_unit` is the unit of the level."""
    chain = list(parent_chain(lambda one: items(model)[one].parent, item))
    keys: list[RefKey] = [("item", one) for one in chain]
    owner = items(model)[item].unit
    if owner is not None and owner == view_unit:
        if any(item_role(model, one).strip for one in chain):
            keys.append(("strips", None))
        keys.append(("group", effective_placement(model, item, Aspect.FUNCTION)))
    keys.append(("fields", field_devices(model).get(item)))
    return [*keys, *_unit_keys(model, owner)]


def _box_of(keys: list[RefKey], lookup: dict[RefKey, int]) -> int | None:
    """The first drawn box among `keys`; a key naming no id names nothing."""
    named = [k for k in keys if k[1] is not None or k[0] == "strips"]
    return next((lookup[k] for k in named if k in lookup), None)


def _ends(model: Model, subject: Id[Any]) -> list[Id[Any]]:
    """The items a subject names: itself, its port's or function's item, a conductor's two ends."""
    if subject_kind(subject) is SubjectKind.ITEM:
        return [subject]
    if subject_kind(subject) is SubjectKind.PORT:
        return [item_of_port(model, subject)]
    if subject_kind(subject) is SubjectKind.FUNCTION:
        return [functions(model)[subject].item]
    if subject_kind(subject) is SubjectKind.CONDUCTOR:
        record = conductors(model)[subject]
        return [item_of_port(model, record.a), item_of_port(model, record.b)]
    return []


def _boxes_of(
    model: Model, rows: ViewRows, lookup: dict[RefKey, int], subject: Id[Any]
) -> list[int]:
    """The drawn boxes a subject counts on, in the order of its ends."""
    if subject_kind(subject) is SubjectKind.UNIT:
        keys = [_unit_keys(model, subject)]
    else:
        keys = [_item_keys(model, one, rows.unit) for one in _ends(model, subject)]
    found = [_box_of(k, lookup) for k in keys]
    return [at for at in found if at is not None]


def _wires_of(rows: ViewRows, subject: Id[Any], ends: list[int]) -> list[int]:
    """The lines a subject counts on: a cable item's own lines, a conductor's between its ends."""
    if subject_kind(subject) is SubjectKind.ITEM:
        return [i for i, line in enumerate(rows.lines) if line.via == subject]
    pair = {rows.boxes[e].key for e in ends}
    if subject_kind(subject) is not SubjectKind.CONDUCTOR or len(pair) != _ENDS:
        return []
    return [i for i, line in enumerate(rows.lines) if {line.a, line.b} == pair]


def subject_marks(
    model: Model, rows: ViewRows, lookup: dict[RefKey, int], subject: Subject
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """`(boxes, lines)` indexes of `rows` the subject counts on; the lines when it has any.

    `lookup` is `view_lookup(model, rows)`. A cable item counts on its own lines, a conductor on
    the line between its two boxes; else the subject counts on each distinct box of its ends.
    """
    ends = _boxes_of(model, rows, lookup, subject)
    if wires := _wires_of(rows, subject, ends):
        return (), tuple(wires)
    return tuple(dict.fromkeys(ends)), ()
