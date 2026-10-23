"""A mate whose halves fall in two drawing sets keeps a cut end in each (UNIT-SCOPE, Q02)."""

from pathlib import Path
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from conventions_fixtures import house
from fransys_el import build, symbol_kit
from fransys_el.placement_markers import pin_ports
from fransys_el.placement_sets import bare_pins, cut_lines, drawing_scopes, restrict
from fransys_el.write_stubs import stub_ends

from electrical_symbols import LIBRARY

_PROJECT: dict[str, Any] = {
    "title": "Mate",
    "number": "P-1",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _design(*, unit_plug: bool):
    """Plug P1 of harness -W3 mated to X1 (in a unit, or at top level); P2 mated to K1."""
    parts = fransys_parts.load_path(Path("examples/demo-parts/demo_parts"))
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    ext, group = d.location("EXT", "External"), d.group("NET", "Network")
    if unit_plug:
        u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        x1 = u.item("DEMO-CONN-2P", tag="X1", at=u.location("C1", "Cabinet"), group=group)
        u.boundary(x1)
    else:
        x1 = d.item("DEMO-CONN-2P", tag="X1", at=ext, group=group)
    w3 = d.harness(name="w3", tag="W3", at=ext, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=ext, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=ext, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=ext)
    for core in (1, 2):
        cable.core(core, p1[str(core)], p2[str(core)])
    k1 = d.item("DEMO-CONN-2P", tag="K1", at=ext, group=group)
    d.mate(p1, x1)
    d.mate(p2, k1)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _sets(model):
    kit = symbol_kit(model, LIBRARY)
    problem = build(model, kit, house(), LIBRARY)[0]
    bare = bare_pins(model, kit)
    return model, [
        (s, restrict(problem, s, bare, cut_lines(model, kit))) for s in drawing_scopes(model, kit)
    ]


@pytest.fixture(scope="module")
def across():
    return _sets(_design(unit_plug=True))


@pytest.fixture(scope="module")
def whole():
    return _sets(_design(unit_plug=False))


def _named(sym: str) -> str:
    return sym.split(" ", maxsplit=1)[0]


def test_a_mate_across_two_sets_keeps_a_cut_end_in_each(across) -> None:
    _, sets = across
    unit_sets = [p for s, p in sets if s.of_unit is not None]
    top_sets = [p for s, p in sets if s.of_unit is None]
    assert len(unit_sets) == 1 == len(top_sets)
    (unit_set,), (top_set,) = unit_sets, top_sets
    assert {_named(c.pin.sym) for n in unit_set.nets for c in n.cut} == {"X1"}
    assert {_named(c.pin.sym) for n in top_set.nets for c in n.cut} == {"W3-P1"}
    assert len(unit_set.nets) == 2 == len(top_set.nets)
    assert all(tuple(c.pin for c in n.cut) == n.pins for n in unit_set.nets)


def test_the_half_with_no_conductor_names_the_far_end_through_the_mate(across) -> None:
    model, sets = across
    (unit_set,) = (p for s, p in sets if s.of_unit is not None)
    kit = symbol_kit(model, LIBRARY)
    ports = pin_ports(model, kit)
    for net in unit_set.nets:
        ends = stub_ends(model, ports[net.cut[0].pin])
        assert ends is not None
        near, far, carrier = ends
        assert far != near
        assert carrier is not None


def test_a_mate_whole_in_one_set_is_unchanged(whole) -> None:
    _, sets = whole
    assert len(sets) == 1
    (_, part) = sets[0]
    assert all(n.cut == () for n in part.nets)
    assert len(part.facts.mates) == 4


def test_the_cut_pins_of_one_connector_of_one_harness_share_a_line_key(across) -> None:
    """R481: X1's pins leave by the same line -W3, so the core draws them in one stub."""
    _, sets = across
    (unit_set,) = (p for s, p in sets if s.of_unit is not None)
    lines = {c.line for n in unit_set.nets for c in n.cut}
    assert len(unit_set.nets) == 2
    assert len(lines) == 1
    assert "" not in lines
