"""The overview's connections one by one, and the terminals that only pass a wire through (O3a).

`overview_graph` aggregates conductors into links; a folded level lifts them again, so it reads
them back one conductor (or mate) at a time. A terminal with exactly two plain wire ends, neither
on another strip, is a pass-through: the level draws one line between the far ends. Any other
terminal (bridged, three or more ends, wired to a strip) keeps its strip as a box.
"""

from typing import NamedTuple

from fransys_model.derive.facts.item_predicates import terminal_items
from fransys_model.derive.facts.units import unit_items
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.tables import conductors, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port, Unit

from .lookups import item_of_port
from .memo import Memo
from .overview import overview_graph
from .rows import OverviewLinkKind

__all__ = ["Conn", "Through", "connections", "split_through", "unit_connections"]

_PLAIN = frozenset({ConductorKind.WIRE, ConductorKind.CORE})
_ENDS = 2


class Conn(NamedTuple):
    """One connection: a conductor between two ports, or one mate (no ports).

    `wire` is true for a plain wire or cable core, false for a jumper, rail or mate.
    `via_text` is the carrier's printed designation, `None` for none.
    """

    a: Id[Item]
    a_port: Id[Port] | None
    b: Id[Item]
    b_port: Id[Port] | None
    kind: OverviewLinkKind
    via: Id[Item] | None
    via_text: str | None
    wire: bool


class Through(NamedTuple):
    """A pass-through terminal: its strip and the connection joining its two far ends."""

    terminal: Id[Item]
    strip: Id[Item]
    conn: Conn


@Memo
def connections(model: Model) -> tuple[Conn, ...]:
    """Every conductor and mate of the model as one `Conn`, in `overview_graph` link order."""
    found: list[Conn] = []
    for link in overview_graph(model).links:
        if not link.conductors:
            found += [
                Conn(link.a, None, link.b, None, link.kind, None, None, wire=False)
            ] * link.count
            continue
        for conductor in link.conductors:
            record = conductors(model)[conductor]
            a_first = item_of_port(model, record.a) == link.a
            ports = (record.a, record.b) if a_first else (record.b, record.a)
            found.append(
                Conn(
                    link.a,
                    ports[0],
                    link.b,
                    ports[1],
                    link.kind,
                    link.via,
                    link.via_designation,
                    wire=record.kind in _PLAIN,
                )
            )
    return tuple(found)


@Memo
def _conns_at(model: Model) -> dict[Id[Item], tuple[int, ...]]:
    """For each item, the positions in `connections(model)` of the connections it ends."""
    found: dict[Id[Item], list[int]] = {}
    for at, conn in enumerate(connections(model)):
        for end in {conn.a, conn.b}:
            found.setdefault(end, []).append(at)
    return {item: tuple(held) for item, held in found.items()}


@Memo
def unit_connections(model: Model, unit: Id[Unit]) -> tuple[Conn, ...]:
    """The connections ending in `unit` or a unit inside it, and all those at a terminal they reach.

    Whole terminals are kept, so `split_through` sees every wire of a terminal.
    """
    at, conns = _conns_at(model), connections(model)
    picked = {n for item in unit_items(model, unit) for n in at.get(item, ())}
    terminals = terminal_items(model)
    for n in tuple(picked):
        for end in {conns[n].a, conns[n].b} & terminals:
            picked.update(at[end])
    return tuple(conns[n] for n in sorted(picked))


def _far(conn: Conn, terminal: Id[Item]) -> tuple[Id[Item], Id[Port] | None, Conn]:
    """The end of `conn` away from `terminal`: its item, port and the conn itself."""
    return (conn.b, conn.b_port, conn) if conn.a == terminal else (conn.a, conn.a_port, conn)


def _joined(first: Conn, second: Conn, terminal: Id[Item]) -> Conn:
    """The conn between the far ends of two conns at `terminal`; a cable if either is one."""
    (a, a_port, one), (b, b_port, two) = sorted(
        (_far(first, terminal), _far(second, terminal)), key=lambda end: end[0]
    )
    carried = [c for c in (one, two) if c.via is not None]
    kind = OverviewLinkKind.CABLE if carried else OverviewLinkKind.WIRE
    via = carried[0] if carried else None
    return Conn(
        a,
        a_port,
        b,
        b_port,
        kind,
        None if via is None else via.via,
        None if via is None else via.via_text,
        wire=True,
    )


def split_through(
    model: Model, conns: tuple[Conn, ...]
) -> tuple[tuple[Conn, ...], tuple[Through, ...]]:
    """`conns` without those at a pass-through terminal, and one `Through` per such terminal.

    The terminals are in item order. A conn between two terminals never passes through.
    """
    terminals = terminal_items(model)
    at: dict[Id[Item], list[Conn]] = {}
    for conn in conns:
        for end in {conn.a, conn.b} & terminals:
            at.setdefault(end, []).append(conn)
    passing: dict[Id[Item], Through] = {}
    for terminal, held in sorted(at.items()):
        strip = items(model)[terminal].parent
        far = {_far(c, terminal)[0] for c in held}
        if len(held) == _ENDS and all(c.wire for c in held) and strip and not far & terminals:
            passing[terminal] = Through(terminal, strip, _joined(held[0], held[1], terminal))
    plain = tuple(c for c in conns if not ({c.a, c.b} & passing.keys()))
    return plain, tuple(passing.values())
