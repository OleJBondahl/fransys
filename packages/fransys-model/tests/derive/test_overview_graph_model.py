"""Tests for `overview_graph` (design/derive-queries-structure.md, decision 0028)."""

from connector_builders import make_connector
from plant import Plant
from query_builders import (
    make_core,
    make_node,
    make_part,
    make_pin,
    make_placement,
    reversed_tables,
)

from fransys_model.derive import OverviewLinkKind, overview_graph
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

_WIRE, _CABLE, _MATE = OverviewLinkKind.WIRE, OverviewLinkKind.CABLE, OverviewLinkKind.MATE


def _ids(*keys: str) -> list:
    return [make_id(Item, (key,)) for key in keys]


def test_an_empty_model_has_an_empty_graph() -> None:
    """Nothing to draw: three empty tuples."""
    graph = overview_graph(Plant().model())
    assert (graph.nodes, graph.links, graph.signals) == ((), (), ())


def test_there_is_one_node_per_item_with_its_facts() -> None:
    """Designation, description, parent, location label, MPN and the installed flag."""
    plant = Plant()
    parent = plant.item("cab", designation="A1")
    plant.item(
        "k1",
        parent=parent,
        part=make_part(plant, "relay", "MPN-R"),
        designation="K1",
        installed=False,
    )
    site = make_node("site", None)
    plant.add(site, make_placement("p", make_id(Item, ("k1",)), site.id))
    nodes = {node.item: node for node in overview_graph(plant.model()).nodes}
    k1 = nodes[make_id(Item, ("k1",))]
    assert (k1.designation, k1.description, k1.parent) == ("-K1", "Invented", parent)
    assert (k1.location_label, k1.mpn, k1.installed) == ("SITE", "MPN-R", False)
    cabinet = nodes[parent]
    assert (cabinet.parent, cabinet.location_label, cabinet.mpn, cabinet.installed) == (
        None,
        None,
        None,
        True,
    )


def test_an_unnumbered_item_is_a_node_with_no_designation_and_raises_nothing() -> None:
    """The one query that tolerates it: `None`, sorted after every numbered item."""
    plant = Plant()
    for key, designation in (("b", "B1"), ("bare-2", None), ("a", "A1"), ("bare-1", None)):
        plant.item(key, designation=designation)
    nodes = overview_graph(plant.model()).nodes
    assert [node.designation for node in nodes] == ["-A1", "-B1", None, None]
    assert [node.item for node in nodes[2:]] == sorted(_ids("bare-1", "bare-2"))


def test_nodes_are_sorted_by_designation_as_a_whole_string_then_id() -> None:
    """`-K10` before `-K2`; one designation twice falls to the item id."""
    plant = Plant()
    for key, designation in (("k2", "K2"), ("k10", "K10"), ("twin-b", "T"), ("twin-a", "T")):
        plant.item(key, designation=designation)
    nodes = overview_graph(plant.model()).nodes
    assert [node.designation for node in nodes] == ["-K10", "-K2", "-T", "-T"]
    assert [node.item for node in nodes[2:]] == sorted(_ids("twin-a", "twin-b"))


def test_an_accessory_node_reads_its_holders_designation() -> None:
    """A function-less link under the tagged holder `F11` is a node reading `-F11`, as the
    holder's node does.

    Fails on the base: the accessory has no designation of its own and the node says `None`.
    """
    plant = Plant()
    holder = plant.item("holder", part=make_part(plant, "h", "MPN-H"), designation="F11")
    link = plant.item("link", part=make_part(plant, "f", "MPN-F"), parent=holder)
    model, _ = number(plant.model())
    nodes = {node.item: node for node in overview_graph(model).nodes}
    assert nodes[holder].designation == "-F11"
    assert nodes[link].designation == "-F11"


