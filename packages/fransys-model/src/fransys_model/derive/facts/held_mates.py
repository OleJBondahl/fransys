"""The mates 0.22 still refuses (R2223): the one fact `check_mates_disabled` reads."""

from collections import Counter

from fransys_model.derive.function_scopes import function_scopes
from fransys_model.vocab.tables import mates
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab.connectivity import Mate

__all__ = ["held_mates"]


def held_mates(model: Model) -> list[Mate]:
    """The mates 0.22 still refuses: halves that share a drawing set, or a function on two mates (R2223.2)."""
    on = Counter(function for mate in mates(model).values() for function in (mate.a, mate.b))
    return [
        mate
        for mate in mates(model).values()
        if on[mate.a] > 1 or on[mate.b] > 1 or not set(function_scopes(model, mate.a)).isdisjoint(function_scopes(model, mate.b))
    ]
