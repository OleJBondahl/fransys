"""The series-parallel reduction of one region: merge parallel edges, contract series nodes (SP2).

An edge runs from node `u` to node `v` and carries a part. `SOURCE` and `SINK` are the region's
two ends; every other node is an int. The reduction repeats until nothing changes.
"""

from collections import defaultdict

from fransys_model.derive.order import series_part_key
from fransys_model.derive.rows_series_parallel import ParallelRow, SeriesRow, SeriesRowPart

__all__ = ["SINK", "SOURCE", "Edge", "reduce_region"]

SOURCE = -1
SINK = -2
type Edge = tuple[int, int, SeriesRowPart]


def reduce_region(edges: list[Edge]) -> SeriesRowPart | None:
    """The one part from `SOURCE` to `SINK` the edges reduce to, else `None` (a bridge)."""
    while True:
        merged = _merge_parallel(edges)
        joined = _contract_one(merged)
        if joined is None:
            break
        edges = joined
    if len(merged) == 1 and merged[0][:2] == (SOURCE, SINK):
        return merged[0][2]
    return None


def _flat(parts: list[SeriesRowPart], kind: type[SeriesRow | ParallelRow]) -> list[SeriesRowPart]:
    """The parts with each part of the same kind opened into its own parts."""
    out: list[SeriesRowPart] = []
    for part in parts:
        out.extend(part.parts if isinstance(part, kind) else (part,))
    return out


def _merge_parallel(edges: list[Edge]) -> list[Edge]:
    """Edges with the same two nodes in the same direction become one parallel, at the first."""
    groups: dict[tuple[int, int], list[SeriesRowPart]] = defaultdict(list)
    for u, v, part in edges:
        groups[u, v].append(part)
    out: list[Edge] = []
    for (u, v), parts in groups.items():
        if len(parts) == 1:
            out.append((u, v, parts[0]))
        else:
            flat = sorted(_flat(parts, ParallelRow), key=series_part_key)
            out.append((u, v, ParallelRow(parts=tuple(flat))))
    return out


def _contract_one(edges: list[Edge]) -> list[Edge] | None:
    """The first inner node with one edge in and another out contracted to a series, else None."""
    ins: dict[int, list[int]] = defaultdict(list)
    outs: dict[int, list[int]] = defaultdict(list)
    for i, (u, v, _) in enumerate(edges):
        outs[u].append(i)
        ins[v].append(i)
    for node, into in ins.items():
        if node >= 0 and len(into) == 1 and len(outs[node]) == 1:
            first, then = into[0], outs[node][0]
            if first != then:
                return _joined(edges, first, then)
    return None


def _joined(edges: list[Edge], first: int, then: int) -> list[Edge]:
    """`edges` with `first` and `then` replaced, at `first`'s place, by their series."""
    u, _, a = edges[first]
    _, v, b = edges[then]
    series = SeriesRow(parts=tuple(_flat([a, b], SeriesRow)))
    return [(u, v, series) if i == first else e for i, e in enumerate(edges) if i != then]
