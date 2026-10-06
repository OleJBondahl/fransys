"""ROOT-PORT measure: what a unit's own drawing set prints for a port of the unit's sole root.

Designer ruling 2026-09-25: in a unit's OWN set a port held by the unit's own root
(`is_own_unit_root`) prints without the root's tag, on drawings and in lists alike (`-X1:1`, not
`-U2-X1:1`); the parent's set keeps the root's tag. The lists already pass `unit=` to
`port_designation` (`connector_rows`, `terminal_rows`, `wire_rows`). One test per root-port
kind compares the text the own set DRAWS (`label_text`, `marker_text`) with the text the LISTS print
for the same port, never with `port_designation` itself. A row of lone pins names its connector once
(`tag.conn`): on the own set `-X1`, on the parent's `-U2-X1` (decision model-0073). The off stub in
an own set that names a root pin is not measured here (UNIT-DRAWING step 3 removes those stubs).

Kinds: K1 a device with two labelled connector functions, K2 a device with one, K3 a terminal-kind
function of a device root, K4 a terminal strip that is the unit's sole root, K5 the coil and contact
functions of a relay root. Every fixture is a top-level unit built from the demo parts alone.

Can-fail: `test_the_comparison_flags_a_root_tag_mismatch` proves the comparison helper reports a
difference. The own-set `..._row_of_lone_pins_...` test and the `..._row_header_of_a_top_level_...`
test fail on the base commit on their own assertion line, which is the measurement; the other tests
guard the texts that must not change (K2 to K5, the pin views, the parent's stubs).
"""

import functools
from dataclasses import replace
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_layout.engines.schematic.read.tag_texts import tag_texts
from fransys_layout.stages import LabelKind as StageLabelKind
from fransys_layout.stages import LabelRequest
from fransys_layout.stages.tags import pin_tag
from fransys_model.derive import is_own_unit_root, item_designation
from fransys_model.derive.drawing_text import label_text, marker_text
from fransys_model.derive.queries import connector_rows, terminal_rows, wire_rows
from fransys_model.derive.wire_ends import ordered_wire_ends
from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    LinkMarker,
    Page,
    StarKind,
    layout_of,
)
from fransys_model.vocab.membership import unit_own_roots
from fransys_model.vocab.tables import conductors, functions, items, ports, units

