"""The series-parallel structure of the drawn wiring, one tree per region (SERIES-PARALLEL SP1).

A symbol is an edge from its input end (its N pins) to its output end (its S pins). The nets of
one end join it to every end they meet, as one node. Rails, open ends and hubs end a region.
"""

lazy from collections.abc import Mapping, Sequence

from fransys_model.derive.facts.closure import physical_nets
from fransys_model.derive.order import series_part_key
from fransys_model.derive.rows_series_parallel import SeriesParallel, SeriesRow
from fransys_model.derive.series_parallel_reduce import SINK, SOURCE, reduce_region
from fransys_model.derive.stands import stands
from fransys_model.layout import Side
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["series_parallel"]

type End = tuple[str, Side]
type Ends = Mapping[Id[Port], End]
type Net = tuple[Id[Port], ...]
type Leg = tuple[str, int, int]
type Raw = tuple[str, int | None, int | None]
_HUB = 2  # a symbol wired by more pin groups than its two ends is a hub (SP1)
_FLOW = (Side.N, Side.S)


def series_parallel(model: Model, ends: Ends) -> SeriesParallel:
    """Each region's series in signal direction, and the symbols of each region that is no tree.

    `ends` maps each drawn port to its symbol key and the side it leaves by: N is the input end,
    S the output end, E and W neither. A net on a rail joins nothing. A symbol whose wired pins
    span more than two functions is a hub: it ends a region and is in none. An end on a rail, on
    no wire or on a hub, and a node no symbol enters or leaves, is the region's source or sink.
    """
    nets = _wiring(model, ends)
    hubs = _hubs(model, ends, nets)
    regions: list[SeriesRow] = []
    bridges: list[tuple[str, ...]] = []
    for group in _regions(_raw(*_nodes(ends, nets, hubs))):
        legs = _legs(group)
        part = reduce_region([(u, v, leaf) for leaf, u, v in legs])
        if part is None:
            bridges.append(tuple(leaf for leaf, _, _ in legs))
        else:
            regions.append(part if isinstance(part, SeriesRow) else SeriesRow(parts=(part,)))
    return SeriesParallel(regions=tuple(regions), bridges=tuple(bridges))


def _wiring(model: Model, ends: Ends) -> list[Net]:
    """The drawn ports of each net that joins two symbols or more; a net in `stands` is a rail."""
    rail = stands(model)
    out: list[Net] = []
    for net in physical_nets(model):
        drawn = tuple(p for p in net.ports if p in ends)
        joins = len({ends[p][0] for p in drawn}) > 1
        if joins and not any(p in rail for p in net.ports):
            out.append(drawn)
    return out


def _hubs(model: Model, ends: Ends, nets: Sequence[Net]) -> frozenset[str]:
    """The symbols whose wired ports belong to more than two functions."""
    table = ports(model)
    groups: dict[str, set[object]] = {}
    for net in nets:
        for port in net:
            groups.setdefault(ends[port][0], set()).add(table[port].function)
    return frozenset(leaf for leaf, found in groups.items() if len(found) > _HUB)


def _root[T](parent: dict[T, T], x: T) -> T:
    while parent.get(x, x) != x:
        x = parent[x]
    return x


def _nodes(
    ends: Ends, nets: Sequence[Net], hubs: frozenset[str]
) -> tuple[dict[End, int], set[int]]:
    """Each wired end of a symbol that is no hub to its node, and the nodes that meet a hub."""
    parent: dict[End, End] = {}
    met: list[tuple[list[End], bool]] = []
    for net in nets:
        flow = list(dict.fromkeys(ends[p] for p in net if _flows(ends[p], hubs)))
        met.append((flow, any(ends[p][0] in hubs for p in net)))
        for end in flow[1:]:
            parent[_root(parent, end)] = _root(parent, flow[0])
    return _labelled(parent, met)


def _labelled(
    parent: dict[End, End], met: Sequence[tuple[list[End], bool]]
) -> tuple[dict[End, int], set[int]]:
    """Each end's node number, first met first, and the nodes on a net that meets a hub."""
    label: dict[End, int] = {}
    node: dict[End, int] = {}
    stops: set[int] = set()
    for flow, at_hub in met:
        for end in flow:
            node[end] = label.setdefault(_root(parent, end), len(label))
        if at_hub and flow:
            stops.add(node[flow[0]])
    return node, stops


def _flows(end: End, hubs: frozenset[str]) -> bool:
    return end[0] not in hubs and end[1] in _FLOW


def _raw(node: Mapping[End, int], stops: set[int]) -> list[Raw]:
    """Each symbol from its input node to its output node; an end on a hub or none is None."""
    raw: list[Raw] = []
    for leaf in sorted({end[0] for end in node}, key=series_part_key):
        u, v = node.get((leaf, Side.N)), node.get((leaf, Side.S))
        if u != v:
            raw.append((leaf, None if u in stops else u, None if v in stops else v))
    return raw


def _regions(raw: Sequence[Raw]) -> list[list[Raw]]:
    """The symbols joined by a node, a region of two symbols or more each, by first symbol."""
    parent: dict[int, int] = {}
    for _, u, v in raw:
        if u is not None and v is not None:
            parent[_root(parent, u)] = _root(parent, v)
    groups: dict[object, list[Raw]] = {}
    for leaf, u, v in raw:
        end = u if u is not None else v
        key = leaf if end is None else _root(parent, end)
        groups.setdefault(key, []).append((leaf, u, v))
    return [g for g in groups.values() if len(g) > 1]


def _legs(raw: Sequence[Raw]) -> list[Leg]:
    """Each symbol of one region as an edge; a node no symbol enters or leaves is SOURCE or SINK."""
    into = {v for _, _, v in raw}
    out_of = {u for _, u, _ in raw}
    return [
        (
            leaf,
            SOURCE if u is None or u not in into else u,
            SINK if v is None or v not in out_of else v,
        )
        for leaf, u, v in raw
    ]
