"""Field case: six output channels each drive a relay coil in a second group, with a wide row spacing (400) as a consumer's cabinet used.
The bug: the fit gate refused every coil at 400 spacing and counted the column's own coil twice, so each coil stood on another page.
Fixed by layout-0208 (amended by R1), the fit gate never sends a channel's coil back; a too-tall column continues (LC1, layout-0215)."""

from functools import cache
from typing import Any

import fransys as fr
import pytest
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU
from fransys_el.drawn_identity import net_text

from electrical_symbols import MARKER_TURNED, marker_symbol
from fransys_model.derive import net_of
from fransys_model.vocab.tables import functions, items, ports

COUNT = 6
PINS = tuple(f"CH{j:02d}-" for j in range(1, COUNT + 1))
MARKER_KEYS = {marker_symbol("tag"), MARKER_TURNED}


@cache
def _built() -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True)
    with d.function("PLC", "Controller"):
        plc = d.device("A1", None, pins=PINS, external=True)
    with d.function("B", "Relays"):
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", COUNT).run("R", COUNT, bridged=True)
        relays = [d.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(COUNT)]
        for i, relay in enumerate(relays):
            d.series(plc[PINS[i]], relay.coil["A1"], wire=(BU, 0.5))
            d.series(relay.coil["A2"], rail[i + 1].outer, wire=(BU, 0.5))
    with d.function("L", "Loads"):
        live = d.terminal_strip("X3", "DEMO-TB-2.5-TWIN", 3).run("R", 3, bridged=True)
        for i, relay in enumerate(relays):
            lamp = d.device(f"P{i + 1}", "DEMO-LAMP-24")
            d.series(relay.co_1["14"], lamp.lamp["1"], wire=(BU, 0.5))
            d.series(lamp.lamp["2"], live[i // 2 + 1].outer, wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc).model


def _tagged(model) -> dict[Any, tuple[Any, Any]]:
    """Each function's (item tag, function name)."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    return {f.id: (tag_of[f.item], f.name) for f in functions(model).values()}


def _drawn(model) -> dict[Any, Any]:
    """Each drawn symbol by its item tag and its function's id."""
    return {(one.tag, one.owner): one for one in symbol_subjects(model)}


def test_every_coil_stands_under_its_channel_pin() -> None:
    model = _built()
    named = _tagged(model)
    drawn = _drawn(model)
    (box,) = (s for s in drawn.values() if s.key == "generic-box" and s.tag == "A1")
    coil_of = {named[f][0]: drawn[(named[f][0], f.value)] for f in named if named[f][1] == "coil"}
    for i, pin in enumerate(PINS, start=1):
        coil = coil_of[f"K{i}"]
        assert coil.page == box.page, i
        assert coil.x == box.x + dict(box.offsets)[pin], i  # the coil's `in` pin is at its origin x
        assert coil.y > box.y, i
    assert len({s.y for s in coil_of.values()}) == 1  # one row: the chained coil too


def test_no_marker_stands_at_a_channel_or_its_coil() -> None:
    """No coil has a reference back to the module: each channel wire is drawn as a wire."""
    model = _built()
    by_id = ports(model)
    named = _tagged(model)
    drawings = list(drawn_pages(model).values())
    routed = {w.net for d in drawings for w in d.wires}
    ends = {pid: p for pid, p in by_id.items() if (p.name == "A1" and named[p.function][1] == "coil") or named[p.function][0] == "A1"}
    assert len(ends) >= COUNT
    assert not [s for d in drawings for s in d.symbols if s.key in MARKER_KEYS], "a channel wire is drawn as a wire, so no marker stands on any page"
    coil_a1 = [pid for pid, p in ends.items() if named[p.function][1] == "coil"]
    assert len(coil_a1) == COUNT
    nets = [net_of(model, pid) for pid in coil_a1]
    assert None not in nets
    assert {net_text(model, pid) for pid in coil_a1} <= routed


def test_the_contacts_stay_with_the_loads_they_switch() -> None:
    model = _built()
    named = _tagged(model)
    pages: dict[Any, set[Any]] = {}
    for function, thing in ((f, named[f]) for f in named):
        for one in _drawn(model).values():
            if one.owner == function.value:
                pages.setdefault(thing, set()).add(one.page)
    for i in range(1, COUNT + 1):
        assert pages[(f"K{i}", "co_1")] == pages[(f"P{i}", "lamp")]


@pytest.mark.rule("ROW-ON-GRID")
def test_every_symbol_origin_and_wire_end_x_stands_on_the_wiring_grid() -> None:
    """The row solver's positions are whole cells: a lead meets its rail at one x (KI-318, R1614 solved positions on the wiring grid)."""
    drawings = list(drawn_pages(_built()).values())
    assert [s.x for d in drawings for s in d.symbols if s.x % 8] == []
    assert [pt for d in drawings for w in d.wires for pt in (w.points[0], w.points[-1]) if pt[0] % 8] == []
