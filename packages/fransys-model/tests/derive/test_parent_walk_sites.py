"""Every leaf-to-root walk over a parent chain ends on a cycle the same way (REVIEW-M M6).

The validators report `CONTAINMENT_CYCLE`, `ASPECT_CYCLE` and `UNIT_CYCLE`; a query over such a
model must still end, and stop before a node it has already passed. One test per site that
walks `Item.parent`, `AspectNode.parent` or `Unit.parent`, each on the smallest cyclic model
whose answer tells where the walk stopped.
"""

from decimal import Decimal

from plant import Plant

from fransys_model.derive import external
from fransys_model.derive.designation import (
    designating_ancestors,
    designation_holder,
    unit_location,
)
from fransys_model.derive.drawing_text import location_path
from fransys_model.derive.lookups import effective_placement, unit_chain
from fransys_model.derive.unit_nodes import own_nodes_by_unit
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import Aspect, PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part


def _item(key: str) -> Id[Item]:
    return make_id(Item, (key,))


def _node(plant: Plant, key: str, label: str, *, parent: str) -> Id[AspectNode]:
    """A location node keyed `key`, under the node keyed `parent`."""
    node = AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=Aspect.LOCATION,
        parent=make_id(AspectNode, (parent,)),
        label=label,
        description="Invented",
    )
    plant.add(node)
    return node.id


def _place(plant: Plant, item: str, node: Id[AspectNode]) -> None:
    key = f"place-{item}"
    plant.add(Placement(id=make_id(Placement, (key,)), key=(key,), item=_item(item), node=node))


def _cable_child(plant: Plant, key: str, parent: Id[Item]) -> None:
    """An item under `parent` carrying a `cable` facet and a cable part: `parent` is then a
    harness (RW4b: `is_cable` needs a `CableProductFacet`, not just a `cable` facet).

    None of these marker cables carries a core, so `core_colours` stays empty (0 cores).
    """
    part = Part(
        id=make_id(Part, (key, "cable-part")),
        key=(key, "cable-part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description=f"Invented {key}",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        part,
        CableProductFacet(
            id=make_id(CableProductFacet, (key, "product")),
            key=(key, "product"),
            subject=part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    child = plant.item(key, parent=parent, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=child,
            length_mm=None,
        )
    )


def _location_cycle(plant: Plant) -> tuple[Id[AspectNode], Id[AspectNode]]:
    """Location nodes `a` and `b`, each the other's parent."""
    return (
        _node(plant, "a", "A", parent="b"),
        _node(plant, "b", "B", parent="a"),
    )


def test_location_path_over_a_node_cycle_stops_before_the_repeat() -> None:
    plant = Plant()
    a, b = _location_cycle(plant)
    assert location_path(plant.model(), a) == ((b, "B"), (a, "A"))


def test_location_path_of_no_node_is_empty() -> None:
    assert location_path(Plant().model(), None) == ()


def test_unit_location_over_a_node_cycle_is_the_placed_node() -> None:
    plant = Plant()
    unit = plant.unit("u")
    plant.item("r", unit=unit)
    a, _ = _location_cycle(plant)
    _place(plant, "r", a)
    assert unit_location(plant.model(), unit) == a


def test_effective_placement_over_an_item_cycle_finds_the_ancestors_node() -> None:
    plant = Plant()
    x = plant.item("x", parent=_item("y"))
    plant.item("y", parent=x)
    a, _ = _location_cycle(plant)
    _place(plant, "y", a)
    assert effective_placement(plant.model(), x, Aspect.LOCATION) == a


def test_effective_placement_over_an_item_cycle_with_no_placement_is_none() -> None:
    plant = Plant()
    x = plant.item("x", parent=_item("y"))
    plant.item("y", parent=x)
    assert effective_placement(plant.model(), x, Aspect.LOCATION) is None


def test_designating_ancestors_over_a_cycle_not_through_the_item_stops_at_the_repeat() -> None:
    """`i` sits in the harness `h`, which sits in the harness `o`, which sits in `h` again."""
    plant = Plant()
    h = plant.item("h", parent=_item("o"))
    o = plant.item("o", parent=h)
    _cable_child(plant, "ch", h)
    _cable_child(plant, "co", o)
    item = plant.item("i", parent=h)
    assert designating_ancestors(plant.model(), item) == (o, h)


def test_designating_ancestors_over_a_cycle_through_the_item_stops_at_the_item() -> None:
    """`c` is a cable under the harness `h` that sits under `c`: `c` itself is never listed."""
    plant = Plant()
    h = plant.item("h", parent=_item("c"))
    _cable_child(plant, "c", h)
    assert designating_ancestors(plant.model(), _item("c")) == (h,)


def test_designation_holder_over_a_cycle_of_accessories_is_the_last_before_the_repeat() -> None:
    """Each item takes the other's designation (its class code says it will be tagged)."""
    plant = Plant()
    part = plant.part("K")
    a = plant.item("a", parent=_item("b"), part=part)
    b = plant.item("b", parent=a, part=part)
    assert designation_holder(plant.model(), a) == b


def test_designation_holder_stops_at_the_first_item_that_keeps_its_own_designation() -> None:
    plant = Plant()
    part = plant.part("K")
    top = plant.item("top", part=part, designation="K1")
    accessory = plant.item("acc", parent=top, part=part)
    assert designation_holder(plant.model(), accessory) == top


def test_own_nodes_over_a_cycle_of_ordinary_items_ends_and_reads_the_placed_node() -> None:
    """`_of_a_cable` asks whether an item is a cable's, a harness's or a member of one."""
    plant = Plant()
    unit = plant.unit("u")
    plant.item("x", parent=_item("y"), unit=unit)
    plant.item("y", parent=_item("x"), unit=unit)
    a, _ = _location_cycle(plant)
    _place(plant, "x", a)
    assert own_nodes_by_unit(plant.model())[unit] == frozenset({a, make_id(AspectNode, ("b",))})


def test_own_nodes_skips_an_item_under_a_cable_even_in_a_cycle() -> None:
    plant = Plant()
    unit = plant.unit("u")
    plant.item("x", parent=_item("y"), unit=unit)
    y = plant.item("y", parent=_item("x"), unit=unit)
    _cable_child(plant, "cab", y)
    a, _ = _location_cycle(plant)
    _place(plant, "x", a)
    assert own_nodes_by_unit(plant.model())[unit] == frozenset()


def test_unit_chain_over_a_unit_cycle_stops_before_the_repeat() -> None:
    plant = Plant()
    a = plant.unit("a", parent=make_id(Unit, ("b",)))
    b = plant.unit("b", parent=a)
    assert unit_chain(plant.model(), a) == [a, b]


def test_external_over_an_item_cycle_ends_the_walk_and_reports_not_external() -> None:
    """No item in the cycle carries `external=True`, so the memoised walk ends without one."""
    plant = Plant()
    a = plant.item("a", parent=_item("b"))
    b = plant.item("b", parent=a)
    model = plant.model()
    assert external(model, a) is False
    assert external(model, b) is False
