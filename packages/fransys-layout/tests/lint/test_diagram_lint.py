"""BD8's four ERROR checks: each has a failing hand case and a clean twin one coordinate away."""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_diagram
from fransys_layout.lint._diagram_scene import Scene, SceneBox, SceneLine, SceneText
from fransys_layout.lint.codes import (
    ALL_CODES,
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_TEXT_OVERLAP,
)
from fransys_model.kernel import Severity

A, B, C, CABLE = hid("item", 1), hid("item", 2), hid("item", 3), hid("cable", 9)
G = 8


def _box(box, x, y, *, width=40, tabs=()) -> SceneBox:
    return SceneBox(box=box, rect=Box(x=x, y=y, width=width, height=24), tabs=tabs)


def _line(points, *, start=A, stop=B) -> SceneLine:
    return SceneLine(
        cable=CABLE,
        a=A,
        b=B,
        start=start,
        stop=stop,
        points=tuple(Point(x=x, y=y) for x, y in points),
    )


def _scene(boxes=(), texts=(), lines=(), markers=()) -> Scene:
    return Scene(boxes=tuple(boxes), texts=tuple(texts), lines=tuple(lines), markers=tuple(markers))


def _codes(scene: Scene) -> list[str]:
    return [one.code for one in lint_diagram(scene)]


def test_boxes_overlapping_by_one_g_fail_and_touching_edges_pass() -> None:
    assert _codes(_scene([_box(A, 0, 0), _box(B, 40 - G, 0)])) == [DIAGRAM_BOX_OVERLAP]
    assert _codes(_scene([_box(A, 0, 0), _box(B, 40, 0)])) == []


def test_a_tab_over_a_neighbour_box_overlaps() -> None:
    tab = (Box(x=36, y=8, width=16, height=8),)
    assert _codes(_scene([_box(A, 0, 0, tabs=tab), _box(B, 48, 0)])) == [DIAGRAM_BOX_OVERLAP]
    assert _codes(_scene([_box(A, 0, 0, tabs=tab), _box(B, 52, 0)])) == []


def test_box_overlap_names_both_boxes() -> None:
    (found,) = lint_diagram(_scene([_box(A, 0, 0), _box(B, 8, 0)]))
    assert set(found.subjects) == {A, B}
    assert found.severity is Severity.ERROR


def test_a_line_through_a_third_box_fails_and_routed_around_passes() -> None:
    boxes = [_box(A, 0, 0), _box(B, 160, 0), _box(C, 80, 0)]
    through = _line([(40, 12), (160, 12)])
    around = _line([(40, 12), (60, 12), (60, 40), (140, 40), (140, 12), (160, 12)])
    (found,) = lint_diagram(_scene(boxes, lines=[through]))
    assert (found.code, set(found.subjects)) == (DIAGRAM_LINE_THROUGH_BOX, {CABLE, C})
    assert _codes(_scene(boxes, lines=[around])) == []


def test_a_line_along_a_box_edge_is_clean() -> None:
    boxes = [_box(A, 0, 0), _box(B, 160, 0), _box(C, 80, 0)]
    assert _codes(_scene(boxes, lines=[_line([(40, 0), (160, 0)])])) == []
    assert _codes(_scene(boxes, lines=[_line([(40, 8), (160, 8)])])) == [DIAGRAM_LINE_THROUGH_BOX]


def test_a_line_through_a_third_boxes_tab_fails() -> None:
    boxes = [
        _box(A, 0, 0),
        _box(B, 160, 0),
        _box(C, 80, 48, tabs=(Box(x=88, y=32, width=8, height=24),)),
    ]
    assert _codes(_scene(boxes, lines=[_line([(40, 12), (160, 12)])])) == []
    tabbed = [
        _box(A, 0, 0),
        _box(B, 160, 0),
        _box(C, 80, 48, tabs=(Box(x=88, y=4, width=8, height=24),)),
    ]
    assert _codes(_scene(tabbed, lines=[_line([(40, 12), (160, 12)])])) == [
        DIAGRAM_LINE_THROUGH_BOX
    ]


def test_texts_overlapping_fail_and_one_g_apart_pass() -> None:
    first = SceneText(owner=A, rect=Box(x=0, y=0, width=40, height=8))
    near = SceneText(owner=B, rect=Box(x=0, y=7, width=40, height=8))
    apart = SceneText(owner=B, rect=Box(x=0, y=8, width=40, height=8))
    (found,) = lint_diagram(_scene(texts=[first, near]))
    assert (found.code, set(found.subjects)) == (DIAGRAM_TEXT_OVERLAP, {A, B})
    assert _codes(_scene(texts=[first, apart])) == []


def test_a_line_end_off_the_outline_fails() -> None:
    boxes = [_box(A, 0, 0), _box(B, 80, 0)]
    assert _codes(_scene(boxes, lines=[_line([(40, 12), (80, 12)])])) == []
    off = _codes(_scene(boxes, lines=[_line([(40 + G, 12), (80, 12)])]))
    assert off == [DIAGRAM_LINE_OFF_BOX]
    inside = _codes(_scene(boxes, lines=[_line([(32, 12), (80, 12)])]))
    assert inside == [DIAGRAM_LINE_OFF_BOX]


def test_a_line_end_on_a_tab_outline_is_clean() -> None:
    tab = (Box(x=40, y=8, width=16, height=8),)
    boxes = [_box(A, 0, 0, tabs=tab), _box(B, 80, 0)]
    assert _codes(_scene(boxes, lines=[_line([(56, 12), (80, 12)])])) == []
    assert _codes(_scene(boxes, lines=[_line([(60, 12), (80, 12)])])) == [DIAGRAM_LINE_OFF_BOX]


def test_a_cut_half_must_end_on_a_marker_anchor() -> None:
    boxes = [_box(A, 0, 0)]
    cut = _line([(40, 12), (80, 12)], stop=None)
    assert _codes(_scene(boxes, lines=[cut], markers=[Point(x=80, y=12)])) == []
    assert _codes(_scene(boxes, lines=[cut], markers=[Point(x=88, y=12)])) == [DIAGRAM_LINE_OFF_BOX]


def test_the_four_codes_are_listed() -> None:
    codes = {
        DIAGRAM_BOX_OVERLAP,
        DIAGRAM_LINE_OFF_BOX,
        DIAGRAM_LINE_THROUGH_BOX,
        DIAGRAM_TEXT_OVERLAP,
    }
    assert codes <= set(ALL_CODES)
    scene = _scene(
        [_box(A, 0, 0), _box(B, 8, 0), _box(C, 1000, 990)],
        [
            SceneText(owner=A, rect=Box(x=0, y=0, width=8, height=8)),
            SceneText(owner=B, rect=Box(x=0, y=0, width=8, height=8)),
        ],
        [_line([(1000, 1000), (1008, 1000)])],
    )
    found = lint_diagram(scene)
    assert {one.code for one in found} == codes
    assert {one.severity for one in found} == {Severity.ERROR}
