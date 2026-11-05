"""Which functions the schematic carries undrawn, by reason, and an accessory's (KIT-FACTS).

One home for the rules the old engine ran at three points of its read step; model-0371.
"""

lazy from collections.abc import Set as AbstractSet

from fransys_model.derive.accessory_unused import declares_all_unused
from fransys_model.derive.designation_label import takes_parents_designation
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.units import boundary, units
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.loose import function_is_loose
from fransys_model.derive.rows_drawn import Carried, CarriedReason, FunctionSymbol
from fransys_model.derive.unused import function_is_reached, function_is_unused
from fransys_model.vocab.tables import functions, mates
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port

__all__ = ["accessory_functions", "carried_functions"]


def carried_functions(model: Model, *, hide_unused_pins: bool, wired: AbstractSet[Id[Port]]) -> tuple[Carried, ...]:
    """The functions left off the schematic, one `Carried` each per reason, reasons in enum order.

    `UNWIRED`: nothing connected, or a terminal on no kept connection, net group or mate.
    `SPARE`: unused (an unwired contact is a spare either way; `hide_unused_pins` adds the rest).
    `OFF_DOCUMENT`: a boundary terminal no wire inside reaches, kept for the parent's black box.
    A unit's boundary function is never loose, spare or idle: its replica column needs it.
    `wired` is the engine's set of ports on kept connections.
    """
    edges = frozenset(f for unit in units(model) for f in boundary(model, unit))
    mated = frozenset(f for mate in mates(model).values() for f in (mate.a, mate.b))
    ids = tuple(functions(model))
    terminals = [f for f in ids if function_role(model, f).terminal]
    by_reason = {
        CarriedReason.UNWIRED: frozenset(f for f in ids if f not in edges and function_is_loose(model, f))
        | frozenset(
            f
            for f in terminals
            if f not in edges and f not in mated and not any(p in wired for p in build_indexes(model).ports_by_function.get(f, ()))
        ),
        CarriedReason.SPARE: frozenset(
            f for f in ids if f not in edges and function_is_unused(model, f) and (hide_unused_pins or function_role(model, f).plain_contact)
        ),
        CarriedReason.OFF_DOCUMENT: frozenset(f for f in terminals if f in edges and f not in mated and not function_is_reached(model, f)),
    }
    return tuple(Carried(reason=reason, symbol=FunctionSymbol(function=f)) for reason, held in by_reason.items() for f in ids if f in held)


def accessory_functions(model: Model) -> tuple[Id[Function], ...]:
    """Every function of an accessory declared open on purpose, whatever the profile says.

    ACCESSORY-UNDRAWN, ruling 25: such a function draws nothing, so no row requires it.
    """
    table = functions(model)
    return tuple(f for f in table if declares_all_unused(model, table[f].item) and takes_parents_designation(model, table[f].item))
