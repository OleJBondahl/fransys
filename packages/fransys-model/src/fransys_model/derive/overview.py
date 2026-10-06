"""The overview query: items, their connections and the signals between them.

See design/derive-queries-structure.md.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.tables import conductors, functions, items, mates, parts, ports
lazy from fransys_model.kernel import Model

from .closure import physical_nets
from .designation import designation_holder, own_designation_or_none, printed_designation
from .lookups import item_description, item_of_port, location_label, pin_order, terminal_items
from .natural_order import natural_key
from .rows import (
    OverviewGraph,
    OverviewLink,
    OverviewLinkKind,
    OverviewNode,
    OverviewPort,
    OverviewSignal,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Item

    type _Group = tuple[Id[Item], Id[Item], OverviewLinkKind, Id[Item] | None]


def _designation(model: Model, item: Item, terminals: frozenset[Id[Item]]) -> str | None:
    """`item`'s printed designation, `None` when it has none yet (a terminal always has one).

    It is `printed_designation`, so this graph names an item as a list does.
    An accessory prints its holder's text: `None` when that holder has none and is no terminal.
    """
    holder = designation_holder(model, item.id)
    if own_designation_or_none(model, items(model)[holder]) is None and holder not in terminals:
        return None
    return printed_designation(model, item.id)


def _nodes(model: Model) -> tuple[OverviewNode, ...]:
    terminals = terminal_items(model)
    all_parts = parts(model)
    nodes = [
        OverviewNode(
            item=item.id,
            designation=_designation(model, item, terminals),
            description=item_description(model, item.id),
            parent=item.parent,
            location_label=location_label(model, item.id),
            mpn=None if item.part is None else all_parts[item.part].mpn,
            installed=item.installed,
        )
        for item in items(model).values()
    ]
    return tuple(
        sorted(
            nodes,
            key=lambda node: (
                node.designation is None,
                natural_key(node.designation or ""),
                node.item,
            ),
        )
    )


def _links(model: Model) -> tuple[OverviewLink, ...]:
    terminals = terminal_items(model)
    all_items = items(model)
    wires: dict[_Group, list[Conductor]] = {}
    for conductor in conductors(model).values():
        first, second = sorted((item_of_port(model, conductor.a), item_of_port(model, conductor.b)))
        if first == second:
            continue
        kind = OverviewLinkKind.WIRE if conductor.carrier is None else OverviewLinkKind.CABLE
        wires.setdefault((first, second, kind, conductor.carrier), []).append(conductor)
    joined: dict[_Group, int] = {}
    for mate in mates(model).values():
        first, second = sorted((functions(model)[mate.a].item, functions(model)[mate.b].item))
        if first != second:
            key = (first, second, OverviewLinkKind.MATE, None)
            joined[key] = joined.get(key, 0) + 1
    links = [
        OverviewLink(
            a=a,
            b=b,
            kind=kind,
            via=via,
            via_designation=None if via is None else _designation(model, all_items[via], terminals),
            count=len(found),
            conductors=tuple(sorted(conductor.id for conductor in found)),
        )
        for (a, b, kind, via), found in wires.items()
    ] + [
        OverviewLink(
            a=a, b=b, kind=kind, via=None, via_designation=None, count=count, conductors=()
        )
        for (a, b, kind, _), count in joined.items()
    ]
    return tuple(
        sorted(
            links,
            key=lambda link: (link.a, link.b, link.kind.value, link.via is not None, link.via),
        )
    )


def _signals(model: Model) -> tuple[OverviewSignal, ...]:
    signals = []
    for net in physical_nets(model):
        found = sorted(
            (
                OverviewPort(
                    item=item_of_port(model, port), port=port, marking=ports(model)[port].name
                )
                for port in net.ports
            ),
            key=lambda one: (one.item, pin_order(one.marking, one.port)),
        )
        if len({one.item for one in found}) >= 2:  # noqa: PLR2004 -- a signal spans two items
            signals.append(OverviewSignal(ports=tuple(found)))
    return tuple(
        sorted(
            signals, key=lambda s: (s.ports[0].item, pin_order(s.ports[0].marking, s.ports[0].port))
        )
    )


def overview_graph(model: Model) -> OverviewGraph:
    """The overview: one node per item, the aggregated links between items, the multi-item signals.

    This query does not raise for an item with no designation yet: `OverviewNode.designation` (and a
    link's `via_designation`) is `None` there, so a half-finished design still draws. Other
    designations are `printed_designation` (`"-K1"`, `"-X1:L1:1"`). Nodes sort by `(designation with
    None last, id)`. A link joins two items by one kind and one `via`: `wire` for a conductor with
    no carrier, `cable` for the conductors of one cable item, `mate` for `Mate`s between functions
    of the two items (`count` is the number of mates, `conductors` empty). `a` is the smaller id;
    links sort by `(a, b, kind value, via)`, no `via` first. A signal is a physical net
    (`physical_nets`) that reaches at least two items, its ports sorted by `(item id, pin order,
    port id)`; signals sort by their first port.
    """
    return OverviewGraph(nodes=_nodes(model), links=_links(model), signals=_signals(model))
