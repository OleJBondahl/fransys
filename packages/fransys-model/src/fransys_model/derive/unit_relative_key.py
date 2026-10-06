"""FD2: an item's designation identity is its key with its unit's own prefix dropped.

Reached as `fransys_model.derive.unit_relative_key.unit_relative_key`, never re-exported
from `derive/__init__.py` -- `derive.baseline`'s own precedent (orchestrator appendix point 4:
no new top-level `derive` export for this).
"""

from fransys_model.vocab.tables import items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import AuthoringKey, Id, Model
lazy from fransys_model.vocab.core import Item

from .lookups import require


def unit_relative_key(model: Model, item: Id[Item]) -> AuthoringKey:
    """`item`'s key, relative to its own unit (FD2): the identity every build of it shares.

    Two instances of one release, and a standalone build, all give the same key -- "key for
    key" (units spec U7). An item of no unit (`item.unit is None`) keeps its whole key. An
    item of a unit: the unit's own record's `key` always ends with the literal segment
    `"unit"` (`fransys_author.design.Scope.unit`), and every item made through that
    unit's own `Scope`, or a scope nested in it, shares the SAME prefix (`Scope.unit()`
    keeps the prefix unchanged) -- so this drops `len(unit.key) - 1` leading segments from
    `item.key`: two plain key slices, verified from the authoring code itself, never a
    string operation or a re-parse (CLAUDE.md invariant 4).

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    record = require(items(model).get(item), "item", item)
    if record.unit is None:
        return record.key
    unit_record = require(units_table(model).get(record.unit), "unit", record.unit)
    return record.key[len(unit_record.key) - 1 :]
