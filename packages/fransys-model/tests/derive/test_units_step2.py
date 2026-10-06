"""Units spec STEP 2: `derive.units`/`unit_subtree`/`unit_items`/`standalone`/`boundary` (U8)
and per-unit numbering (U7).

`docs/archive/specs/2026-09-22-units.md` U7, U8; `docs/decisions/model-0038-units.md`.
"""

import dataclasses

import pytest
from plant import Plant
from query_builders import make_node, make_placement

from fransys_model.derive import (
    boundary,
    external,
    number,
    reference_designation,
    standalone,
    unit_items,
    unit_subtree,
    units,
)
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.derive.passes.numbering import (
    DESIGNATION_DUPLICATE,
    REFERENCE_DESIGNATION_DUPLICATE,
)
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import items as items_of
from fransys_model.vocab.units import Boundary

# ---- U8: units, unit_subtree, unit_items, standalone ---------------------------------------


@dataclasses.dataclass(frozen=True)
class _Nested:
    """Root -> mid -> leaf units, one item directly in each."""

    root: Id[Unit]
    mid: Id[Unit]
    leaf: Id[Unit]
    root_item: Id[Item]
    mid_item: Id[Item]
    leaf_item: Id[Item]


def _nested_units(plant: Plant, *, outside_item: bool) -> _Nested:
    """Build `_Nested`; with `outside_item`, also add one item in none of the three units."""
    root = plant.unit("root")
    mid = plant.unit("mid", parent=root)
    leaf = plant.unit("leaf", parent=mid)
    nested = _Nested(
        root=root,
        mid=mid,
        leaf=leaf,
        root_item=plant.item("root-item", unit=root),
        mid_item=plant.item("mid-item", unit=mid),
        leaf_item=plant.item("leaf-item", unit=leaf),
    )
    if outside_item:
        plant.item("outside-item")
    return nested


def test_units_lists_every_unit_in_id_order() -> None:
    """`sorted(units(model))` is every `Unit`, sorted by id -- checked by value, not by the walk."""
    plant = Plant()
    ids = _nested_units(plant, outside_item=False)
    model = plant.model()
    found = sorted(units(model))
    assert len(found) == 3
    assert found == sorted((ids.root, ids.mid, ids.leaf))


def test_unit_subtree_and_unit_items_are_checked_by_value() -> None:
    """Each unit's subtree is itself and every unit below it; items follow the same subtree."""
    plant = Plant()
    ids = _nested_units(plant, outside_item=True)
    model = plant.model()
    assert unit_subtree(model, ids.root) == frozenset({ids.root, ids.mid, ids.leaf})
    assert unit_subtree(model, ids.mid) == frozenset({ids.mid, ids.leaf})
    assert unit_subtree(model, ids.leaf) == frozenset({ids.leaf})
    assert unit_items(model, ids.root) == frozenset({ids.root_item, ids.mid_item, ids.leaf_item})
    assert unit_items(model, ids.mid) == frozenset({ids.mid_item, ids.leaf_item})
    assert unit_items(model, ids.leaf) == frozenset({ids.leaf_item})


def test_standalone_is_false_for_all_three_when_an_item_sits_outside_every_unit() -> None:
    """An item with `unit=None` belongs to no subtree, so no unit's subtree holds every item."""
    plant = Plant()
    ids = _nested_units(plant, outside_item=True)
    model = plant.model()
    # examined: three units and a fourth item outside all of them
    assert len(sorted(units(model))) == 3
    assert len(model.tables["item"]) == 4
    assert standalone(model, ids.root) is False
    assert standalone(model, ids.mid) is False
    assert standalone(model, ids.leaf) is False


def test_standalone_is_true_for_the_root_only_once_the_outside_item_is_gone() -> None:
    """Without the outside item, every item sits under the root's subtree, and only its."""
    plant = Plant()
    ids = _nested_units(plant, outside_item=False)
    model = plant.model()
    assert len(model.tables["item"]) == 3
    assert standalone(model, ids.root) is True
    assert standalone(model, ids.mid) is False
    assert standalone(model, ids.leaf) is False


