"""The listing key: an item's identity across a rename, one home (CR6, model-0300)."""

from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .unit_relative_key import unit_relative_key


def listing_key(model: Model, item: Id[Item]) -> str:
    """`item`'s authoring key relative to its own unit, `/`-joined: the text a v2 listing stores.

    It survives a `place=` or `group=` change and auto-numbering; a tag change or a move into a
    function block changes it. The writer and the diff call this; nothing else builds the text.
    """
    return "/".join(unit_relative_key(model, item))


def instance_key(model: Model, unit: Id[Unit] | None, owner_unit: Id[Unit]) -> str:
    """The key of `owner_unit`, nested in `unit`, as `unit`'s listing reads it, `/`-joined.

    Prefixes the key of an end on a nested unit's boundary: two instances of one release differ.
    """
    table = units_table(model)
    skip = 0 if unit is None else len(table[unit].key) - 1
    return "/".join(table[owner_unit].key[skip:])
