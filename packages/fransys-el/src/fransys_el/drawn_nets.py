"""CONNECTION_NOT_DRAWN over the drawn netlist: every conductor end of a drawn port is drawn (R1573, R1617, CP-S2c-1).

The expected side is `derive.far_pins`: each conductor end of a port drawn at its home. An end is drawn when ink joins its two
ports into one piece, a reference pair or stub names the far port, its line is stubbed, or its where-text is printed.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.derive import far_pins
from fransys_model.layout import StarKind

from .drawn_finding import drawn_finding
from .drawn_graph import Union
from .drawn_power import inked_power

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model
    from fransys_model.layout import LinkMarker

    from .drawn_netlist import Netlist

__all__ = ["not_drawn_findings"]


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
    """Each port an off stub is drawn at, with the far ports its stubs name, on its home page only."""
    found: dict[str, set[str]] = defaultdict(set)
    for key, record in net.records.items():
        if record.star is StarKind.OFF and (node := net.markers.get(key)) is not None and record.pairs:
            for here, far in _listed(net, record, node):
                found[here].add(far)
    return found


def _lined(net: Netlist, port: str) -> bool:
    """True when the port's home page stubs the port's line, the end of every conductor of that line (R481)."""
    return any((page, net.lined.get(port, "")) in net.stub_lines for page in net.home.get(port, ()))


def _roots(net: Netlist, port: str, stubs: dict[str, set[str]]) -> set[object]:
    """The live components the port joins by its home point; its copies join where a stub or each placement's where-text ends it (R798, R1396).

    A port of a set that was not drawn has no home to read: its copies on the pages that did draw are all there is (KI-812).
    """
    ended = port in stubs or _lined(net, port) or port in net.texted or port in net.skipped
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


def _carried(net: Netlist, stubs: dict[str, set[str]], joined: Union, powered: set[str], end: tuple[str, str]) -> bool:
    """True when the end at `near` is drawn (R1573, R1617): joined to `far` in one piece, marked, or a power symbol inked to its pin (R1631).

    A mark is a stub at `near` that names `far`, the stubbed line of `near`, or the where-text of its copy.
    R4 (ink to the pin) replaces the model-net read.
    """
    near, far = end
    if set(end) & powered or _lined(net, near) or near in net.texted or far in stubs.get(near, ()):
        return True
    return bool({joined.find(r) for r in _roots(net, near, stubs)} & {joined.find(r) for r in _roots(net, far, stubs)})


def _unmarked(model: Model, net: Netlist, stubs: dict[str, set[str]], joined: Union) -> list[tuple[str, str]]:
    """Each `(near, far)` conductor end of a port drawn at its home that no wire, reference, stub or where-text draws."""
    held = [net.ids[p] for p in net.placed if net.at_home(p)]
    powered = inked_power(net, model)
    return [(n.value, f.value) for n, f in far_pins(model, held) if not _carried(net, stubs, joined, powered, (n.value, f.value))]


def not_drawn_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """One WARNING per conductor end of a port drawn at its home that no wire, reference, stub or where-text draws (R1573, R1617)."""
    stubs = _stubs(net)
    message = "1 conductor end not drawn: no wire, reference, stub or where-text"
    return tuple(drawn_finding("CONNECTION_NOT_DRAWN", (net.ids[near],), message) for near, _ in _unmarked(model, net, stubs, _pairs(net, stubs)))
