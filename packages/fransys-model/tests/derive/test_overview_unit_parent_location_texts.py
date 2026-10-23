"""`unit_parent` and `location_texts` read directly, on the overview unit plant and a place tree."""

from overview_builders import unit_plant
from plant import Plant

from fransys_model.derive import location_texts, unit_parent
from fransys_model.kernel import make_id
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.enums import Aspect


def test_unit_parent_of_nested_and_root() -> None:
    """The nested unit names the outer one; the outer one is a root."""
    model, outer, nested = unit_plant()
    assert unit_parent(model, nested) == outer
    assert unit_parent(model, outer) is None


def test_location_texts_prints_the_signed_path_per_label() -> None:
    """A root place prints `+ER`; its child prints the full path `+ER+C1`."""
    plant = Plant()
    root = make_id(AspectNode, ("er",))
    for key, label, parent in (("er", "ER", None), ("c1", "C1", root)):
        plant.add(
            AspectNode(
                id=make_id(AspectNode, (key,)),
                key=(key,),
                aspect=Aspect.LOCATION,
                parent=parent,
                label=label,
                description="Place",
            )
        )
    assert location_texts(plant.model()) == {"ER": "+ER", "C1": "+ER+C1"}


def test_location_texts_is_empty_without_places() -> None:
    """A model with no location node gives no texts."""
    assert location_texts(Plant().model()) == {}
