"""Tests: the placement builder's table reads, as derive facts (model-0308).

One invented plant, frozen once for the module: a cabinet with a panel, the panel with a rail,
a pump under the cabinet with no unit, and a bare item with nothing under it. The cabinet
function has two ports, the rail function one, the pump function none. One location node.
"""

import pytest
from plant import Plant

from fransys_model.derive import (
    function_item,
    function_ports,
    has_function,
    item_functions,
    item_parents,
    item_unit,
    node_label,
    port_function,
    port_name,
)
from fransys_model.kernel import Model, make_id
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import ports

CABINET = make_id(Unit, ("cabinet",))
PANEL = make_id(Unit, ("panel",))
RAIL = make_id(Unit, ("rail",))
CAB_ITEM = make_id(Item, ("cab_item",))
PANEL_ITEM = make_id(Item, ("panel_item",))
RAIL_ITEM = make_id(Item, ("rail_item",))
PUMP_ITEM = make_id(Item, ("pump",))
BARE_ITEM = make_id(Item, ("bare",))
CAB_FN = make_id(Function, ("cab_item", "cab_fn"))
RAIL_FN = make_id(Function, ("rail_item", "rail_fn"))
PUMP_FN = make_id(Function, ("pump", "pump_fn"))
MISSING_FN = make_id(Function, ("nowhere", "missing_fn"))
CAB_P1 = make_id(Port, ("cab_item", "cab_fn", "p1"))
CAB_P2 = make_id(Port, ("cab_item", "cab_fn", "2"))
RAIL_P1 = make_id(Port, ("rail_item", "rail_fn", "p1"))
LOCATION = make_id(AspectNode, ("p1",))


@pytest.fixture(scope="module")
def model() -> Model:
    """The invented plant of this module, frozen once."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    panel = plant.unit("panel", name="panel", parent=cabinet)
    rail = plant.unit("rail", name="rail", parent=panel)
    cab_item = plant.item("cab_item", unit=cabinet)
    plant.item("panel_item", parent=cab_item, unit=panel)
    rail_item = plant.item("rail_item", parent=PANEL_ITEM, unit=rail)
    pump = plant.item("pump", parent=cab_item)
    plant.item("bare")
    cab_fn = plant.function(cab_item, "cab_fn")
    plant.port(cab_fn, "p1")
    plant.port(cab_fn, "2")
    rail_fn = plant.function(rail_item, "rail_fn")
    plant.port(rail_fn, "p1")
    plant.function(pump, "pump_fn")
    plant.add(
        AspectNode(
            id=LOCATION,
            key=("p1",),
            aspect=Aspect.LOCATION,
            parent=None,
            label="P1",
            description="Place",
        )
    )
    return plant.model()


def test_function_item_is_the_item_a_function_belongs_to(model: Model) -> None:
    """The cabinet function belongs to the cabinet item; the rail function to the rail item."""
    assert function_item(model, CAB_FN) == CAB_ITEM
    assert function_item(model, RAIL_FN) == RAIL_ITEM


def test_has_function_is_true_for_a_planted_function(model: Model) -> None:
    """A planted function is a function of the model."""
    assert has_function(model, CAB_FN)


def test_has_function_is_false_for_an_unknown_function(model: Model) -> None:
    """An id that was never planted is not a function."""
    assert not has_function(model, MISSING_FN)


def test_item_functions_maps_each_item_with_functions_to_its_set(model: Model) -> None:
    """The cabinet, rail and pump items each hold their one function; the panel and bare items
    hold none and so have no entry."""
    functions_of = item_functions(model)
    assert functions_of[CAB_ITEM] == frozenset({CAB_FN})
    assert functions_of[RAIL_ITEM] == frozenset({RAIL_FN})
    assert functions_of[PUMP_ITEM] == frozenset({PUMP_FN})
    assert set(functions_of) == {CAB_ITEM, RAIL_ITEM, PUMP_ITEM}


def test_item_functions_leaves_out_an_item_without_functions(model: Model) -> None:
    """The panel item and the bare item have no functions, so no entry in the map."""
    functions_of = item_functions(model)
    assert PANEL_ITEM not in functions_of
    assert BARE_ITEM not in functions_of


def test_function_ports_are_the_ports_of_the_function_in_table_order(model: Model) -> None:
    """The cabinet function has its two ports, in the order the ports table gives them."""
    table = ports(model)
    in_table_order = tuple(port for port in table if table[port].function == CAB_FN)
    assert function_ports(model, CAB_FN) == in_table_order
    assert sorted(function_ports(model, CAB_FN)) == sorted((CAB_P1, CAB_P2))


def test_function_ports_of_a_function_with_one_port(model: Model) -> None:
    """The rail function has exactly its one port."""
    assert function_ports(model, RAIL_FN) == (RAIL_P1,)


def test_function_ports_of_a_function_without_ports_is_empty(model: Model) -> None:
    """The pump function has no ports."""
    assert function_ports(model, PUMP_FN) == ()


def test_port_name_is_the_name_the_port_was_planted_with(model: Model) -> None:
    """The cabinet function's ports are named `p1` and `2`; the rail's `p1`."""
    assert port_name(model, CAB_P1) == "p1"
    assert port_name(model, CAB_P2) == "2"
    assert port_name(model, RAIL_P1) == "p1"


def test_port_function_is_the_function_the_port_was_planted_on(model: Model) -> None:
    """Each planted port names its function; a port the model lacks has none."""
    assert port_function(model, CAB_P1) == CAB_FN
    assert port_function(model, RAIL_P1) == RAIL_FN
    assert port_function(model, make_id(Port, ("cab_item", "cab_fn", "nowhere"))) is None


def test_node_label_is_the_aspect_node_label(model: Model) -> None:
    """The location node's label is `P1`."""
    assert node_label(model, LOCATION) == "P1"


def test_item_unit_is_the_unit_the_item_is_recorded_in(model: Model) -> None:
    """The cabinet item is in the cabinet unit; the panel item in the panel unit."""
    assert item_unit(model, CAB_ITEM) == CABINET
    assert item_unit(model, PANEL_ITEM) == PANEL


def test_item_unit_is_none_for_an_item_with_no_unit(model: Model) -> None:
    """The bare item was planted with no unit."""
    assert item_unit(model, BARE_ITEM) is None


def test_item_parents_maps_each_child_to_its_parent(model: Model) -> None:
    """The panel item and the pump sit under the cabinet item; the rail item under the panel."""
    assert item_parents(model) == {
        PANEL_ITEM: CAB_ITEM,
        PUMP_ITEM: CAB_ITEM,
        RAIL_ITEM: PANEL_ITEM,
    }


def test_item_parents_has_no_entry_for_a_root_item(model: Model) -> None:
    """The cabinet and the bare item have no parent, so no entry."""
    parents = item_parents(model)
    assert CAB_ITEM not in parents
    assert BARE_ITEM not in parents
