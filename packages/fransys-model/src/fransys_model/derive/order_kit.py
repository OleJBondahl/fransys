"""The orders of the chain and pin readers (KIT-FACTS): ranked picks, rows by field."""

from typing import TYPE_CHECKING
lazy from collections.abc import Iterable, Mapping

lazy from fransys_model.derive.order import functions_in_order
lazy from fransys_model.derive.rows_pin_views import PinMate
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


__all__ = [
    "lower_function",
    "pin_items_in_order",
    "pin_mates_in_order",
    "source_end",
]


def lower_function[D: SupportsRichComparison](one: Id[Function], other: Id[Function], one_rank: D, other_rank: D) -> Id[Function]:
    """The mate end that ranks higher, drawn lower; `one` when they tie."""
    return one if max(one_rank, other_rank) is one_rank else other


def pin_items_in_order[K: SupportsRichComparison, V](pins: Mapping[K, V]) -> list[tuple[K, V]]:
    """A pin table's items by port handle."""
    return sorted(pins.items())


def pin_mates_in_order(found: Iterable[PinMate]) -> tuple[PinMate, ...]:
    """Mated pin pairs by upper pin, then lower pin."""
    return tuple(sorted(found, key=lambda pair: (pair.upper, pair.lower)))


def source_end(model: Model, ends: Iterable[tuple[Id[Function], int]]) -> tuple[Id[Function], int]:
    """R939.3: the end of a trunk its poles are read at: the function lowest in `functions_in_order`, then end side, then id."""
    rank = {function: place for place, function in enumerate(functions_in_order(model, {function for function, _ in ends}))}
    return min(ends, key=lambda end: (rank[end[0]], end[1], end[0]))
