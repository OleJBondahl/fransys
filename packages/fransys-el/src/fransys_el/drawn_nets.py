"""CONNECTION_NOT_DRAWN over the drawn netlist: every group the model joins is drawn joined (R682, R685).

The expected side is `derive.drawn_groups`. A group's placed ports are drawn when wires, dots, a reference
pair or a link join them into one piece. A group with a port off the document, or in two pieces, is drawn only
when each piece carries an off stub that names a port of the group outside it (a cut end, R676).
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from electrical_symbols import power_symbol_key
from fransys_model.derive import connected_ports, drawn_groups, far_pins, port_power_text
from fransys_model.layout import StarKind

from .drawn_finding import drawn_finding
from .drawn_graph import Union
from .drawn_netlist import POWER_KEYS

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model
    from fransys_model.layout import LinkMarker

    from .drawn_netlist import Netlist

__all__ = ["not_drawn_findings"]

_NAMED = 4
_MIN_PORTS = 2


def _listed(net: Netlist, record: LinkMarker, node: tuple[object, object]) -> list[tuple[str, str]]:
    """The `(port, far)` conductors an off stub ends on its page: its own, and each listed pair drawn joined to the stub's node (BUNDLE, R682, R1334).

    A bundle's one stub lists every lane it stands for; the plan names them, and only a lane inked into the stub's drawn piece is joined by it.
    """
    root = net.union.find(node)
    first, *rest = ((p.value, f.value) for p, f in ((x.port, x.far) for x in record.pairs))
    own = [(p, f) for p, f in rest if p == first[0]]  # the other conductors of the stub's own pin: one box, a line each (R1581)
    inked = [
        (p, f)
        for p, f in rest
        if p != first[0]
        and any(page == record.page and at in net.pages[page].nodes and net.union.find((page, at)) == root for page, at in net.placed.get(p, ()))
    ]
    return [pair for pair in (first, *own, *inked) if record.page in net.home.get(pair[0], ())]


def _stubs(net: Netlist) -> dict[str, set[str]]:
    """Each port an off stub is drawn at (and the wired port it stands for), with the far ports its stubs name, on its home page only."""
    found: dict[str, set[str]] = defaultdict(set)
    outer: dict[str, list[str]] = defaultdict(list)
    for port, inner in net.linked.items():
        outer[inner].append(port)
    for key, record in net.records.items():
        if record.star is StarKind.OFF and (node := net.markers.get(key)) is not None and record.pairs:
            for here, far in _listed(net, record, node):
                for port in (here, *outer[here]):
                    found[port].add(far)
    return found


def _lined(net: Netlist, port: str) -> bool:
    """True when the port's home page stubs the port's line, the end of every conductor of that line (R481)."""
    return any((page, net.lined.get(port, "")) in net.stub_lines for page in net.home.get(port, ()))


def _ends(net: Netlist, piece: set[str], members: list[str], stubs: dict[str, set[str]]) -> bool:
    """True when a port of `piece` carries an off stub naming a port of the group outside it.

    A stub on a line is the end of every conductor of that line (R481): a port of `piece` that stands on a page
    where its line is stubbed is ended.
    """
    outside = set(members) - piece
    return any(stubs.get(port, set()) & outside for port in piece) or (bool(outside) and any(_lined(net, port) for port in piece))


def _roots(net: Netlist, port: str, stubs: dict[str, set[str]]) -> set[object]:
    """The live components the port joins by its home point; its copies join where a stub or each placement's where-text ends it (R798, R1396)."""
    ended = port in stubs or _lined(net, port) or port in net.texted
    port = net.linked.get(port, port)
    points = net.placed.get(port, ()) if ended else net.at_home(port)
    return {net.union.find(place) for place in points} & net.live


def _pairs(net: Netlist, stubs: dict[str, set[str]]) -> Union:
    """The drawn pieces joined by reference pairs, transitively: two pieces whose stubs each name a port in the other."""
    names: dict[object, set[object]] = defaultdict(set)
    for port, fars in stubs.items():
        for root in _roots(net, port, stubs):
            names[root].update(r for far in fars for r in _roots(net, far, stubs))
    joined = Union()
    for root, others in names.items():
        for other in others:
            if root in names.get(other, ()):
                joined.join(root, other)
    return joined


