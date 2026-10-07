"""CRASH-BOUNDARY (layout-0057): two conductors of one port that leave for another location
must not crash `write_layout` ("the records put name one id twice, with different content").

A unit's boundary terminal `X1`, wired at the top level to two relays in another location: its
`external` port carries two crossing conductors, so two off stubs stand on that one port. Each
stub names its own far end; before the fix both read the last one (`+FLD-K1:A1 A1`, K2 never
named) and both records took one key. An off stub's key names its far port where a paired
marker names its partner's port. Stubs on one port share one box (S20 M3): one lead whose
`marker_text` has a line per far end, the box wide enough for every line.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records,
`marker_text` and `off_stub_text`.
"""

from collections import Counter
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.derive.drawing_text import marker_text, off_stub_text
from fransys_model.kernel import Severity
from fransys_model.layout import LinkMarker, StarKind, layout_of, profile_of
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Boundary terminal crash",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(relay_pins: tuple[tuple[str, str], ...]):
    """A cabinet unit with a boundary terminal `X1` at +C1, wired at the top level to one relay
    coil pin per `relay_pins` entry `(relay tag, pin)`, the relays standing at +FLD."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    terminal = cab.item("DEMO-TB-2.5", tag="X1", at=c1, group=group)
    cab.boundary(terminal)
    fld = d.location("FLD", "Field")
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {}
    for tag, pin in relay_pins:
        if tag not in relays:
            relays[tag] = d.item("DEMO-RLY-2CO-24", tag=tag, at=fld, group=group)
        wire(terminal["external"], relays[tag].fn("coil")[pin])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _stubs_of_x1(model) -> list[LinkMarker]:
    """The off stubs standing on X1's `external` port."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF
        and ports(model)[m.port].name == "external"
        and functions(model)[ports(model)[m.port].function].key[:2] == ("cab", "X1")
    ]


def test_two_relays_on_one_boundary_terminal_port_build_and_each_is_named() -> None:
    """One port, two far devices: two stubs with keys of their own, each far end named once, in
    one shared box (M3)."""
    # UNDO: schematic/write/markers.py: link_markers, the off stub's far end text: every stub
    #     takes the port's last end (K2 never named, both keys equal)
    model = _build((("K1", "A1"), ("K2", "A1")))
    stubs = _stubs_of_x1(model)
    assert len(stubs) == 2
    assert len({m.id for m in stubs}) == len({m.key for m in stubs}) == 2
    assert all(m.partner == m.id for m in stubs)
    texts = sorted(off_stub_text(model, m) for m in stubs)
    assert any(text.endswith("+FLD-K1:A1") for text in texts)
    assert any(text.endswith("+FLD-K2:A1") for text in texts)
    _one_box(model, stubs)


def _one_box(model, stubs: list[LinkMarker]) -> None:
    """M3: the stubs of one port stand in one box (one `(x, y, stub_extra, width, height)`), one
    of them its lead, whose text has a line per stub, and the box is wide enough for the lines."""
    assert len({(m.x, m.y, m.stub_extra, m.width, m.height) for m in stubs}) == 1
    (lead,) = [m for m in stubs if m.lead]
    lines = marker_text(model, lead).split("\n")
    assert len(lines) == len(stubs)
    assert len(lines) * profile_of(model).text_height <= lead.width


