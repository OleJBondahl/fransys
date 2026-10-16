"""Stage 1, y cycle split: the y graph of a flow, the nets to cross-link, the fans left over.

Stage 5 holds each lane's cells in order and each fan's drivers above its legs. A cell standing
twice in one column (a symbol dealt into two lanes, a folded member's join) is one node. A ring
through those is unsolvable, so the nets that close it leave their fans and become cross links.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .keys import natural_key
from .topology_cycles import cyclic_parts, y_cycle_cuts
from .unionfind import UnionFind
from .values import Attach, CrossLink, Fan

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .topology_cycles import Edge
    from .values import Column, PinRef

type NetOf = Mapping[PinRef, str]
type Nodes = dict[tuple[str, int, int], str]


def _nodes(columns: Sequence[Column]) -> Nodes:
    """The y node of every cell: a symbol standing in two lanes, or joined at a head, is one."""
    uf, ids = UnionFind(), {}
    for col in columns:
        first: dict[str, str] = {}
        for li, lane in enumerate(col.lanes):
            for i, cell in enumerate(lane.cells):
                ids[col.id, li, i] = node = f"{col.id}:{li}:{i}"
                uf.find(node)
                if cell.sym in first:
                    uf.union(first[cell.sym], node)
                first.setdefault(cell.sym, node)
        for li, end in enumerate(col.heads):
            if end.is_join and end.pin is not None:
                uf.union(first[end.pin.sym], f"{col.id}:{li}:0")
    return {k: uf.find(n)[0] for k, n in ids.items()}


def net_in(fan: Fan, pin: PinRef, net_of: NetOf) -> str:
    """The net of a fan's attachment: the fan's one net, else the net of the pin (a bundle)."""
    return fan.nets[0] if len(fan.nets) == 1 else net_of[pin]


def _fan_edges(fan: Fan, nodes: Nodes, net_of: NetOf | None) -> set[Edge]:
    """Each driver above each leg; the edge is gone once the net of either is cut."""
    ends = [
        [
            (
                nodes[a.column, a.lane, a.cell],
                None if net_of is None else net_in(fan, a.pin, net_of),
            )
            for a in side
            if a.column is not None
        ]
        for side in (fan.drivers, fan.legs)
    ]
    return {
        (a, b, frozenset(o for o in (oa, ob) if o is not None))
        for a, oa in ends[0]
        for b, ob in ends[1]
    }


def y_edges(columns: Sequence[Column], fans: Sequence[Fan], net_of: NetOf | None) -> list[Edge]:
    """Stack edges (fixed, head above foot) and fan edges (owned by their nets)."""
    nodes = _nodes(columns)
    out: set[Edge] = set()
    for col in columns:
        for li, lane in enumerate(col.lanes):
            out.update(
                (nodes[col.id, li, i - 1], nodes[col.id, li, i], frozenset())
                for i in range(1, len(lane.cells))
            )
    for fan in fans:
        out |= _fan_edges(fan, nodes, net_of)
    return sorted(out, key=lambda e: (e[0], e[1], sorted(e[2])))


def y_cycles(columns: Sequence[Column], fans: Sequence[Fan]) -> list[frozenset[str]]:
    """The one test for a y cycle: the cell nodes of every ring; empty when stage 5 can solve."""
    edges = y_edges(columns, fans, None)
    return cyclic_parts([(a, b) for a, b, _ in edges])


def check_acyclic(columns: Sequence[Column], fans: Sequence[Fan]) -> None:
    """Raise when a y cycle is left after the split: the finder missed a ring."""
    rings = y_cycles(columns, fans)
    if rings:
        where = sorted({n.split(":")[0] for ring in rings for n in ring}, key=natural_key)
        text = (
            f"stage 1 left a y cycle through columns {', '.join(where)}: "
            "the cycle finder missed a ring, report it"
        )
        raise ValueError(text)


def cut_nets(
    columns: Sequence[Column], fans: Sequence[Fan], net_of: Mapping[PinRef, str]
) -> frozenset[str]:
    """The nets to take out of their fans: the fewest drivers lost, ties by natural key."""
    edges = y_edges(columns, fans, net_of)
    cost: dict[str, int] = defaultdict(int)
    for fan in fans:
        for a in fan.drivers:
            cost[net_in(fan, a.pin, net_of)] += 1
    return y_cycle_cuts(edges, cost, natural_key)


def _ends_of(fan: Fan, net: str, net_of: NetOf) -> tuple[Attach, ...]:
    return tuple(
        dict.fromkeys(a for a in (*fan.drivers, *fan.legs) if net_in(fan, a.pin, net_of) == net)
    )


def _split_fan(
    fan: Fan, cuts: AbstractSet[str], net_of: Mapping[PinRef, str]
) -> tuple[Fan | None, dict[str, tuple[Attach, ...]]]:
    """The fan without its cut nets (None when a side is empty) and the ends each net takes."""
    rest = tuple(n for n in fan.nets if n not in cuts)
    if len(rest) == len(fan.nets):
        return fan, {}
    drivers = tuple(a for a in fan.drivers if net_in(fan, a.pin, net_of) in rest)
    legs = tuple(a for a in fan.legs if net_in(fan, a.pin, net_of) in rest)
    if not drivers or not legs:
        return None, {n: _ends_of(fan, n, net_of) for n in fan.nets}
    hub = fan.hub if any(a.pin.sym == fan.hub for a in (*drivers, *legs)) else None
    kept = replace(fan, nets=rest, drivers=drivers, legs=legs, hub=hub)
    return kept, {n: _ends_of(fan, n, net_of) for n in fan.nets if n in cuts}


def split_fans(
    fans: Sequence[Fan],
    cross: Sequence[CrossLink],
    cuts: AbstractSet[str],
    net_of: Mapping[PinRef, str],
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...]]:
    """Fans without the cut nets, and the cross links with one more per cut net."""
    kept: list[Fan] = []
    links = list(cross)
    for fan in fans:
        one, moved = _split_fan(fan, cuts, net_of)
        if one is not None:
            kept.append(one)
        links.extend(CrossLink(net, ends) for net, ends in moved.items())
    return tuple(kept), tuple(sorted(links, key=lambda c: natural_key(c.net)))