def _verdict(net: Netlist, members: list[str], stubs: dict[str, set[str]], joined: Union | None = None) -> tuple[list[str], list[str], int] | None:
    """The unreached ports, the drawn ports and the piece count of a group; None when it is drawn.

    Pieces joined by reference pairs count as one. Only a port's home counts (R798): a wired copy covers neither an unwired home
    nor a piece it completes alone. A group with no member drawn anywhere is not drawn.
    """
    placed = [p for p in members if net.at_home(p)]
    if not placed:
        return None if any(p in net.placed for p in members) else ([], [], 0)
    lost = [p for p in placed if p not in net.linked and not any(at in net.pages[page].nodes for page, at in net.at_home(p))]
    joined = _pairs(net, stubs) if joined is None else joined
    pieces: dict[object, set[str]] = defaultdict(set)
    for port in placed:
        if port not in lost:
            for root in _roots(net, port, stubs):
                pieces[joined.find(root)].add(port)
    whole = any(len(piece) == len(members) for piece in pieces.values())
    if lost or not (whole or all(_ends(net, piece, members, stubs) for piece in pieces.values())):
        return lost, placed, len(pieces)
    return None


def _powered(model: Model, net: Netlist) -> set[str]:
    """The ports drawn as a power symbol that names its potential (R1631): a ground or PE symbol, or a supply symbol with a printed text."""
    supply = power_symbol_key("supply")
    return {
        port
        for part in net.pages.values()
        for symbol in part.drawing.symbols
        if symbol.key in POWER_KEYS
        for port in symbol.ports
        if symbol.key != supply or port_power_text(model, net.ids[port]) is not None
    }


def _carried(net: Netlist, stubs: dict[str, set[str]], joined: Union, powered: set[str], end: tuple[str, str]) -> bool:
    """True when the end at `near` is drawn (R1573, R1617): joined to `far` in one piece, marked, or a power symbol that names its potential (R1631).

    A mark is a stub at either end that names the other, the stubbed line of `near`, or the where-text of its copy.
    """
    near, far = end
    if set(end) & powered or _lined(net, near) or near in net.texted or far in stubs.get(near, ()) or near in stubs.get(far, ()):
        return True
    return bool({joined.find(r) for r in _roots(net, near, stubs)} & {joined.find(r) for r in _roots(net, far, stubs)})


def _unmarked(model: Model, net: Netlist, stubs: dict[str, set[str]], joined: Union) -> list[tuple[str, str]]:
    """Each `(near, far)` conductor end of a port drawn at its home that no wire, reference, stub or where-text draws."""
    held = [net.ids[p] for p in net.placed if net.at_home(p)]
    powered = _powered(model, net)
    return [(n.value, f.value) for n, f in far_pins(model, held) if not _carried(net, stubs, joined, powered, (n.value, f.value))]


def _end_findings(model: Model, net: Netlist, stubs: dict[str, set[str]], joined: Union, flagged: set[object]) -> tuple[Finding, ...]:
    """One WARNING per undrawn conductor end whose port no group finding already names (R1573, R1617)."""
    message = "1 conductor end not drawn: no wire, reference, stub or where-text"
    return tuple(
        drawn_finding("CONNECTION_NOT_DRAWN", (net.ids[near],), message)
        for near, _ in _unmarked(model, net, stubs, joined)
        if net.ids[near] not in flagged
    )


def not_drawn_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """One WARNING per group the model joins whose drawn ports are not joined, as R685 counts joins.

    A group held by parallel conductors counts once.
    """
    keep = {p.value for p in connected_ports(model)}
    stubs, seen = _stubs(net), set()
    joined = _pairs(net, stubs)
    found: list[Finding] = []
    for group in drawn_groups(model):
        members = [p.value for p in group if p.value in keep]
        if len(members) < _MIN_PORTS or frozenset(members) in seen:
            continue
        seen.add(frozenset(members))
        if verdict := _verdict(net, members, stubs, joined):
            lost, placed, pieces = verdict
            subjects = tuple(net.ids[p] for p in ((*lost, *placed) or members)[:_NAMED] if p in net.ids)
            found.append(
                drawn_finding("CONNECTION_NOT_DRAWN", subjects, f"{len(lost)} of {len(placed)} drawn port(s) not reached; {pieces} piece(s)")
            )
    return (*found, *_end_findings(model, net, stubs, joined, {p for finding in found for p in finding.subjects}))
