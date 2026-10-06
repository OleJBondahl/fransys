"""Where "prints the holder's designation" and "is a fitted rating part" differ (model-0154).

A function-less child of a protection holder is a rating source (model-0151), and an untagged,
footprint-free child is an accessory (model-0058, model-0119). The two tests read functions
differently, each rightly: these two cases pin the differences.
"""

from current_plant import fuse, rate
from plant import Plant

from fransys_model.derive import takes_parents_designation
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.rating_readers import function_ratings


def _holder_and_child(plant: Plant) -> tuple[Id[Item], Id[Item]]:
    """A protection holder `F` and a rated, function-less child `L` of it."""
    fuse(plant, "F", None)
    holder = make_id(Item, ("F",))
    child = plant.item("L", part=rate(plant, "L", "4"), parent=holder)
    return holder, child


def _sources(plant: Plant) -> int:
    return len(function_ratings(plant.model(), Plant.function_id("F", "f")))


def test_a_child_with_a_function_only_below_it_is_a_rating_source_but_no_accessory() -> None:
    """The child has no function of its own: it is a fitted link, yet a device by its descendant."""
    plant = Plant()
    _, child = _holder_and_child(plant)
    below = plant.item("G", part=plant.part("G"), parent=child)
    plant.function(below, "g")
    model, _ = number(plant.model())
    assert _sources(plant) == 1
    assert not takes_parents_designation(model, child)


def test_a_contact_block_is_an_accessory_but_no_rating_source() -> None:
    """The child's only function is a contact: it prints the holder's designation, rates nothing."""
    plant = Plant()
    _, child = _holder_and_child(plant)
    plant.function(child, "c", kind=FunctionKind.CONTACT_NO)
    model, _ = number(plant.model())
    assert takes_parents_designation(model, child)
    assert _sources(plant) == 0
