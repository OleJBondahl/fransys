"""D9 (layout deep dive): a port the router leaves with no wire joins the net's markers.

Every drawn port of a net shows a wire or a marker. K5, K6, K7 are joined by conductors at the
hub K6's `A2`, which faces away from the others' `A1` (ends of one side are wired, S20 M12), so
they form a star drawn as markers; a declared net `SHARED` also names K1. The net's wire-drawn ports
are then K1 alone, so the router has no pair to span and K1 would show nothing: it gets its own
branch marker and the star's reference lists it. Built through the `fransys` facade from
`examples/demo-parts`. Layout-0055 review: a side element never joins, a port joins once, the
first star by reference port takes it, a port with its own drawn wire still joins, and a group
with no star or with two or more ports outside every star is left as it was.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_layout.stages.references import Star, with_orphans
from fransys_layout.stages.types import NetGroup, PortRef, Role
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import Id, Severity
from fransys_model.layout import LinkMarker, Route, StarKind, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Net orphan port",
    "number": "P-1007",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_RELAY = "DEMO-RLY-2CO-24"


def test_a_port_the_router_leaves_with_no_wire_gets_a_marker_and_the_reference_lists_it() -> None:
    """K1 has no wire partner: it carries a branch marker and the reference lists its position."""
    # UNDO: engines/schematic/engine.py, `stars = with_orphans(...)`: use `stars`
    #     unchanged (the unfixed rule): K1 has neither a route nor a marker
    model, port = _build(
        ("K1", "K5", "K6", "K7"),
        [("K5", "K6.A2"), ("K6.A2", "K7")],  # the hub's A2 faces the other way: no same-side wire
        [("SHARED", ("K1", "K5", "K6.A2", "K7"))],
    )
    markers = layout_of(model, LinkMarker)
    for tag, id_ in port.items():  # every drawn port shows a wire or a marker
        assert _marks(model, id_) or _routed(model, id_), tag
    (own,) = (m for m in markers.values() if m.port == port["K1"])
    reference = markers[own.partner]
    assert reference.port == port["K6.A2"]  # the branch names the star's reference, the hub K6
    # the reference lists one position for each branch marker that names it, K1's included
    branches = [
        m for m in markers.values() if m.star is StarKind.BRANCH and m.partner == own.partner
    ]
    assert own in branches
    assert len(branches) == 3
    assert marker_text(model, reference).endswith(" +2")  # C2: the first and a count


def _build(tags, wires, nets):
    """Coil relays `tags`; `wires` join two coil ports, `nets` are declared over coil ports.

    An end is a tag (its `A1`) or `"K6.A2"`; a wire's third item names the port at both ends.
    Same-side ends of one net are wire-joined (S20 M12), so a star needs ends of both sides.
    Returns the model and the id of each port named, by its end.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cabinet, group = d.location("C1", "Cabinet"), d.group("G1", "Group")
    wire = d.wiring(colour="BU", gauge="0.5")
    coil = {
        tag: d.item(_RELAY, tag=tag, name=tag.lower(), at=cabinet, group=group).fn("coil")
        for tag in tags
    }
    named: dict[str, Any] = {}

    def end(spec: str, default: str = "A1") -> Any:
        tag, _, name = spec.partition(".")
        named[spec] = coil[tag][name or default]
        return named[spec]

    for a, b, *port in wires:
        wire(end(a, *port), end(b, *port))
    for name, members in nets:
        d.net(name, *(end(spec) for spec in members))
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    return result.model, {spec: one.id for spec, one in named.items()}


def _marks(model, port):
    return [m for m in layout_of(model, LinkMarker).values() if m.port == port]


def _routed(model, port):
    return any(port in {r.a, r.b} for r in layout_of(model, Route).values())


def test_a_side_element_port_keeps_its_wire_to_the_host_and_gets_no_marker() -> None:
    """K8 is strapped in parallel with K6 (a side element): its wire stays, it gets no marker."""
    # UNDO: stages/references/nets.py, `with_orphans`: drop
    #     `or alone[0].function in side` from the skip test: K8, the group's
    #     lone outsider, gets a branch marker as well
    model, port = _build(
        ("K5", "K6", "K7", "K8"),
        [("K5", "K6"), ("K6", "K7"), ("K6", "K8"), ("K6", "K8", "A2")],
        [("SHARED", ("K5", "K6", "K7", "K8"))],
    )
    assert not _marks(model, port["K8"])
    assert _routed(model, port["K8"])


