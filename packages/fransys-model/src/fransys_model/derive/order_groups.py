"""The order of function groups: profile rank, then natural key, then the authored order hints.

The one home of the overview's lane order (R338, ported from the old schematic stages). A hint
cycle leaves the hints out; the drawing engine reports the cycle.
"""

lazy from collections.abc import Mapping, Sequence
lazy from collections.abc import Set as AbstractSet
lazy from typing import Any

from fransys_model.kernel import natural_key
from fransys_model.layout import OrderHint, layout_of, profile_of
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import aspect_nodes
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode

__all__ = ["function_groups_in_order"]


def _key_text(key: tuple[Any, ...]) -> tuple[Any, ...]:
    """An authoring key's parts in natural order, part by part (`F2` before `F10`)."""
    return tuple(natural_key(str(part)) for part in key)


def _rank_key(
    node: AspectNode, ranks: Mapping[str, int], place: Mapping[tuple[Any, ...], int]
) -> tuple[Any, ...]:
    """The label's profile rank; unranked groups last, by natural key, then by key."""
    rank = ranks.get(node.label)
    return (1, 0, place[_key_text(node.key)], node.key) if rank is None else (0, rank, 0, node.key)


def _blockers(heads: Sequence[Id[Any]], hints: Sequence[OrderHint]) -> dict[int, set[int]] | None:
    """Per index, the indices that must come first; `None` when no hint names two heads here."""
    positions = {head: index for index, head in enumerate(heads)}
    blockers: dict[int, set[int]] = {index: set() for index in range(len(heads))}
    applied = False
    for hint in hints:
        if hint.before in positions and hint.after in positions:
            blockers[positions[hint.after]].add(positions[hint.before])
            applied = True
    return blockers if applied else None


def _unblocked(count: int, blockers: Mapping[int, set[int]]) -> list[int] | None:
    """Indices, each the first still waiting whose blockers are placed; `None` on a cycle."""
    order: list[int] = []
    placed: set[int] = set()
    while len(order) < count:
        waiting = (index for index in range(count) if index not in placed)
        free = next((index for index in waiting if blockers[index] <= placed), None)
        if free is None:
            return None
        placed.add(free)
        order.append(free)
    return order


def function_groups_in_order(
    model: Model, unit: Id[Any] | None, used: AbstractSet[Id[Any]]
) -> tuple[Id[AspectNode], ...]:
    """The `used` function groups (`=` aspect nodes) in order, for `unit`'s profile (`None`: top).

    By the profile's `group_ranks` of each label, unranked last in natural key order, then moved
    by the authored order hints in a stable pass. A hint cycle leaves every hint out.
    """
    nodes = sorted(
        (n for n in aspect_nodes(model).values() if n.aspect is Aspect.FUNCTION),
        key=lambda n: n.key,
    )
    place = {text: rank for rank, text in enumerate(sorted({_key_text(n.key) for n in nodes}))}
    ranks = profile_of(model, unit).group_ranks
    ranked = sorted((n for n in nodes if n.id in used), key=lambda n: _rank_key(n, ranks, place))
    heads = [n.id for n in ranked]
    blockers = _blockers(heads, tuple(layout_of(model, OrderHint).values()))
    order = None if blockers is None else _unblocked(len(heads), blockers)
    return tuple(heads) if order is None else tuple(heads[index] for index in order)
