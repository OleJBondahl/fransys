"""Tests: what operates a switch, and a switch block under a head (model-0222, OPERATED-BY O2, O4).

A head sold apart from its blocks states `operated_by` and has no function; its blocks hold
`switch` functions and print the head's designation. A complete device states it on itself.
"""

from plant import Plant

from fransys_model.derive import item_designation, operated_by, owned_contacts
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind, OperatedBy, PartCategory
from fransys_model.vocab.templates import Part


def _part(plant: Plant, name: str, operated: OperatedBy | None) -> Part:
    """Add an invented class-S part named `name` stating `operated`."""
    part = Part(
        id=make_id(Part, (name,)),
        key=(name,),
        mpn=f"EXAMPLE-{name}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="S",
        operated_by=operated,
    )
    plant.add(part)
    return part


def _head_with_blocks(head_operated: OperatedBy | None, block_operated: OperatedBy | None = None):
    """A head with two switch blocks; the plant, the head, the blocks and their switches."""
    plant = Plant()
    head = plant.item("head", part=_part(plant, "head", head_operated).id)
    block_part = _part(plant, "block", block_operated).id
    blocks = [plant.item(f"block-{n}", part=block_part, parent=head) for n in (1, 2)]
    switches = [plant.function(b, "sw", kind=FunctionKind.SWITCH) for b in blocks]
    return plant, head, blocks, switches


def test_a_switch_is_operated_by_its_nearest_holders_operator() -> None:
    plant, _, _, switches = _head_with_blocks(OperatedBy.MUSHROOM)
    model = plant.model()
    assert [operated_by(model, sw) for sw in switches] == [OperatedBy.MUSHROOM] * 2


def test_a_holder_two_levels_up_operates_the_switch() -> None:
    plant = Plant()
    head = plant.item("head", part=_part(plant, "head", OperatedBy.TURN).id)
    adapter = plant.item("adapter", part=_part(plant, "adapter", None).id, parent=head)
    block = plant.item("block", part=_part(plant, "block", None).id, parent=adapter)
    switch = plant.function(block, "sw", kind=FunctionKind.SWITCH)
    assert operated_by(plant.model(), switch) is OperatedBy.TURN


def test_a_switchs_own_part_beats_its_holder() -> None:
    plant, _, _, switches = _head_with_blocks(OperatedBy.MUSHROOM, OperatedBy.POSITION)
    assert operated_by(plant.model(), switches[0]) is OperatedBy.POSITION


def test_no_part_states_it_gives_none_and_a_contact_is_never_asked() -> None:
    plant, head, _, switches = _head_with_blocks(None)
    contact = plant.function(head, "no", kind=FunctionKind.CONTACT_NO)
    model = plant.model()
    assert operated_by(model, switches[0]) is None
    assert operated_by(model, contact) is None


def test_switch_blocks_under_a_stating_head_print_the_heads_designation() -> None:
    plant, head, blocks, _ = _head_with_blocks(OperatedBy.MUSHROOM)
    model, _ = number(plant.model())
    assert item_designation(model, head) == "S1"
    assert [item_designation(model, b) for b in blocks] == ["S1", "S1"]
    assert owned_contacts(model, head) == ()


def test_switch_children_of_a_holder_that_states_nothing_keep_their_own_designations() -> None:
    plant, head, blocks, _ = _head_with_blocks(None)
    model, _ = number(plant.model())
    texts = {item_designation(model, b) for b in (head, *blocks)}
    assert len(texts) == 3


def test_a_complete_device_under_a_stating_holder_keeps_its_own_designation() -> None:
    plant, head, blocks, _ = _head_with_blocks(OperatedBy.MUSHROOM, OperatedBy.PUSH)
    model, _ = number(plant.model())
    texts = {item_designation(model, b) for b in (head, *blocks)}
    assert len(texts) == 3
