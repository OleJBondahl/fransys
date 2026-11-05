"""A reference marker joins the drawn wire whose end lies at its port point and nothing wider (R882).

The leg of a one-sided pin ends at the marker's point; a leg ending one grid off joins nothing.
"""

from types import SimpleNamespace
from typing import Any

from fransys_el.drawn_netlist import PagePart, _marker_nodes

from fransys_layout.core import page_graph


def _marker_at(x: int, y: int) -> SimpleNamespace:
    return SimpleNamespace(id="m:k", ports=("p",), net="n", key="marker", x=x, y=y)


def _node_of_marker(leg_end: tuple[int, int]) -> Any:
    wires = [((0, 0), (80, 0)), ((80, 0), leg_end)]  # the lane, then the leg off its end
    graph = page_graph(wires, set(), ())
    nodes = frozenset(p for edge in graph.edges for p in edge)
    drawing: Any = SimpleNamespace(symbols=[_marker_at(80, 8)])  # the one field `_marker_nodes` reads
    pages: Any = {"page": PagePart(drawing, {}, graph, nodes, frozenset())}
    return _marker_nodes(pages)["k"]


def test_the_marker_joins_a_leg_that_ends_at_its_point() -> None:
    assert _node_of_marker((80, 8)) == ("page", (80, 8))


def test_a_leg_ending_one_grid_off_the_marker_does_not_join_it() -> None:
    assert _node_of_marker((80, 16)) is None
