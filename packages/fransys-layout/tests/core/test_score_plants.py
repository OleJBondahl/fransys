"""One planted case per P rule: moving one symbol flips its count from 0 to 1."""

from fransys_layout.core import Box, Pin, Scene, Wire, score


def _box(bid: str, page: int, x: int, y: int, pins: tuple[Pin, ...]) -> Box:
    return Box(bid, page, x - 8, y - 16, 16, 32, pins)


def _two_parts(*, moved: bool, page_of_b: int = 0) -> Scene:
    """A above B on one net; `moved` shifts B one column right, bending the wire into an L."""
    bx = 16 if moved else 0
    a = _box("A", 0, 0, 40, (Pin("out", 0, 56, "n1"),))
    b = _box("B", page_of_b, bx, 100, (Pin("in", bx, 84, "n1"),))
    pts = ((0, 56), (0, 70), (bx, 70), (bx, 84)) if moved else ((0, 56), (0, 84))
    return Scene((a, b), (Wire("n1", 0, pts),))


def _junction_scene(*, moved: bool) -> Scene:
    bx = 16 if moved else 0
    top = _box("T", 0, 0, 40, (Pin("out", 0, 56, "n1"),))
    pins = (Pin("n", bx, 92, "n1", node=0), Pin("s", bx, 108, "n1", node=0))
    pts = ((0, 56), (0, 74), (bx, 74), (bx, 92)) if moved else ((0, 56), (0, 92))
    return Scene((top, _box("J", 0, bx, 100, pins)), (Wire("n1", 0, pts),))


def test_p5_loose_flips_when_a_symbol_is_moved_off_its_wire() -> None:
    assert score(_two_parts(moved=False)).placement["loose"] == []
    off = _two_parts(moved=False)
    moved = Scene((off.boxes[0], _box("B", 0, 40, 100, (Pin("in", 40, 84, "n1"),))), off.wires)
    assert score(moved).placement["loose"] == ["B"]


def test_p4_junction_off_line_flips_when_a_junction_is_moved_a_column() -> None:
    assert score(_junction_scene(moved=False)).placement["junction_off_line"] == []
    assert score(_junction_scene(moved=True)).placement["junction_off_line"] == ["J"]


def test_p2_pair_cut_flips_when_one_end_of_a_pair_moves_to_another_page() -> None:
    assert score(_two_parts(moved=False)).placement["pair_cut"] == []
    moved = _two_parts(moved=False, page_of_b=1)
    assert score(moved).placement["pair_cut"] == ["n1"]


def test_a_rail_net_is_never_a_cut_pair() -> None:
    scene = _two_parts(moved=False, page_of_b=1)
    rail = Scene(scene.boxes, scene.wires, scene.markers, frozenset({"n1"}))
    assert score(rail).placement["pair_cut"] == []


def _attached(*, moved: bool) -> Scene:
    """A box pin on net n1; a column attached to it stands under it, or one column over."""
    ax = 16 if moved else 0
    card = Box("CARD", 0, 0, 40, 16, 32, (Pin("ch", 0, 56, "n1", box=True),))
    coil = Box("COIL", 0, ax, 100, 16, 32, (Pin("in", ax, 84, "n1"),), attached=True)
    return Scene((card, coil), ())


def test_p1_attached_off_pin_flips_when_a_coil_stands_a_column_off_its_pin() -> None:
    assert score(_attached(moved=False)).placement["attached_off_pin"] == []
    assert score(_attached(moved=True)).placement["attached_off_pin"] == ["COIL.in"]


def _fan(*, head_page: int) -> Scene:
    """A head feeding two legs on page 0; the head stands on page 0 or on page 1."""
    head = Box("F", head_page, 0, 40, 16, 32, (Pin("out", 0, 56, "n1"),), head=True)
    legs = tuple(
        Box(f"L{i}", 0, 32 * i, 100, 16, 32, (Pin("in", 32 * i, 84, "n1"),)) for i in (1, 2)
    )
    return Scene((head, *legs), ())


def test_p3_head_off_legs_flips_when_the_head_moves_to_the_page_without_its_legs() -> None:
    assert score(_fan(head_page=0)).placement["head_off_legs"] == []
    assert score(_fan(head_page=1)).placement["head_off_legs"] == ["F.out"]


def _strip(*, low_y: int) -> Scene:
    """Two terminals of strip X on one page, each wired down; the second sits at `low_y`."""
    boxes, wires = [], []
    for i, y in enumerate((100, low_y)):
        x = 40 * i
        pin = Pin("s", x, y + 8, f"n{i}", side="S")
        boxes.append(Box(f"T{i}", 0, x, y, 16, 16, (pin,), strip="X"))
        wires.append(Wire(f"n{i}", 0, ((x, y + 8), (x, y + 40))))
    return Scene(tuple(boxes), tuple(wires))


def test_p6_row_broken_flips_when_one_terminal_of_a_row_moves_down() -> None:
    assert score(_strip(low_y=100)).placement["row_broken"] == []
    assert score(_strip(low_y=108)).placement["row_broken"] == ["T1"]
