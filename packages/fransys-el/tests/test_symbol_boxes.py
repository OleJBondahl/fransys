"""`symbol_kit` gives a generic box to a function no symbol draws (el-0006, over KIT-FACTS).

A lone boxed function is a box over its port names; two boxed functions of one item are one item
box on the lead, its ports named by `derive.box_port_text`.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from fransys_el import symbol_kit
from placement_fixtures import leads
lazy from fransys_el.placement_kit import Pick

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY
from fransys_model.derive import box_port_text
from fransys_model.vocab import functions, items, ports
lazy from fransys_model.kernel import Model

if TYPE_CHECKING:
    from pathlib import Path

_PINS = ("CH01-", "CH02-", "CH03-")


def _build() -> Model:
    d = fr.design("demo_parts")
    d.device("A1", None, pins=_PINS, external=True)
    d.device("B1", "DEMO-PROX-PNP")
    return fr.build(d).model


def _picks() -> tuple[Model, dict[str | None, Pick]]:
    model = _build()
    kit = symbol_kit(model, LIBRARY)
    tag = {f.id: items(model)[f.item].tag for f in functions(model).values()}
    return model, {tag[f]: pick for f, pick in leads(kit).items() if pick.key == GENERIC_BOX_KEY}


def test_a_lone_boxed_function_is_a_box_over_its_port_names() -> None:
    model, boxes = _picks()
    pick = boxes["A1"]
    assert sorted(pick.ports.values()) == sorted(_PINS)
    assert pick.members == ()
    assert len(pick.ports) == len(_PINS)
    assert set(pick.ports) <= set(ports(model))


def test_two_boxed_functions_of_one_item_are_one_box_named_by_box_port_text() -> None:
    model, boxes = _picks()
    pick = boxes["B1"]
    names = {f.name for f in functions(model).values() if items(model)[f.item].tag == "B1"}
    assert len(pick.members) == 1
    assert len(names) == 2
    expected = {
        box_port_text(f.name, p.name)
        for f in functions(model).values()
        if items(model)[f.item].tag == "B1"
        for p in ports(model).values()
        if p.function == f.id
    }
    assert set(pick.ports.values()) == expected


def _b1_pins(*, hide: bool) -> set[str]:
    """B1's box pin names with only its power pin 1 wired, whether the box is the item's (`power.3`) or the lone function's (`3`)."""
    d = fr.design("demo_parts")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    sensor = d.device("B1", "DEMO-PROX-PNP")
    d.series(sensor.power["1"], d.device("P1", "DEMO-LAMP-24")["1"])
    result = fr.build(d)
    expect_codes(result, "FUNCTION_HALF_CONNECTED", "WIRE_ROW_UNRESOLVED")
    tag = {f.id: items(result.model)[f.item].tag for f in functions(result.model).values()}
    picks = {tag[f]: p for f, p in leads(symbol_kit(result.model, LIBRARY)).items() if p.key == GENERIC_BOX_KEY}
    return {name.rsplit(".", 1)[-1] for name in picks["B1"].ports.values()}


def test_an_unused_box_pin_is_drawn_only_with_hide_off() -> None:
    """KI-148 hide half: `box_picks` asks `derive.port_is_unused`, so a bare pin of a half-wired box is no pick port under hide."""
    shown, hidden = _b1_pins(hide=False), _b1_pins(hide=True)
    assert "3" in shown
    assert "3" not in hidden
    assert "1" in hidden


class _Io(NamedTuple):
    x1: fr.Device


@fr.unit("demo-idle-red", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _idle_box(u: fr.Design) -> _Io:
    u.layout.profile(hide_unused_pins=True)
    u.device("P1", "DEMO-LAMP-24")
    return _Io(u.device("X1", "DEMO-RED-2IN", interface=True))


def test_a_hiding_unit_draws_its_idle_interface_boundary_without_a_placement_problem(tmp_path: Path) -> None:
    """The box leaves an idle interface device's pins off, so the unit boundary asks no pin of them (PLACEMENT_PROBLEM)."""
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_idle_box, "U1")
    cover = tmp_path / "c.md"
    cover.write_text("# C\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "demo-idle-red", cover=cover), fr.document(preset, cabinet, cover=cover))
    assert "PLACEMENT_PROBLEM" not in {f.code for f in result.findings}
