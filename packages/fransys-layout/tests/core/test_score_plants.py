"""One planted case per P rule: moving one symbol flips its count from 0 to 1. Plus Q's terms."""

from dataclasses import replace
from typing import TypedDict, Unpack

import pytest
from scene_fixtures import flow, layout, problem

from fransys_layout.core import Box, Orientation, Size, outputs
from fransys_layout.core.outputs import Scene, SceneBox, SceneMarker, ScenePin, SceneWire
from fransys_layout.core.score import WEIGHTS, placement_flags, score
from fransys_layout.core.values import RefKind


def _pin(name: str, x: int, y: int, net: str | None, **kw) -> ScenePin:
    return ScenePin(
        name,
        x,
        y,
        kw.pop("side", "S"),
        net,
        kw.pop("node", None),
        kw.pop("biased", False),
        kw.pop("box", False),
        kw.pop("head", False),
    )


class _Flags(TypedDict, total=False):
    attached: bool
    strip: str | None
    orient: Orientation


def _box(
    bid: str, page: int, x: int, y: int, pins: tuple[ScenePin, ...], **kw: Unpack[_Flags]
) -> SceneBox:
    body = Box(x - 8, y - 16, 16, 32)
    flags: _Flags = {"attached": False, "strip": None, "orient": "R0", **kw}
    return SceneBox(bid, page, body, body, pins, **flags)


def _wire(net: str, page: int, points: tuple) -> SceneWire:
    return SceneWire(net, page, points, 1, "straight")


def _scene(boxes, wires, markers=(), rails=frozenset(), fill=()) -> Scene:
    pages = len({b.page for b in boxes})
    return Scene(
        Size(100, 100),
        pages,
        tuple(boxes),
        tuple(wires),
        tuple(markers),
        rails,
        fill,
        (),
        (),
        (),
    )


def _flags(scene: Scene) -> dict[str, list[str]]:
    return placement_flags(scene)


def _two_parts(*, moved: bool, page_of_b: int = 0) -> Scene:
    """A above B on one net; `moved` shifts B one column right, bending the wire into an L."""
    bx = 16 if moved else 0
    a = _box("A", 0, 0, 40, (_pin("out", 0, 56, "n1"),))
    b = _box("B", page_of_b, bx, 100, (_pin("in", bx, 84, "n1"),))
    pts = ((0, 56), (0, 70), (bx, 70), (bx, 84)) if moved else ((0, 56), (0, 84))
    return _scene((a, b), (_wire("n1", 0, pts),))


def _junction_scene(*, moved: bool) -> Scene:
    bx = 16 if moved else 0
    top = _box("T", 0, 0, 40, (_pin("out", 0, 56, "n1"),))
    pins = (_pin("n", bx, 92, "n1", node=0), _pin("s", bx, 108, "n1", node=0))
    pts = ((0, 56), (0, 74), (bx, 74), (bx, 92)) if moved else ((0, 56), (0, 92))
    return _scene((top, _box("J", 0, bx, 100, pins)), (_wire("n1", 0, pts),))


def test_p5_loose_flips_when_a_symbol_is_moved_off_its_wire() -> None:
    assert _flags(_two_parts(moved=False))["loose"] == []
    off = _two_parts(moved=False)
    moved = _scene((off.boxes[0], _box("B", 0, 40, 100, (_pin("in", 40, 84, "n1"),))), off.wires)
    assert _flags(moved)["loose"] == ["B"]


def test_p4_junction_off_line_flips_when_a_junction_is_moved_a_column() -> None:
    assert _flags(_junction_scene(moved=False))["junction_off_line"] == []
    assert _flags(_junction_scene(moved=True))["junction_off_line"] == ["J"]


def test_p2_pair_cut_flips_when_one_end_of_a_pair_moves_to_another_page() -> None:
    assert _flags(_two_parts(moved=False))["pair_cut"] == []
    moved = _two_parts(moved=False, page_of_b=1)
    assert _flags(moved)["pair_cut"] == ["n1"]


def test_a_rail_net_is_never_a_cut_pair() -> None:
    scene = _two_parts(moved=False, page_of_b=1)
    rail = _scene(scene.boxes, scene.wires, scene.markers, frozenset({"n1"}))
    assert _flags(rail)["pair_cut"] == []


def _attached(*, moved: bool) -> Scene:
    """A box pin on net n1; a column attached to it stands under it, or one column over."""
    ax = 16 if moved else 0
    card = _box("CARD", 0, 0, 40, (_pin("ch", 0, 56, "n1", box=True),))
    coil = _box("COIL", 0, ax, 100, (_pin("in", ax, 84, "n1"),), attached=True)
    return _scene((card, coil), ())


