"""Where the ports a connection names are drawn, private to the coherence check.

Refs: package-layout.md 4, lint.md 6.8.

A port's position is its placed function's origin plus the position of the symbol port its
`DrawnPort` names. Its function is the `PortRef` that names it, so nothing is found by geometry.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.geometry import LayoutError, Point, port_page_at

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import (
        Connection,
        DrawnFunction,
        Handle,
        NetGroup,
        PlacedFunction,
    )

# `(drawing_set, page)`: a page is identified by this pair throughout the check.
type Page = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Ports:
    """The named ports: each one's physical net, its position per page, its function's pages."""

    net: dict[Handle, Handle]
    at: dict[tuple[Handle, Page], Point]
    # R7 B5: where an end with `PortRef.symbol_port` lands: another port of its node
    also: dict[tuple[Handle, Page], frozenset[Point]]
    pages: dict[Handle, tuple[Page, ...]]


def locate(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
) -> Ports:
    """Locate every port a connection or net group names, on each page its function is on."""
    where = _placements(placed)
    named = _named(connections, net_groups)
    also = _also(connections, where)
    return Ports(
        net={port: net for port, (_, net) in named.items()},
        at=_at(named, where, {one.function: one for one in drawn}),
        also={key: frozenset(points) for key, points in also.items()},
        pages={function: tuple(sorted(pages)) for function, pages in where.items()},
    )


def _placements(placed: tuple[PlacedFunction, ...]) -> dict[Handle, dict[Page, PlacedFunction]]:
    """Each function's placement per page; a function placed twice on one page is a fault."""
    where: dict[Handle, dict[Page, PlacedFunction]] = defaultdict(dict)
    for one in placed:
        page = (one.drawing_set, one.page)
        if page in where[one.function]:
            msg = "one function is placed twice on one page"
            raise LayoutError(msg)
        where[one.function][page] = one
    return where


def _at(
    named: Mapping[Handle, tuple[Handle, Handle]],
    where: Mapping[Handle, Mapping[Page, PlacedFunction]],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> dict[tuple[Handle, Page], Point]:
    """The page position of each named port of a placed function."""
    at: dict[tuple[Handle, Page], Point] = {}
    for port in sorted(named):
        function = named[port][0]
        if function not in where:
            continue
        name = _symbol_port(port, drawn_of.get(function))
        for page, placement in where[function].items():
            symbol = next((one for one in placement.geometry.ports if one.name == name), None)
            if symbol is None:
                msg = "a drawn port is not a port of the symbol its function is placed with"
                raise LayoutError(msg)
            at[port, page] = port_page_at(placement.at, symbol)
    return at


def _also(
    connections: tuple[Connection, ...], where: Mapping[Handle, Mapping[Page, PlacedFunction]]
) -> dict[tuple[Handle, Page], set[Point]]:
    """Where each end with a `symbol_port` lands, per page (R7 B5)."""
    also: dict[tuple[Handle, Page], set[Point]] = defaultdict(set)
    for ref in (ref for one in connections for ref in (one.a, one.b) if ref.symbol_port):
        for page, placement in where.get(ref.function, {}).items():
            symbol = next(p for p in placement.geometry.ports if p.name == ref.symbol_port)
            also[ref.port, page].add(port_page_at(placement.at, symbol))
    return also


def _named(
    connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> dict[Handle, tuple[Handle, Handle]]:
    """Each named port with its function and physical net; a port named two ways is a fault."""
    found: dict[Handle, tuple[Handle, Handle]] = {}
    refs = [(ref, one.physical_net) for one in connections for ref in (one.a, one.b)]
    refs += [(ref, group.physical_net) for group in net_groups for ref in group.ports]
    for ref, net in refs:
        if found.setdefault(ref.port, (ref.function, net)) != (ref.function, net):
            msg = "one port is named with two different functions or physical nets"
            raise LayoutError(msg)
    return found


def _symbol_port(port: Handle, function: DrawnFunction | None) -> str:
    """The symbol port name `port` is drawn at; a function or port that is not drawn is a fault."""
    if function is None:
        msg = "an end function of a connection is placed but not among the drawn functions"
        raise LayoutError(msg)
    name = next((one.symbol_port for one in function.ports if one.port == port), None)
    if name is None:
        msg = "a port of a connection is not among its function's drawn ports"
        raise LayoutError(msg)
    return name
