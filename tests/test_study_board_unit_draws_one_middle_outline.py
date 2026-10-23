"""The study board's unit draws as one middle outline on its page.

Every interface box of the unit stands inside the outline, on its edge, and no box or symbol
of another item does. Built through `fr` from `demo_parts`, with and without the side hint
(one module fixture per build).
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _core_boxes import Rect, box_rect, connector_names, named_boxes, outline_rect
from _drawn_pages import drawn_pages

if TYPE_CHECKING:
    import fransys as fr

    from fransys_layout.drawing import Drawing

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ha_study_board import build  # noqa: E402 -- needs the tests folder on sys.path first

INTERFACES = {"-U1-J1", "-U1-J2", "-U1-J3", "-U1-J5", "-U1-J7"}
MATES = {"-W11-P11": "-U1-J1", "-W12-P12": "-U1-J2", "-W13-P13": "-U1-J3"}
MATES |= {"-W15-P15": "-U1-J5", "-W17-P17": "-U1-J7"}


@pytest.fixture(scope="module", params=[False, True], ids=["no-hint", "hint"])
def board(request: pytest.FixtureRequest) -> fr.BuildResult:
    return build(hint=request.param)


def _inside(inner: Rect, outer: Rect) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _overlaps(a: Rect, b: Rect) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _named(result: fr.BuildResult, drawing: object) -> dict:
    return named_boxes(drawing, set(connector_names(result.model).values()))


def _middle(result: fr.BuildResult) -> list:
    """The outlines on a page where the unit's plugs stand: the parent's, not the unit's own."""
    return [
        (drawing, outline)
        for drawing in drawn_pages(result.model).values()
        for outline in drawing.outlines
        if MATES.keys() <= _named(result, drawing).keys()
    ]


def test_every_interface_box_stands_inside_the_outline_on_an_edge(board: fr.BuildResult) -> None:
    assert _middle(board)
    for drawing, outline in _middle(board):
        _interfaces_inside(board, drawing, outline)


def _interfaces_inside(board: fr.BuildResult, drawing: object, outline: object) -> None:
    named = _named(board, drawing)
    frame = outline_rect(outline)
    assert named.keys() >= INTERFACES
    for name in INTERFACES:
        box = box_rect(named[name])
        assert _inside(box, frame), name
        assert box[1] == frame[1] or box[3] == frame[3], name  # its outer edge on the outline


def test_no_box_or_symbol_of_another_item_stands_inside_the_outline(board: fr.BuildResult) -> None:
    for drawing, outline in _middle(board):
        _nothing_foreign_inside(board, drawing, outline)


def _nothing_foreign_inside(board: fr.BuildResult, drawing: Drawing, outline: object) -> None:
    frame = outline_rect(outline)
    foreign = [box for name, box in _named(board, drawing).items() if name not in INTERFACES]
    assert foreign
    assert not [box for box in foreign if _overlaps(box_rect(box), frame)]
    on_page = list(drawing.symbols)
    assert on_page
    assert not [p for p in on_page if frame[0] < p.x < frame[2] and frame[1] < p.y < frame[3]]


def test_each_plug_box_stands_face_to_face_outside_its_interface_box(
    board: fr.BuildResult,
) -> None:
    for drawing, outline in _middle(board):
        _plugs_face_to_face(board, drawing, outline)


def _plugs_face_to_face(board: fr.BuildResult, drawing: object, outline: object) -> None:
    named = _named(board, drawing)
    for plug, interface in MATES.items():
        p, j = box_rect(named[plug]), box_rect(named[interface])
        assert p[3] == j[1] or p[1] == j[3], plug  # they touch, face to face
        assert p[0] < j[2], plug  # one above the other
        assert j[0] < p[2], plug
        assert not _overlaps(p, outline_rect(outline)), plug  # outside the outline


def test_the_side_hint_puts_bus_in_on_the_top_edge(
    board: fr.BuildResult, request: pytest.FixtureRequest
) -> None:
    hinted = request.node.callspec.params["board"]
    for drawing, outline in _middle(board):
        j3 = box_rect(_named(board, drawing)["-U1-J3"])
        frame = outline_rect(outline)
        top = j3[1] == frame[1]
        assert top is hinted
        assert top or j3[3] == frame[3]