def test_p1_attached_off_pin_flips_when_a_coil_stands_a_column_off_its_pin() -> None:
    assert _flags(_attached(moved=False))["attached_off_pin"] == []
    assert _flags(_attached(moved=True))["attached_off_pin"] == ["COIL.in"]


def _fan(*, head_page: int) -> Scene:
    """A head feeding two legs on page 0; the head stands on page 0 or on page 1."""
    head = _box("F", head_page, 0, 40, (_pin("out", 0, 56, "n1", head=True),))
    legs = tuple(_box(f"L{i}", 0, 32 * i, 100, (_pin("in", 32 * i, 84, "n1"),)) for i in (1, 2))
    return _scene((head, *legs), ())


def test_p3_head_off_legs_flips_when_the_head_moves_to_the_page_without_its_legs() -> None:
    assert _flags(_fan(head_page=0))["head_off_legs"] == []
    assert _flags(_fan(head_page=1))["head_off_legs"] == ["F.out"]


def _strip(*, low_y: int, bands=()) -> Scene:
    """Two terminals of strip X on one page, each wired down; the second sits at `low_y`."""
    boxes, wires = [], []
    for i, y in enumerate((100, low_y)):
        x = 40 * i
        pin = _pin("s", x, y + 8, f"n{i}", side="S")
        boxes.append(_box(f"T{i}", 0, x, y, (pin,), strip="X"))
        wires.append(_wire(f"n{i}", 0, ((x, y + 8), (x, y + 40))))
    return replace(_scene(boxes, wires), bands=bands)


def test_p6_row_broken_flips_when_one_terminal_of_a_row_moves_down() -> None:
    assert _flags(_strip(low_y=100))["row_broken"] == []
    assert _flags(_strip(low_y=108))["row_broken"] == ["T1"]


def test_p6_a_strip_split_over_two_rows_at_two_heights_is_clean() -> None:
    two_rows = ((0, ((0, 150), (150, 300))),)
    assert _flags(_strip(low_y=200, bands=two_rows))["row_broken"] == []


def test_p6_a_strip_inside_one_row_at_two_heights_is_flagged() -> None:
    one_row = ((0, ((0, 300),)),)
    assert _flags(_strip(low_y=200, bands=one_row))["row_broken"] == ["T1"]


def _crossing(*, marked: bool) -> Scene:
    """One horizontal wire of n1 crossing one vertical wire of n2; a tag marker when `marked`."""
    wires = (
        _wire("n1", 0, ((0, 50), (100, 50))),
        _wire("n2", 0, ((50, 0), (50, 100))),
    )
    boxes = (_box("A", 0, 0, 50, (_pin("o", 0, 50, "n1", node=0),)),)
    markers = (SceneMarker("n1", RefKind.TAG, 0, 0, 0, "A", "o", "", "N"),) if marked else ()
    return _scene(boxes, wires, markers)


def test_q_is_the_weighted_sum() -> None:
    got = score(_crossing(marked=True))
    assert got.X == 1
    assert dict(got.R) == {"tag_pair": 1}
    assert pytest.approx(WEIGHTS["ref"] * 1 + WEIGHTS["x"]) == got.Q


def test_a_page_adds_w_p() -> None:
    one, two = _two_parts(moved=False), _two_parts(moved=False, page_of_b=1)
    assert pytest.approx(WEIGHTS["p"]) == score(two).Q - score(one).Q


def test_an_empty_fill_adds_w_f_and_a_scene_with_no_rows_adds_nothing() -> None:
    base = _two_parts(moved=False)
    thin = _scene(base.boxes, base.wires, fill=(0.0,))
    assert pytest.approx(WEIGHTS["f"]) == score(thin).Q - score(base).Q


def test_a_planted_layout_scores_end_to_end_through_outputs_scene() -> None:
    got = score(outputs.scene(layout(), problem(), flow()))
    assert dict(got.P) == {
        "attached_off_pin": 1,
        "head_off_legs": 1,
        "junction_off_line": 0,
        "loose": 2,
        "pair_cut": 1,
        "row_broken": 0,
    }
    assert (got.pages, got.fill) == (2, (0.1, 0.0))
    assert pytest.approx(WEIGHTS["ref"] + WEIGHTS["p"] + WEIGHTS["f"] * (0.9**2 + 1.0)) == got.Q


def test_scene_pin_without_head_raises() -> None:
    with pytest.raises(TypeError):
        ScenePin("1", 0, 0, "S", None, None, biased=False, box=False)  # ty: ignore[missing-argument] the test proves head is required
