"""A chain stood beside a host (layout-0174): which way its column reads."""

from dataclasses import replace
from typing import TYPE_CHECKING

from .types import Home

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import Chain, ChainEntry, Column, DrawnFunction, FunctionSpec, Handle

_TWO = 2  # a chain has a first and a last end only from two functions
type _Steps = Sequence[tuple[ChainEntry, FunctionSpec]]


def read_down(
    chain: Chain,
    steps: _Steps,
    specs: Mapping[Handle, FunctionSpec],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> list[tuple[ChainEntry, FunctionSpec]]:
    """The steps top to bottom: the end on the host's upper net first, the chain's own order else.

    Each step keeps its function and takes the index of the place it now stands at.
    """
    host = None if chain.beside is None else specs.get(chain.beside)
    drawing = None if chain.beside is None else drawn_of.get(chain.beside)
    if host is None or drawing is None or not _upside_down(steps, host, drawing):
        return list(steps)
    places = [entry.index for entry, _ in steps]
    return [
        (replace(entry, index=place), spec)
        for place, (entry, spec) in zip(places, reversed(steps), strict=True)
    ]


def _end_nets(steps: _Steps, at: int, neighbour: int) -> frozenset[Handle]:
    """The nets of the function at `at` that its neighbour in the chain does not touch."""
    own = {port.physical_net for port in steps[at][1].ports}
    return frozenset(own - {port.physical_net for port in steps[neighbour][1].ports})


def _top(host: FunctionSpec, drawing: DrawnFunction, nets: frozenset[Handle]) -> int | None:
    """The drawn height of the host's highest port on one of `nets`, `None` when it has none."""
    symbol_port = {port.port: port.symbol_port for port in drawing.ports}
    at = {port.name: port.at.y for port in drawing.geometry.ports}
    found = [
        at[symbol_port[port.port]]
        for port in host.ports
        if port.physical_net in nets and symbol_port.get(port.port) in at
    ]
    return min(found, default=None)


def _upside_down(steps: _Steps, host: FunctionSpec, drawing: DrawnFunction) -> bool:
    """Whether the chain's last end reads first: on the host's upper net, or alone on the host."""
    if len(steps) < _TWO:
        return False
    first = _top(host, drawing, _end_nets(steps, 0, 1))
    last = _top(host, drawing, _end_nets(steps, -1, -2))
    if last is None:
        return False
    return first is None or first > last


def beside_hosts(columns: Sequence[Column]) -> dict[AuthoringKey, AuthoringKey]:
    """Each beside column's key with the key of the column its host stands in."""
    homes = {
        cell.function: column.key
        for column in columns
        for cell in column.cells
        if cell.home is not Home.ELSEWHERE
    }
    return {
        column.key: homes[column.beside]
        for column in columns
        if column.beside in homes and homes[column.beside] != column.key
    }


def beside_links(columns: Sequence[Column]) -> set[tuple[AuthoringKey, AuthoringKey]]:
    """The pairs of a beside column and its host's, as `partition` keeps them together."""
    return {(min(key, host), max(key, host)) for key, host in beside_hosts(columns).items()}


def beside_cells(columns: Sequence[Column]) -> frozenset[Handle]:
    """The functions standing in a beside column."""
    return frozenset(cell.function for column in columns if column.beside for cell in column.cells)
