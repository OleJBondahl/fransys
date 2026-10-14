"""Boxes over placed pin views: hand-made views, no model and no engine."""

from types import SimpleNamespace
from typing import Any

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
from fransys_layout.stages.box_views import (
    BoxSpec,
    cell_views,
    cells_on_top,
    drawn_hidden,
    face_plugs,
    hidden_views,
    moved_markers,
    moved_views,
    placed_boxes,
    slot_rows,
)
from fransys_layout.stages.connector_boxes import CELL_ROWS, HALF, box_size
from fransys_layout.stages.types import LinkMarker, MarkerSide, PlacedFunction

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
    # the view's body is 16 wide around x 40; the box is 64 wide, so it starts at 40 - 32
    (box,) = placed_boxes([view(1, x=40)], [spec(1, (1,), cells=False)], TH, PAGE)
    assert (box.box.width, box.box.height) == box_size(LINES, [], text_height=TH)
    assert box.box.x == 8


def test_a_box_over_wide_views_is_as_wide_as_its_cells_and_starts_at_the_first() -> None:
    # HL19: views at 40 and 200 no longer stretch the box; it starts under the first pin's cell
    (box,) = placed_boxes([view(1, x=40), view(2, x=200)], [spec(1, (1, 2))], TH, PAGE)
    assert (box.box.x, box.box.width) == (32, box_size(LINES, ["1", "2"], text_height=TH)[0])


def test_a_cell_stands_beside_the_last_on_the_pins_edge_and_the_texts_start_past_it() -> None:
    (box,) = placed_boxes([view(1, x=40), view(2, x=200)], [spec(1, (1, 2))], TH, PAGE)
    assert [cell.port for cell in box.cells] == [hid("port", 1), hid("port", 2)]
    assert [cell.box.x + cell.box.width // 2 for cell in box.cells] == [40, 56]
    assert {cell.box.y for cell in box.cells} == {100}
    assert box.texts == (Point(x=32 + HALF, y=100 + CELL_ROWS * G + HALF),)


def test_a_view_moves_onto_its_slot_and_every_boxed_view_loses_its_keepout() -> None:
    # HL19: the lead from a cell to its symbol is the route from the moved view
    views = [view(1, x=40), view(2, x=200)]
    (box,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE)
    moves = cell_views(views, [box])
    assert moves == {
        (hid("port", 1), 1, 1): (0, 0, Facing.N, Point(x=40, y=100)),
        (hid("port", 2), 1, 1): (-144, 0, Facing.N, Point(x=56, y=100)),
    }
    moved = moved_views(views, moves)
    assert {v.geometry.keepout for v in moved} == {Box(x=0, y=0, width=0, height=0)}
    assert [(v.function, v.at.x) for v in moved] == [
        (hid("port", 1), 40),
        (hid("port", 2), 56),
    ]


def test_a_cell_less_box_gives_each_pin_two_grids_in_pin_order() -> None:
    views = [view(2, x=200), view(1, x=40)]
    (box,) = placed_boxes(views, [spec(1, (1, 2), cells=False)], TH, PAGE)
    assert [(s.port, s.x) for s in box.slots] == [(hid("port", 1), 40), (hid("port", 2), 56)]
    assert box.cells == ()


def test_each_box_and_the_cells_between_its_slots_are_blocked_and_the_slots_are_not() -> None:
    views = [view(1, x=40), view(2, x=72)]
    (box,) = placed_boxes(views, [spec(1, (1, 2), cells=False)], TH, PAGE)
    y = box.slots[0].y
    blocks = slot_rows([box])[box.drawing_set, box.page]
    assert [(s.box.x, s.box.y) for s in blocks.hard] == [(48, y)]
    assert [s.box for s in blocks.soft] == [box.box]


def test_a_view_facing_into_its_box_turns_to_face_away_and_stands_on_the_far_side_of_its_slot() -> (
    None
):
    # a pin facing S under a box hanging from the row: its lead would have to enter the box
    views = [view(1, x=40), view(2, x=56, facing=Facing.S)]
    (box,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE)
    moves = cell_views(views, [box])
    assert moves[hid("port", 2), 1, 1][2] is Facing.N
    moved = moved_views(views, moves)
    assert [v.geometry.ports[0].facing for v in moved] == [Facing.N, Facing.N]


def _marker(*, y: int, port: int = 2) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", port),
        side=MarkerSide.USER,
        drawing_set=1,
        page=1,
        at=Point(x=40, y=100),
        box=Box(x=34, y=y, width=12, height=56),
        partner_page=2,
        vertical=True,
    )


