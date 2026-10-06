"""Tests: an add-on contact block prints its parent's designation and its contacts are the parent's.

Decision model-0119, amending model-0058 (CONVENTIONS-V06 V10). A child item whose functions are
all contacts, with nothing below it, no tag and no footprint, is an accessory of its parent.
"""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive import (
    bom_lines,
    designation_list,
    item_designation,
    owned_contacts,
    takes_parents_designation,
)
from fransys_model.derive.passes.numbering import number
from fransys_model.vocab.enums import FunctionKind

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item


def designation_list_ids(model: Model) -> set[Id[Item]]:
    """The item ids with a row in the designations list."""
    return {row.item for row in designation_list(model)}


def _contactor(plant: Plant) -> tuple[Id[Item], Id[Function], Id[Function], Id[Item]]:
    """A coil item `K1` with a main contact of its own, and an untagged child block."""
    contactor = plant.item("k1", part=plant.part("K"), designation="K1")
    coil = plant.function(contactor, "coil", kind=FunctionKind.COIL)
    own = plant.function(contactor, "main", kind=FunctionKind.CONTACT_NO)
    block = plant.item("block", part=plant.part("Q"), parent=contactor)
    return contactor, coil, own, block


def test_a_contacts_only_child_prints_its_parents_designation() -> None:
    """The block has two contacts and no tag; it prints `K1`, has no row, owns nothing itself."""
    plant = Plant()
    contactor, _, _, block = _contactor(plant)
    no = plant.function(block, "c53", kind=FunctionKind.CONTACT_NO)
    nc = plant.function(block, "c61", kind=FunctionKind.CONTACT_NC)
    model, _ = number(plant.model())
    assert takes_parents_designation(model, block)
    assert item_designation(model, block) == "K1"
    assert block not in designation_list_ids(model)
    assert set(owned_contacts(model, contactor)) >= {no, nc}
    assert owned_contacts(model, block) == ()


def test_a_device_owns_its_own_contacts_and_its_blocks() -> None:
    """`owned_contacts` lists the contactor's main contact and the block's, sorted by id."""
    plant = Plant()
    contactor, _, own, block = _contactor(plant)
    extra = plant.function(block, "c53", kind=FunctionKind.CONTACT_CO)
    model, _ = number(plant.model())
    owned = owned_contacts(model, contactor)
    assert owned == tuple(sorted((own, extra)))


def test_a_child_with_a_protection_function_keeps_its_own_designation() -> None:
    """An overload relay: a contact and a generic function. It is numbered and listed."""
    plant = Plant()
    contactor, _, _, _ = _contactor(plant)
    overload = plant.item("f2", part=plant.part("F"), parent=contactor)
    plant.function(overload, "protection")
    own = plant.function(overload, "c95", kind=FunctionKind.CONTACT_NC)
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, overload)
    assert item_designation(model, overload) == "F1"
    assert overload in designation_list_ids(model)
    assert owned_contacts(model, overload) == (own,)


def test_a_contact_child_with_a_coil_keeps_its_own_designation() -> None:
    """A child with a coil and a contact is a device of its own."""
    plant = Plant()
    contactor, _, _, _ = _contactor(plant)
    relay = plant.item("k2", part=plant.part("K"), parent=contactor)
    plant.function(relay, "coil", kind=FunctionKind.COIL)
    plant.function(relay, "c13", kind=FunctionKind.CONTACT_NO)
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, relay)


def test_a_block_with_an_authored_tag_keeps_it() -> None:
    """model-0058: an authored tag makes the block an ordinary item."""
    plant = Plant()
    contactor, _, _, _ = _contactor(plant)
    tagged = plant.item("q12", part=plant.part("Q"), parent=contactor, designation="Q12")
    plant.function(tagged, "c53", kind=FunctionKind.CONTACT_NO)
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, tagged)
    assert item_designation(model, tagged) == "Q12"


def test_a_block_with_a_function_below_it_is_no_accessory() -> None:
    """A contacts-only item with a child that carries a function is a device."""
    plant = Plant()
    contactor, _, _, block = _contactor(plant)
    plant.function(block, "c53", kind=FunctionKind.CONTACT_NO)
    child = plant.item("below", part=plant.part("Z"), parent=block)
    plant.function(child, "p")
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, block)
    assert contactor  # the parent is unchanged


def test_a_blocks_bom_line_stays_and_prints_the_parents_designation() -> None:
    """model-0058's accessory path: the block's part has its own line, designation `-K1`."""
    plant = Plant()
    _, _, _, block = _contactor(plant)
    plant.function(block, "c53", kind=FunctionKind.CONTACT_NO)
    block_part = plant.part("Q")
    model, _ = number(plant.model())
    (line,) = [ln for ln in bom_lines(model) if ln.part == block_part]
    assert (line.count, line.designations) == (1, ("-K1",))
    assert len(bom_lines(model)) == 2
