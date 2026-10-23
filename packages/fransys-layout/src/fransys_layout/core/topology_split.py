"""Stage 1, y cycle split: the y graph of a flow, the nets to cross-link, the fans left over.

Stage 5 holds each lane's cells in order and each fan's drivers above its legs. A cell standing
twice in one column (a symbol dealt into two lanes, a folded member's join) is one node. A ring
through those is unsolvable, so the nets that close it leave their fans and become cross links.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .errors import CoreError
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
type Boxes = dict[str, str]


def _box_end(col: Column) -> tuple[str, str] | None:
    """The box and the node of the cell a column's first box-pin end stands on (stage 5 attach)."""
    for li, end in enumerate(col.heads):
        if end.kind == "boxpin" and end.pin is not None:
            return end.pin.sym, f"{col.id}:{li}:0"
    for li, end in enumerate(col.feet):
        if end.kind == "boxpin" and end.pin is not None:
            return end.pin.sym, f"{col.id}:{li}:{len(col.lanes[li % len(col.lanes)].cells) - 1}"
    return None


def _column_nodes(col: Column, uf: UnionFind) -> Nodes:
    """Name the cells of one column; a symbol in two lanes and a head join are one node."""
    first: dict[str, str] = {}
    ids: Nodes = {}
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
    return ids


def _nodes(columns: Sequence[Column]) -> tuple[Nodes, Boxes]:
    """The y node of every cell and every box: a symbol in two lanes, a join, or a box is one."""
    uf, ids = UnionFind(), {}
    for col in columns:
        ids.update(_column_nodes(col, uf))
    boxes: Boxes = {}
    for col in columns:
        if (at := _box_end(col)) is not None:
            uf.union(f"box:{at[0]}", at[1])
            boxes[at[0]] = f"box:{at[0]}"
    return {k: uf.find(n)[0] for k, n in ids.items()}, {b: uf.find(n)[0] for b, n in boxes.items()}


def net_in(fan: Fan, pin: PinRef, net_of: NetOf) -> str:
    """The net of a fan's attachment: the fan's one net, else the net of the pin (a bundle)."""
    return fan.nets[0] if len(fan.nets) == 1 else net_of[pin]


class BundleError(CoreError):
    """A bundle fan cannot be split: a driver and a leg stand on one node, or a member is cut."""


def _end_node(a: Attach, nodes: tuple[Nodes, Boxes]) -> str:
    """The y node an attachment stands on: its cell, or its box."""
    cells, boxes = nodes
    if a.column is not None:
        return cells[a.column, a.lane, a.cell]
    return boxes.get(a.pin.sym, f"box:{a.pin.sym}")


def bundle_conflicts(
    columns: Sequence[Column], fans: Sequence[Fan]
) -> list[tuple[Fan, tuple[str, ...], tuple[Attach, ...]]]:
    """Each bundle whose driver and leg stand on one y node: the bundle, the nodes, the drivers."""
    nodes = _nodes(columns)
    out = []
    for fan in (f for f in fans if f.lanes > 1):
        legs = {_end_node(a, nodes) for a in fan.legs}
        hit = [(a, n) for a in fan.drivers if (n := _end_node(a, nodes)) in legs]
        if hit:
            out.append((fan, tuple(dict.fromkeys(n for _, n in hit)), tuple(a for a, _ in hit)))
    return out


def check_bundles(columns: Sequence[Column], fans: Sequence[Fan]) -> None:
    """Raise BundleError when a bundle's driver and leg stand on one node: no stack can seat it."""
    for fan, both, _ in bundle_conflicts(columns, fans):
        text = (
            f"bundle {fan.id} (nets {', '.join(fan.nets)}) has a driver and a leg on one "
            f"node ({', '.join(both)}): give the node's pins one "
            "side, or draw the bundle's nets apart"
        )
        raise BundleError(text)


def _fan_edges(fan: Fan, nodes: tuple[Nodes, Boxes], net_of: NetOf | None) -> set[Edge]:
    """Each driver above each leg; a box pin stands on its box's node; gone once a net is cut."""
    ends = [
        [
            (_end_node(a, nodes), None if net_of is None else net_in(fan, a.pin, net_of))
            for a in side
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
    cells = nodes[0]
    out: set[Edge] = set()
    for col in columns:
        for li, lane in enumerate(col.lanes):
            out.update(
                (cells[col.id, li, i - 1], cells[col.id, li, i], frozenset())
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
    check_bundles(columns, fans)
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
    if fan.lanes > 1:
        text = (
            f"stage 1 cut net {next(n for n in fan.nets if n in cuts)} out of bundle {fan.id}: "
            "a bundle lane is its net's place, so a member cannot leave; report the circuit"
        )
        raise BundleError(text)
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


def split_conflict_ends(
    columns: Sequence[Column], fans: Sequence[Fan], cross: Sequence[CrossLink]
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...]]:
    """A fan's legs on a node its drivers stand on leave it, each a cross link to a driver (R418).

    Only those ends conflict; the rest keeps the fan and its trunk. A fan left with no leg, or
    a bundle, stays whole for the net cut.
    """
    nodes = _nodes(columns)
    kept: list[Fan] = []
    links = list(cross)
    for fan in fans:
        above = {_end_node(a, nodes) for a in fan.drivers}
        out = [a for a in fan.legs if _end_node(a, nodes) in above]
        legs = tuple(a for a in fan.legs if a not in out)
        free = [a for a in fan.drivers if _end_node(a, nodes) not in _nodes_of(out, nodes)]
        if not out or not legs or fan.lanes > 1 or not free:
            kept.append(fan)
            continue
        kept.append(replace(fan, legs=legs))
        links.extend(CrossLink(fan.nets[0], (a, free[0])) for a in out)
    return tuple(kept), tuple(links)


def _nodes_of(ends: Sequence[Attach], nodes: tuple[Nodes, Boxes]) -> set[str]:
    return {_end_node(a, nodes) for a in ends}
