"""The order of the ports of an item box: a function's ports together, functions by marking."""

from fransys_model.kernel import natural_key
from fransys_model.vocab.tables import ports as ports_table
lazy from fransys_model.derive.rows_item_boxes import BoxCandidate
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["box_port_ranks"]


def box_port_ranks(model: Model, members: tuple[BoxCandidate, ...]) -> dict[Id[Port], int]:
    """Each port's rank: functions by first marking then id, each function's ports as given."""
    table = ports_table(model)
    first = {
        c.function: min((natural_key(table[p].name) for p in c.ports), default=()) for c in members
    }
    ranked = sorted(members, key=lambda c: (first[c.function], c.function))
    return {port: rank for rank, port in enumerate(p for c in ranked for p in c.ports)}
