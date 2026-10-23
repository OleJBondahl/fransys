"""The placed overview views: every view of `overview_view_rows` the engine placed (model-0306).

It is the one join of the rows to the `layout.overview_*` records, through their keys.
"""

from typing import Any
lazy from collections.abc import Iterable

from fransys_model.kernel import make_id
from fransys_model.layout import (
    BoxKey,
    OverviewBox,
    OverviewLine,
    OverviewRef,
    OverviewView,
    box_key,
    layout_of,
    line_key,
    view_key,
)
lazy from fransys_model.kernel import Model

from .overview_view_rows import overview_units, overview_view_rows
from .rows_overview_placed import (
    PlacedBox,
    PlacedHead,
    PlacedLine,
    PlacedPoint,
    PlacedTab,
    PlacedView,
    RefRow,
)
lazy from .rows_overview_view import ViewBox, ViewLine, ViewRows

__all__ = ["overview_placed_views"]


def _row(ref: OverviewRef) -> RefRow:
    return RefRow(kind=ref.kind, unit=ref.unit, item=ref.item, node=ref.node)


def _ref(ref: OverviewRef | None) -> RefRow | None:
    return None if ref is None else _row(ref)


def _box(row: ViewBox, record: OverviewBox) -> PlacedBox:
    tabs = tuple(
        PlacedTab(
            index=t.index, x=t.x, y=t.y, text_width=t.text_width, width=t.width, height=t.height
        )
        for t in record.tabs
    )
    return PlacedBox(
        ref=_row(row.key.ref),
        at=_ref(row.key.at),
        members=tuple(_row(m.ref) for m in row.members),
        x=record.x,
        y=record.y,
        width=record.width,
        height=record.height,
        tabs=tabs,
    )


def _line(index: dict[BoxKey, int], row: ViewLine, record: OverviewLine) -> PlacedLine:
    return PlacedLine(
        a=index[row.a],
        b=index[row.b],
        points=tuple(PlacedPoint(x=p.x, y=p.y) for p in record.points),
        text_x=record.text_x,
        text_y=record.text_y,
    )


def _placed(rows: ViewRows, tables: tuple[Any, Any, Any]) -> PlacedView | None:
    views, boxes, lines = tables
    key = view_key(rows.unit, rows.level, rows.mode, rows.open)
    view = views.get(make_id(OverviewView, key))
    if view is None:
        return None
    index = {b.key: i for i, b in enumerate(rows.boxes)}
    placed_boxes = tuple(
        _box(b, boxes[make_id(OverviewBox, box_key(key, b.key))]) for b in rows.boxes
    )
    placed_lines = tuple(
        _line(
            index,
            ln,
            lines[make_id(OverviewLine, line_key(key, ln.kind, (ln.a, ln.b), (ln.via, ln.strip)))],
        )
        for ln in rows.lines
    )
    heads = tuple(PlacedHead(node=node, x=x, y=y) for node, x, y in view.ext.get("lane_heads", ()))
    return PlacedView(
        rows=rows,
        level=_ref(rows.level),
        open=_ref(rows.open),
        boxes=placed_boxes,
        lines=placed_lines,
        lane_heads=heads,
    )


def overview_placed_views(
    model: Model, found: Iterable[ViewRows] | None = None
) -> tuple[PlacedView, ...]:
    """The views the engine placed, in the order of `overview_view_rows`; one it did not is absent.

    `found` are the rows to join, when the caller already holds them; else every unit's views.
    """
    rows = (
        [r for unit in overview_units(model) for r in overview_view_rows(model, unit)]
        if found is None
        else list(found)
    )
    tables = (
        layout_of(model, OverviewView),
        layout_of(model, OverviewBox),
        layout_of(model, OverviewLine),
    )
    placed = (_placed(r, tables) for r in rows)
    return tuple(p for p in placed if p is not None)
