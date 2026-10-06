"""The column pairs a D1 pole link joins, for `partition`'s group split (deep-dive D4).

A pole link is the connection `lint.chains` calls `CHAIN_BROKEN` when a marker pair cuts it: both
ends are pole ports (a function's symbol through path) on a net of exactly two ports. This is
the one home of `pole_ports` and `net_sizes`: `lint/chains.py` imports them from here, since a
stage may not import the lint layer.
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .lookups import nets_from_pairs

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey

    from .types import Column, Connection, DrawnFunction, Handle, NetGroup

_NET_OF_TWO = 2


def pole_links(
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
) -> tuple[tuple[AuthoringKey, AuthoringKey], ...]:
    """The sorted, unique pairs of distinct column keys a D1 pole link joins (no replica homes)."""
    poles = {one.function: pole_ports(one) for one in drawn}
    sizes = net_sizes(connections, net_groups)
    homes: defaultdict[Handle, list[AuthoringKey]] = defaultdict(list)
    for column in columns:
        for cell in column.cells:
            if not cell.replica:
                homes[cell.function].append(column.key)
    links: set[tuple[AuthoringKey, AuthoringKey]] = set()
    for one in connections:
        if (
            one.a.port in poles.get(one.a.function, frozenset())
            and one.b.port in poles.get(one.b.function, frozenset())
            and sizes[one.a.port] == _NET_OF_TWO
        ):
            links.update(
                (min(x, y), max(x, y))
                for x in homes.get(one.a.function, ())
                for y in homes.get(one.b.function, ())
                if x != y
            )
    return tuple(sorted(links))


def pole_ports(function: DrawnFunction) -> frozenset[Handle]:
    """The model ports on `function`'s symbol through path: D1's pole, empty without one."""
    through = function.geometry.through
    if through is None:
        return frozenset()
    poles = function.geometry.poles
    prefixes = [""] if poles <= 1 else [f"{n}." for n in range(1, poles + 1)]
    names = {f"{prefix}{end}" for prefix in prefixes for end in (through.start, through.end)}
    return frozenset(port.port for port in function.ports if port.symbol_port in names)


def net_sizes(
    connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> dict[Handle, int]:
    """The port count of the net each connected or grouped port is on (union-find)."""
    ends = [(one.a.port, one.b.port) for one in connections]
    for group in net_groups:
        ports = [end.port for end in group.ports]
        ends.extend(pairwise(ports))
    nets = nets_from_pairs(ends)
    return {port: len(ports) for ports in nets.groups().values() for port in ports}
