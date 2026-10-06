"""D4, S15: a declared net whose ports stand in two locations ends in stubs, as a conductor does.

`stages/offstubs.py::groups_by_location` splits a `NetGroup` into its location parts by
`ends_in_stubs`; a part of two or more ports stays a group, and consecutive parts are joined by
one stub pair between their lowest-handle ports (`read/offstubs.py::off_texts` names each end).
The model is hand-built: items in `+ER+C1` and `+AR+C1`, two locations with no common ancestor,
and one declared `Net` over one port of each (the fixture of the root
`test_marker_text_agrees_across_nested_locations.py`, rewritten in step 5's Part 5 to assert a
stub label at each end and no `#` reference).

Can-fail, checked by probe: with `groups_by_location` returning the groups unsplit and no join,
the two-location net is a plain marker pair again and the first test fails. With
`lint/coherence.py` keying its claim map `{one.net: one}` again (before `_by_net`), the 2+2
test sees `ROUTE_WRONG_PORT` and `CONNECTION_NOT_DRAWN`: one part hid the other's route.
"""

from fransys_layout.engines import lay_out_schematic
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN, FUNCTION_UNPLACED_IN_COLUMN
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import LinkMarker, Route, StarKind, layout_of
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Placement,
    Port,
    PortRole,
)

_ORIGIN = Origin(file="tests/engines/test_net_group_stubs.py", line=1, note="D4")
# the INFO each lone connector carries in any layout of this fixture: no chain claims it
_LONE_CONNECTORS = [FUNCTION_UNPLACED_IN_COLUMN]


def _node(key: tuple[str, ...], label: str, aspect: Aspect, parent: AspectNode | None):
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=aspect,
        parent=None if parent is None else parent.id,
        label=label,
        description=f"invented {label}",
    )


def _item_at(tag: str, group: AspectNode, location: AspectNode) -> tuple:
    """A one-port connector item `tag` placed at `group` and `location`: its records, its port."""
    item = Item(
        id=make_id(Item, ("probe", tag)),
        key=("probe", tag),
        part=None,
        parent=None,
        position=None,
        tag=tag,
        description=f"invented {tag}",
    )
    function = Function(
        id=make_id(Function, (*item.key, "fn")),
        key=(*item.key, "fn"),
        item=item.id,
        template=None,
        name="fn",
        kind=FunctionKind.CONNECTOR,
    )
    port = Port(
        id=make_id(Port, (*function.key, "1")),
        key=(*function.key, "1"),
        function=function.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    placements = tuple(
        Placement(
            id=make_id(Placement, (*item.key, "at", *node.key)),
            key=(*item.key, "at", *node.key),
            item=item.id,
            node=node.id,
        )
        for node in (group, location)
    )
    return (item, function, port, *placements), port


def _laid_out(at: dict[str, str]):
    """Items `tag -> "ER" | "AR"` (each location's child `C1`), one net `S` over their ports.

    Returns the laid-out model, its findings and each tag's port id.
    """
    er = _node(("probe", "er"), "ER", Aspect.LOCATION, None)
    ar = _node(("probe", "ar"), "AR", Aspect.LOCATION, None)
    leaf = {
        "ER": _node(("probe", "er", "c1"), "C1", Aspect.LOCATION, er),
        "AR": _node(("probe", "ar", "c1"), "C1", Aspect.LOCATION, ar),
    }
    group = _node(("probe", "grp"), "G", Aspect.FUNCTION, None)
    records, port_of = [er, ar, *leaf.values(), group], {}
    for tag, location in at.items():
        found, port = _item_at(tag, group, leaf[location])
        records.extend(found)
        port_of[tag] = port.id
    net = Net(
        id=make_id(Net, ("probe", "net")),
        key=("probe", "net"),
        name="S",
        net_class=NetClass.CONTROL,
        ports=tuple(port_of.values()),
    )
    draft = Draft()
    draft.extend((*records, net), origin=_ORIGIN)
    written, findings = lay_out_schematic(freeze(draft))
    return written, findings, port_of


def test_a_net_across_two_locations_ends_in_a_stub_at_each_port() -> None:
    """Two ports, one per location: an off stub at each, no reference, branch or severed pair."""
    written, findings, port_of = _laid_out({"p1": "ER", "p2": "AR"})
    markers = layout_of(written, LinkMarker).values()
    assert sorted(m.port for m in markers) == sorted(port_of.values())
    assert all(m.star is StarKind.OFF for m in markers), [m.star for m in markers]
    assert {m.far for m in markers} == set(port_of.values())
    assert [f.code for f in findings] == _LONE_CONNECTORS * len(port_of)


def test_a_three_port_net_is_stubbed_only_between_the_lowest_ports_of_its_two_parts() -> None:
    """Two ports at `+ER+C1`, one at `+AR+C1`: one stub pair, from the lower-handle ER port to
    the AR port; the two ER ports are still one group, a route between them, no marker there."""
    written, findings, port_of = _laid_out({"p1": "ER", "p2": "ER", "p3": "AR"})
    lower, higher = sorted((port_of["p1"], port_of["p2"]))
    markers = layout_of(written, LinkMarker).values()
    assert sorted(m.port for m in markers) == sorted((lower, port_of["p3"]))
    assert all(m.star is StarKind.OFF for m in markers)
    assert higher not in {m.port for m in markers}
    routes = layout_of(written, Route).values()
    assert any({r.a, r.b} == {lower, higher} for r in routes)
    assert CONNECTION_NOT_DRAWN not in {f.code for f in findings}
    assert [f.code for f in findings] == _LONE_CONNECTORS * len(port_of)


def test_two_parts_of_two_ports_each_keep_one_net_and_each_draw_their_own_route() -> None:
    """Two ports in each location: two groups of one net, a route in each, one stub pair
    between the two lowest ports, and no finding about the net (the lint reads both parts)."""
    written, findings, port_of = _laid_out({"p1": "ER", "p2": "ER", "p3": "AR", "p4": "AR"})
    er = sorted((port_of["p1"], port_of["p2"]))
    ar = sorted((port_of["p3"], port_of["p4"]))
    markers = layout_of(written, LinkMarker).values()
    assert sorted(m.port for m in markers) == sorted((er[0], ar[0]))
    assert all(m.star is StarKind.OFF for m in markers)
    ends = [{r.a, r.b} for r in layout_of(written, Route).values()]
    assert set(er) in ends
    assert set(ar) in ends
    assert [f.code for f in findings] == _LONE_CONNECTORS * len(port_of)
