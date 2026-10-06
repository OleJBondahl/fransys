"""`Item.description` holds only what the author wrote; `item_description` reads the rest (SC4).

Six author paths make an item; each is frozen and read two ways: the stored field, and
`derive.item_description`. The catalogue's parts have distinct, non-empty descriptions, so a
swap between two parts would show.
"""

from typing import TYPE_CHECKING

from fransys_author import Design

from fransys_model.derive import designation_list, item_description, items, overview_graph
from fransys_model.kernel import Id, Model, freeze, merge

if TYPE_CHECKING:
    from fransys_model.vocab import Item

_RELAY = "test part TEST-RLY-2CO"
_TERMINAL = "test part TEST-TB"
_CABLE = "test part TEST-CBL-2"


def _model(parts, d: Design) -> Model:
    return freeze(merge(parts, d.draft()))


def _stored_and_read(model: Model, item: Id[Item]) -> tuple[str, str]:
    return items(model)[item].description, item_description(model, item)


def test_a_part_item_with_no_authored_description_stores_empty_and_reads_the_parts(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    assert _stored_and_read(_model(parts, d), k1.id) == ("", _RELAY)


def test_a_part_item_with_an_authored_description_stores_and_reads_it(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1", description="pump 1 run relay")
    assert _stored_and_read(_model(parts, d), k1.id) == ("pump 1 run relay",) * 2


def test_a_part_less_item_with_an_authored_description_stores_and_reads_it(parts):
    d = Design(parts)
    board = d.item(None, tag="A1", description="the main board")
    assert _stored_and_read(_model(parts, d), board.id) == ("the main board",) * 2


def test_a_part_less_strip_stores_empty_and_reads_empty(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    assert _stored_and_read(_model(parts, d), x1.id) == ("", "")


def test_a_cable_stores_empty_and_reads_the_parts(parts):
    d = Design(parts)
    w1 = d.cable("TEST-CBL-2", tag="W1")
    assert _stored_and_read(_model(parts, d), w1.id) == ("", _CABLE)


def test_a_strip_terminal_stores_empty_and_reads_the_parts(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB")
    assert _stored_and_read(_model(parts, d), t1.id) == ("", _TERMINAL)


def test_the_designation_list_and_the_overview_read_the_parts_description(parts):
    """The two callers of `item_description`: a part item's row and node carry the part's text."""
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    k2 = d.item("TEST-RLY-2CO", tag="K2", description="own text")
    model = _model(parts, d)
    rows = {row.item: row.description for row in designation_list(model)}
    nodes = {node.item: node.description for node in overview_graph(model).nodes}
    assert rows == nodes == {k1.id: _RELAY, k2.id: "own text"}
