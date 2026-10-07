"""BD8's four ERROR checks on a block diagram's own scene (block-diagrams spec)."""

from itertools import combinations, pairwise

from fransys_layout.geometry import Box, Point, overlaps
from fransys_layout.stages.space import crosses, run_of
from fransys_model.kernel import Finding, Severity

from ._diagram_scene import Ident, Scene, SceneBox, SceneLine, shapes
from .codes import (
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_TEXT_OVERLAP,
)


def _error(code: str, subjects: tuple[Ident, ...], message: str) -> Finding:
    return Finding(code=code, severity=Severity.ERROR, subjects=subjects, message=message)


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
    inside = rect.x <= point.x <= rect.x + rect.width and rect.y <= point.y <= rect.y + rect.height
    interior = rect.x < point.x < rect.x + rect.width and rect.y < point.y < rect.y + rect.height
    return inside and not interior


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


def lint_diagram(scene: Scene) -> tuple[Finding, ...]:
    """All four BD8 checks, sorted by code and subjects."""
    found = (
        *check_box_overlap(scene),
        *check_line_through_box(scene),
        *check_text_overlap(scene),
        *check_line_off_box(scene),
    )
    return tuple(sorted(found, key=lambda one: (one.code, one.subjects)))
