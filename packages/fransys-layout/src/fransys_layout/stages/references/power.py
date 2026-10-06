"""D5, step 6: which decided ends take a power symbol, not a reference.

One end that would be a reference (a severed pair's end, a star's, a split's) on a port of a
power net takes the symbol of that net (R5). An off stub keeps its stub label (LD7), and so does
a reference merged with one. A joined run has one end decided (its first), so it gets one symbol.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import PowerEnd

    from .types import MarkerDecision


def with_power_ends(
    markers: tuple[MarkerDecision, ...], power: Mapping[Any, PowerEnd]
) -> tuple[MarkerDecision, ...]:
    """`markers`, each reference end on a `power` port flagged with its symbol and text."""
    return tuple(
        _flagged(one, power[one.port]) if _takes_symbol(one, power) else one for one in markers
    )


def _takes_symbol(one: MarkerDecision, power: Mapping[Any, PowerEnd]) -> bool:
    """Whether `one` is a reference end on a power port: no off stub, no merged stub line."""
    return one.port in power and one.star != "off" and one.merge is None


def _flagged(one: MarkerDecision, end: PowerEnd) -> MarkerDecision:
    """`one` as the power end `end`."""
    return replace(one, symbol=end.symbol, symbol_text=end.text or "")
