"""The six ERROR checks: each has a failing hand case and a clean twin one coordinate away."""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_diagram
from fransys_layout.lint._diagram_scene import Scene, SceneBox, SceneLine, SceneText
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


def _label(x, y, *, owner=CABLE) -> SceneText:
    return SceneText(owner=owner, rect=Box(x=x, y=y, width=24, height=8))


def _struck(label, *lines) -> list[str]:
    scene = Scene(boxes=(), texts=(label,), lines=tuple(lines), markers=(), labels=(label,))
    return [one.code for one in lint_diagram(scene) if one.code != "DIAGRAM_LINE_OFF_BOX"]


def test_a_line_through_a_label_strikes_it() -> None:
    other = hid("cable", 8)
    line = SceneLine(
        cable=other, a=A, b=B, start=A, stop=B, points=(Point(x=40, y=0), Point(x=40, y=40))
    )
    assert _struck(_label(32, 16), line) == ["DIAGRAM_LABEL_STRUCK"]
    assert _struck(_label(48, 16), line) == []


def test_a_line_along_a_label_edge_does_not_strike_it() -> None:
    line = SceneLine(
        cable=CABLE, a=A, b=B, start=A, stop=B, points=(Point(x=32, y=0), Point(x=32, y=40))
    )
    assert _struck(_label(32, 16), line) == []


def _track(points, cable) -> SceneLine:
    return SceneLine(
        cable=cable,
        a=A,
        b=B,
        start=A,
        stop=B,
        points=tuple(Point(x=x, y=y) for x, y in points),
    )


def test_two_cables_sharing_a_track_segment_are_found() -> None:
    one, two = _track([(0, 8), (0, 40)], CABLE), _track([(0, 24), (0, 56)], hid("cable", 8))
    found = [c for c in _codes(_scene(lines=[one, two])) if c != "DIAGRAM_LINE_OFF_BOX"]
    assert found == ["DIAGRAM_LINES_SHARE_TRACK"]


def test_tracks_that_only_touch_or_cross_are_clean() -> None:
    one = _track([(0, 8), (0, 40)], CABLE)
    touching = _track([(0, 40), (0, 56)], hid("cable", 8))
    crossing = _track([(-8, 24), (8, 24)], hid("cable", 7))
    found = _codes(_scene(lines=[one, touching, crossing]))
    assert "DIAGRAM_LINES_SHARE_TRACK" not in found


def test_one_cables_own_lines_may_share_a_trunk() -> None:
    one, two = _track([(0, 8), (0, 40)], CABLE), _track([(0, 8), (0, 56)], CABLE)
    assert "DIAGRAM_LINES_SHARE_TRACK" not in _codes(_scene(lines=[one, two]))
