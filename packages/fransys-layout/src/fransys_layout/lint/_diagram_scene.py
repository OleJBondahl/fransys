"""The scene a block diagram is linted on (BD8): boxes, tabs, texts, lines and cut-line markers.

Its own values, not the engine's: lint may not import `engines`, and the checks need only geometry.
"""

from typing import Any

from fransys_layout.geometry import Box, Point
from fransys_model.kernel import Id, value

type Ident = Id[Any]


@value
class SceneBox:
    """One box: its subject, its rectangle and the rectangles of its tabs."""

    box: Id[Any]
    rect: Box
    tabs: tuple[Box, ...]


@value
class SceneText:
    """One printed text (a box line, a tab text or a line label) and its owner, a box or a cable."""

    owner: Id[Any]
    rect: Box


@value
class SceneLine:
    """An orthogonal polyline: `points[0]` ends at box `start`, `points[-1]` at `stop`.

    `stop` is None when the far end is a marker of a line cut between sheets.
    """

    cable: Id[Any]
    a: Id[Any]
    b: Id[Any]
    start: Id[Any]
    stop: Id[Any] | None
    points: tuple[Point, ...]


@value
class Scene:
    """Everything BD8 checks on one sheet; `markers` are the anchor points of cut-line markers."""

    boxes: tuple[SceneBox, ...]
    texts: tuple[SceneText, ...]
    lines: tuple[SceneLine, ...]
    markers: tuple[Point, ...]


def shapes(one: SceneBox) -> tuple[Box, ...]:
    """The rectangle of a box followed by its tabs."""
    return (one.rect, *one.tabs)
