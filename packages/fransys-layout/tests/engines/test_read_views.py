"""D8: the helpers of `read/views.py` that take plain values, on hand-built specs and refs.

`item_views`, `without_idle_pins`, `without_idle_terminals`, `pin_mates` and the
`connections.py` filters read the model too: `test_read.py` and `test_board_internal.py` cover
them end to end. What is left here is the value-only half: a pin view per connector pin and the
re-pointing of a connection's end at a pin or an item view.
"""

import dataclasses

from samples import function_spec, hid

from fransys_layout.engines.schematic.read.views import pin_views, reitem, repin
from fransys_layout.stages import PortRef


def test_a_function_that_is_not_a_connector_is_no_pin_view() -> None:
    """A contact keeps its handle, key and ports: no view, no `pin_of` entry."""
    contact = function_spec(1)
    specs, pin_of = pin_views((contact,))
    assert specs == (contact,)
    assert pin_of == {}


def test_a_connector_with_no_pin_is_no_pin_view() -> None:
    """No pin, no view: the connector itself stays."""
    bare = dataclasses.replace(function_spec(1, kind="connector"), ports=())
    specs, pin_of = pin_views((bare,))
    assert specs == (bare,)
    assert pin_of == {}


def test_a_connector_becomes_one_view_per_pin_named_in() -> None:
    """Each pin: handle = its port, key `(..., "pin", <pin name>)`, one port `in`, one pole."""
    connector = function_spec(1, kind="connector")
    specs, pin_of = pin_views((connector,))
    first, second = connector.ports
    assert pin_of == {first.port: connector.function, second.port: connector.function}
    assert [view.function for view in specs] == [first.port, second.port]
    assert [view.key for view in specs] == [
        ("invented", "fn1", "pin", "13"),
        ("invented", "fn1", "pin", "14"),
    ]
    assert [view.pin_function for view in specs] == [connector.function] * 2
    assert [view.ports for view in specs] == [
        (dataclasses.replace(first, name="in"),),
        (dataclasses.replace(second, name="in"),),
    ]
    assert all(view.poles == 1 and view.pole_pairs == () for view in specs)


def test_the_views_come_back_sorted_by_handle_whatever_the_kind() -> None:
    """A connector's pin views sort with the other specs by handle: function 1 before port 21."""
    connector, contact = function_spec(2, kind="connector"), function_spec(1)
    specs, _ = pin_views((connector, contact))
    assert [view.function for view in specs] == [
        contact.function,
        hid("port", 21),
        hid("port", 22),
    ]


def test_a_ref_on_an_item_view_port_is_moved_to_the_view() -> None:
    """A port in `view_of` names the item as its function, the port unchanged."""
    ref = PortRef(function=hid("function", 1), port=hid("port", 11))
    moved = reitem(ref, {hid("port", 11): hid("item", 1)})
    assert moved == PortRef(function=hid("item", 1), port=hid("port", 11))


def test_a_ref_on_a_port_no_item_view_holds_is_left_alone() -> None:
    """A port not in `view_of` is returned as it is, its `symbol_port` too."""
    ref = PortRef(function=hid("function", 1), port=hid("port", 11), symbol_port="top")
    assert reitem(ref, {hid("port", 12): hid("item", 1)}) == ref


def test_a_ref_on_a_pin_is_moved_to_the_pin_view() -> None:
    """A port in `pin_of` is its own view's function."""
    ref = PortRef(function=hid("function", 1), port=hid("port", 11))
    moved = repin(ref, {hid("port", 11): hid("function", 1)})
    assert moved == PortRef(function=hid("port", 11), port=hid("port", 11))


def test_a_ref_on_a_port_that_is_no_pin_is_left_alone() -> None:
    """A port not in `pin_of` is returned as it is, its `symbol_port` too."""
    ref = PortRef(function=hid("function", 1), port=hid("port", 11), symbol_port="top")
    assert repin(ref, {}) == ref