def _build_with_marker(far: tuple[str, ...]):
    """`_build`'s X1 wired to relays at +FLD `far`, and to K4, K5 and K6 at +C1: a net of four with
    one terminal point, which drew a star with a reference marker on X1's `external` before
    layout-0080 made every conductor leaving the unit a stub. Returns the build result."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    x1 = cab.item("DEMO-TB-2.5", tag="X1", at=c1, group=group)
    cab.boundary(x1)
    fld, wire = d.location("FLD", "Field"), d.wiring(colour="BU", gauge="0.5")
    for tag in far:
        wire(
            x1["external"], d.item("DEMO-RLY-2CO-24", tag=tag, at=fld, group=group).fn("coil")["A1"]
        )
    for tag in ("K4", "K5", "K6"):
        wire(
            x1["external"], d.item("DEMO-RLY-2CO-24", tag=tag, at=c1, group=group).fn("coil")["A1"]
        )
    return fr.build(parts, d.draft(), layout_trigger_document())


def test_three_far_ends_on_one_port_share_one_box_with_a_line_each() -> None:
    """Three far devices: one box (M3) with three lines, wide for three."""
    # UNDO: stages/texts/stand.py `joined_box`: `sum(b.width for b in boxes) - trim`
    #     -> `first.width` (the box holds one line's width, the lines overprint)
    model = _build((("K1", "A1"), ("K2", "A1"), ("K3", "A1")))
    stubs = _stubs_of_x1(model)
    assert len(stubs) == 3
    _one_box(model, stubs)


def test_a_port_wired_to_five_relays_gives_all_five_stubs_one_box() -> None:
    """X1's `external` is wired to five relays, two at +FLD and three at +C1 (layout-0080): each
    conductor leaving the unit is a stub at each end, whatever the location, so the port
    carries five off stubs, one per relay, each far end named, in one shared box (M3)."""
    # UNDO: stages/texts/stand.py `joined_box`: `sum(b.width for b in boxes) - trim`
    #     -> `first.width` (the box holds one line's width, the lines overprint)
    result = _build_with_marker(("K1", "K2"))
    model = result.model
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    x1 = [
        m
        for m in layout_of(model, LinkMarker).values()
        if functions(model)[ports(model)[m.port].function].key[:2] == ("cab", "X1")
    ]
    assert Counter(m.star for m in x1) == {StarKind.OFF: 5}
    tails = [off_stub_text(model, m).rsplit("-", 1)[1] for m in x1]
    assert sorted(tails) == ["K1:A1", "K2:A1", "K4:A1", "K5:A1", "K6:A1"]
    _one_box(model, x1)


def test_two_cables_to_one_far_port_build_and_keep_two_stubs() -> None:
    """Two cables from X1 to one pin of one relay: one far port, two carriers. The key adds the
    carrier's key so the two stubs stay two records (one key made the freeze reject the id)."""
    # UNDO: schematic/write/markers.py: link_markers `reached[end.port, end.far] > 1` -> `False`
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    x1 = cab.item("DEMO-TB-2.5", tag="X1", at=c1, group=group)
    cab.boundary(x1)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=d.location("FLD", "Field"), group=group)
    for name in ("ca", "cb"):
        d.cable("DEMO-CBL-4G1.5", name=name, at=c1).core(1, x1["external"], k1.fn("coil")["A1"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    stubs = _stubs_of_x1(model)
    assert len({m.far for m in stubs}) == 1
    assert len({m.id for m in stubs}) == len({m.key for m in stubs}) == 2
    assert {off_stub_text(model, m).split(" ")[0] for m in stubs} == {"-W1", "-W2"}


def test_two_pins_of_one_relay_on_one_port_share_one_box_and_read_both() -> None:
    """One port, one far device, two pins: two stubs with keys of their own on one shared box
    whose text lists both pins."""
    # UNDO: schematic/write/markers.py: link_markers, the off stub's `star_key` value
    #     `off_key(one, end_of[...])` -> `key_to(one, one.star_partner)` (its own port again: one
    #     key for both stubs); and `_marker_fields` `box_x = one.box.x` -> `one.box.x + one.lead`
    #     (the two stubs' box_x differ)
    model = _build((("K1", "A1"), ("K1", "A2")))
    stubs = _stubs_of_x1(model)
    assert len({m.id for m in stubs}) == 2
    (box_x,) = {m.box_x for m in stubs}  # one shared box: both stubs carry the same `box_x`
    assert box_x is not None
    (text,) = {off_stub_text(model, m) for m in stubs}  # the order of the pins is derive's
    head, _, tails = text.split(" ", 1)[1].partition(":")
    assert (head, sorted(tails.split())) == ("+FLD-K1", ["A1", "A2"])
