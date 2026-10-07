"""HL6's boxes over placed pin views: hand-made views, no model and no engine."""

from types import SimpleNamespace

from samples import hid

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Orientation,
    Point,
    PortGeometry,
    SymbolGeometry,
)
from fransys_layout.stages.box_views import BoxSpec, drawn_hidden, hidden_views, placed_boxes
from fransys_layout.stages.connector_boxes import CELL_ROWS, HALF, box_size
from fransys_layout.stages.types import PlacedFunction

G = WIRING_GRID  # 8
TH = 8  # text height; text_width("DEMO-HSG-4M") = 57 at it, so the box is 72 wide
LINES = ("DEMO-HSG-4M",)
PAGE = Box(x=0, y=0, width=400, height=300)


def pin_geometry(facing: Facing) -> SymbolGeometry:
    """One pin at the origin facing `facing`, its body on the other side of it."""
    body = Box(x=-G, y=0 if facing is Facing.N else -2 * G, width=2 * G, height=2 * G)
    return SymbolGeometry(
        key="contact-female",
        poles=1,
        orientation=Orientation.R0,
        body=body,
        keepout=body,
        through=None,
        ports=(PortGeometry(name="1", at=Point(x=0, y=0), facing=facing),),
        slots=(),
    )


def view(port: int, *, x: int, y: int = 100, page: int = 1, facing: Facing = Facing.N):
    """The pin view of port `port`: its function id is its port id."""
    return PlacedFunction(
        function=hid("port", port),
        drawing_set=1,
        page=page,
        column=("invented", f"c{x}"),
        at=Point(x=x, y=y),
        geometry=pin_geometry(facing),
    )


def spec(function: int, ports: tuple[int, ...], *, cells: bool = True) -> BoxSpec:
    ids = tuple(hid("port", port) for port in ports)
    return BoxSpec(
        function=hid("function", function),
        lines=LINES,
        cells=tuple((port, str(n)) for n, port in enumerate(ids, 1)) if cells else (),
        ports=ids,
    )


def test_a_box_hangs_from_its_pins_row_when_the_pins_face_north() -> None:
    (box,) = placed_boxes([view(1, x=40), view(2, x=64)], [spec(1, (1, 2))], TH, PAGE)
    assert box.box.y == 100


def test_a_box_stands_above_its_pins_row_when_the_pins_face_south() -> None:
    views = [view(1, x=40, facing=Facing.S), view(2, x=64, facing=Facing.S)]
    (box,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE)
    assert box.box.y + box.box.height == 100


def test_a_box_is_centred_over_one_narrow_view_at_its_natural_width() -> None:
    # the view's body is 16 wide around x 40; the box is 72 wide, so it starts at 40 - 36
    (box,) = placed_boxes([view(1, x=40)], [spec(1, (1,), cells=False)], TH, PAGE)
    assert (box.box.width, box.box.height) == box_size(LINES, [], text_height=TH)
    assert box.box.x == 4


def test_a_box_over_wide_views_spans_them() -> None:
    # bodies from 40 - 8 to 200 + 8: wider than the natural 72
    (box,) = placed_boxes([view(1, x=40), view(2, x=200)], [spec(1, (1, 2))], TH, PAGE)
    assert (box.box.x, box.box.width) == (32, 176)
    assert box.box.width >= box_size(LINES, ["1", "2"], text_height=TH)[0]


def test_a_cell_stands_under_each_pin_on_the_pins_edge_and_the_texts_start_past_it() -> None:
    (box,) = placed_boxes([view(1, x=40), view(2, x=200)], [spec(1, (1, 2))], TH, PAGE)
    assert [cell.port for cell in box.cells] == [hid("port", 1), hid("port", 2)]
    assert [cell.box.x + cell.box.width // 2 for cell in box.cells] == [40, 200]
    assert {cell.box.y for cell in box.cells} == {100}
    assert box.texts == (Point(x=32 + HALF, y=100 + CELL_ROWS * G + HALF),)


def test_south_facing_cells_stand_on_the_bottom_edge_and_the_texts_at_the_top() -> None:
    views = [view(1, x=40, facing=Facing.S), view(2, x=200, facing=Facing.S)]
    (box,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE)
    assert {cell.box.y + cell.box.height for cell in box.cells} == {100}
    assert box.texts == (Point(x=32 + HALF, y=box.box.y + HALF),)


def test_two_pages_give_two_boxes_and_a_view_not_on_a_page_gives_no_box_there() -> None:
    views = [view(1, x=40), view(2, x=200), view(1, x=40, page=2), view(3, x=80)]
    boxes = placed_boxes(views, [spec(1, (1, 2)), spec(2, (3,)), spec(3, (4,))], TH, PAGE)
    assert [(box.function, box.page) for box in boxes] == [
        (hid("function", 1), 1),
        (hid("function", 2), 1),
        (hid("function", 1), 2),
    ]
    # page 2 holds only port 1's view, so only its cell
    assert [cell.port for cell in boxes[2].cells] == [hid("port", 1)]


def test_hidden_views_hold_every_port_of_every_spec() -> None:
    hidden = hidden_views([spec(1, (1, 2)), spec(2, (3,), cells=False)])
    assert hidden == {hid("port", 1), hid("port", 2), hid("port", 3)}


def test_a_hidden_view_is_drawn_hidden_but_on_the_page_where_a_marker_stands_at_it() -> None:
    views = [view(1, x=40), view(1, x=40, page=2), view(2, x=64), view(9, x=80)]
    marker = SimpleNamespace(port=hid("port", 1), drawing_set=1, page=2)
    hidden = drawn_hidden(views, frozenset({hid("port", 1), hid("port", 2)}), [marker])
    # port 1 keeps its symbol on page 2 only; port 9 is no boxed view
    assert hidden == ((hid("port", 1), 1, 1), (hid("port", 2), 1, 1))


def test_a_box_at_the_content_boxs_side_moves_in_to_it() -> None:
    # centred over a view at x 16 it would start at -20; on the right edge at 400 - 72 + 20
    (left,) = placed_boxes([view(1, x=16)], [spec(1, (1,), cells=False)], TH, PAGE)
    (right,) = placed_boxes([view(1, x=384)], [spec(1, (1,), cells=False)], TH, PAGE)
    assert (left.box.x, right.box.x + right.box.width) == (0, 400)