def test_wires_between_two_items_are_one_link_with_their_count() -> None:
    """Two conductors without a carrier between one pair: one `wire` link, count 2."""
    plant = Plant()
    plant.item("x", designation="X1")
    plant.item("y", designation="Y1")
    fx, fy = plant.function(make_id(Item, ("x",)), "f"), plant.function(make_id(Item, ("y",)), "f")
    first = plant.wire(plant.port(fx, "1"), plant.port(fy, "1"), key="w1")
    second = plant.wire(plant.port(fy, "2"), plant.port(fx, "2"), key="w2")
    (link,) = overview_graph(plant.model()).links
    assert (link.kind, link.via, link.via_designation, link.count) == (_WIRE, None, None, 2)
    assert link.conductors == tuple(sorted((first, second)))
    assert (link.a, link.b) == tuple(sorted(_ids("x", "y")))


def test_a_and_b_are_stored_smaller_id_first_whichever_way_the_conductor_runs() -> None:
    """The unordered pair is one link: `x` to `y` and `y` to `x` aggregate together."""
    plant = Plant()
    x, y = make_pin(plant, "x", "X1"), make_pin(plant, "y", "Y1")
    plant.wire(x, y, key="forward")
    x2 = plant.port(plant.function_id("x", "f"), "2")
    y2 = plant.port(plant.function_id("y", "f"), "2")
    plant.wire(y2, x2, key="backward")
    (link,) = overview_graph(plant.model()).links
    assert link.count == 2
    assert link.a < link.b


def test_the_cores_of_one_cable_between_two_items_are_one_cable_link_via_the_cable() -> None:
    """Three cores of `W1` between `X1` and `Y1`: `cable`, `via` the cable, count 3."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    for index in (1, 2, 3):
        a = (
            make_pin(plant, f"x{index}", "X1")
            if index == 1
            else plant.port(plant.function_id("x1", "f"), str(index))
        )
        b = (
            make_pin(plant, f"y{index}", "Y1")
            if index == 1
            else plant.port(plant.function_id("y1", "f"), str(index))
        )
        make_core(plant, f"core-{index}", cable, (a, b), index=index)
    (link,) = overview_graph(plant.model()).links
    assert (link.kind, link.via, link.via_designation, link.count) == (_CABLE, cable, "-W1", 3)
    assert len(link.conductors) == 3


def test_two_cables_and_a_wire_between_one_pair_are_three_links() -> None:
    """Aggregation is per (pair, kind, via): each cable and the plain wire stay apart."""
    plant = Plant()
    w1, w2 = plant.item("w1", designation="W1"), plant.item("w2", designation="W2")
    x = [make_pin(plant, "x", "X1")] + [
        plant.port(plant.function_id("x", "f"), str(n)) for n in (2, 3)
    ]
    y = [make_pin(plant, "y", "Y1")] + [
        plant.port(plant.function_id("y", "f"), str(n)) for n in (2, 3)
    ]
    make_core(plant, "c1", w1, (x[0], y[0]), index=1)
    make_core(plant, "c2", w2, (x[1], y[1]), index=1)
    plant.wire(x[2], y[2], key="plain")
    links = overview_graph(plant.model()).links
    assert [(link.kind, link.via) for link in links] == sorted(
        [(_WIRE, None), (_CABLE, w1), (_CABLE, w2)],
        key=lambda pair: (pair[0].value, pair[1] is not None, pair[1]),
    )


def test_links_of_one_pair_are_sorted_by_the_kind_value() -> None:
    """`cable` before `wire`, whatever the authoring order (`via` breaks ties within a kind)."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    x = [make_pin(plant, "x", "X1")] + [
        plant.port(plant.function_id("x", "f"), str(n)) for n in (2, 3)
    ]
    y = [make_pin(plant, "y", "Y1")] + [
        plant.port(plant.function_id("y", "f"), str(n)) for n in (2, 3)
    ]
    plant.wire(x[0], y[0], key="plain")
    make_core(plant, "c1", cable, (x[1], y[1]), index=1)
    plant.wire(x[2], y[2], key="plain-2")
    links = overview_graph(plant.model()).links
    assert [link.kind.value for link in links] == ["cable", "wire"]


