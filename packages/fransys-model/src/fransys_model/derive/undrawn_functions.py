"""Which functions the schematic leaves undrawn: loose, spare and idle ones (KIT-FACTS).

One home for the three rules the old engine ran at three points of its read step.
"""

lazy from collections.abc import Set as AbstractSet

from fransys_model.derive.accessory_unused import declares_all_unused
from fransys_model.derive.designation_label import takes_parents_designation
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.units import boundary, units
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.loose import function_is_loose
from fransys_model.derive.rows_undrawn import UndrawnFunctions
from fransys_model.derive.unused import function_is_reached, function_is_unused
from fransys_model.vocab.tables import functions, mates
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Port


def undrawn_functions(
    model: Model, *, hide_unused_pins: bool, wired: AbstractSet[Id[Port]]
) -> UndrawnFunctions:
    """The functions left off the schematic, in five sets by reason.

    A unit's boundary function is never loose, spare or idle: its replica column needs it.
    `wired` is the engine's set of ports on kept connections; `hide_unused_pins` the profile
    switch (an unwired contact is a spare either way). `accessory` holds every function of an
    accessory whatever either says (ACCESSORY-UNDRAWN, ruling 25).
    """
    edges = frozenset(f for unit in units(model) for f in boundary(model, unit))
    mated = frozenset(f for mate in mates(model).values() for f in (mate.a, mate.b))
    table = functions(model)
    ids = tuple(table)
    terminals = [f for f in ids if function_role(model, f).terminal]
    return UndrawnFunctions(
        loose=tuple(f for f in ids if f not in edges and function_is_loose(model, f)),
        spare=tuple(
            f
            for f in ids
            if f not in edges
            and function_is_unused(model, f)
            and (hide_unused_pins or function_role(model, f).plain_contact)
        ),
        idle=tuple(
            f for f in terminals if f not in edges and f not in mated and not _on(model, f, wired)
        ),
        accessory=tuple(f for f in ids if _of_accessory(model, table[f].item)),
        elsewhere=tuple(
            f
            for f in terminals
            if f in edges and f not in mated and not function_is_reached(model, f)
        ),
    )


def _on(model: Model, function: Id[Function], wired: AbstractSet[Id[Port]]) -> bool:
    """Whether any port of `function` is in `wired`."""
    return any(p in wired for p in build_indexes(model).ports_by_function.get(function, ()))


def _of_accessory(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is an accessory declared open on purpose: it draws nothing."""
    return declares_all_unused(model, item) and takes_parents_designation(model, item)
