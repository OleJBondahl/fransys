"""`unit_crossings`, `boundary_owners`, `unmatched_port_names`, `strips_without_tag`."""

from connector_builders import make_connector
from plant import Plant

from fransys_model.derive.facts.mates import unmatched_port_names
from fransys_model.derive.facts.strip_without_tag import strips_without_tag
from fransys_model.derive.facts.unit_crossings import (
    crossed_units,
    crosses_out_of,
    declared_owners,
    ends,
    function_gender,
)
from fransys_model.derive.facts.unit_index import boundary_owners, unit_index
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import Gender
from fransys_model.vocab.units import UnusedBoundary


def _plant() -> Plant:
    """Unit `cab` holds item x1; loose y has no unit; one wire joins their pins."""
    plant = Plant()
    cab = plant.unit("cab")
    plant.item("x1", unit=cab)
    plant.item("y")
    one = plant.pin("x1", "X1", "1")
    other = plant.pin("y", "Y", "1")
    plant.wire(one, other, key="w")
    plant.boundary(cab, Plant.function_id("x1", "X1"))
    return plant


def test_a_wire_to_an_item_outside_leaves_the_unit_by_its_inner_end_only() -> None:
    model = _plant().model()
    cab = make_id(Unit, ("cab",))
    x1, y = Plant.function_id("x1", "X1"), Plant.function_id("y", "Y")
    assert len(ends(model)) == 2
    assert crosses_out_of(model, cab, x1)
    assert not crosses_out_of(model, cab, y)
    item_x, item_y = make_id(Item, ("x1",)), make_id(Item, ("y",))
    assert crossed_units(model, item_x, item_y) == (cab,)
    assert crossed_units(model, item_y, item_x) == ()


def test_a_repeated_boundary_record_keeps_its_repeat_where_the_index_dedups() -> None:
    plant = _plant()
    cab = make_id(Unit, ("cab",))
    x1 = Plant.function_id("x1", "X1")
    plant.boundary(cab, x1, key="again")
    model = plant.model()
    assert boundary_owners(model)[x1] == (cab, cab)
    assert unit_index(model).boundary_of[cab] == (x1,)


def test_declared_owners_keep_the_owners_at_the_declaring_scope_else_all() -> None:
    plant = _plant()
    scoped = plant.unit("scopeA")
    function = Plant.function_id("x1", "X1")
    key = ("scopeA", "unused_boundary", "f")
    unused = UnusedBoundary(id=make_id(UnusedBoundary, key), key=key, function=function)
    model = plant.model()
    cab = make_id(Unit, ("cab",))
    assert declared_owners(model, unused, [cab, scoped]) == [scoped]
    assert declared_owners(model, unused, [cab]) == [cab]


def test_function_gender_is_male_or_female_only() -> None:
    plant = Plant()
    plant.item("p")
    plant.item("q")
    plant.item("r")
    male, _ = make_connector(plant, ("p", "J"), ("1",), gender=Gender.MALE)
    neutral, _ = make_connector(plant, ("q", "J"), ("1",), gender=Gender.NEUTRAL)
    none, _ = make_connector(plant, ("r", "J"), ("1",), gender=None)
    model = plant.model()
    assert function_gender(model, male) is Gender.MALE
    assert function_gender(model, neutral) is None
    assert function_gender(model, none) is None


def test_unmatched_port_names_are_the_names_one_side_lacks() -> None:
    plant = Plant()
    for name in ("1", "2", "3"):
        plant.pin("plug", "J1", name)
    for name in ("1", "2", "4"):
        plant.pin("socket", "J1", name)
    mate = plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    assert unmatched_port_names(plant.model(), mate) == {"3", "4"}


def test_unmatched_port_names_are_empty_for_equal_sides() -> None:
    plant = Plant()
    plant.pin("plug", "J1", "1")
    plant.pin("socket", "J1", "1")
    mate = plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    assert unmatched_port_names(plant.model(), mate) == frozenset()


def test_a_partless_untagged_top_level_item_is_a_strip_without_tag() -> None:
    plant = Plant()
    bare = plant.item("bare")
    plant.item("named", designation="X1")
    plant.item("child", parent=bare)
    assert strips_without_tag(plant.model()) == (bare,)
