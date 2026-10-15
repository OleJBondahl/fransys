"""Tests: `child_items` lists the items whose `parent` is the given item, in `Id` order."""

from plant import Plant

from fransys_model.derive import child_items
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.tables import items


def test_child_items_are_the_items_whose_parent_is_the_coil_in_id_order() -> None:
    """A coil with two add-on contact blocks: the blocks are its children, the lamp is not."""
    plant = Plant()
    coil = plant.item("coil", part=plant.part("K"), designation="K1")
    block_a = plant.item("contact-block-a", part=plant.part("C"), parent=coil)
    block_b = plant.item("contact-block-b", part=plant.part("C"), parent=coil)
    plant.item("lamp", part=plant.part("L"))
    model = plant.model()
    assert sum(1 for item in items(model).values() if item.parent == coil) == 2
    assert child_items(model, coil) == (
        make_id(Item, ("contact-block-a",)),
        make_id(Item, ("contact-block-b",)),
    )
    assert block_a == make_id(Item, ("contact-block-a",))
    assert block_b == make_id(Item, ("contact-block-b",))


def test_a_leaf_has_no_child_items() -> None:
    """A block has no items below it, so its children are empty."""
    plant = Plant()
    coil = plant.item("coil", part=plant.part("K"), designation="K1")
    block = plant.item("contact-block-a", part=plant.part("C"), parent=coil)
    assert child_items(plant.model(), block) == ()
