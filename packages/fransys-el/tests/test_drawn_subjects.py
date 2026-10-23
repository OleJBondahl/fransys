"""`drawn_subjects` gives a drawn symbol's lead function from the kit's picks (R468 S2)."""

import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import drawn_subjects, symbol_kit
from fransys_el.drawn_ids import core_symbol_id
from fransys_el.placement_ids import symbol_ids

from electrical_symbols import LIBRARY
from fransys_model.derive import function_item, item_designation, port_function
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port

pytestmark = pytest.mark.rule("DRAWING-SUBJECT")


@cache
def _built():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k = d.device("K1", "DEMO-CTR-3P-NC")
        lamp = d.device("P1", "DEMO-LAMP-24")
        psu = d.device("T1", "DEMO-PSU-24-OK")
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
    d.detail.wire(k.coil["A1"], lamp.lamp["1"], wire=(BU, 0.5))
    d.detail.wire(k.aux["14"], psu.output["+"], wire=(BU, 0.5))
    d.detail.wire(strip[1].outer, lamp.lamp["2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    model = result.model
    return model, result.drawings, drawn_subjects(model, symbol_kit(model, LIBRARY))


def _designations(model, subjects) -> set[str]:
    return {item_designation(model, function_item(model, f)) for f in subjects.values()}


def test_each_picked_symbol_drawn_has_its_lead_function() -> None:
    model, drawings, subjects = _built()
    drawn = {s.id for d in drawings.values() for s in d.symbols}
    assert {s for s in subjects if s in drawn}
    assert {"K1", "P1", "T1"} <= _designations(model, subjects)
    assert set(subjects.values()) <= set(functions(model))


def test_a_power_symbol_is_absent() -> None:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("R", 2, bridged=True)
        d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
        lamp = d.device("P1", "DEMO-LAMP-24")
    d.detail.wire(rail[1].outer, lamp.lamp["1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    built = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    subjects = drawn_subjects(built.model, symbol_kit(built.model, LIBRARY))
    power = [s for dr in built.drawings.values() for s in dr.symbols if s.key == "power-supply"]
    assert power
    assert not {s.id for s in power} & set(subjects)


def test_a_terminal_has_a_subject() -> None:
    _, drawings, subjects = _built()
    terminals = [s for d in drawings.values() for s in d.symbols if s.key == "terminal"]
    assert terminals
    assert all(s.id in subjects for s in terminals)


def test_a_text_owner_is_a_drawn_symbol_with_a_subject() -> None:
    _, drawings, subjects = _built()
    texts = [t for d in drawings.values() for t in d.texts]
    owned = [t for t in texts if t.owner is not None]
    assert owned
    assert all(t.owner in subjects for t in owned)


def test_a_pin_view_gives_the_function_of_its_port() -> None:
    d = fr.design("demo_parts", place="EXT")
    ext = d.location("EXT", "External")
    switch = d.device("K1", "DEMO-SWITCH-2P", external=True)
    harness = d.harness("W3")
    near = d.device(None, "DEMO-CONN-2P", name="p1", parent=harness)
    far = d.device(None, "DEMO-CONN-2P", name="p2", parent=harness)
    cable = d.cable("W1", "DEMO-CBL-4G1.5", name="c", parent=harness, length_m=3)
    cable.core(1, near.x1["1"], far.x1["1"])
    d.mate(far, switch.x1)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    built = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, ext, cover=cover))
    kit = symbol_kit(built.model, LIBRARY)
    subjects = drawn_subjects(built.model, kit)
    pins = [k for k in symbol_ids(built.model, kit) if k in ports(built.model)]
    assert pins
    assert set(subjects.values()) <= set(functions(built.model))
    lead = symbol_ids(built.model, kit)
    for k in pins:
        assert subjects[core_symbol_id(lead[k])] == port_function(built.model, cast("Id[Port]", k))
