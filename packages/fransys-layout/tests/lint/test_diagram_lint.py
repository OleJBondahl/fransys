"""The four ERROR checks: each has a failing hand case and a clean twin one coordinate away."""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_diagram
from fransys_layout.lint._diagram_scene import Scene, SceneBox, SceneLine
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


def test_box_overlap_names_both_boxes() -> None:
    (found,) = lint_diagram(_scene([_box(A, 0, 0), _box(B, 8, 0)]))
    assert set(found.subjects) == {A, B}
    assert found.severity is Severity.ERROR