def test_mates_between_functions_of_two_items_are_one_mate_link_counted_by_mates() -> None:
    """Two mates between `H1` and `B1`: one `mate` link, count 2, no conductors."""
    plant = Plant()
    plant.item("h1", designation="H1")
    plant.item("b1", designation="B1")
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    p2, _ = make_connector(plant, ("h1", "P2"), ("1",))
    j1, _ = make_connector(plant, ("b1", "J1"), ("1",))
    j2, _ = make_connector(plant, ("b1", "J2"), ("1",))
    plant.mate(p1, j1, key="m1")
    plant.mate(p2, j2, key="m2")
    (link,) = overview_graph(plant.model()).links
    assert (link.kind, link.via, link.count, link.conductors) == (_MATE, None, 2, ())


def test_a_mate_inside_one_item_and_a_conductor_inside_one_item_give_no_link() -> None:
    """Self-connections are not links."""
    plant = Plant()
    plant.item("h1", designation="H1")
    p1, p1_ports = make_connector(plant, ("h1", "P1"), ("1", "2"))
    p2, _ = make_connector(plant, ("h1", "P2"), ("1",))
    plant.mate(p1, p2, key="self-mate")
    plant.wire(p1_ports["1"], p1_ports["2"], key="loop")
    assert overview_graph(plant.model()).links == ()


def test_a_cable_link_whose_cable_is_unnumbered_has_no_via_designation_and_raises_nothing() -> None:
    """The overview tolerates the half-finished design in `via_designation` too."""
    plant = Plant()
    cable = plant.item("w1", designation=None)
    make_core(plant, "c1", cable, (make_pin(plant, "x", "X1"), make_pin(plant, "y", "Y1")), index=1)
    (link,) = overview_graph(plant.model()).links
    assert (link.via, link.via_designation) == (cable, None)


def test_a_net_across_two_items_is_a_signal_with_ports_in_item_then_pin_order() -> None:
    """Ports `10` and `2` on one item come out `2, 10`; items in id order."""
    plant = Plant()
    x = plant.function(plant.item("x", designation="X1"), "f")
    y = plant.function(plant.item("y", designation="Y1"), "f")
    ports = [plant.port(x, "10"), plant.port(x, "2"), plant.port(y, "1")]
    plant.wire(ports[0], ports[2], key="a")
    plant.wire(ports[1], ports[2], key="b")
    (signal,) = overview_graph(plant.model()).signals
    items_in_order = [one.item for one in signal.ports]
    assert items_in_order == sorted(items_in_order)
    x_markings = [one.marking for one in signal.ports if one.item == make_id(Item, ("x",))]
    assert x_markings == ["2", "10"]
    assert {one.port for one in signal.ports} == set(ports)


def test_a_net_inside_one_item_is_not_a_signal() -> None:
    """Two ports of one item joined by a conductor span one item: no signal."""
    plant = Plant()
    f = plant.function(plant.item("x", designation="X1"), "f")
    plant.wire(plant.port(f, "1"), plant.port(f, "2"), key="loop")
    assert overview_graph(plant.model()).signals == ()


def test_an_unconnected_port_is_not_a_signal() -> None:
    """A net of one port spans one item."""
    plant = Plant()
    make_pin(plant, "x", "X1")
    assert overview_graph(plant.model()).signals == ()


def test_a_mated_pair_of_connectors_joins_into_a_signal() -> None:
    """Closure joins ports of equal name across a mate, so two items share a signal."""
    plant = Plant()
    plant.item("h1", designation="H1")
    plant.item("b1", designation="B1")
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    j1, _ = make_connector(plant, ("b1", "J1"), ("1",))
    plant.mate(p1, j1)
    (signal,) = overview_graph(plant.model()).signals
    assert {one.item for one in signal.ports} == set(_ids("h1", "b1"))


