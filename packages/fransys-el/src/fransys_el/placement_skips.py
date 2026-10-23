"""`Skipped`: a thing the builder left out of the problem, and why (P6.1 reads it)."""

from dataclasses import dataclass

from fransys_layout.core import natural_key

__all__ = [
    "FUNCTION_UNWIRED",
    "FUNCTION_WITHOUT_SYMBOL",
    "NET_UNDER_TWO_DRAWN_PINS",
    "NOT_SERIES_PARALLEL",
    "SPARE_FUNCTION",
    "SPARE_TERMINAL",
    "Skipped",
    "in_order",
]

NET_UNDER_TWO_DRAWN_PINS = "net_under_two_drawn_pins"
FUNCTION_WITHOUT_SYMBOL = "function_without_symbol"
NOT_SERIES_PARALLEL = "not_series_parallel"
FUNCTION_UNWIRED = "function_unwired"
SPARE_TERMINAL = "spare_terminal"
SPARE_FUNCTION = "spare_function"


@dataclass(frozen=True, slots=True)
class Skipped:
    """One omission: `what` ("net", "function" or "region"), its `id` and the `reason`.

    `more` holds a region's other function ids, after its first in `id`.
    """

    what: str
    id: str
    reason: str
    more: tuple[str, ...] = ()


def in_order(found: set[Skipped] | frozenset[Skipped]) -> tuple[Skipped, ...]:
    """The omissions by `what`, then natural order of id; deterministic whatever the input."""
    return tuple(sorted(found, key=lambda s: (s.what, natural_key(s.id))))
