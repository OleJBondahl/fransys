"""Tests: validator messages name things by `ref(...)`, never by authoring key (overview-0003)."""

import dataclasses

from plant import Plant

from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.validators.potential_without_supply import (
    POTENTIAL_WITHOUT_SUPPLY,
    check_potential_without_supply,
)
from fransys_model.vocab.validators.revisions import (
    REVISION_INITIALS_MISSING,
    check_revisions,
)
from fransys_model.vocab.validators.structure import CONTAINMENT_CYCLE, check_structure
from fransys_model.vocab.validators.units import MATE_NOT_CONNECTOR, check_units


def test_a_mate_to_a_coil_names_the_mate_and_the_function_by_reference() -> None:
    plant = Plant()
    item = plant.item("coil-item")
    coil = plant.function(item, "coil", kind=FunctionKind.COIL)
    plug = plant.function(plant.item("plug-item"), "plug", kind=FunctionKind.CONNECTOR)
    mate = plant.mate(plug, coil, key="the-mate")
    (finding,) = [f for f in check_units(plant.model()) if f.code == MATE_NOT_CONNECTOR]
    assert f"mate {ref(mate)} has end {ref(coil)} of kind" in finding.message
    assert "the-mate" not in finding.message


def test_a_net_without_a_supply_names_the_net_by_reference() -> None:
    plant = Plant()
    function = plant.function(plant.item("dev"), "fn")
    net = plant.net("the-net", (plant.port(function, "1"),), potential="L9")
    (finding,) = [
        f
        for f in check_potential_without_supply(plant.model())
        if f.code == POTENTIAL_WITHOUT_SUPPLY
    ]
    assert f"net {ref(net)} (" in finding.message
    assert "the-net" not in finding.message


def test_a_revision_without_initials_names_itself_as_it_prints() -> None:
    plant = Plant()
    key = ("rev-key", "revision", "7")
    plant.add(
        Revision(
            id=make_id(Revision, key),
            key=key,
            release=None,
            version=2,
            revision=7,
            date="2026-01-01",
            text="Invented",
            created="",
        )
    )
    (finding,) = [f for f in check_revisions(plant.model()) if f.code == REVISION_INITIALS_MISSING]
    assert finding.message == "revision 2.7 has no created initials"
    assert "rev-key" not in finding.message


def test_a_containment_cycle_lists_its_items_by_reference() -> None:
    plant = Plant()
    a = plant.item("item-a")
    b = plant.item("item-b", parent=a)
    first = next(record for record in plant.records if record.id == a)
    plant.records[plant.records.index(first)] = dataclasses.replace(first, parent=b)
    (finding,) = [f for f in check_structure(plant.model()) if f.code == CONTAINMENT_CYCLE]
    assert ref(a) in finding.message
    assert ref(b) in finding.message
    assert "item-a" not in finding.message
