"""The loosest bound each function sits in, over every current chain (rating checks)."""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.current.bounds import CurrentBound, highest
from fransys_model.derive.facts.current.chains import chains_unordered

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.enums import Current


def worst_bounds(model: Model) -> dict[tuple[Id[Function], Current], CurrentBound]:
    """Per function and kind, the largest bound of any position the function sits in.

    A function in several positions (a relay pole with two links, a mate with several pins) is
    compared with the loosest bound, the worst gap; the choice is `highest`.
    """
    found: dict[tuple[Id[Function], Current], list[CurrentBound]] = {}
    for chain in chains_unordered(model):
        for position in chain.positions:
            for function in position.functions:
                for bound in position.bounds:
                    found.setdefault((function, bound.kind), []).append(bound)
    return {key: highest(bounds) for key, bounds in found.items()}