def test_unit_subtree_unit_items_and_standalone_refuse_an_unknown_unit() -> None:
    """Unknown identity: `SchemaError`, the rule every derive query follows (decision 0021)."""
    plant = Plant()
    _nested_units(plant, outside_item=False)
    model = plant.model()
    nope = make_id(Unit, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        unit_subtree(model, nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("unit", nope)
    with pytest.raises(SchemaError) as excinfo:
        unit_items(model, nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("unit", nope)
    with pytest.raises(SchemaError) as excinfo:
        standalone(model, nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("unit", nope)
    with pytest.raises(SchemaError) as excinfo:
        boundary(model, nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("unit", nope)


def test_external_refuses_an_unknown_item() -> None:
    """`external`'s own locator raises for an unknown item id, not a unit id (units spec U8)."""
    plant = Plant()
    _nested_units(plant, outside_item=False)
    model = plant.model()
    nope = make_id(Item, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        external(model, nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("item", nope)


def test_boundary_lists_the_units_functions_in_id_order_deduplicated() -> None:
    """Two `Boundary` records naming the same function still list it once."""
    plant = Plant()
    unit_id = plant.unit("board")
    plant.pin("x1", "conn", "1")
    plant.pin("x2", "conn", "1")
    fn_x1 = Plant.function_id("x1", "conn")
    fn_x2 = Plant.function_id("x2", "conn")
    plant.add(
        Boundary(id=make_id(Boundary, ("b1",)), key=("b1",), unit=unit_id, function=fn_x1),
        Boundary(id=make_id(Boundary, ("b2",)), key=("b2",), unit=unit_id, function=fn_x2),
        Boundary(id=make_id(Boundary, ("b3",)), key=("b3",), unit=unit_id, function=fn_x2),
    )
    model = plant.model()
    found = boundary(model, unit_id)
    assert len(found) == 2
    assert found == tuple(sorted((fn_x1, fn_x2)))


def test_boundary_of_a_unit_with_no_boundary_function_is_empty() -> None:
    """A real unit, examined, with nothing declared as its interface."""
    plant = Plant()
    unit_id = plant.unit("lone")
    model = plant.model()
    assert unit_id in sorted(units(model))
    assert boundary(model, unit_id) == ()


# ---- U7: per-unit numbering -----------------------------------------------------------------


def _two_instances(plant: Plant) -> tuple[Id[Unit], Id[Unit], Id[Item], Id[Item]]:
    """Two instances of one unit, each with one relay item, both siblings under `parent=None`."""
    part = plant.part("K")
    unit_a = plant.unit("instance-a", name="board")
    unit_b = plant.unit("instance-b", name="board")
    relay_a = plant.item("relay-a", part=part, unit=unit_a)
    relay_b = plant.item("relay-b", part=part, unit=unit_b)
    return unit_a, unit_b, relay_a, relay_b


def test_two_instances_of_one_unit_each_number_k1() -> None:
    """Per-unit numbering: the sibling group is `(unit, parent, class_code)` (units spec U7)."""
    plant = Plant()
    _unit_a, _unit_b, relay_a, relay_b = _two_instances(plant)
    model, findings = number(plant.model())
    designations = {
        item.id: own_designation_or_none(model, item) for item in items_of(model).values()
    }
    assert designations[relay_a] == "K1"
    assert designations[relay_b] == "K1"
    assert findings == ()


def test_designation_duplicate_uses_the_same_group_as_numbering() -> None:
    """`-X2` authored alike in two unit instances is not a `DESIGNATION_DUPLICATE`."""
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    item_a = plant.item("x2-a", designation="X2", unit=unit_a)
    item_b = plant.item("x2-b", designation="X2", unit=unit_b)
    model, findings = number(plant.model())
    # examined: both items kept the authored designation, not resolved to something else
    designations = {
        item.id: own_designation_or_none(model, item) for item in items_of(model).values()
    }
    assert designations[item_a] == "X2"
    assert designations[item_b] == "X2"
    assert [f.code for f in findings if f.code == DESIGNATION_DUPLICATE] == []


def test_reference_designation_duplicate_for_two_unit_instances_at_one_location() -> None:
    """Two instances of one unit, each `K1` (U7), placed at the same `+` node: one collision."""
    plant = Plant()
    _unit_a, _unit_b, relay_a, relay_b = _two_instances(plant)
    node = make_node("er", None)
    plant.add(
        node, make_placement("p-a", relay_a, node.id), make_placement("p-b", relay_b, node.id)
    )
    model, findings = number(plant.model())
    assert reference_designation(model, relay_a) == "+ER-K1"
    assert reference_designation(model, relay_b) == "+ER-K1"
    reference_findings = [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE]
    assert len(reference_findings) == 1
    (finding,) = reference_findings
    assert set(finding.subjects) == {relay_a, relay_b}


def test_can_fail_the_same_two_instances_under_two_locations_give_nothing() -> None:
    """Can-fail twin: a location per instance, as the worked example does, and no collision."""
    plant = Plant()
    _unit_a, _unit_b, relay_a, relay_b = _two_instances(plant)
    node_a, node_b = make_node("er1", None), make_node("er2", None)
    plant.add(
        node_a,
        node_b,
        make_placement("p-a", relay_a, node_a.id),
        make_placement("p-b", relay_b, node_b.id),
    )
    model, findings = number(plant.model())
    # examined: both relays are still K1, distinguished only by the location prefix
    designations = {
        item.id: own_designation_or_none(model, item) for item in items_of(model).values()
    }
    assert designations[relay_a] == "K1"
    assert designations[relay_b] == "K1"
    assert reference_designation(model, relay_a) == "+ER1-K1"
    assert reference_designation(model, relay_b) == "+ER2-K1"
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_a_product_only_placement_does_not_gate_a_reference_designation_duplicate() -> None:
    """A `PRODUCT`-aspect placement renders no `=`/`+` segment, so it does not count as placed."""
    plant = Plant()
    _unit_a, _unit_b, relay_a, relay_b = _two_instances(plant)
    node = make_node("a1", None, Aspect.PRODUCT)
    plant.add(
        node, make_placement("p-a", relay_a, node.id), make_placement("p-b", relay_b, node.id)
    )
    model, findings = number(plant.model())
    assert reference_designation(model, relay_a) == "-K1"
    assert reference_designation(model, relay_b) == "-K1"
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_items_with_unit_none_number_exactly_as_before() -> None:
    """No unit at all: the group is `(None, P)`, `P` the nearest read-through ancestor (C3b).

    `board` is a real board (`PcbFacet`), so it is read through: `board-f` still numbers
    within it alone, `F1`. `top-f1` and `top-f2` share the model's top-level group.
    """
    plant = Plant()
    fuse = plant.part("F")
    board = plant.item("board", part=plant.board_part())
    plant.item("board-f", part=fuse, parent=board)
    plant.item("top-f1", part=fuse)
    plant.item("top-f2", part=fuse)
    model, _ = number(plant.model())
    designations = {
        item.key[0]: own_designation_or_none(model, item) for item in items_of(model).values()
    }
    assert designations == {
        "board": "A1",
        "board-f": "F1",
        "top-f1": "F1",
        "top-f2": "F2",
    }
