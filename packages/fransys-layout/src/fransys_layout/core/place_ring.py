"""Stage 5, y: name the symbols of a y ring, for the error a cyclic page raises (layout-0327)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .node_names import BOX
from .pack import cell_node
from .topology_cycles import cyclic_parts

if TYPE_CHECKING:
    from .constraints import Graph
    from .place_env import PageEnv


def _nodes(env: PageEnv, g: Graph) -> list[tuple[str, str]]:
    """Every cell node of the page with its symbol, then each box node an edge names."""
    out = [
        (cell_node(pc.id, li, i), cell.sym)
        for pc in env.pcs.values()
        for li, cells in enumerate(pc.lanes)
        for i, cell in enumerate(cells)
    ]
    ends = (n for a, b, _ in g.edges for n in (a, b) if n.startswith(BOX))
    return [*out, *((n, n[len(BOX) :]) for n in ends)]


def ring_symbols(env: PageEnv, g: Graph) -> tuple[str, ...]:
    """The symbols (their problem keys) on any ring of `g`, in page order."""
    roots = {n: g.uf.find(n) for n in g.nodes}
    tight = {
        roots[a][0]
        for a, b, d in g.edges
        if roots[a][0] == roots[b][0] and roots[b][1] - roots[a][1] < d
    }
    parts = cyclic_parts([(roots[a][0], roots[b][0]) for a, b, _ in g.edges])
    ring = tight.union(*parts)
    return tuple(dict.fromkeys(sym for node, sym in _nodes(env, g) if roots[node][0] in ring))
