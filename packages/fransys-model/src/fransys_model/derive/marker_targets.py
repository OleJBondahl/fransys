"""A link marker with many targets prints the first and a count (owner 2026-10-05, model-0139).

A marker names the other ends of its net. Up to `FULL_TARGETS` it prints each, one line each.
Past that it prints one line, the first target and `+n` more distinct ones, so its box stays
one line wide; layout sizes the box with `marker_lines`, derive prints with `target_lines`.
The first of them is a terminal of the net when it has one (`target_order`, model-0235).
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Sequence

from fransys_model.derive.kinds import item_kind
from fransys_model.vocab.enums import ItemKind
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import LinkMarker

FULL_TARGETS = 2


def more_count(targets: int) -> int:
    """The most others a ` +k` can name for a marker with `targets` ends: 0 when it prints none."""
    return targets if targets > FULL_TARGETS else 0


def more_text(others: int) -> str:
    """The ` +k` a marker prints after its first target, `k` the other distinct ends."""
    return f" +{others}"


def marker_lines(targets: int) -> int:
    """The lines a marker with `targets` other ends prints: one each up to the limit, else one."""
    return targets if targets <= FULL_TARGETS else 1


def target_lines(number: int, positions: Sequence[str]) -> list[str]:
    """`#n-<position>` per distinct target, or the first (reading order) and `+<k>`."""
    distinct = list(dict.fromkeys(positions))
    if len(positions) <= FULL_TARGETS:
        return [f"#{number}-{position}" for position in distinct]
    more = more_text(len(distinct) - 1) if len(distinct) > 1 else ""
    return [f"#{number}-{distinct[0]}{more}"]


def target_order(model: Model, marker: LinkMarker, ends: Sequence[LinkMarker]) -> list[LinkMarker]:
    """The other ends of `marker`'s net, `ends` in reading order less `marker`; a terminal first.

    Past `FULL_TARGETS` only the first prints, so it is the first terminal end when the net has
    one, else the first in reading order. Up to the limit every end prints and the order stays.
    """
    others = [one for one in ends if one.id != marker.id]
    if len(others) <= FULL_TARGETS:
        return others
    terminals = [
        one
        for one in others
        if item_kind(model, functions(model)[ports(model)[one.port].function].item)
        is ItemKind.TERMINAL
    ]
    return [*terminals[:1], *(one for one in others if one not in terminals[:1])]
