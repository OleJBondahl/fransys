"""What a pin source seeds into a unit before numbering, as plain rows (model-0281).

`pin_positions` is a unit's items and instances by structure alone; `seed_pins` joins a pin source
to them. No facet, id or origin is built here: the facade turns the rows into records.
"""

from fransys_model.vocab.tables import items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import AuthoringKey, Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .lookups import terminal_items
from .numbering_moves import gone_or_moved, same_place
from .numbering_pins import item_position, unit_position
from .rows_numbering import AssignedSeed, PinPosition, SeedRows, UnitTagSeed
lazy from .rows_baseline import NumberingItem, NumberingPins


def _at(triple: tuple[AuthoringKey, AuthoringKey | None, str | None]) -> PinPosition:
    key, scope, code = triple
    return PinPosition(key=key, scope=scope, code=code)


def instances(model: Model, unit: Id[Unit]) -> dict[AuthoringKey, Id[Unit]]:
    """The instances directly inside `unit`, by their key relative to it."""
    return {
        unit_position(model, child.id)[0]: child.id
        for child in units_table(model).values()
        if child.parent == unit
    }


def _item_rows(model: Model, unit: Id[Unit]) -> dict[AuthoringKey, tuple[Item, PinPosition]]:
    """Each non-terminal item of `unit` by key, printed or not (seeding runs before numbering)."""
    terminals = terminal_items(model)
    found = {}
    for item in items(model).values():
        if item.unit != unit or item.id in terminals:
            continue
        position = _at(item_position(model, item.id))
        found[position.key] = (item, position)
    return found


def pin_positions(model: Model, unit: Id[Unit]) -> tuple[PinPosition, ...]:
    """`unit`'s non-terminal items and direct instances as `(key, scope, code)`, by key."""
    rows = [position for _item, position in _item_rows(model, unit).values()]
    rows.extend(_at(unit_position(model, child)) for child in instances(model, unit).values())
    return tuple(sorted(rows, key=lambda position: position.key))


def _pin_applies(pin: NumberingItem, position: PinPosition, *, tagged: bool) -> bool:
    """An unauthored pin gives an untagged thing its text while its scope and code still match."""
    return not pin.authored and not tagged and same_place(pin, position)


def _assigned(model: Model, unit: Id[Unit], source: NumberingPins) -> tuple[AssignedSeed, ...]:
    by_key = _item_rows(model, unit)
    seeds = []
    for pin in source.items:
        if (hit := by_key.get(pin.key)) is None:
            continue
        item, position = hit
        if _pin_applies(pin, position, tagged=item.tag is not None):
            seeds.append(AssignedSeed(item=item.id, key=item.key, text=pin.text))
    return tuple(seeds)


def _tags(model: Model, unit: Id[Unit], source: NumberingPins) -> tuple[UnitTagSeed, ...]:
    by_key = instances(model, unit)
    seeds = []
    for pin in source.items:
        if (child := by_key.get(pin.key)) is None:
            continue
        position = _at(unit_position(model, child))
        record = units_table(model)[child]
        if _pin_applies(pin, position, tagged=record.tag is not None):
            seeds.append(UnitTagSeed(instance=child, key=record.key, text=pin.text))
    return tuple(seeds)


def seed_pins(model: Model, unit: Id[Unit], source: NumberingPins) -> SeedRows:
    """The assigned items, assigned instances and reserved texts `source` seeds into `unit`.

    A pin seeds only a thing it still matches in key, scope and code that carries no written tag.
    Reserved texts are every pin gone or moved, plus the source's own `retired`.
    """
    return SeedRows(
        assigned=_assigned(model, unit, source),
        tags=_tags(model, unit, source),
        reserved=gone_or_moved(source, pin_positions(model, unit)),
    )


__all__ = ["instances", "pin_positions", "seed_pins"]
