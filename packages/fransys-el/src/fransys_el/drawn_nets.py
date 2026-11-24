"""CONNECTION_NOT_DRAWN over the drawn netlist: every conductor end of a drawn port is drawn (R1573, R1617, CP-S2c-1).

The expected side is `derive.far_pins`: each conductor end of a port drawn at its home. An end is drawn when ink joins its two
ports into one piece, a reference pair or stub names the far port, its line is stubbed, or its where-text is printed.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.derive import far_pins, rail_drawn_by
from fransys_model.kernel import UnionFind
from fransys_model.layout import StarKind

from .drawn_ends import ink_without_conductor
from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import LinkMarker, Page

    from .drawn_netlist import Netlist

__all__ = ["not_drawn_findings"]

type _Node = tuple[Id[Page], tuple[int, int]]


def _listed(net: Netlist, record: LinkMarker, node: _Node) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The `(port, far)` conductors an off stub ends on its page: its own, each pair inked to its node, then those on a lane foot (R1334).

    A bundle's one stub lists every lane it stands for; a lane inked into its piece is joined by it. A lane whose end is a
    read foot at the stub's x (`Netlist.lanes`) lies on its ink too: its pair is the second list, kept by `_stubs` on a name back.
    """
    root, first, *rest = net.union.find(node), *((p.value, f.value) for p, f in ((x.port, x.far) for x in record.pairs))
    own = [(p, f) for p, f in rest if p == first[0]]  # the other conductors of the stub's own pin: one box, a line each (R1581)
    at = {p: [place for place in net.placed.get(p, ()) if place[0] == record.page] for p, _ in rest}
    feet = {net.union.find(foot) for foot in net.lanes.joined if foot[0] == record.page and foot[1][0] == node[1][0]}
    inked = [
        (p, f)
        for p, f in rest
        if p != first[0] and any(place[1] in net.pages[record.page].nodes and net.union.find(place) == root for place in at[p])
    ]
    on_foot = [(p, f) for p, f in rest if p != first[0] and (p, f) not in inked and any(net.union.find(place) in feet for place in at[p])]
    home = [pair for pair in (first, *own, *inked) if record.page in net.home.get(pair[0], ())]
    return home, [pair for pair in on_foot if record.page in net.home.get(pair[0], ())]


def _stubs(net: Netlist) -> dict[str, set[str]]:
    """Each port an off stub is drawn at, with the far ports its stubs name, on its home page only.

    A lane on a read foot counts when its far end names it back (R3541).
    """
    found: dict[str, set[str]] = defaultdict(set)
    fed: list[tuple[str, str]] = []
    for key, record in net.records.items():
        if record.star is StarKind.OFF and (node := net.markers.get(key)) is not None and record.pairs:
            sure, on_foot = _listed(net, record, node)
            fed += on_foot
            for here, far in sure:
                found[here].add(far)
    named = {port: set(fars) for port, fars in found.items()}
    for here, far in fed:
        if here in named.get(far, ()):
            found[here].add(far)
    return found


def _lined(net: Netlist, port: str) -> bool:
    """True when the port's home page stubs the port's line, the end of every conductor of that line, and the port stands on a node (R481)."""
    stubbed = any((page, net.lined.get(port, "")) in net.stub_lines for page in net.home.get(port, ()))
    return stubbed and any(at in net.pages[page].nodes for page, at in net.at_home(port))


def _roots(net: Netlist, port: str, stubs: dict[str, set[str]]) -> set[_Node]:
    """The live components the port joins by its home point; its copies join where a stub or each placement's where-text ends it (R798, R1396).

    A port of a set that was not drawn has no home to read: its copies on the pages that did draw are all there is (KI-812).
    """
    ended = port in stubs or _lined(net, port) or port in net.texted or port in net.skipped
    points = net.placed.get(port, ()) if ended else net.at_home(port)
    return {net.union.find(place) for place in points} & net.live


def _pairs(net: Netlist, stubs: dict[str, set[str]]) -> UnionFind[_Node]:
    """The drawn pieces joined by reference pairs, transitively: two pieces whose stubs each name a port in the other."""
    names: dict[_Node, set[_Node]] = defaultdict(set)
    for port, fars in stubs.items():
        for root in _roots(net, port, stubs):
            names[root].update(r for far in fars for r in _roots(net, far, stubs))
    joined: UnionFind[_Node] = UnionFind()
    for root, others in names.items():
        for other in others:
            if root in names.get(other, ()):
                joined.union(root, other)
    return joined


def _carried(net: Netlist, stubs: dict[str, set[str]], joined: UnionFind[_Node], end: tuple[str, str]) -> bool:
    """True when the end at `near` is drawn (R1573, R1617): joined to `far` in one piece, or marked.

    A mark is a stub at `near` that names `far`, or the stubbed line of `near`. A where-text names a copy, never an end: ink carries it.
    A power symbol's end is one piece with its far symbol by `join_power`, so it needs no term here.
    """
    near, far = end
    if _lined(net, near) or far in stubs.get(near, ()) or end in net.named:
        return True
    return bool({joined.find(r) for r in _roots(net, near, stubs)} & {joined.find(r) for r in _roots(net, far, stubs)})


def _unmarked(model: Model, net: Netlist, stubs: dict[str, set[str]], joined: UnionFind[_Node]) -> list[tuple[str, str]]:
    """Each `(near, far)` conductor end of a port drawn at its home that no wire, reference, stub or where-text draws.

    A pin that stands the power symbol of the flagged rail terminal `far` draws that terminal (`rail_drawn_by`, owner 2026-10-25),
    when its symbol is on a page: a rail-fed pin with no symbol drawn is a conductor end no ink draws.
    """
    held = [net.ids[p] for p in net.placed if net.at_home(p)]
    symbols = {p for part in net.pages.values() for p in part.powers}
    fed = {(pin.value, terminal.value) for terminal, pins in rail_drawn_by(model).items() for pin in pins if pin.value in symbols}
    ends = ((n.value, f.value) for n, f in far_pins(model, held))
    return [end for end in ends if end not in fed and not _carried(net, stubs, joined, end)]


def not_drawn_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """One finding per conductor end that no wire, reference, stub or where-text draws (R1573, R1617), then per ink run no conductor makes."""
    stubs = _stubs(net)
    message = "1 conductor end not drawn: no wire, reference, stub or where-text"
    ends = (drawn_finding("CONNECTION_NOT_DRAWN", (net.ids[near],), message) for near, _ in _unmarked(model, net, stubs, _pairs(net, stubs)))
    return (*ends, *ink_without_conductor(model, net))