def test_signals_are_sorted_by_their_first_port() -> None:
    """Two nets authored in reverse: the one whose first port sorts first comes first."""
    plant = Plant()
    items = {key: plant.function(plant.item(key, designation=key.upper()), "f") for key in "abcd"}
    plant.wire(plant.port(items["c"], "1"), plant.port(items["d"], "1"), key="late")
    plant.wire(plant.port(items["a"], "1"), plant.port(items["b"], "1"), key="early")
    signals = overview_graph(plant.model()).signals
    firsts = [(signal.ports[0].item, signal.ports[0].marking) for signal in signals]
    assert firsts == sorted(firsts)
    assert len(signals) == 2


def test_signal_ports_tied_on_item_and_marking_sort_by_port_id() -> None:
    """Two ports of one item sharing a marking, in one signal: deterministic by port id."""
    plant = Plant()
    x_item = plant.item("x", designation="X1")
    fx1 = plant.function(x_item, "f1")
    fx2 = plant.function(x_item, "f2")
    fy = plant.function(plant.item("y", designation="Y1"), "f")
    px1 = plant.port(fx1, "1")
    px2 = plant.port(fx2, "1")
    py = plant.port(fy, "1")
    plant.wire(px1, py, key="w1")
    plant.wire(px2, py, key="w2")
    (signal,) = overview_graph(plant.model()).signals
    on_x = [one.port for one in signal.ports if one.item == x_item]
    assert len(on_x) == 2
    assert on_x == sorted(on_x)


def test_signals_tied_on_the_first_ports_item_and_marking_sort_by_the_first_ports_own_id() -> None:
    """Two signals whose leading `(item, marking)` tie: the tie breaks by that port's own id,
    never a mix of one signal's fields with the other's."""
    plant = Plant()
    # Names picked by trying candidates directly (ids are content-hashed and unpredictable by
    # name): "b"'s item id sorts below both "y1"'s and "y2"'s, so it leads both signals and the
    # two signals tie on (item, marking) -- and functions "p"/"q" give it a port whose raw id
    # order DISAGREES with the two nets' own processing order, so the final sort's port tiebreak
    # is load-bearing here, not masked by an accidental pre-sort.
    hub_item = plant.item("b", designation="B1")
    fa = plant.function(hub_item, "p")
    fb = plant.function(hub_item, "q")
    pa, pb = plant.port(fa, "1"), plant.port(fb, "1")
    fy1 = plant.function(plant.item("y1", designation="Y1"), "f")
    fy2 = plant.function(plant.item("y2", designation="Y1"), "f")
    # different from each other and from the hub's own "1", and set so a key built from the WRONG
    # port's marking (rather than the hub's) would sort these two signals in the OPPOSITE order
    # from the correct one (which sorts by the hub ports' own ids, pb before pa).
    py1, py2 = plant.port(fy1, "1"), plant.port(fy2, "9")
    plant.wire(pa, py1, key="s1")
    plant.wire(pb, py2, key="s2")

    signals = overview_graph(plant.model()).signals
    assert len(signals) == 2
    firsts = [signal.ports[0] for signal in signals]
    # examined: both signals' leading port is the hub's, tied on (item, marking)
    assert {one.item for one in firsts} == {hub_item}
    assert {one.marking for one in firsts} == {"1"}
    assert [one.port for one in firsts] == sorted(one.port for one in firsts)


def test_the_graph_does_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same graph."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    x, y = make_pin(plant, "x", "X1"), make_pin(plant, "y", None)
    make_core(plant, "c1", cable, (x, y), index=1)
    plant.item("h1", designation="H1")
    plant.item("b1", designation="B1")
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    j1, _ = make_connector(plant, ("b1", "J1"), ("1",))
    plant.mate(p1, j1)
    model = plant.model()
    assert overview_graph(reversed_tables(model)) == overview_graph(model)
