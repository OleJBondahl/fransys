"""Tests for `overview_graph` (decision 0028)."""

from plant import Plant
from query_builders import (
    make_pin,
)

from fransys_model.derive import OverviewLinkKind, natural_key, overview_graph
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

_WIRE, _CABLE, _MATE = OverviewLinkKind.WIRE, OverviewLinkKind.CABLE, OverviewLinkKind.MATE


def _ids(*keys: str) -> list:
    return [make_id(Item, (key,)) for key in keys]


def test_a_and_b_are_stored_lower_designation_first_whichever_way_the_conductor_runs() -> None:
    """The unordered pair is one link: `x` to `y` and `y` to `x` aggregate together."""
    plant = Plant()
    x, y = make_pin(plant, "x", "X1"), make_pin(plant, "y", "Y1")
    plant.wire(x, y, key="forward")
    x2 = plant.port(plant.function_id("x", "f"), "2")
    y2 = plant.port(plant.function_id("y", "f"), "2")
    plant.wire(y2, x2, key="backward")
    (link,) = overview_graph(plant.model()).links
    assert link.count == 2
    assert (link.a, link.b) == tuple(_ids("x", "y"))  # X1 before Y1


def test_links_list_by_the_natural_designations_of_their_ends_not_item_id() -> None:
    """Twelve spokes on one hub: the links run `-X1`, `-X2`, ..., `-X12` by digit runs."""
    plant = Plant()
    hub = make_pin(plant, "hub", "A0")
    for n in range(1, 13):
        plant.wire(make_pin(plant, f"s{n}", f"X{n}"), hub, key=f"w{n}")
    graph = overview_graph(plant.model())
    label = {node.item: node.designation for node in graph.nodes}
    keys = [
        (natural_key(label[link.a] or ""), natural_key(label[link.b] or "")) for link in graph.links
    ]
    assert keys == sorted(keys)
    assert len(keys) == 12
