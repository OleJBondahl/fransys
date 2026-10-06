"""D5, step 6: a join on a power net stays a wire only while its straight wire is free.

A run with a power port that `join_y` can align is still drawn as symbols when another port of
its page stands on the wire's line between its ends, as a power symbol's lead would cross the
wire. The run gives `JOIN_UNALIGNED` (`WARNING`), D1's fallback, and each end takes its symbol.
"""

from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Protocol

from fransys_layout.geometry import Facing

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import DrawnFunction
    from fransys_model.kernel import Id

    from .joins import Spot
    from .types import Page


class Clear(Protocol):
    """Whether a run's wire is free, given the run's case (`at_ends`, D5); `_decided` asks it."""

    def __call__(self, page: Page, run: tuple[Spot, ...], *, at_ends: bool) -> bool: ...


@dataclass(frozen=True, slots=True)
class PowerClearance:
    """What a power run's free wire is judged by: page spots, port x, power ports (D5)."""

    by_page: Mapping[Page, tuple[Spot, ...]]
    x_of: Mapping[Id[Any], int]
    power: frozenset[Id[Any]]


def always_clear(*_run: object, **_case: object) -> bool:
    """The `Clear` of a plant with no power net: every run's wire is free, whatever it is asked."""
    return True


def run_clearance(
    spots: Mapping[Id[Any], tuple[Spot, ...]],
    drawn: tuple[DrawnFunction, ...],
    power: frozenset[Id[Any]],
) -> Clear:
    """`_power_clear` over every port's `Spot`s and port x, for `_wired_beside`'s runs."""
    by_page: dict[Page, list[Spot]] = defaultdict(list)
    for found in spots.values():
        for spot in found:
            by_page[spot.page].append(spot)
    x_of = {
        port.port: geometry.at.x
        for one in drawn
        for port in one.ports
        for geometry in one.geometry.ports
        if geometry.name == port.symbol_port
    }
    return partial(
        _power_clear,
        clearance=PowerClearance(
            {page: tuple(found) for page, found in by_page.items()}, x_of, power
        ),
    )


def _power_clear(
    page: Page,
    run: tuple[Spot, ...],
    *,
    at_ends: bool,
    clearance: PowerClearance,
) -> bool:
    """Whether a power run's wire is free: no other port on its line stands between its ends."""
    facing = run[0].facing
    x_of = clearance.x_of
    if facing not in (Facing.N, Facing.S) or not any(s.end.port in clearance.power for s in run):
        return True
    own = {s.end.port for s in run}
    keys = [(s.index, x_of[s.end.port]) for s in run]
    low, high = min(keys), max(keys)
    return not any(
        low < (other.index, x_of[other.end.port]) < high
        for other in clearance.by_page[page]
        if other.end.port not in own
        and other.facing is facing
        and _on_line(other, run[0], at_ends=at_ends)
    )


def _on_line(other: Spot, first: Spot, *, at_ends: bool) -> bool:
    """Whether `other` stands on the line `first`'s run lies on."""
    if at_ends:
        return other.end.row == (0 if other.facing is Facing.N else other.last)
    return other.end.offset == first.end.offset
