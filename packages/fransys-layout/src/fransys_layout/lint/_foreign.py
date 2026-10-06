"""A link marker's stub or box on another item's symbol or port (S20 tally 8a, layout-0076).

A stub, or a box, that runs through or stands on a symbol or a port that is not the marker's own
reads as a connection to it. The marker's own function is the one with a port at `marker.at`;
every other placed function of the page is foreign. A stub is `stages.stub_runs`; a foreign
symbol is its body box, a foreign port its page point.

- `stub_through_symbols`: a stub through a foreign body's interior, or over a foreign port, is a
  `WIRE_THROUGH_SYMBOL` (the stub is a wire render draws), subjects (connection, port, function).
- `box_on_symbols`: a box over a foreign body's interior, or holding a foreign port, is a
  `TEXT_OVERLAP`, subjects the marker's port and the function, sorted.
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import contains_point, overlaps, port_page_at
from fransys_layout.stages.stub_runs import functions_through
from fransys_model.kernel import Finding, Severity

from .codes import TEXT_OVERLAP, WIRE_THROUGH_SYMBOL

if TYPE_CHECKING:
    from fransys_layout.geometry import Box, Point
    from fransys_layout.stages import Handle, LinkMarker, PlacedFunction


def stub_through_symbols(
    markers: tuple[LinkMarker, ...],
    placed: tuple[PlacedFunction, ...],
    bodies: tuple[tuple[PlacedFunction, Box], ...],
) -> list[Finding]:
    """One `WIRE_THROUGH_SYMBOL` per (marker, foreign function) its stub runs through or over."""
    ports = _ports(placed)
    boxes = {one.function: box for one, box in bodies}
    found: dict[tuple[Handle, ...], Finding] = {}
    for marker in markers:
        for function in functions_through(marker, boxes, ports):
            subjects = tuple(sorted((marker.connection, marker.port, function)))
            found.setdefault(
                subjects,
                Finding(
                    code=WIRE_THROUGH_SYMBOL,
                    severity=Severity.WARNING,
                    subjects=subjects,
                    message="a link marker's stub runs through a symbol that is not its own",
                ),
            )
    return [found[subjects] for subjects in sorted(found)]


def box_on_symbols(
    markers: tuple[LinkMarker, ...],
    placed: tuple[PlacedFunction, ...],
    bodies: tuple[tuple[PlacedFunction, Box], ...],
) -> list[Finding]:
    """One `TEXT_OVERLAP` per (marker, foreign function) whose body or port its box stands on."""
    ports = _ports(placed)
    found: dict[tuple[Handle, ...], Finding] = {}
    for marker in markers:
        box = marker.box
        for one, body in bodies:
            if one.function in _owners(marker, ports):
                continue
            if overlaps(box, body) or any(_inside(box, point) for point in ports[one.function]):
                subjects = tuple(sorted((marker.port, one.function)))
                found.setdefault(
                    subjects,
                    Finding(
                        code=TEXT_OVERLAP,
                        severity=Severity.WARNING,
                        subjects=subjects,
                        message="a link marker's box stands on a symbol that is not its own",
                    ),
                )
    return [found[subjects] for subjects in sorted(found)]


def _ports(placed: tuple[PlacedFunction, ...]) -> dict[Handle, tuple[Point, ...]]:
    """Each placed function's port points on the page."""
    return {
        one.function: tuple(port_page_at(one.at, g) for g in one.geometry.ports) for one in placed
    }


def _owners(marker: LinkMarker, ports: Mapping[Handle, tuple[Point, ...]]) -> set[Handle]:
    """The functions with a port at the marker's point: its own."""
    return {function for function, points in ports.items() if marker.at in points}


def _inside(box: Box, point: Point) -> bool:
    """Whether `point` lies in `box`, edges included."""
    return contains_point(box, point.x, point.y)
