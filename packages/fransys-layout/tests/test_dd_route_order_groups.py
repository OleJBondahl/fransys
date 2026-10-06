"""D15 (layout deep dive): a net group's spanning tree is built in drawn order, not handle order.

Four relay coils stand in one row on `examples/demo-parts`. A declared net names both ports of K2
and both ports of K3 and no conductor joins them, so the router spans the four ports itself. K2's
two ports are a short pair, K3's two ports are a short pair, and the two long candidates between
the pairs are equally far: one of them closes a loop and is dropped. A port handle must not
decide which one, or renaming an item moves a wire.
"""

from typing import TYPE_CHECKING, Any

from dd_chain_fixtures import build, design

from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import Severity
from fransys_model.layout import Route, layout_of
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

RELAY = "DEMO-RLY-2CO-24"
TAGS = ("K1", "K2", "K3", "K4")
MEMBERS = (("K2", "A1"), ("K2", "A2"), ("K3", "A1"), ("K3", "A2"))
# `name=` of K2 becomes its key and so its port handles; its tag (the designation) is unchanged.
# Found by scratch search (claude-tools/probe_net_tree_rename.py) over K1 to K4 with suffixes a-h:
# only this rename of K2 flips the tie on the base router.
RENAMED = "K2a"

Point = tuple[int, int]
End = tuple[str | None, tuple[str, ...], str]


def _build(rename: str | None = None) -> Any:
    """The four coils and the declared net; `rename` is the `name=` key of K2 (its tag stays)."""
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    coil = {
        tag: d.item(RELAY, name=rename if tag == "K2" else None, tag=tag, at=c, group=g).fn("coil")
        for tag in TAGS
    }
    d.net("SHARED", *(coil[tag][marking] for tag, marking in MEMBERS))
    return build(parts, d)


def _end(model: Model, port: Id) -> End:
    """A port as `(item tag, its function's key after the item, marking)`, named or not."""
    function = functions(model)[ports(model)[port].function]
    item = items(model)[function.item]
    return own_designation_or_none(model, item), function.key[1:], ports(model)[port].name


def _routes(model: Model) -> dict[tuple[End, ...], tuple[Point, ...]]:
    """Every route by its two ends; its points read in the lesser direction, so a flip is moot."""
    found = {}
    for route in layout_of(model, Route).values():
        points = tuple((point.x, point.y) for point in route.points)
        found[tuple(sorted((_end(model, route.a), _end(model, route.b))))] = min(
            points, points[::-1]
        )
    return found


def _member_ports(model: Model) -> list[End]:
    """The four net members, in the order of their port handles."""
    by_end = {_end(model, port): port for port in ports(model)}
    return sorted(
        ((tag, ("fn", "coil"), marking) for tag, marking in MEMBERS), key=lambda end: by_end[end]
    )


def test_renaming_an_item_leaves_every_route_of_a_net_group_byte_identical() -> None:
    """D15: an item's name feeds only handles, so renaming K2 moves no wire of the net.

    The rename changes the handles of K2's two ports and so the order the four ports sort in. On
    the handle-ordered tree that changes which of the two equally long links between K2's and K3's
    ports is kept, and so one wire of the net.
    """
    # UNDO: stages/route.py _tree, sort `pairs` by `(distance, one.port, other.port)` alone (the
    #       handle tie-break, as the base did)
    before, after = _build(), _build(rename=RENAMED)
    for result in (before, after):
        assert not [f for f in result.findings if f.severity is Severity.ERROR]
    ports_before, ports_after = _member_ports(before.model), _member_ports(after.model)
    assert set(ports_before) == set(ports_after)
    assert ports_before != ports_after, (
        "the rename must change the order the net's ports sort in, or it proves nothing"
    )
    routes = _routes(before.model)
    members = {(tag, ("fn", "coil"), marking) for tag, marking in MEMBERS}
    net = [ends for ends in routes if set(ends) <= members]
    assert len(net) == len(MEMBERS) - 1, "a spanning tree of the four ports has three edges"
    assert _routes(after.model) == routes
