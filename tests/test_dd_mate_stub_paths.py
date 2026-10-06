"""D10 (layout deep dive): the branches of `stages/offstubs.py` and `read/offstubs.py`, one by one.

`test_dd_mate_stub.py` covers the worked example (a cabinet connector mated across a location
to a harness plug, the core plug to plug, the far plug mated to a device). These cases cover
what it does not: a core with no carrier, a far plug with no mate, a mate inside one
location (still stubbed, since the pin is a top-level unit's boundary), a mate whose plug pin
carries no core, and the two small helpers on their own.
Each test reads `read_inputs` (the stage inputs the stub is written into), never the layout.
"""

import dataclasses
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.offstubs import end_text, far_maps, off_reads
from fransys_layout.stages.offstubs import bridge, crosses_location, mate_stub
from fransys_layout.stages.types import EDGE_KIND, StubText
from fransys_model.derive.designation import item_designation, own_designation_or_none
from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import conductors, functions, items, mates, ports

_PROJECT: dict[str, Any] = {
    "title": "Mate stub paths",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(*, bare: bool = False, far_mate: bool = True, one_location: bool = False):
    """Cabinet connector X1 mated to plug P1 of harness W3; core P1 to P2; P2 mated to K1.

    `bare` runs a bare wire, with no carrier, instead of a cable core. `far_mate` False leaves
    P2 unmated. `one_location` puts the whole harness and K1 in the cabinet's location.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=u.group("NET", "Network"))
    u.boundary(x1)
    ext, group = d.location("EXT", "External"), d.group("NET", "Network")
    where = c1 if one_location else ext
    w3 = d.harness(name="w3", tag="W3", at=where, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=where, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=where, group=group)
    k1 = d.item("DEMO-CONN-2P", tag="K1", at=where, group=group)
    if bare:
        wire = d.wiring(colour="BU", gauge="0.5")
        wire(p1["1"], p2["1"])
    else:
        cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=where)
        cable.core(1, p1["1"], p2["1"])
    d.mate(p1, x1)
    if far_mate:
        d.mate(p2, k1)
    return fr.build(parts, d.draft()).model


def _pin_pair(model, inputs):
    """The specs of X1's pin 1 and of the plug pin mated to it, and their ports."""
    tag = {spec.function: item_designation(model, spec.item) for spec in inputs.functions}
    name = {spec.function: ports(model)[spec.function].name for spec in inputs.functions}
    spec_of = {spec.function: spec for spec in inputs.functions}
    for pair in inputs.mates:
        for near, far in ((pair.a, pair.b), (pair.b, pair.a)):
            if tag.get(near) == "X1" and name[near] == "1":
                return spec_of[near], spec_of[far]
    msg = "no mate at X1 pin 1"
    raise AssertionError(msg)


def _x1_texts(model, inputs):
    """The stub `PortText`s written for a pin of X1."""
    return [
        t
        for t in inputs.off_texts
        if item_designation(model, functions(model)[ports(model)[t.port].function].item) == "X1"
    ]


def test_a_core_with_no_carrier_stubs_with_no_cable_and_ends_at_the_far_device() -> None:
    """A bare wire: the stub text has an empty cable and the `OffEnd` no carrier."""
    # UNDO: engines/schematic/read/offstubs.py: `end_text` reads `record.carrier`
    #   as the harness (`carrier = "w3"`) instead of `None` for a wire with none
    model = _build(bare=True)
    inputs = read_inputs(model)
    (text,) = _x1_texts(model, inputs)
    (end,) = (e for e in inputs.off_ends if e.port == text.port)
    assert end.carrier is None
    assert (text.text.cable, text.text.far) == ("", "+EXT-K1")
    assert item_designation(model, functions(model)[ports(model)[end.far].function].item) == "K1"


def test_a_cable_core_names_the_outermost_carrier() -> None:
    """The core's carrier is the cable -W3C inside the harness: the `OffEnd` names the harness."""
    # UNDO: engines/schematic/read/offstubs.py: `end_text`'s carrier walk stops
    #   after reading `record.carrier` (no `while` loop), so the carrier is the cable, not -W3
    model = _build()
    inputs = read_inputs(model)
    (text,) = _x1_texts(model, inputs)
    (end,) = (e for e in inputs.off_ends if e.port == text.port)
    assert end.carrier is not None
    assert item_designation(model, end.carrier) == "W3"
    assert text.text.cable == "-W3"


def test_a_far_plug_with_no_mate_is_named_itself() -> None:
    """P2 mated to nothing: no transparency, the stub names P2's own port."""
    # UNDO: engines/schematic/read/offstubs.py: `end_text` looks the far port up
    #   with `mated.get(...) or K1` (a fixed partner), so a plug with no mate reads as K1
    model = _build(far_mate=False)
    inputs = read_inputs(model)
    (text,) = _x1_texts(model, inputs)
    (end,) = (e for e in inputs.off_ends if e.port == text.port)
    far = functions(model)[ports(model)[end.far].function]
    assert own_designation_or_none(model, items(model)[far.item]) == "P2"


def test_a_mate_inside_one_location_stubs_a_top_level_units_pin() -> None:
    """Everything in the cabinet's location: the mate crosses no location, yet X1 is the
    boundary pin of a top-level unit and its mate stands in no unit, so the pin gets the stub
    (units spec U2, layout-0080): the unit rule, not the location rule, writes it."""
    # UNDO: stages/offstubs.py: `ends_in_stubs` returns only
    #   `crosses_location(a, b)` (no stub for a boundary pin whose far end is outside its unit)
    model = _build(one_location=True)
    inputs = read_inputs(model)
    assert [t.text for t in _x1_texts(model, inputs)] == [
        StubText(cable="-W3", far="+C1-K1", port=":1")
    ]
    x1, p1 = _pin_pair(model, inputs)
    assert not crosses_location(x1, p1)


def test_a_mate_whose_plug_pin_ends_no_conductor_gives_none() -> None:
    """`mate_stub` with no conductor of `within` at the plug pin returns `None`."""
    # UNDO: stages/offstubs.py: `mate_stub` indexes
    #   `ending[0]` without the `if not ending` return (an IndexError)
    model = _build()
    inputs = read_inputs(model)
    x1, p1 = _pin_pair(model, inputs)
    reads = off_reads(model, far_maps(model))
    assert mate_stub((), (x1, p1), (x1.function, p1.function), reads) is None
    found = mate_stub(inputs.connections, (x1, p1), (x1.function, p1.function), reads)
    assert found is not None


def test_a_mate_stub_is_the_bridge_and_the_conductors_end_moved_to_the_pin() -> None:
    """The stub connection ends at the pin and a stand-in; its text and `OffEnd` are the pin's."""
    # UNDO: stages/offstubs.py: `mate_stub` returns the text and
    #   the `OffEnd` without `dataclasses.replace(..., port=near)` (they keep the plug pin's port)
    model = _build()
    inputs = read_inputs(model)
    x1, p1 = _pin_pair(model, inputs)
    maps = far_maps(model)
    reads = off_reads(model, maps)
    found = mate_stub(inputs.connections, (x1, p1), (x1.function, p1.function), reads)
    assert found is not None
    connection, text, end = found
    assert x1.function in (connection.a.port, connection.b.port)
    assert EDGE_KIND in (connection.a.function.kind, connection.b.function.kind)
    assert text.port == x1.function
    assert end.port == x1.function
    assert (text, end) != end_text(model, maps, connection, p1.function)
    assert connection == bridge(connection, x1.function, p1.function)


def _build_two_wires(*, n_to_p2: int, n_to_k2: int):
    """X1 mated to P1; two bare wires leave P1 pin 1, one to P2 (mated to K1), one to a jumper K2.

    The wires' `n` is part of their authoring key, so it sets the handle and not the ends.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=u.group("NET", "Network"))
    u.boundary(x1)
    ext, group = d.location("EXT", "External"), d.group("NET", "Network")
    w3 = d.harness(name="w3", tag="W3", at=ext, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=ext, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=ext, group=group)
    k1 = d.item("DEMO-CONN-2P", tag="K1", at=ext, group=group)
    k2 = d.item("DEMO-CONN-2P", tag="K2", at=ext, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(p1["1"], p2["1"], n=n_to_p2)
    wire(p1["1"], k2["1"], n=n_to_k2)
    d.mate(p1, x1)
    d.mate(p2, k1)
    return fr.build(parts, d.draft()).model


def test_the_conductor_a_mate_stub_names_does_not_depend_on_a_handle() -> None:
    """Two conductors end at the plug pin: renaming their keys must not change the stub text."""
    # UNDO: stages/offstubs.py: `mate_stub` orders the conductors
    #   at the pin by `key=lambda c: c.handle` alone (hash order), not by the far end first
    texts = []
    for n_to_p2, n_to_k2 in ((1, 2), (2, 1), (5, 3), (3, 5)):
        model = _build_two_wires(n_to_p2=n_to_p2, n_to_k2=n_to_k2)
        (text,) = _x1_texts(model, read_inputs(model))
        texts.append(text.text)
    assert len(set(texts)) == 1


def _old_end(model, c, near):
    """The end text as `_off_texts` built it before `far_maps`: mates and ports rebuilt inline."""
    record = conductors(model)[c.handle]
    carrier = record.carrier
    while carrier is not None and items(model)[carrier].parent is not None:
        carrier = items(model)[carrier].parent
    cable = "" if carrier is None else "-" + item_designation(model, carrier)
    mated = {}
    for mate in mates(model).values():
        mated[mate.a], mated[mate.b] = mate.b, mate.a
    by_name = {(p.function, p.name): p.id for p in ports(model).values()}
    far = record.b if near == record.a else record.a
    far = by_name.get((mated.get(ports(model)[far].function), ports(model)[far].name), far)
    head, tail = stub_far_end(model, far)
    return StubText(cable=cable, far=head, port=tail), carrier, far


def test_far_maps_map_by_function_and_name_and_end_text_equals_the_inline_build() -> None:
    """`far_maps` keys ports by `(function, name)`, mates both ways; `end_text` reads no more."""
    # UNDO: engines/schematic/read/offstubs.py: `far_maps` keys `by_name` by
    #   `(p.function, p.id)` instead of `(p.function, p.name)`, or fills `partner` one way only
    for kwargs in ({}, {"bare": True}, {"far_mate": False}, {"one_location": True}):
        model = _build(**kwargs)
        maps = far_maps(model)
        assert all(
            maps.by_name[function, record.name] == port
            for port, record in ports(model).items()
            for function in (record.function,)
        )
        assert len(maps.by_name) == len(ports(model))
        assert all(maps.partner[b] == a and maps.partner[a] == b for a, b in maps.partner.items())
        assert len(maps.partner) == 2 * len(mates(model))
        for c in read_inputs(model).connections:
            for near in (c.a.port, c.b.port):
                text, end = end_text(model, maps, c, near)
                assert (text.text, end.carrier, end.far) == _old_end(model, c, near)


def test_crosses_location_needs_two_specs_each_in_a_location() -> None:
    """`None`, an empty location path, the same location and two locations."""
    # UNDO: stages/offstubs.py: `crosses_location` drops the
    #   `not a.location_path or not b.location_path` test (an IndexError on the empty path)
    model = _build()
    x1, p1 = _pin_pair(model, read_inputs(model))
    bare = dataclasses.replace(p1, location_path=())
    assert crosses_location(x1, p1)
    assert not crosses_location(x1, x1)
    assert not crosses_location(None, p1)
    assert not crosses_location(x1, None)
    assert not crosses_location(bare, p1)
    assert not crosses_location(x1, bare)
