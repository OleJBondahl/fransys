"""The `ConnectorBox` builder: keys by drawing set, texts and cells in index order."""

from fransys_layout.engines.schematic.write.harness import connector_boxes
from fransys_layout.engines.schematic.write.keys import PREFIX, WriteKeys
from fransys_layout.geometry import Box, Point
from fransys_layout.stages.connector_boxes import BoxCell, PlacedConnectorBox
from fransys_model.kernel import make_id
from fransys_model.layout import DrawingSet, Page, PageRole
from fransys_model.vocab import Function, Port

FUNCTION = make_id(Function, ("f", "p1"))
PORT = make_id(Port, ("f", "p1", "1"))


def _set(name: str, number: int) -> DrawingSet:
    key = (*PREFIX, "drawing_set", name)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="t"
    )


def _page(drawing_set: DrawingSet, number: int) -> Page:
    key = (*drawing_set.key, str(number))
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="t",
    )


def _keys() -> WriteKeys:
    return WriteKeys(
        function={FUNCTION: ("f", "p1")},
        port={},
        conductor={},
        item={},
        unit={},
        aspect_node={},
        port_function={},
        port_name={},
        item_function={},
    )


def _placed(drawing_set: int, page: int) -> PlacedConnectorBox:
    return PlacedConnectorBox(
        function=FUNCTION,
        drawing_set=drawing_set,
        page=page,
        box=Box(x=8, y=16, width=40, height=32),
        texts=(Point(x=12, y=20), Point(x=12, y=36)),
        cells=(BoxCell(port=PORT, box=Box(x=8, y=32, width=16, height=16)),),
    )


def test_two_boxes_of_one_function_in_two_drawing_sets_get_two_keys() -> None:
    sets = {1: _set("one", 1), 2: _set("two", 2)}
    page_of = {(1, 1): _page(sets[1], 1), (2, 2): _page(sets[2], 2)}
    records = connector_boxes(_keys(), [_placed(1, 1), _placed(2, 2)], page_of, sets, "t")
    assert len({r.key for r in records}) == 2
    assert len({r.id for r in records}) == 2
    assert records[0].key == (*PREFIX, "connector_box", "f", "p1", "drawing_set", "one")


def test_a_second_page_of_one_function_in_one_set_adds_its_page_number() -> None:
    sets = {1: _set("one", 1)}
    page_of = {(1, 1): _page(sets[1], 1), (1, 2): _page(sets[1], 2)}
    first, second = connector_boxes(_keys(), [_placed(1, 1), _placed(1, 2)], page_of, sets, "t")
    assert second.key == (*first.key, "page", "2")


def test_the_record_carries_its_texts_and_cells_in_index_order() -> None:
    sets = {1: _set("one", 1)}
    page_of = {(1, 1): _page(sets[1], 1)}
    (record,) = connector_boxes(_keys(), [_placed(1, 1)], page_of, sets, "stamp")
    assert [(t.index, t.x, t.y) for t in record.texts] == [(0, 12, 20), (1, 12, 36)]
    assert [(c.index, c.port, c.x, c.y, c.width, c.height) for c in record.cells] == [
        (0, PORT, 8, 32, 16, 16)
    ]
    assert (record.x, record.y, record.width, record.height) == (8, 16, 40, 32)
    assert record.page == page_of[1, 1].id
    assert record.produced_by == "stamp"
