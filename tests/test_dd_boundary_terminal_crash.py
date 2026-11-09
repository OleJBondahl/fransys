"""Layout-0057: two conductors of one port that leave for another location
must not crash `write_layout` ("the records put name one id twice, with different content").

A unit's boundary terminal `X1`, wired at the top level to two relays in another location: its
"""

from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import cabinet_document, layout_trigger_document, unit_document
from fransys_author.design import Design

from electrical_symbols import LIBRARY
from fransys_layout.symbols import text_room_on
from fransys_model.derive.drawing_text import marker_text
from fransys_model.derive.stub_text import off_stub_text
from fransys_model.layout import LinkMarker, StarKind, layout_of, sheet_format_of
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Boundary terminal crash",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _close_coils(d: Design, relays: Any, at: Any, group: Any, tag: str = "X2") -> None:
    """Wire each relay's coil A2 to the terminal `tag` at `at`, so no coil is half connected."""
    x2 = d.strip(tag, at=at).terminal("DEMO-TB-2.5", group=group)
    wire, last = d.wiring(colour="BU", gauge="0.5"), None
    for relay in relays:  # the first coil takes the terminal; each next coil chains to the one before (a point takes one, R1266)
        wire(relay.fn("coil")["A2"], x2.inner if last is None else last)
        last = relay.fn("coil")["A2"]


def _build(relay_pins: tuple[tuple[str, str], ...]):
    """A cabinet unit with a boundary terminal `X1` at +C1, wired at the top level to one relay
    coil pin per `relay_pins` entry `(relay tag, pin)`, the relays standing at +FLD."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    terminal = cab.strip("X1", at=c1).terminal("DEMO-TB-2.5-TWIN", group=group)
    cab.boundary(terminal)
    fld = d.location("FLD", "Field")
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {}
    for tag, pin in relay_pins:
        if tag not in relays:
            relays[tag] = d.item("DEMO-RLY-2CO-24", tag=tag, at=fld, group=group)
        wire(terminal.outer, relays[tag].fn("coil")[pin])
    _close_coils(d, [r for tag, r in relays.items() if ("A2" not in {pin for t, pin in relay_pins if t == tag})], fld, group)
    return fr.build(parts, d.draft(), layout_trigger_document(), unit_document(cab), cabinet_document(fld)).model


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
    """One port, two far devices: one stub, one box, a line each, so each far end is named (R1581)."""
    # UNDO: layout/core/cut_ledger.py `_named`: a stub end names the first far pin only (K2 never named)
    model = _build((("K1", "A1"), ("K2", "A1")))
    (stub,) = _stubs_of_x1(model)
    assert stub.partner == stub.id
    assert off_stub_text(model, stub).split("\n") == ["→ +FLD-K1:A1", "→ +FLD-K2:A1"]
    _one_box(model, stub, 2)


def _one_box(model, stub: LinkMarker, lines: int) -> None:
    """R1581: the stub is one box with a line per far end, wide enough for the lines."""
    assert len(marker_text(model, stub).split("\n")) == lines
    assert lines * text_room_on(model, sheet_format_of(model, None), LIBRARY) <= stub.width


def test_two_cables_to_one_far_port_build_and_name_both_cables() -> None:
    """Two cables from X1 to one pin of one relay: one far port, two carriers, so one stub names both cables (R1581)."""
    # UNDO: model/derive/stub_far.py: a stub end names the first conductor to a far pin only (R1590)
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    x1 = cab.strip("X1", at=c1).terminal("DEMO-TB-2.5-TWIN", group=group)
    cab.boundary(x1)
    fld = d.location("FLD", "Field")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=fld, group=group)
    _close_coils(d, [k1], fld, group)
    for name in ("ca", "cb"):
        d.cable("DEMO-CBL-4G1.5", name=name, at=c1).core(1, x1.outer, k1.fn("coil")["A1"])
    model = fr.build(parts, d.draft(), layout_trigger_document(), unit_document(cab), cabinet_document(fld)).model
    (stub,) = _stubs_of_x1(model)
    assert sorted(line.split(" ")[0] for line in off_stub_text(model, stub).split("\n")) == ["-W1", "-W2"]


def test_two_pins_of_one_relay_on_one_port_share_one_box_and_read_both() -> None:
    """One port, one far device, two pins: one stub, one box, a line for each pin (R1581)."""
    # UNDO: layout/core/cut_ledger.py `_named`: a stub end names the first far pin only (A2 never named)
    model = _build((("K1", "A1"), ("K1", "A2")))
    (stub,) = _stubs_of_x1(model)
    assert off_stub_text(model, stub).split("\n") == ["→ +FLD-K1:A1", "→ +FLD-K1:A2"]
    _one_box(model, stub, 2)
