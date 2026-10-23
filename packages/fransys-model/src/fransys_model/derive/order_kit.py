"""The orders of the chain and pin readers (KIT-FACTS): ranked picks, rows by field."""

from typing import TYPE_CHECKING
lazy from collections.abc import Iterable, Mapping

lazy from fransys_model.derive.rows_device_chains import ChainCandidate, ChainRow
lazy from fransys_model.derive.rows_pin_views import PinMate
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Function, Item

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


__all__ = [
    "candidates_in_order",
    "chains_in_order",
    "first_device",
    "lower_function",
    "pin_items_in_order",
    "pin_mates_in_order",
]


def first_device[D: SupportsRichComparison](
    devices: Iterable[Id[Item]], ranks: Mapping[Id[Item], D]
) -> Id[Item]:
    """LC3: the device of the lowest rank, then the lowest handle."""
    pool = list(devices)
    lowest = min(ranks[device] for device in pool)
    return min(device for device in pool if ranks[device] == lowest)


def lower_function(
    one: Id[Function], other: Id[Function], one_rank: object, other_rank: object
) -> Id[Function]:
    """The mate end that ranks higher, drawn lower; `one` when they tie."""
    return other if other_rank > one_rank else one  # ty: ignore[unsupported-operator]  # ranks are tuples of one shape


def pin_items_in_order[K: SupportsRichComparison, V](pins: Mapping[K, V]) -> list[tuple[K, V]]:
    """A pin table's items by port handle."""
    return sorted(pins.items())


def candidates_in_order(items: Iterable[ChainCandidate]) -> list[ChainCandidate]:
    """One device's function candidates by function key."""
    return sorted(items, key=lambda c: c.key)


def chains_in_order(found: Iterable[ChainRow]) -> tuple[ChainRow, ...]:
    """Chains by their member handles."""
    return tuple(sorted(found, key=lambda chain: chain.members))


def pin_mates_in_order(found: Iterable[PinMate]) -> tuple[PinMate, ...]:
    """Mated pin pairs by upper pin, then lower pin."""
    return tuple(sorted(found, key=lambda pair: (pair.upper, pair.lower)))
