"""CORE-ACCOUNT: after the last round, every directed conductor end is drawn as a wire or named by one stub that stands (CL1, R2650).

A wire joins the two pins of an end when the router's pieces (`PageRoutes.pieces`) and the ports one node ties put them in one piece.
Any other end is NAMED when the piece of its near pin holds a pin that a placed marker, an anchor, a fan lane or a join stands at or for.
Each end is in exactly one state.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .cut_ledger import standing
from .unionfind import UnionFind
from .values import Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from .flow_values import CutResult
    from .outputs import Marker, Placement
    from .values import PlacementProblem
    from .widen import Round

__all__ = ("account_findings", "unaccounted")

type Pair = tuple[PinRef, PinRef]


def _key(pin: PinRef) -> str:
    return f"{pin.sym}/{pin.pin}"


def _state(joined: UnionFind, carried: Collection[str], end: Pair, stubs: int) -> str:
    """What is wrong with `end`, given the pieces that join pins, the pieces a carrier stands in and the stubs that name it; "" when nothing."""
    near, far = end
    if joined.find(_key(near))[0] == joined.find(_key(far))[0]:
        return "accounted twice: drawn as a wire and named by a stub" if stubs else ""
    if stubs > 1:
        return "accounted twice: named by two stubs"
    return "" if joined.find(_key(near))[0] in carried else "not accounted: no wire and no marker stands for it"


def account_findings(
    far_ends: Collection[Pair],
    pieces: Iterable[Sequence[PinRef]],
    stood: Collection[PinRef],
    markers: Iterable[Marker],
    nets: tuple[Mapping[PinRef, str], Mapping[str, int]],
) -> tuple[Finding, ...]:
    """A finding per directed end in neither state or in both: `pieces` the pins each drawn piece joins, `stood` the pins a carrier stands at.

    `nets` is each pin's net and each symbol's page.
    """
    net_of, page_of = nets
    joined = UnionFind()
    for piece in pieces:
        for pin in piece[1:]:
            joined.union(_key(piece[0]), _key(pin))
    carried = {joined.find(_key(p))[0] for p in stood}
    named = Counter((p, far) for m in markers for p in (m.end, *m.also) for far in m.far)
    out = []
    for near, far in far_ends:
        if state := _state(joined, carried, (near, far), named[near, far]):
            net = net_of.get(near, "")
            text = f"conductor {near.sym}.{near.pin} to {far.sym}.{far.pin} of net {net} {state}"
            out.append(Finding("CONNECTION_NOT_ACCOUNTED", text, page_of.get(near.sym), f"{near.sym},{net}"))
    return tuple(out)


def unaccounted(cut: CutResult, placement: Placement, rnd: Round, problem: PlacementProblem) -> tuple[Finding, ...]:
    """CORE-ACCOUNT over the finished layout: the pieces the last round's wires make, and the markers it placed."""
    where = {p.sym: pg.page for pg in placement.pages for p in pg.placed}
    tied = [tuple(PinRef(s.id, p) for p in node) for s in problem.symbols for node in s.nodes if len(node) > 1]
    pieces = [*tied, *(pc for pr in rnd.routes.pages for pc in pr.pieces)]
    stood = standing(problem, cut.flow, where, rnd.markers)
    return account_findings(problem.facts.far_ends, pieces, stood, rnd.markers, ({p: n.id for n in problem.nets for p in n.pins}, where))
