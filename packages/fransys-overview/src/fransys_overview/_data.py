"""The page's data: every view at its recorded positions with the text its rows print (O22).

No Id and no record key reaches the output: things are named by their place in a table, and the
tables follow printed order, so renaming every Id leaves the bytes alone (decision 0136).
"""

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from fransys_model.derive import (
    effective_placement,
    item_kind,
    item_pages,
    overview_graph,
    overview_tree,
    overview_units,
    overview_view_rows,
    text_room_g,
)
from fransys_model.kernel import make_id
from fransys_model.layout import (
    BoxKey,
    OverviewBox,
    OverviewLine,
    OverviewRef,
    OverviewRefKind,
    OverviewView,
    box_key,
    layout_of,
    line_key,
    profile_of,
    sheet_format_of,
    view_key,
)
from fransys_model.vocab import Aspect, aspect_nodes, items, units

from ._data_alt import lens_data, matrix_data
from ._data_changes import changes_data
from ._data_findings import findings_data
from ._data_heads import heads_data
from ._data_places import holds_of
from ._palette import palette_data
from ._tabs import tab_texts

if TYPE_CHECKING:
    from fransys_model.derive import OverviewNode, ViewBox, ViewLine, ViewRows
    from fransys_model.derive.baseline import ListingDiff
    from fransys_model.kernel import Finding, Id, Model

Json = dict[str, Any]
Texts = dict[tuple[int, int], str]


class _Tables:
    """The tables a view names things by: items, units and aspect nodes, each by its index."""

    def __init__(self, model: Model) -> None:
        self.model = model
        profile = profile_of(model)
        sheet = sheet_format_of(model, profile.sheet_format)
        self.text_height = text_room_g(profile.text_height_mm, sheet.module_mm)
        graph = overview_graph(model)
        self.nodes = graph.nodes
        self.pages = item_pages(model)
        self.item_ix = {n.item: i for i, n in enumerate(graph.nodes)}
        self.unit_ix = {u: i for i, u in enumerate(u for u in overview_units(model) if u)}
        self.aspect_ix: dict[Id[Any], int] = {}
        self.unit_label: dict[Id[Any], str] = {}
        self.aspect_label: dict[Id[Any], str] = {}

    def learn(self, rows: ViewRows) -> None:
        """Take the texts of the unit, group and place boxes of `rows` as those things' labels."""
        for box in rows.boxes:
            ref = box.key.ref
            if ref.kind is OverviewRefKind.UNIT and ref.unit is not None:
                self.unit_label.setdefault(ref.unit, box.lines[0])
            elif ref.node is not None:
                self.aspect_label.setdefault(ref.node, box.lines[0])

    def aspect(self, node: Id[Any]) -> int:
        """The index of an aspect node, in order of first use."""
        return self.aspect_ix.setdefault(node, len(self.aspect_ix))

    def ref(self, ref: OverviewRef | None) -> list[Any] | None:
        """A reference as `[kind, index]`, with the index into its table, or `None`."""
        if ref is None:
            return None
        if ref.item is not None:
            return [ref.kind.value, self.item_ix[ref.item]]
        if ref.unit is not None:
            return [ref.kind.value, self.unit_ix[ref.unit]]
        if ref.node is not None:
            return [ref.kind.value, self.aspect(ref.node)]
        return [ref.kind.value, None]


def _group_of(model: Model, item: Id[Any]) -> str | None:
    """The label of the function group `item` is placed in, else `None`."""
    node = effective_placement(model, item, Aspect.FUNCTION)
    return None if node is None else aspect_nodes(model)[node].label


def _unit_parent(tables: _Tables, unit: Id[Any]) -> int | None:
    """The table index of the unit `unit` sits in, else `None`."""
    parent = units(tables.model)[unit].parent
    return None if parent is None else tables.unit_ix[parent]


def _classes(tables: _Tables, ref: OverviewRef, unit: Id[Any] | None) -> list[str | None]:
    """The class of a box in each colour split: unit, function group, item kind, location."""
    model = tables.model
    if ref.item is not None:
        record = items(model)[ref.item]
        node = tables.nodes[tables.item_ix[ref.item]]
        group = _group_of(model, ref.item)
        owner = tables.unit_label.get(record.unit) if record.unit is not None else None
        return [owner, group, item_kind(model, ref.item).value, node.location_label]
    own = tables.unit_label.get(ref.unit) if ref.unit is not None else None
    if ref.kind is OverviewRefKind.GROUP:
        return [tables.unit_label.get(unit), tables.aspect_label.get(ref.node), "group", None]
    if ref.kind is OverviewRefKind.PLACE:
        return [None, None, "place", tables.aspect_label.get(ref.node)]
    kind = {"unit": "unit", "fields": "field devices", "strips": "strip"}[ref.kind.value]
    return [own if own is not None else tables.unit_label.get(unit), None, kind, None]


