"""The six ERROR checks on a block diagram's own scene (block-diagrams spec, LEGACY-B3 L12)."""

from itertools import combinations, pairwise
lazy from collections.abc import Iterable

from fransys_layout.fix_text import finding
from fransys_layout.geometry import Box, Point, contains_point, overlaps
from fransys_layout.routing.space import crosses, run_of, runs_along
from fransys_layout.routing.track_index import TrackIndex
lazy from fransys_model.kernel import Finding, findings_sorted

from ._diagram_scene import Ident, Scene, SceneLine, shapes
from .codes import (
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LABEL_STRUCK,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_LINES_SHARE_TRACK,
    DIAGRAM_TEXT_OVERLAP,
)


def check_box_overlap(scene: Scene) -> tuple[Finding, ...]:
    """Two boxes share interior, or a tab of one overlaps another box's rectangle or tab."""
    return tuple(
        finding(DIAGRAM_BOX_OVERLAP, (one.box, two.box), "Two boxes overlap.")
        for one, two in combinations(scene.boxes, 2)
        if any(overlaps(a, b) for a in shapes(one) for b in shapes(two))
    )


def check_text_overlap(scene: Scene) -> tuple[Finding, ...]:
    """Two printed texts share interior area, or a line label shares it with a box or a tab."""
    texts = tuple(
        finding(DIAGRAM_TEXT_OVERLAP, (one.owner, two.owner), "Two texts overlap.")
        for one, two in combinations(scene.texts, 2)
        if overlaps(one.rect, two.rect)
    )
    on_box = tuple(
        finding(DIAGRAM_TEXT_OVERLAP, (label.owner, one.box), "A label overlaps a box.")
        for label in scene.labels
        for one in scene.boxes
        if any(overlaps(label.rect, shape) for shape in shapes(one))
    )
    return texts + on_box


type Tracks = TrackIndex[int]


def _crossed(shapes_by_id: Iterable[tuple[Box, int]], tracks: Tracks) -> set[tuple[int, int]]:
    """The `(line, id)` of each line with a run through the interior of a shape."""
    return {(j, i) for shape, i in shapes_by_id for run, j in tracks.near(shape) if crosses(shape, run)}


def check_line_through_box(scene: Scene, tracks: Tracks) -> tuple[Finding, ...]:
    """A line passes through the interior of a box or tab other than its own two."""
    hits = _crossed(((shape, i) for i, one in enumerate(scene.boxes) for shape in shapes(one)), tracks)
    return tuple(
        finding(DIAGRAM_LINE_THROUGH_BOX, (scene.lines[j].cable, scene.boxes[i].box), "A line crosses a third box.")
        for j, i in hits
        if scene.boxes[i].box not in (scene.lines[j].start, scene.lines[j].stop)
    )


def _on_outline(point: Point, rect: Box) -> bool:
    interior = rect.x < point.x < rect.x + rect.width and rect.y < point.y < rect.y + rect.height
    return contains_point(rect, point.x, point.y) and not interior


def _ends_on(point: Point, box: Ident, scene: Scene) -> bool:
    return any(_on_outline(point, shape) for one in scene.boxes if one.box == box for shape in shapes(one))


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
        finding(DIAGRAM_LINE_OFF_BOX, subjects, "A line end is off its box outline.") for line in scene.lines for subjects in _off_ends(line, scene)
    )


def check_label_struck(scene: Scene, tracks: Tracks) -> tuple[Finding, ...]:
    """A line passes through the interior of a line label: a label never lies under a line."""
    hits = _crossed(((label.rect, i) for i, label in enumerate(scene.labels)), tracks)
    return tuple(finding(DIAGRAM_LABEL_STRUCK, (scene.labels[i].owner, scene.lines[j].cable), "A line strikes a label.") for j, i in hits)


def check_collinear_overlap(scene: Scene, tracks: Tracks) -> tuple[Finding, ...]:
    """Two lines of different cables share a track segment of positive length."""
    pairs = {
        (a, b)
        for run, a in tracks.entries
        for box in (Box(x=run.x, y=run.y, width=run.to_x - run.x, height=run.to_y - run.y),)
        for other, b in tracks.near(box)
        if a < b and runs_along(box, other)
    }
    return tuple(
        finding(DIAGRAM_LINES_SHARE_TRACK, (scene.lines[a].cable, scene.lines[b].cable), "Two cables share a track.")
        for a, b in pairs
        if scene.lines[a].cable != scene.lines[b].cable
    )


def scene_tracks(scene: Scene) -> Tracks:
    """The runs of every line of `scene`, keyed by track: the one index the checks share."""
    return TrackIndex((run_of(a, b), j) for j, line in enumerate(scene.lines) for a, b in pairwise(line.points))


def lint_diagram(scene: Scene) -> tuple[Finding, ...]:
    """All six checks, sorted by code and subjects."""
    tracks = scene_tracks(scene)
    found = (
        *check_label_struck(scene, tracks),
        *check_collinear_overlap(scene, tracks),
        *check_box_overlap(scene),
        *check_line_through_box(scene, tracks),
        *check_text_overlap(scene),
        *check_line_off_box(scene),
    )
    return findings_sorted(found, by_message=False)
