"""RR-O1: the facts the stages and the writer read in place of a kind, a key or an id kind."""

from samples import function_spec, hid

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.engines.schematic.write.keys import WriteKeys, view_of
from fransys_layout.geometry import generic_box_geometry, symbol_geometry
from fransys_model.layout import PlacementView


def test_only_the_labelled_box_geometry_is_a_generic_box() -> None:
    """A library symbol is no generic box, the placeholder is."""
    assert generic_box_geometry(("a", "b")).generic_box
    assert not symbol_geometry("make-contact").generic_box


def test_no_kind_row_is_an_item_view_and_only_a_channel_kind_is_a_channel() -> None:
    """`item_view` is set only on a spec standing for a whole item; no kind's row sets it."""
    assert not function_spec(1).roles.item_view
    assert not kind_roles("item").item_view
    assert kind_roles("plc_channel").plc_channel
    assert not kind_roles("contact_no").plc_channel


def test_a_handle_draws_the_view_the_key_table_gives_it() -> None:
    """An item with a first function is an item view, a port handle a pin view, else a function."""
    item, function, port = hid("item", 1), hid("function", 1), hid("port", 1)
    keys = WriteKeys(
        function={},
        port={},
        conductor={},
        item={},
        unit={},
        aspect_node={},
        port_function={port: function},
        port_name={port: "1"},
        item_function={item: function},
    )
    assert view_of(keys, item) is PlacementView.ITEM
    assert view_of(keys, port) is PlacementView.PIN
    assert view_of(keys, function) is PlacementView.FUNCTION
