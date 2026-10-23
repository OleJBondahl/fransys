"""A net group's spanning tree is built in drawn order, not handle order.

Four relay coils stand in one row on `examples/demo-parts`. A declared net names both ports of K2
and both ports of K3 and no conductor joins them, so the router spans the four ports itself. K2's
two ports are a short pair, K3's two ports are a short pair, and the two long candidates between
the pairs are equally far: one of them closes a loop and is dropped. A port handle must not
decide which one, or renaming an item moves a wire.
"""

from typing import Any

from _drawn_pages import drawn_pages
from dd_chain_fixtures import build, design

from fransys_model.kernel import Severity

RELAY = "DEMO-RLY-2CO-24"
TAGS = ("K1", "K2", "K3", "K4")
MEMBERS = (("K2", "A1"), ("K2", "A2"), ("K3", "A1"), ("K3", "A2"))
# `name=` of K2 becomes its key and so its port handles; its tag (the designation) is unchanged.
# Found by a scratch search over K1 to K4 with suffixes a-h:
# only this rename of K2 flips the tie on the base router.
RENAMED = "K2a"

Point = tuple[int, int]


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


def _routes(result: Any) -> list[tuple[Point, ...]]:
    """Every drawn wire's points, read in the lesser direction so a flip is moot, in page order."""
    return [
        min(w.points, w.points[::-1])
        for drawing in drawn_pages(result.model).values()
        for w in drawing.wires
    ]


def test_renaming_an_item_leaves_every_route_of_a_net_group_byte_identical() -> None:
    """An item's name feeds only handles, so renaming K2 moves no wire of the net.

    The rename changes the handles of K2's two ports and so the order the four ports sort in. On
    the handle-ordered tree that changes which of the two equally long links between K2's and K3's
    ports is kept, and so one wire of the net.
    """
    # UNDO: stages/route.py _tree, sort `pairs` by `(distance, one.port, other.port)` alone (the
    #       handle tie-break, as the base did)
    before, after = _build(), _build(rename=RENAMED)
    for result in (before, after):
        assert not [f for f in result.findings if f.severity is Severity.ERROR]
    routes = _routes(before)
    # four ports spanned by a tree: three edges, drawn as the wires of the page
    assert len(routes) >= len(MEMBERS) - 1, "a spanning tree of the four ports has three edges"
    assert _routes(after) == routes
