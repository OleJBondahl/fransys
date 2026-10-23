"""`symbol_kit` gives a generic box to a function no symbol draws (el-0006, over KIT-FACTS).

A lone boxed function is a box over its port names; two boxed functions of one item are one item
box on the lead, its ports named by `derive.box_port_text`.
"""

import fransys as fr
from fransys_el import Pick, symbol_kit
from placement_fixtures import leads

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY
from fransys_model.derive import box_port_text
from fransys_model.vocab import functions, items, ports
lazy from fransys_model.kernel import Model

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