def test_a_marker_moves_with_its_view_and_a_marker_on_no_moved_view_stays() -> None:
    other = _marker(y=108, port=9)
    moves = {(hid("port", 2), 1, 1): (16, -8, Facing.S, Point(x=56, y=92))}
    moved, same = moved_markers([_marker(y=108), other], moves)
    assert (moved.at, moved.box.x, moved.box.y) == (Point(x=56, y=92), 50, 100)
    assert same == other


def test_a_marker_on_the_side_the_pin_does_not_face_is_mirrored_about_the_pin() -> None:
    (moved,) = moved_markers(
        [_marker(y=108)], {(hid("port", 2), 1, 1): (0, 0, Facing.N, Point(x=40, y=100))}
    )
    assert (moved.box.y, moved.box.height) == (100 - 8 - 56, 56)


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


def _reach(*points: Point) -> dict[tuple[Any, int, int], tuple[Point, ...]]:
    """Port 1's view on page 1 leads to `points` (layout-0211)."""
    return {(hid("port", 1), 1, 1): points}


def test_cells_turn_to_the_edge_their_leads_run_to_and_the_texts_take_the_other() -> None:
    views = [view(1, x=40), view(2, x=200)]
    (box,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE, _reach(Point(x=40, y=300)))
    bottom = box.box.y + box.box.height
    assert box.box.y == 100  # the rectangle stays where the pins' row hangs it
    assert {cell.box.y + cell.box.height for cell in box.cells} == {bottom}
    assert {(slot.y, slot.facing) for slot in box.slots} == {(bottom, Facing.S)}
    assert box.texts == (Point(x=32 + HALF, y=100 + HALF),)


def test_a_tie_no_lead_or_a_lead_end_on_the_box_keeps_the_cells_on_the_pins_edge() -> None:
    box = Box(x=0, y=100, width=64, height=48)
    below, above = Point(x=8, y=300), Point(x=8, y=20)
    assert cells_on_top(box, [], pins_edge=True)
    assert not cells_on_top(box, [above, below], pins_edge=False)
    assert cells_on_top(box, [below, Point(x=8, y=100)], pins_edge=True)
    assert not cells_on_top(box, [below], pins_edge=True)
    assert cells_on_top(box, [above], pins_edge=False)


def test_a_plug_takes_the_edge_away_from_its_mates_cells_and_its_slots_face_out() -> None:
    views = [view(1, x=40), view(2, x=64)]
    (mate,) = placed_boxes(views, [spec(1, (1, 2))], TH, PAGE, _reach(Point(x=40, y=300)))
    # the plug's own pins face south, so its slots came out on its bottom edge
    (plug,) = placed_boxes([view(3, x=40, facing=Facing.S)], [spec(2, (3,), cells=False)], TH, PAGE)
    faced = {one.function: one for one in face_plugs([mate, plug], {plug.function: mate.function})}
    moved = faced[plug.function]
    assert moved.box.y + moved.box.height == mate.box.y
    assert {(slot.y, slot.facing) for slot in moved.slots} == {(moved.box.y, Facing.N)}


def test_a_marker_on_a_turned_view_stands_on_its_slot_not_where_its_old_pin_moved() -> None:
    # the view turned about its origin: its pin, and so its marker, stand on the slot
    (moved,) = moved_markers(
        [_marker(y=108)], {(hid("port", 2), 1, 1): (0, 0, Facing.S, Point(x=40, y=132))}
    )
    assert (moved.at, moved.box.y) == (Point(x=40, y=132), 140)


def test_a_lead_end_too_near_the_box_to_route_keeps_the_cells_on_the_pins_edge() -> None:
    """Layout-0211 (2026-10-14): a far end a grid above the box leaves no lane past the cells."""
    box = Box(x=0, y=100, width=64, height=48)
    near, far = Point(x=8, y=100 - WIRING_GRID), Point(x=8, y=100 - 4 * WIRING_GRID)
    assert not cells_on_top(box, [near], pins_edge=False)
    assert cells_on_top(box, [far], pins_edge=False)
