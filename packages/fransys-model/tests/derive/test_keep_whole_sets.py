"""Tests: `keep_whole_sets` names what is drawn together (EL-1 fact 11)."""

from decimal import Decimal

from plant import Plant

from fransys_model.derive.facts.keep_whole import keep_whole_sets
from fransys_model.kernel import Draft, Id, Origin, freeze, make_id
from fransys_model.layout import PoleGroup
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part


def _item(key: str) -> object:
    return make_id(Item, (key,))


def test_a_coil_and_its_add_on_block_are_one_set() -> None:
    """The lamp has no child, so it is in no set."""
    plant = Plant()
    coil = plant.item("coil", part=plant.part("K"), designation="K1")
    plant.item("block", part=plant.part("C"), parent=coil)
    plant.item("lamp", part=plant.part("L"))
    found = keep_whole_sets(plant.model())
    assert len(found.item_boxes) == 1
    assert found.item_boxes == (frozenset({_item("coil"), _item("block")}),)


def test_a_pole_group_is_its_functions() -> None:
    """Three one-pole contacts of one device stand as one set."""
    plant = Plant()
    item = plant.item("q1", part=plant.part("Q"))
    poles = tuple(plant.function(item, name) for name in ("p1", "p2", "p3"))
    group = PoleGroup(id=make_id(PoleGroup, ("g",)), key=("g",), functions=poles, selector=False)
    draft = Draft()
    draft.extend(plant.records, origin=Origin(file="t.py", line=1, note="x"))
    draft.extend([group], origin=Origin(file="t.py", line=2, note="x"))
    found = keep_whole_sets(freeze(draft))
    assert len(found.pole_groups) == 1
    assert found.pole_groups == (frozenset(poles),)


def _cable(plant: Plant, key: str, unit: Id[Unit]) -> Id[Item]:
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn="M",
        manufacturer="E",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, (key, "part", "product")),
        key=(key, "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(part, product)
    item = plant.item(key, part=part.id, unit=unit)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")), key=(key, "cable"), subject=item, length_mm=None
        )
    )
    return item


def test_a_unit_with_a_two_core_cable_line_is_one_set() -> None:
    """The cable draws as a line (two cores); its unit keeps its items together."""
    plant = Plant()
    unit = plant.unit("u1")
    plant.revision(unit)
    plant.unit("u2")
    cable = _cable(plant, "w1", unit)
    plant.item("dev", unit=unit)
    a, b = plant.pin("x", "f", "a"), plant.pin("x", "f", "b")
    c, d = plant.pin("y", "f", "a"), plant.pin("y", "f", "b")
    plant.core(a, c, key="c1", carrier=cable)
    plant.core(b, d, key="c2", carrier=cable)
    found = keep_whole_sets(plant.model())
    assert len(found.line_units) == 1
    assert found.line_units == (frozenset({_item("w1"), _item("dev")}),)
