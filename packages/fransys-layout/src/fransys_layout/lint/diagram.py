"""The six ERROR checks on a block diagram's own scene (block-diagrams spec, LEGACY-B3 L12)."""

from itertools import combinations, pairwise

from fransys_layout.fix_text import fix_text
from fransys_layout.geometry import Box, Point, contains_point, overlaps
from fransys_layout.routing.space import Run, crosses, run_of
from fransys_model.kernel import Finding, Severity

from ._diagram_scene import Ident, Scene, SceneBox, SceneLine, shapes
from .codes import (
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LABEL_STRUCK,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_LINES_SHARE_TRACK,
    DIAGRAM_TEXT_OVERLAP,
    UNCLEARABLE,
)


def _error(code: str, subjects: tuple[Ident, ...], message: str) -> Finding:
    """ERROR, or INFO for a code in `UNCLEARABLE` (layout-0252)."""
    severity = Severity.INFO if code in UNCLEARABLE else Severity.ERROR
    return Finding(
        code=code, severity=severity, subjects=subjects, message=message, fix=fix_text(code)
    )


def check_box_overlap(scene: Scene) -> tuple[Finding, ...]:
    """Two boxes share interior, or a tab of one overlaps another box's rectangle or tab."""
    return tuple(
        _error(DIAGRAM_BOX_OVERLAP, (one.box, two.box), "Two boxes overlap.")
        for one, two in combinations(scene.boxes, 2)
        if any(overlaps(a, b) for a in shapes(one) for b in shapes(two))
    )


def check_text_overlap(scene: Scene) -> tuple[Finding, ...]:
    """Two printed texts share interior area."""
    return tuple(
        _error(DIAGRAM_TEXT_OVERLAP, (one.owner, two.owner), "Two texts overlap.")
        for one, two in combinations(scene.texts, 2)
        if overlaps(one.rect, two.rect)
    )


def _passes_through(line: SceneLine, one: SceneBox) -> bool:
    runs = [run_of(a, b) for a, b in pairwise(line.points)]
    return any(crosses(shape, run) for shape in shapes(one) for run in runs)


def check_line_through_box(scene: Scene) -> tuple[Finding, ...]:
    """A line passes through the interior of a box or tab other than its own two."""
    return tuple(
        _error(DIAGRAM_LINE_THROUGH_BOX, (line.cable, one.box), "A line crosses a third box.")
        for line in scene.lines
        for one in scene.boxes
        if one.box not in (line.start, line.stop) and _passes_through(line, one)
    )


def _on_outline(point: Point, rect: Box) -> bool:
    interior = rect.x < point.x < rect.x + rect.width and rect.y < point.y < rect.y + rect.height
    return contains_point(rect, point.x, point.y) and not interior


def _ends_on(point: Point, box: Ident, scene: Scene) -> bool:
    return any(
        _on_outline(point, shape) for one in scene.boxes if one.box == box for shape in shapes(one)
    )


def _off_ends(line: SceneLine, scene: Scene) -> list[tuple[Ident, Ident]]:
    """The `(cable, box)` of each end of `line` that is not where it belongs."""
    off = []
    if not _ends_on(line.points[0], line.start, scene):
        off.append((line.cable, line.start))
    if line.stop is None:
        if line.points[-1] not in scene.markers:
            off.append((line.cable, line.start))
    elif not _ends_on(line.points[-1], line.stop, scene):
        off.append((line.cable, line.stop))
    return off


def check_line_off_box(scene: Scene) -> tuple[Finding, ...]:
    """A line end is not on the outline of its box or a tab of it, or of a marker."""
    return tuple(
        _error(DIAGRAM_LINE_OFF_BOX, subjects, "A line end is off its box outline.")
        for line in scene.lines
        for subjects in _off_ends(line, scene)
    )


def _runs(line: SceneLine) -> list[Run]:
    return [run_of(a, b) for a, b in pairwise(line.points)]


def check_label_struck(scene: Scene) -> tuple[Finding, ...]:
    """A line passes through the interior of a line label: a label never lies under a line."""
    return tuple(
        _error(DIAGRAM_LABEL_STRUCK, (label.owner, line.cable), "A line strikes a label.")
        for label in scene.labels
        for line in scene.lines
        if any(crosses(label.rect, run) for run in _runs(line))
    )


def _shared(one: Run, other: Run) -> bool:
    """Whether two runs lie on one track and overlap by more than a point."""
    if one.x == one.to_x and other.x == other.to_x:
        return one.x == other.x and min(one.to_y, other.to_y) > max(one.y, other.y)
    if one.y == one.to_y and other.y == other.to_y:
        return one.y == other.y and min(one.to_x, other.to_x) > max(one.x, other.x)
    return False


def check_collinear_overlap(scene: Scene) -> tuple[Finding, ...]:
    """Two lines of different cables share a track segment of positive length."""
    return tuple(
        _error(DIAGRAM_LINES_SHARE_TRACK, (one.cable, other.cable), "Two cables share a track.")
        for one, other in combinations(scene.lines, 2)
        if one.cable != other.cable and any(_shared(r, s) for r in _runs(one) for s in _runs(other))
    )


def lint_diagram(scene: Scene) -> tuple[Finding, ...]:
    """All six checks, sorted by code and subjects."""
    found = (
        *check_label_struck(scene),
        *check_collinear_overlap(scene),
        *check_box_overlap(scene),
        *check_line_through_box(scene),
        *check_text_overlap(scene),
        *check_line_off_box(scene),
    )
    return tuple(sorted(found, key=lambda one: (one.code, one.subjects)))