def test_a_port_with_its_own_drawn_wire_keeps_it_and_still_gets_the_marker() -> None:
    """Layout-0055: K1 is wired to K9 (no star) and is the declared net's lone outsider: both."""
    # UNDO: engines/schematic/engine.py, `stars = with_orphans(...)`: use `stars`
    #     unchanged: K1 keeps its wire but loses its branch marker
    model, port = _build(
        ("K1", "K5", "K6", "K7", "K9"),
        [("K5", "K6.A2"), ("K6.A2", "K7"), ("K1", "K9")],
        [("SHARED", ("K1", "K5", "K6.A2", "K7"))],
    )
    marks = _marks(model, port["K1"])
    assert [m.star for m in marks if m.star is not None] == [StarKind.BRANCH]
    # its own conductor is still drawn: a wire, or (cut between two pages) a wire-end marker
    assert _routed(model, port["K1"]) or [m for m in marks if m.star is None]


def test_two_stars_in_one_group_list_the_orphan_under_the_first_by_reference_port() -> None:
    """K1 joins one star: the one whose reference port sorts first (hub K6, or K3)."""
    # UNDO: stages/references/nets.py, `with_orphans`:
    #     `for i, star in enumerate(found)` to
    #     `for i, star in reversed(list(enumerate(found)))`: K1 names the
    #     other star's reference
    model, port = _build(
        ("K1", "K2", "K3", "K4", "K5", "K6", "K7"),
        [("K5", "K6.A2"), ("K6.A2", "K7"), ("K2", "K3.A2"), ("K3.A2", "K4")],
        [("SHARED", ("K1", "K2", "K3.A2", "K4", "K5", "K6.A2", "K7"))],
    )
    (own,) = (m for m in _marks(model, port["K1"]) if m.star is StarKind.BRANCH)
    reference = layout_of(model, LinkMarker)[own.partner]
    assert reference.port == min(port["K6.A2"], port["K3.A2"])


def _port(n: int) -> PortRef:
    return PortRef(
        function=Id(kind="function", value=f"{n:032x}"), port=Id(kind="port", value=f"{n:032x}")
    )


def _group(*ports: PortRef) -> NetGroup:
    net = Id(kind="net", value=f"{len(ports):032x}")
    return NetGroup(net=net, physical_net=net, role=Role.POWER, ports=ports)


def test_a_group_with_no_star_port_or_two_ports_outside_every_star_is_left_alone() -> None:
    """Layout-0055 consequences: only a group with a star and one outsider adds a port."""
    # UNDO: stages/references/nets.py, `with_orphans`: `len(alone) != 1` to
    #     `len(alone) < 1` (the two-outsider group adds one); drop
    #     `home is None or` (the no-star group crashes)
    one, two, three, x, y = _port(1), _port(2), _port(3), _port(9), _port(8)
    star = Star(ports=(one, two, three), ref=two, conductors=frozenset(), by_designation=True)
    groups = (_group(one, x, y), _group(x), _group(y, x))  # two outsiders; no star port; two
    assert with_orphans((star,), groups, frozenset()) == (star,)


def test_a_port_that_is_the_lone_outsider_of_two_groups_joins_a_star_once() -> None:
    """Layout-0055 review: X outside every star in two groups is added once, not twice."""
    # UNDO: stages/references/nets.py, `with_orphans`: delete
    #     `in_star.add(alone[0].port)`: X is listed twice (`star.ports`,
    #     `star.cluster`)
    one, two, three, x = _port(1), _port(2), _port(3), _port(9)
    star = Star(ports=(one, two, three), ref=two, conductors=frozenset(), by_designation=True)
    (joined,) = with_orphans((star,), (_group(one, x), _group(three, x)), frozenset())
    assert [ref.port for ref in joined.ports].count(x.port) == 1
    assert [port for port, _ in joined.cluster].count(x.port) == 1
