"""`UnitIndex.own_items` and `child_units`: exact membership, the top level under `None`."""

from plant import Plant

from fransys_model.derive.facts.unit_index import unit_index
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item


def _model():
    plant = Plant()
    outer = plant.unit("outer")
    inner = plant.unit("inner", parent=outer)
    plant.item("a", unit=outer)
    plant.item("b", unit=inner)
    plant.item("top")
    return plant.model(), outer, inner


def test_own_items_hold_the_exact_unit_and_none_is_the_top_level() -> None:
    model, outer, inner = _model()
    index = unit_index(model)
    assert index.own_items[outer] == (make_id(Item, ("a",)),)
    assert index.own_items[inner] == (make_id(Item, ("b",)),)
    assert index.own_items[None] == (make_id(Item, ("top",)),)
    assert len(index.items_of[outer]) == 2


def test_child_units_hold_the_direct_children_and_none_the_top_level_units() -> None:
    model, outer, inner = _model()
    index = unit_index(model)
    assert index.child_units[outer] == (inner,)
    assert index.child_units[None] == (outer,)
    assert inner not in index.child_units
