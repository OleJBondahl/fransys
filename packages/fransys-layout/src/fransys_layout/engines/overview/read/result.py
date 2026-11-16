"""The overview engine's result: every placed view's boxes, lines and lane heads, as one value (layout-0611)."""

from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from fransys_layout.geometry import Point
from fransys_model.kernel import Id, value
from fransys_model.layout import OverviewMode, OverviewRef
from fransys_model.vocab.core import Unit
lazy from fransys_layout.lint._diagram_scene import Scene

if TYPE_CHECKING:
    from fransys_layout.engines.overview.read.values import Ident, LineSpec, ViewFacts
    from fransys_layout.engines.overview.sheet_values import DiagramBox, DiagramLine, PlacedSheet


@value
class OverviewPlacedTab:
    """One tab outside a box edge: `index` is its place in the box's tabs, `x`, `y` its corner.

    `text_width` is the width of its text, `width` and `height` its size, all in grid units.
    """

    index: int
    x: int
    y: int
    text_width: int
    width: int
    height: int


@value
class OverviewPlacedBox:
    """A box of a view at `x`, `y` (its top-left corner from the view's), with its tabs in order."""

    x: int
    y: int
    width: int
    height: int
    tabs: tuple[OverviewPlacedTab, ...]


@value
class OverviewPlacedLine:
    """A line of a view: `a`, `b` the positions of its end boxes in the view's boxes.

    `points` run from `a` to `b`; `text_x`, `text_y` is where its text is centred.
    """

    a: int
    b: int
    points: tuple[Point, ...]
    text_x: int
    text_y: int


@value
class OverviewPlacedHead:
    """The top-left corner `x`, `y` of the text of the lane of the group `node`."""

    node: Id[Any]
    x: int
    y: int


@value
class OverviewPlacedView:
    """One placed view, found by `(unit, level, mode, open)`; its boxes and lines follow the rows' order.

    `lane_heads` is a `OverviewPlacedHead` per lane that prints a text; empty for any other view.
    """

    unit: Id[Unit] | None
    level: OverviewRef | None
    mode: OverviewMode
    open: OverviewRef | None
    boxes: tuple[OverviewPlacedBox, ...]
    lines: tuple[OverviewPlacedLine, ...]
    lane_heads: tuple[OverviewPlacedHead, ...]


@value
class OverviewLayout:
    """The placed views of the system overview, in the order the engine read them.

    A view the placer could not place is absent, and the engine reports a finding for it.
    `by_view` gives them by `(unit, level, mode, open)`, the key of `fransys_model.derive.overview_view_rows`.
    """

    views: tuple[OverviewPlacedView, ...]

    def by_view(self) -> dict[tuple[Id[Unit] | None, OverviewRef | None, OverviewMode, OverviewRef | None], OverviewPlacedView]:
        """Each placed view by its `(unit, level, mode, open)`."""
        return {(v.unit, v.level, v.mode, v.open): v for v in self.views}


def _box(placed: DiagramBox, scene: Scene) -> OverviewPlacedBox:
    """The box at its place, its tabs as the lint scene measured them, in the order placed."""
    rects = next(b.tabs for b in scene.boxes if b.box == placed.box)
    tabs = tuple(
        OverviewPlacedTab(index=i, x=r.x, y=r.y, text_width=t.text_width, width=r.width, height=r.height)
        for i, (r, t) in enumerate(zip(rects, placed.tabs, strict=True))
    )
    return OverviewPlacedBox(x=placed.x, y=placed.y, width=placed.width, height=placed.height, tabs=tabs)


def _line(spec: LineSpec, at: Mapping[Ident, int], placed: DiagramLine) -> OverviewPlacedLine:
    """The line of `spec` as placed, its ends as positions in the view's boxes."""
    return OverviewPlacedLine(a=at[spec.a], b=at[spec.b], points=placed.points, text_x=placed.text_x, text_y=placed.text_y)


def placed_view(facts: ViewFacts, sheet: PlacedSheet, scene: Scene) -> OverviewPlacedView:
    """The placed view of `facts` on its one `sheet`."""
    at = {b.box: i for i, b in enumerate(facts.boxes)}
    placed = {p.box: p for p in sheet.boxes}
    lines = {(p.cable, p.a, p.b): p for p in sheet.lines}
    return OverviewPlacedView(
        unit=facts.unit,
        level=facts.level,
        mode=facts.mode,
        open=facts.open,
        boxes=tuple(_box(placed[b.box], scene) for b in facts.boxes),
        lines=tuple(_line(spec, at, lines[spec.carrier, spec.a, spec.b]) for spec in facts.lines),
        lane_heads=tuple(OverviewPlacedHead(node=t.owner, x=t.x, y=t.y) for t in sheet.texts),
    )