_PROJECT: dict[str, Any] = {
    "title": "Root port",
    "number": "P-1",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


# -- fixtures: a top-level unit `u` whose sole root is the item under test -------------------


def _start():
    """The parts, a design, a top-level device `P1` and the unit `u` with its group `G`."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    p1 = d.item("DEMO-CONN-2P", tag="P1", group=d.group("T", "Top"))
    u = d.scope("u").unit("dev", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    return parts, d, u, u.group("G", "Group"), p1


@functools.cache
def _k1():
    """K1: `DEMO-IO-2X` (connectors X1 and X2) is the sole root; its pins wire to two relays."""
    parts, d, u, g, p1 = _start()
    root = u.item("DEMO-IO-2X", tag="U2", group=g, name="root")
    ka = u.item("DEMO-RLY-2CO-24", tag="K1", parent=root, group=g, name="ka")
    kb = u.item("DEMO-RLY-2CO-24", tag="K2", parent=root, group=g, name="kb")
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(root.fn("x1")["1"], ka.fn("coil")["A1"])
    wire(root.fn("x1")["2"], ka.fn("coil")["A2"])
    wire(root.fn("x2")["1"], kb.fn("coil")["A1"])
    wire(root.fn("x2")["2"], kb.fn("coil")["A2"])
    top = d.wiring(colour="BU", gauge="0.5")
    top(root.fn("x1")["1"], p1["1"])
    top(root.fn("x2")["1"], p1["2"])
    u.boundary(root.fn("x1"))
    u.boundary(root.fn("x2"))
    return fr.build(parts, d.draft(), system_document())


@functools.cache
def _k1_pin_rows():
    """K1 again, but the root's pins have no conductor inside the unit, so its set draws a row.

    Carries `CONNECTION_NOT_DRAWN` ERROR findings (the layout's own lint on the lone pins); the
    build raises nothing, only `fr.write` would refuse it.
    """
    parts, d, u, _, p1 = _start()
    root = u.item("DEMO-IO-2X", tag="U2", group=u.group("H", "Row"), name="root")
    p2 = d.item("DEMO-CONN-2P", tag="P2", group=d.group("T2", "Top two"))
    top = d.wiring(colour="BU", gauge="0.5")
    top(root.fn("x1")["1"], p1["1"])
    top(root.fn("x1")["2"], p1["2"])
    top(root.fn("x2")["1"], p2["1"])
    top(root.fn("x2")["2"], p2["2"])
    u.boundary(root.fn("x1"))
    u.boundary(root.fn("x2"))
    return fr.build(parts, d.draft(), system_document())


@functools.cache
def _k2():
    """K2: `DEMO-CONN-2P` (one connector function) is the sole root; a lamp child hangs on it."""
    parts, d, u, g, p1 = _start()
    root = u.item("DEMO-CONN-2P", tag="J9", group=g, name="root")
    lamp = u.item("DEMO-LAMP-24", tag="L1", parent=root, group=g, name="lamp")
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(root["1"], lamp["1"])
    wire(root["2"], lamp["2"])
    d.wiring(colour="BU", gauge="0.5")(root["1"], p1["1"])
    u.boundary(root.fn("x1"))
    return fr.build(parts, d.draft(), system_document())


@functools.cache
def _k3():
    """K3: `DEMO-TB-2.5` placed as a device (no terminal facet) is the sole root."""
    parts, d, u, g, p1 = _start()
    root = u.item("DEMO-TB-2.5", tag="X9", group=g, name="root")
    lamp = u.item("DEMO-LAMP-24", tag="L1", parent=root, group=g, name="lamp")
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(root.fn("terminal")["internal"], lamp["1"])
    wire(root.fn("terminal")["external"], lamp["2"])
    d.wiring(colour="BU", gauge="0.5")(root.fn("terminal")["external"], p1["1"])
    u.boundary(root.fn("terminal"))
    return fr.build(parts, d.draft(), system_document())


@functools.cache
def _k4():
    """K4: the part-less strip `X7` is the sole root; its two terminals are the boundary."""
    parts, d, u, g, p1 = _start()
    strip = u.strip("X7")
    terminals = [strip.terminal("DEMO-TB-2.5", group=g) for _ in range(2)]
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(terminals[0].inner, terminals[1].inner)
    wire(terminals[0].outer, terminals[1].outer)
    top = d.wiring(colour="BU", gauge="0.5")
    top(terminals[0].outer, p1["1"])
    top(terminals[1].outer, p1["2"])
    for terminal in terminals:
        u.boundary(terminal)
    return fr.build(parts, d.draft(), system_document())


@functools.cache
def _k5():
    """K5: `DEMO-RLY-2CO-24` is the sole root (a coil and contacts cannot be a boundary)."""
    parts, d, u, g, _ = _start()
    root = u.item("DEMO-RLY-2CO-24", tag="K7", group=g, name="root")
    lamp = u.item("DEMO-LAMP-24", tag="L1", parent=root, group=g, name="lamp")
    lamp2 = u.item("DEMO-LAMP-24", tag="L2", parent=root, group=g, name="lamp2")
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(root.fn("coil")["A1"], lamp["1"])
    wire(root.fn("coil")["A2"], lamp["2"])
    wire(root.fn("co_1")["11"], lamp2["1"])
    wire(root.fn("co_1")["12"], lamp2["2"])
    return fr.build(parts, d.draft(), system_document())


# -- what a set draws, what the lists print ---------------------------------------------------


def _unit_root(model):
    """The one unit of `model` and its sole root, the pair `is_own_unit_root` answers True for."""
    (unit,) = units(model)
    (root,) = unit_own_roots(model, unit)
    assert is_own_unit_root(model, root, unit)
    return unit, root


def _sets(model, *, own: bool):
    """The ids of the unit's own drawing sets (`own`), or of the top-level ones."""
    return {s.id for s in layout_of(model, DrawingSet).values() if (s.unit is not None) == own}


def _labels(model, *, own: bool):
    """Every label on a page of the unit's own sets (`own`), or of the top-level sets."""
    sets = _sets(model, own=own)
    pages = {p.id for p in layout_of(model, Page).values() if p.drawing_set in sets}
    return [label for label in layout_of(model, Label).values() if label.page in pages]


def _markers(model, *, own: bool):
    """Every link marker on a page of the unit's own sets (`own`), or of the top-level sets."""
    sets = _sets(model, own=own)
    pages = {p.id for p in layout_of(model, Page).values() if p.drawing_set in sets}
    return [m for m in layout_of(model, LinkMarker).values() if m.page in pages]


def _port_named(model, function, name):
    (port,) = [p.id for p in ports(model).values() if p.function == function and p.name == name]
    return port


def _pin_drawn(model, *, own: bool):
    """`{port: text}` of every `tag.pin.<name>` label of the sets: a connector pin's full text."""
    found = {}
    for label in _labels(model, own=own):
        if label.kind is LabelKind.TAG and label.slot.startswith("tag.pin."):
            port = _port_named(model, label.function, label.slot.removeprefix("tag.pin."))
            found[port] = label_text(model, label)
    return found


def _connectors_listed(model, root, unit):
    """`{port: text}` from the connector list of the unit's own document: `-X1` + `:1`."""
    return {
        pin.port: f"{row.designation}:{pin.marking}"
        for row in connector_rows(model, root, unit=unit)
        for pin in row.pins
    }


def _wires_listed(model, unit):
    """`{port: text}` from the wire list of the unit's own document, both ends of each row."""
    found = {}
    for row in wire_rows(model, unit=unit):
        conductor = conductors(model)[row.conductor]
        end_from, end_to = ordered_wire_ends(model, conductor.a, conductor.b)
        found[end_from] = row.from_
        found[end_to] = row.to
    return found


def _mismatches(model, drawn, listed):
    """`[(port key, drawn, listed)]` for every port that both sides name and that differ."""
    return [
        (ports(model)[port].key, text, listed[port])
        for port, text in drawn.items()
        if port in listed and text != listed[port]
    ]


# -- the comparison can fail ------------------------------------------------------------------


def test_the_comparison_flags_a_root_tag_mismatch() -> None:
    """A drawn `-U2-X1:1` against a listed `-X1:1` is reported, a drawn `-X1:1` is not."""
    model = _k1().model
    port = next(iter(_wires_listed(model, _unit_root(model)[0])))
    assert _mismatches(model, {port: "-U2-X1:1"}, {port: "-X1:1"}) != []
    assert _mismatches(model, {port: "-X1:1"}, {port: "-X1:1"}) == []


# -- K1: a device with two labelled connector functions ---------------------------------------


def test_k1_the_own_set_draws_each_root_pin_as_the_lists_print_it() -> None:
    """K1: `-X1:1` in the unit's set, in the connector list and in the wire list; MATCHES."""
    result = _k1()
    assert Severity.ERROR not in {f.severity for f in result.findings}
    model = result.model
    unit, root = _unit_root(model)
    drawn = _pin_drawn(model, own=True)
    assert sorted(drawn.values()) == ["-X1:1", "-X1:2", "-X2:1", "-X2:2"]
    connectors = _connectors_listed(model, root, unit)
    wires = _wires_listed(model, unit)
    assert set(drawn) == set(connectors)
    assert set(drawn) <= set(wires)
    assert _mismatches(model, drawn, connectors) == []
    assert _mismatches(model, drawn, wires) == []


def test_k1_the_parent_set_keeps_the_roots_tag_on_its_pins_and_its_stubs() -> None:
    """K1: the top-level set draws `-U2-X1:1` on the replica and `-U2-X1:1` in the off stubs.

    Before BOUNDARY-DRAW (layout-0080) it drew a star branch marker `-U2-X2:1/2.01.4`
    for the second pin; now both boundary pins carry an off stub.
    """
    model = _k1().model
    drawn = _pin_drawn(model, own=False)
    assert sorted(v for v in drawn.values() if "-U2" in v) == [
        "-U2-X1:1",
        "-U2-X1:2",
        "-U2-X2:1",
        "-U2-X2:2",
    ]

    stubs = {marker_text(model, m) for m in _markers(model, own=False) if m.star is StarKind.OFF}
    assert stubs == {"\N{LEFTWARDS ARROW} -U2-X1:1", "\N{LEFTWARDS ARROW} -U2-X2:1"}


def test_k1_a_row_of_lone_pins_in_the_own_set_names_the_connector_as_the_list_does() -> None:
    """K1: a row of two pins draws the connector once (`tag.conn`); the list names `-X1`, `-X2`."""
    model = _k1_pin_rows().model
    unit, root = _unit_root(model)
    drawn = {
        label.function: label_text(model, label)
        for label in _labels(model, own=True)
        if label.kind is LabelKind.TAG and label.slot == "tag.conn"
    }
    listed = {row.connector: row.designation for row in connector_rows(model, root, unit=unit)}
    assert set(drawn) == set(listed)
    assert sorted(listed.values()) == ["-X1", "-X2"]
    assert drawn == listed


def test_the_row_header_of_a_top_level_set_names_the_connector_behind_the_tag() -> None:
    """A top-level set's `tag.conn` reads `-A1-X1` / `-A1-X2`, and layout measures that text.

    G2, decision model-0073: the header carries the connector segment on every set, as the pin
    views do; on the base commit both read `-A1`. No fixture of the builder draws a row of lone
    pins outside a unit's own set, so a pin's TAG label is re-slotted as `tag.conn` (the text
    render prints for a row lead) and layout's `pin_tag` (what it measures) is called on it.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cab, field = d.location("A", "Cab"), d.location("B", "Field")
    a1 = d.item("DEMO-IO-2X", tag="A1", group=d.group("H", "Row"), at=cab)
    p1 = d.item("DEMO-CONN-2P", tag="P1", group=d.group("T", "Top"), at=field)
    p2 = d.item("DEMO-CONN-2P", tag="P2", group=d.group("T2", "Top two"), at=field)
    top = d.wiring(colour="BU", gauge="0.5")
    top(a1.fn("x1")["1"], p1["1"])
    top(a1.fn("x1")["2"], p1["2"])
    top(a1.fn("x2")["1"], p2["1"])
    top(a1.fn("x2")["2"], p2["2"])
    model = fr.build(parts, d.draft(), system_document()).model
    pins = [
        label
        for label in _labels(model, own=False)
        if label.kind is LabelKind.TAG
        and label.slot == "tag.pin.1"
        and item_designation(model, functions(model)[label.function].item) == "A1"
    ]
    drawn = sorted(label_text(model, replace(label, slot="tag.conn")) for label in pins)
    assert drawn == ["-A1-X1", "-A1-X2"]
    for label in pins:
        port = _port_named(model, label.function, "1")
        request = LabelRequest(kind=StageLabelKind.TAG, subject=port, slot="tag.pin", text="")
        measured = pin_tag(tag_texts(model), request, label.function, frozenset({port}))
        assert (measured.slot, measured.text) == (
            "tag.conn",
            label_text(model, replace(label, slot="tag.conn")),
        )


# -- K2: a device with one connector function -------------------------------------------------


def test_k2_one_connector_device_root_draws_and_lists_the_same_text() -> None:
    """K2: `-J9:1` in the own set and in both lists, `-J9:1` in the parent set; MATCHES, tag kept.

    With one labelled connector `connector_segment` is empty, so no rule drops the root's tag; the
    text the ruling would leave is `:1`, which names nothing.
    """
    model = _k2().model
    unit, root = _unit_root(model)
    drawn = _pin_drawn(model, own=True)
    assert sorted(drawn.values()) == ["-J9:1", "-J9:2"]
    connectors = _connectors_listed(model, root, unit)
    wires = _wires_listed(model, unit)
    assert set(drawn) == set(connectors)
    assert set(drawn) <= set(wires)
    assert _mismatches(model, drawn, connectors) == []
    assert _mismatches(model, drawn, wires) == []
    assert {"-J9:1", "-J9:2"} <= set(_pin_drawn(model, own=False).values())


# -- K3: a terminal-kind function of a device root --------------------------------------------


def test_k3_a_device_terminal_root_draws_and_lists_the_same_text() -> None:
    """K3: strip tag `-X9` + point `internal` in the own set, `-X9:internal` in the wire list."""
    model = _k3().model
    unit, root = _unit_root(model)
    (function,) = [f.id for f in functions(model).values() if f.item == root]
    tags = {
        label.slot: label_text(model, label)
        for label in _labels(model, own=True)
        if label.kind is LabelKind.TAG
        and label.function == function
        and label.slot.startswith("tag.")
    }
    assert tags == {"tag.strip": "-X9", "tag.point": "internal"}
    port = _port_named(model, function, tags["tag.point"])
    drawn = {port: f"{tags['tag.strip']}:{tags['tag.point']}"}
    assert _mismatches(model, drawn, _wires_listed(model, unit)) == []
    assert _wires_listed(model, unit)[port] == "-X9:internal"
    parent = {
        label.slot: label_text(model, label)
        for label in _labels(model, own=False)
        if label.kind is LabelKind.TAG
        and label.function == function
        and label.slot.startswith("tag.")
    }
    assert parent == {"tag.strip": "-X9", "tag.point": "internal"}


# -- K4: a terminal strip that is the unit's sole root ----------------------------------------


def test_k4_a_strip_root_draws_and_lists_each_terminal_the_same() -> None:
    """K4: `-X7:1` and `-X7:2` in the own set, the terminal list and the wire list; MATCHES.

    The strip's tag is the terminal's identity, `-X7:1`; dropping it would leave `:1`. The two
    terminals stand in one row (M12's terminal chain, a D12 run), so the set draws the strip once
    (`tag.strip`) and a short `tag.point` each; the drawn text is the strip, a colon and the point.
    """
    model = _k4().model
    unit, root = _unit_root(model)

    def drawn_of(*, own: bool):
        tags = [
            label
            for label in _labels(model, own=own)
            if label.kind is LabelKind.TAG and label.slot in ("tag.strip", "tag.point")
        ]
        (strip,) = {label_text(model, lb) for lb in tags if lb.slot == "tag.strip"}
        return {
            functions(model)[lb.function].item: f"{strip}:{label_text(model, lb)}"
            for lb in tags
            if lb.slot == "tag.point"
        }

    drawn = drawn_of(own=True)
    listed = {row.terminal: row.designation for row in terminal_rows(model, root, unit=unit)}
    assert sorted(drawn.values()) == ["-X7:1", "-X7:2"]
    assert drawn == listed
    wires = {
        functions(model)[ports(model)[p].function].item: text
        for p, text in _wires_listed(model, unit).items()
    }
    assert wires == listed
    assert sorted(drawn_of(own=False).values()) == ["-X7:1", "-X7:2"]


# -- K5: the coil and contact functions of a relay root ---------------------------------------


def test_k5_a_relay_root_draws_and_lists_each_port_with_the_roots_tag() -> None:
    """K5: tag `-K7` + marking `A1` in the own set, `-K7:A1` in the wire list; MATCHES, tag kept.

    A coil or a contact cannot be a boundary (`BOUNDARY_KIND`), so the parent's set draws nothing
    of this root.
    """
    model = _k5().model
    unit, root = _unit_root(model)
    tag_of = {}
    marking_of = {}
    for label in _labels(model, own=True):
        if label.kind is LabelKind.TAG and label.slot == "tag":
            tag_of[label.function] = label_text(model, label)
        if label.kind is LabelKind.MARKING:
            marking_of[label.port] = label_text(model, label)
    listed = _wires_listed(model, unit)
    drawn = {
        port: f"{tag_of[ports(model)[port].function]}:{marking}"
        for port, marking in marking_of.items()
        if port in listed
        and ports(model)[port].function in tag_of
        and functions(model)[ports(model)[port].function].item == root
    }
    assert sorted(drawn.values()) == ["-K7:11", "-K7:12", "-K7:A1", "-K7:A2"]
    assert _mismatches(model, drawn, listed) == []
    assert not [
        label
        for label in _labels(model, own=False)
        if label.function is not None
        and items(model)[functions(model)[label.function].item].id == root
    ]