def _box(
    tables: _Tables, view: ViewRows, at: tuple[int, ViewBox, OverviewBox], texts: Texts
) -> Json:
    index, box, record = at
    held = holds_of(tables, box)
    return {
        **({} if held is None else {"holds": held}),
        "at": tables.ref(box.key.at),
        "cls": _classes(tables, box.key.ref, view.unit),
        "dashed": box.dashed,
        "h": record.height,
        "lines": list(box.lines),
        "members": [
            {"lines": list(m.lines), "ref": tables.ref(m.ref), "text": m.text} for m in box.members
        ],
        "ref": tables.ref(box.key.ref),
        "tabs": [[t.x, t.y, t.text_width, texts.get((index, t.index))] for t in record.tabs],
        "w": record.width,
        "x": record.x,
        "y": record.y,
    }


def _line(index: dict[BoxKey, int], line: ViewLine, record: OverviewLine) -> Json:
    return {
        "a": index[line.a],
        "b": index[line.b],
        "kind": line.kind,
        "pts": [[p.x, p.y] for p in record.points],
        "text": line.text,
        "tx": record.text_x,
        "ty": record.text_y,
    }


def _view(tables: _Tables, rows: ViewRows, records: tuple[Any, Any, Any]) -> Json | None:
    """One view, or `None` when the engine placed none of it."""
    views, boxes, lines = records
    key = view_key(rows.unit, rows.level, rows.mode, rows.open)
    if make_id(OverviewView, key) not in views:
        return None
    index = {b.key: i for i, b in enumerate(rows.boxes)}
    brecs = [boxes[make_id(OverviewBox, box_key(key, b.key))] for b in rows.boxes]
    lrecs = [
        lines[make_id(OverviewLine, line_key(key, ln.kind, (ln.a, ln.b), (ln.via, ln.strip)))]
        for ln in rows.lines
    ]
    texts = tab_texts(rows, brecs, lrecs, tables.text_height)
    return {
        "boxes": [_box(tables, rows, (i, b, brecs[i]), texts) for i, b in enumerate(rows.boxes)],
        "level": tables.ref(rows.level),
        "heads": heads_data(tables.model, views[make_id(OverviewView, key)]),
        "lines": [_line(index, ln, rec) for ln, rec in zip(rows.lines, lrecs, strict=True)],
        "mode": rows.mode.value,
        "open": tables.ref(rows.open),
        "unit": None if rows.unit is None else tables.unit_ix[rows.unit],
    }


def _item(tables: _Tables, node: OverviewNode) -> Json:
    model = tables.model
    record = items(model)[node.item]
    return {
        "group": _group_of(model, node.item),
        "installed": node.installed,
        "kind": item_kind(model, node.item).value,
        "label": node.designation if node.designation is not None else node.description,
        "location": node.location_label,
        "mpn": node.mpn,
        "pages": [
            [f"{quote(p.file)}#nameddest={quote(p.destination)}", p.text]
            for p in tables.pages.get(node.item, ())
        ],
        "parent": None if node.parent is None else tables.item_ix[node.parent],
        "unit": None if record.unit is None else tables.unit_ix[record.unit],
    }


def _tree(tables: _Tables) -> list[Json]:
    """The parts tree rows, each by the table index of its unit or item."""
    return [
        {
            "item": None if row.item is None else tables.item_ix[row.item],
            "label": row.label,
            "parent": row.parent,
            "unit": None if row.unit is None else tables.unit_ix.get(row.unit),
            "is_unit": row.unit is not None,
        }
        for row in overview_tree(tables.model)
    ]


def page_data(
    model: Model, findings: tuple[Finding, ...] = (), changes: ListingDiff | None = None
) -> Json:
    """Every view that has records, the tables they name, and the signals for tracing."""
    tables = _Tables(model)
    records = (
        layout_of(model, OverviewView),
        layout_of(model, OverviewBox),
        layout_of(model, OverviewLine),
    )
    found = [rows for unit in overview_units(model) for rows in overview_view_rows(model, unit)]
    for rows in found:
        tables.learn(rows)
    built = [(rows, _view(tables, rows, records)) for rows in found]
    views = [v for _, v in built if v is not None]
    drawn = [rows for rows, v in built if v is not None]
    graph = overview_graph(model)
    # A unit with no box in any view (a plant with no system view) prints its parts-tree row text.
    tree_text = {row.unit: row.label for row in overview_tree(model) if row.unit is not None}
    return {
        "changes": changes_data(tables, drawn, changes),
        "findings": findings_data(tables, drawn, findings),
        "items": [_item(tables, n) for n in tables.nodes],
        "lens": lens_data(tables),
        "matrix": matrix_data(tables),
        "signals": [[[tables.item_ix[p.item], p.marking] for p in s.ports] for s in graph.signals],
        "text_height": tables.text_height,
        "tree": _tree(tables),
        "unit_parents": [_unit_parent(tables, u) for u in tables.unit_ix],
        "units": [tables.unit_label.get(u) or tree_text[u] for u in tables.unit_ix],
        "palette": palette_data(),
        "views": views,
    }


__all__ = ["page_data"]
