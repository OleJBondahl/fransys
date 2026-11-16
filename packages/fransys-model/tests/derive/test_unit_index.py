"""`UnitIndex.own_items` and `child_units`: exact membership, the top level under `None`."""

import dataclasses

from plant import Plant

from fransys_model.derive.facts.unit_index import unit_index
from fransys_model.derive.facts.units import drawn_with
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Item, Unit


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


def _by_others() -> tuple[Model, Id[Unit]]:
    """A unit `skid`, a by-others root `x` drawn with it, its child `m`, and a by-others root `y` that sets nothing."""
    plant = Plant()
    skid = plant.unit("skid")
    x = plant.item("x")
    plant.records[-1] = dataclasses.replace(plant.records[-1], external=True, drawn_with=skid)
    plant.item("m", parent=x)
    plant.item("y")
    plant.records[-1] = dataclasses.replace(plant.records[-1], external=True)
    return plant.model(), skid


def test_a_by_others_child_takes_its_roots_drawn_with_and_a_root_with_none_has_none() -> None:
    model, skid = _by_others()
    ids = {k: make_id(Item, (k,)) for k in "xmy"}
    assert [drawn_with(model, ids[k]) for k in "xmy"] == [skid, skid, None]
