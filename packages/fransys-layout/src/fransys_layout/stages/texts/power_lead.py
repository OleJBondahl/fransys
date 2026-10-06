"""D5 ruled 2026-10-02: a power symbol never touches another symbol, a box or a text.

A symbol that would touch one takes a longer lead, the fewest whole grids that clear it, as M7's
branch does. The symbol still faces its pin (A5); only the lead's length changes.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.geometry import Box, boxes_meet, overlaps, port_page_at
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.kernel import Finding, Severity

from .marker_row import stub_boxes
from .power import PowerPlace, power_place

if TYPE_CHECKING:
    from fransys_layout.stages.types import LinkMarker, PlacedFunction, PlacedLabel
    from fransys_model.kernel import Id

# The longest lead tried, in grids; a symbol nothing clears keeps the nearest one
MOST_GRIDS = 12
POWER_SYMBOL_UNPLACED = "POWER_SYMBOL_UNPLACED"

type Block = tuple[Id[Any] | None, Box]


def with_power_leads(
    markers: tuple[LinkMarker, ...],
    placed: tuple[PlacedFunction, ...],
    labels: tuple[PlacedLabel, ...],
) -> tuple[tuple[LinkMarker, ...], tuple[Finding, ...]]:
    """`markers` with each symbol on the fewest lead grids that clear it; one none clears warns."""
    blocks = _blocks(markers, placed, labels)
    owners = {port_page_at(one.at, g): one.function for one in placed for g in one.geometry.ports}
    taken: list[Box] = []
    findings: list[Finding] = []
    seen: set[tuple[Id[Any], int, int]] = set()
    led: dict[int, LinkMarker] = {}
    for index in sorted(range(len(markers)), key=lambda i: _stands(markers[i])):
        one = markers[index]
        if one.symbol and (key := (one.port, one.drawing_set, one.page)) not in seen:
            seen.add(key)
            clear = _led(one, (one.port, owners.get(one.at)), blocks, taken)
            led[index] = clear or one
            taken.append(power_place(led[index]).body)
            findings.extend(() if clear else (_unplaced(led[index]),))
    return tuple(led.get(i, one) for i, one in enumerate(markers)), tuple(findings)


def _stands(marker: LinkMarker) -> tuple[int, int, int, int]:
    """Where a symbol's pin stands on its page: the order symbols take their leads in."""
    return (marker.drawing_set, marker.page, marker.at.x, marker.at.y)


def _unplaced(marker: LinkMarker) -> Finding:
    """The finding of a symbol no lead clears: its port is the subject, the message names both."""
    return Finding(
        code=POWER_SYMBOL_UNPLACED,
        severity=Severity.WARNING,
        subjects=(marker.port,),
        message=(
            f"no lead of up to {MOST_GRIDS} grids clears the {marker.symbol} symbol "
            f"({marker.symbol_text!r}) at this pin: it keeps its one-grid lead"
        ),
    )


def _led(
    marker: LinkMarker,
    own: tuple[Id[Any] | None, ...],
    blocks: tuple[Block, ...],
    taken: Sequence[Box],
) -> LinkMarker | None:
    """`marker` with the fewest lead grids whose symbol is clear, or None when none is."""
    for grids in range(1, MOST_GRIDS + 1):
        led = replace(marker, symbol_grids=grids)
        if _clear(power_place(led), own, blocks, taken):
            return led
    return None


def _clear(
    place: PowerPlace,
    own: tuple[Id[Any] | None, ...],
    blocks: tuple[Block, ...],
    taken: Sequence[Box],
) -> bool:
    """Whether the body touches no block or earlier symbol and the lead crosses no block."""
    others = [box for owner, box in blocks if owner not in own]
    if any(_touches(place.body, box) for box in (*others, *taken)):
        return False
    return not any(_crosses(place.lead, box) for box in others)


def _touches(a: Box, b: Box) -> bool:
    """Whether `a` and `b` share a point: an edge or a corner counts."""
    return boxes_meet(a, b, closed=True)


def _crosses(a: Box, b: Box) -> bool:
    """Whether `a` and `b` share area: an edge or a corner alone does not count."""
    return overlaps(a, b)


def _blocks(
    markers: tuple[LinkMarker, ...],
    placed: tuple[PlacedFunction, ...],
    labels: tuple[PlacedLabel, ...],
) -> tuple[Block, ...]:
    """Every box a symbol must clear, with its owner: a function, a port, or none (a label)."""
    return (
        *((one.function, placed_keepout(one)) for one in placed),
        *((m.port, box) for m in markers if not m.symbol for box in (m.box, *stub_boxes(m))),
        *((None, one.box) for one in labels),
    )
