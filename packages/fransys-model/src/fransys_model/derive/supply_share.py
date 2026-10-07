"""An interface's supply share: how much of what it connects carries a supply (HL13, model-0176)."""

from fractions import Fraction

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.potential import port_potential_rank
from fransys_model.derive.unused import port_is_unused
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["supply_share"]


def supply_share(model: Model, function: Id[Function]) -> Fraction:
    """The share of `function`'s connected pins that carry a supply potential, 0 with none.

    A pin carries a supply when `port_potential_rank` gives it a rank: a rail, 24 V or GND. It is
    a rank, not a direction, since a potential cannot tell "fed by" from "feeds". Layout calls
    it to split a unit's interfaces between its two edges and never asks again.
    """
    idx = build_indexes(model)
    connected = [p for p in idx.ports_by_function.get(function, ()) if not port_is_unused(model, p)]
    if not connected:
        return Fraction(0)
    ranked = sum(port_potential_rank(model, port) is not None for port in connected)
    return Fraction(ranked, len(connected))
