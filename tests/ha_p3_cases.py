"""P3's fr-built cases (layout-0154): a unit whose lines all leave, two top-level units on one
cable, and a unit with a line interface beside a single-wire one. Built from `demo_parts` only.
"""

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
lazy from fransys_author import Item, Location

lazy from fransys_model.kernel import Draft


def _design() -> tuple[Draft, fransys_author.Design]:
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="P3 cases", number="P3", customer="Demo", revision=1, author="XX")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


def _unit(
    d: fransys_author.Design, scope: str, tags: tuple[str, ...]
) -> tuple[Location, list[Item]]:
    """A top-level unit at its own location with one boundary connector per tag."""
    u = d.scope(scope).unit(f"demo-{scope}", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    at = u.location(scope.upper(), f"Cabinet {scope}")
    grp = u.group("NET", "Network")
    connectors = [u.item("DEMO-CONN-2P", tag=tag, at=at, group=grp) for tag in tags]
    for connector in connectors:
        u.boundary(connector)
    return at, connectors


def _harness(d: fransys_author.Design, tag: str, near: Item, far: Item, at: Location) -> None:
    """A top-level harness: a two-core cable from a plug mated to `near` to a plug on `far`."""
    group = d.group(tag, tag)
    harness = d.harness(name=tag.lower(), tag=tag, at=at, group=group)
    plug = d.item("DEMO-CONN-2P", tag=f"{tag}P1", parent=harness, at=at, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", name=f"{tag.lower()}c", parent=harness, at=at)
    cable.core(1, plug["1"], far["1"])
    cable.core(2, plug["2"], far["2"])
    d.mate(plug, near)


def leaving() -> fr.BuildResult:
    """Condition 1: a unit whose only line ends in the field, another drawing set."""
    parts, d = _design()
    cab, (x1,) = _unit(d, "cab", ("X1",))
    fld = d.location("FLD", "Field")
    q1 = d.item("DEMO-CONN-2P", tag="Q1", at=fld, group=d.group("F", "Field"))
    _harness(d, "W3", x1, q1, cab)
    return fr.build(parts, d.draft(), layout_trigger_document())


def two_units() -> fr.BuildResult:
    """Condition 2: a harness between two top-level units, a plug mated to each."""
    parts, d = _design()
    _, (x1,) = _unit(d, "cab", ("X1",))
    _, (x2,) = _unit(d, "box", ("X2",))
    group = d.group("L", "Link")
    site = d.location("SITE", "Site")
    harness = d.harness(name="w5", tag="W5", at=site, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=harness, at=site, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=harness, at=site, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", name="w5c", parent=harness, at=site)
    cable.core(1, p1["1"], p2["1"])
    cable.core(2, p1["2"], p2["2"])
    d.mate(p1, x1)
    d.mate(p2, x2)
    return fr.build(parts, d.draft(), layout_trigger_document())


def mixed() -> fr.BuildResult:
    """Condition 3: a unit with a line interface X1 and a single-wire interface X2."""
    parts, d = _design()
    cab, (x1, x2) = _unit(d, "cab", ("X1", "X2"))
    fld = d.location("FLD", "Field")
    group = d.group("F", "Field")
    q1 = d.item("DEMO-CONN-2P", tag="Q1", at=fld, group=group)
    _harness(d, "W3", x1, q1, cab)
    relay = d.item("DEMO-RLY-2CO-24", tag="K1", at=fld, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(x2["1"], relay.fn("coil")["A1"])
    wire(x2["2"], relay.fn("coil")["A2"])
    return fr.build(parts, d.draft(), layout_trigger_document())


def field_cable() -> fr.BuildResult:
    """Defect 1 (pump p03's -W1): a cable from the terminals at its columns' top to the field."""
    parts, d = _design()
    c1 = d.location("C1", "Cabinet")
    group = d.group("P1", "Pump 1")
    m1 = d.item("DEMO-MOTOR-4KW", tag="M1", at=d.location("F1", "Field"), group=group)
    x1 = d.strip("X1", at=c1)
    terminals = [x1.terminal("DEMO-TB-2.5", group=group) for _ in range(4)]
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=group)
    lamp = d.item("DEMO-LAMP-24", tag="H1", at=c1, group=group)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(terminals[0].inner, q1["1"])
    wire(terminals[1].inner, lamp["1"])
    wire(terminals[2].inner, lamp["2"])
    wire(terminals[3].inner, q1["2"])
    w1 = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=12000)
    for core, (terminal, port) in enumerate(zip(terminals, ("U", "V", "W", "PE"), strict=True), 1):
        w1.core(core, terminal.outer, m1[port])
    return fr.build(parts, d.draft(), layout_trigger_document())


def owned_by_nested() -> fr.BuildResult:
    """Risk 9a (layout-0158): nested unit `io`'s own harness W7, whose plug is `io`'s boundary.

    Its cores run to the parent cabinet's terminals X2, so both its ends stand on the cabinet's
    sheet; `io`'s own sheet holds only the plug.
    """
    parts, d = _design()
    u = d.scope("cab").unit("demo-cab", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = u.location("CAB", "Cabinet")
    x2 = u.strip("X2", at=cab)
    field = [x2.terminal("DEMO-TB-2.5", group=u.group("FLD", "Field wiring")) for _ in range(2)]
    for terminal in field:
        u.boundary(terminal)
    n = u.scope("io", at=cab).unit("demo-io-board", revision=3, interface="2")
    n.revision(3, date="2026-01-01", text="First release", created="XX")
    board_group = n.group("BRD", "I/O board")
    board = n.item("DEMO-PCB-IO", name="board", group=board_group)
    x1 = n.item("DEMO-CONN-2P", tag="X1", parent=board, group=board_group)
    k1 = n.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=board_group)
    wire = n.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    group = n.group("W7", "Board cable")
    harness = n.harness(name="w7", tag="W7", group=group)
    plug = n.item("DEMO-CONN-2P", tag="W7P1", parent=harness, group=group)
    n.mate(plug, x1)
    n.boundary(plug)
    cable = n.cable("DEMO-CBL-4G1.5", name="w7c", parent=harness)
    cable.core(1, plug["1"], field[0].inner)
    cable.core(2, plug["2"], field[1].inner)
    return fr.build(parts, d.draft(), layout_trigger_document())
