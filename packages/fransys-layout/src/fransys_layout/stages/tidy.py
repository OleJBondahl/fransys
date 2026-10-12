"""Stage: what is left to tidy after the marker boxes are set: turned markers, tags, page shift."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable, Mapping, Sequence

from fransys_layout.geometry import WIRING_GRID, Box, Point, contains, is_clear, translate
from fransys_layout.geometry.units import TEXT_GAP
from fransys_layout.stages.space import Run, crosses

from .content import content_box
from .extent import column_extent, page_ink
from .slices import by_plan, page_of
from .types import LabelKind

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey

    from .types import Handle, LinkMarker, PagePlan, PlacedFunction, PlacedLabel, SheetFormat


def turned(marker: LinkMarker, side: int = 1) -> LinkMarker:
    """Amends layout-0053: `marker` moved off its port's wire."""
    box, at = marker.box, marker.at
    width, height = (box.width, box.height) if marker.vertical else (box.height, box.width)
    north = box.y + box.height <= at.y
    via = Point(x=at.x, y=at.y + (-WIRING_GRID if north else WIRING_GRID))
    reach = -(-(width // 2 + WIRING_GRID) // WIRING_GRID) * WIRING_GRID
    end = Point(x=via.x + side * reach, y=via.y)
    y = end.y - WIRING_GRID - height if north else end.y + WIRING_GRID
    moved = Box(x=end.x - width // 2, y=y, width=width, height=height)
    return replace(marker, turn=via, box=moved, stub_extra=0, vertical=True)


def stub(marker: LinkMarker) -> Run:
    """A marker's stub as a vertical `Run`: from its port to its box's near edge."""
    box, at = marker.box, marker.at
    near = box.y + box.height if box.y + box.height <= at.y else box.y
    return Run(x=at.x, y=min(at.y, near), to_x=at.x, to_y=max(at.y, near))


def clear_of_stubs(
    plans: tuple[PagePlan, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    markers: tuple[LinkMarker, ...],
    sheet: SheetFormat,
) -> list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]]:
    """A tag a marker's stub runs through moves to its symbol's mirror side."""
    content = content_box(sheet)
    found = []
    for (placed, labels), mine in zip(pages, by_plan(markers, page_of, plans), strict=True):
        stubs = [stub(m) for m in mine if m.turn is None]
        where = {one.function: one for one in placed}
        bodies = [translate(one.geometry.body, dx=one.at.x, dy=one.at.y) for one in placed]
        kept = list(labels)
        for index, label in enumerate(labels):
            owner = where.get(label.subject)
            if label.kind is not LabelKind.TAG or owner is None:
                continue
            if not any(crosses(label.box, stub) for stub in stubs):
                continue
            body = translate(owner.geometry.body, dx=owner.at.x, dy=owner.at.y)
            box = replace(label.box, x=2 * body.x + body.width - label.box.x - label.box.width)
            others = [one.box for i, one in enumerate(kept) if i != index]
            clear = (
                contains(content, box)
                and not any(crosses(box, stub) for stub in stubs)
                and is_clear(box, (*bodies, *others))
                and is_clear(box, (m.box for m in mine))
            )
            if clear:
                kept[index] = replace(label, box=box)
        found.append((placed, tuple(kept)))
    return found


def _need(
    boxes: Sequence[Box],
    first: Sequence[PlacedLabel],
    axis: str,
    extent: int,
    up: Callable[[int], int],
) -> int:
    """The shift on one axis keeping boxes in the box; on x, texts TEXT_GAP from its left edge."""
    size = "width" if axis == "x" else "height"
    cells = list(boxes)
    lows = [(getattr(b, axis), 0) for b in cells] + [
        (getattr(b.box, axis), TEXT_GAP) for b in first
    ]
    need = max((g - low for low, g in lows if low < g), default=0)
    shift = up(need) if need > 0 else 0
    ink = column_extent([*cells, *(b.box for b in first)])
    return shift if shift and getattr(ink, axis) + getattr(ink, size) + shift <= extent else 0


def shift_pages(
    plans: tuple[PagePlan, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    markers: tuple[LinkMarker, ...],
    sheet: SheetFormat,
    rooms: Mapping[tuple[AuthoringKey, Handle], tuple[int, int]] | None = None,
) -> tuple[
    list[Any],
    tuple[Any, ...],
    tuple[LinkMarker, ...],
]:
    """Each page's placements and labels moved inside the content box.

    An image's reserved room counts as ink (layout-0182), so a shift never pushes it out.
    """

    def up(value: int) -> int:
        return -(-value // WIRING_GRID) * WIRING_GRID

    moved_pages, moved_markers = [], list(markers)
    keys = [page_of(marker) for marker in markers]
    indices_at = by_plan(range(len(markers)), keys.__getitem__, plans)
    for (placed, first), mine in zip(pages, indices_at, strict=True):
        if not placed and not first:
            moved_pages.append((placed, first))
            continue
        dx = _need(ink := page_ink(placed, rooms or {}), first, "x", sheet.content_width, up)
        dy = _need(ink, first, "y", sheet.content_height, up)
        if not dx and not dy:
            moved_pages.append((placed, first))
            continue
        shifted = tuple(replace(one, at=Point(x=one.at.x + dx, y=one.at.y + dy)) for one in placed)
        shifted_first = tuple(
            replace(label, box=translate(label.box, dx=dx, dy=dy)) for label in first
        )
        for i in mine:
            m = moved_markers[i]
            moved_markers[i] = replace(
                m,
                at=Point(x=m.at.x + dx, y=m.at.y + dy),
                box=translate(m.box, dx=dx, dy=dy),
                turn=None if m.turn is None else Point(x=m.turn.x + dx, y=m.turn.y + dy),
            )
        moved_pages.append((shifted, shifted_first))
    placed_all = tuple(one for placed, _ in moved_pages for one in placed)
    return moved_pages, placed_all, tuple(moved_markers)
