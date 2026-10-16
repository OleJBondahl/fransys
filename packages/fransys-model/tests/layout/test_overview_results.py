"""The overview kinds: a view, its boxes and its lines freeze, order their rows and stay apart."""

from typing import Any

import pytest

from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, freeze, make_id
from fransys_model.layout import (
    DIAGRAM_KINDS,
    OVERVIEW_KINDS,
    DiagramSheet,
    OverviewBox,
    OverviewLine,
    OverviewMode,
    OverviewRef,
    OverviewRefKind,
    OverviewTab,
    OverviewView,
    RoutePoint,
    derived_layout_ids,
    layout_of,
)
from fransys_model.vocab.core import Item

_ORIGIN = Origin(file="test_overview_results.py", line=1, note="fixture")
_STAMP = "overview-engine"
_GROUP = OverviewRef(kind=OverviewRefKind.GROUP, node=Id(kind="aspect_node", value="g"))
_STRIPS = OverviewRef(kind=OverviewRefKind.STRIPS)


def _item(tag: str) -> Item:
    key = ("cable", tag)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=None,
        position=None,
        tag=tag,
        description="",
    )


def _view() -> OverviewView:
    key = ("overview", "system")
    return OverviewView(
        id=make_id(OverviewView, key),
        key=key,
        unit=None,
        level=None,
        mode=OverviewMode.PLAIN,
        open=None,
        open_at=None,
        produced_by=_STAMP,
    )


def _box(view: OverviewView, item: Item, tabs: tuple[OverviewTab, ...] = ()) -> OverviewBox:
    key = (*view.key, "box", str(item.tag))
    return OverviewBox(
        id=make_id(OverviewBox, key),
        key=key,
        view=view.id,
        ref=OverviewRef(kind=OverviewRefKind.ITEM, item=item.id),
        stub_of=None,
        dashed=False,
        x=0,
        y=0,
        width=10,
        height=4,
        tabs=tabs,
        produced_by=_STAMP,
    )


def _line(
    view: OverviewView, a: OverviewBox, b: OverviewBox, points: tuple[RoutePoint, ...]
) -> OverviewLine:
    key = (*view.key, "line", a.key[-1], b.key[-1])
    return OverviewLine(
        id=make_id(OverviewLine, key),
        key=key,
        view=view.id,
        a=a.id,
        b=b.id,
        kind="wire",
        via=None,
        strip=None,
        points=points,
        text_x=5,
        text_y=2,
        produced_by=_STAMP,
    )


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _sheet() -> DiagramSheet:
    key = ("sheet", "1")
    return DiagramSheet(
        id=make_id(DiagramSheet, key), key=key, unit=None, number=1, produced_by=_STAMP
    )


def test_a_view_a_box_and_a_line_freeze_and_read_back_unchanged() -> None:
    """Removing a kind's `@record` registration or a field makes the read-back miss the record."""
    w1, w2 = _item("W1"), _item("W2")
    view = _view()
    one, two = _box(view, w1), _box(view, w2)
    points = (RoutePoint(index=0, x=1, y=2), RoutePoint(index=1, x=3, y=2))
    line = _line(view, one, two, points)
    model = _freeze(w1, w2, view, one, two, line)
    assert layout_of(model, OverviewView)[view.id] == view
    assert layout_of(model, OverviewBox)[one.id] == one
    assert layout_of(model, OverviewLine)[line.id] == line


def test_a_reference_holds_only_the_id_its_kind_names() -> None:
    """Dropping the per-kind check in `OverviewRef.__post_init__` lets a unit ref hold an item."""
    item = _item("W1").id
    for kind in (OverviewRefKind.UNIT, OverviewRefKind.ITEM, OverviewRefKind.GROUP):
        with pytest.raises(SchemaError, match="holds only"):
            OverviewRef(kind=kind)
    with pytest.raises(SchemaError, match="holds only"):
        OverviewRef(kind=OverviewRefKind.UNIT, item=item)
    with pytest.raises(SchemaError, match="holds only"):
        OverviewRef(kind=OverviewRefKind.STRIPS, item=item)
    OverviewRef(kind=OverviewRefKind.STRIPS)
    OverviewRef(kind=OverviewRefKind.PLACE)


def _view_of(unit: Any, level: Any, mode: OverviewMode, open_: OverviewRef | None = None) -> Any:
    return OverviewView(
        id=make_id(OverviewView, ("v",)),
        key=("v",),
        unit=unit,
        level=level,
        mode=mode,
        open=open_,
        open_at=None,
        produced_by=_STAMP,
    )


@pytest.mark.parametrize(
    ("unit", "level", "mode"),
    [
        (False, False, OverviewMode.GROUPS),
        (False, False, OverviewMode.SEE_THROUGH),
        (False, False, OverviewMode.LANES),
        (True, False, OverviewMode.LOCATION),
        (True, False, OverviewMode.FIELDS),
        (True, True, OverviewMode.GROUPS),
        (True, True, OverviewMode.PLAIN),
        (False, True, OverviewMode.SEE_THROUGH),
    ],
)
def test_a_view_refuses_a_mode_its_level_cannot_have(*, unit: bool, level: bool, mode: Any) -> None:
    """Dropping `check_view` from `OverviewView.__post_init__` lets every pair through."""
    ids = {"unit": Id(kind="unit", value="u"), "level": _GROUP}
    with pytest.raises(SchemaError, match=r"needs its unit|has no mode"):
        _view_of(ids["unit"] if unit else None, ids["level"] if level else None, mode)


def test_a_view_accepts_the_modes_of_each_level_and_refuses_a_strips_box_open() -> None:
    """The allowed table, and the open kinds: a strips box cannot be the one open thing."""
    unit = Id(kind="unit", value="u")
    _view_of(None, None, OverviewMode.LOCATION)
    _view_of(unit, None, OverviewMode.LANES)
    _view_of(unit, _GROUP, OverviewMode.SEE_THROUGH)
    _view_of(unit, _STRIPS, OverviewMode.SEE_THROUGH)
    with pytest.raises(SchemaError, match="cannot hold a strips open"):
        _view_of(unit, None, OverviewMode.GROUPS, OverviewRef(kind=OverviewRefKind.STRIPS))


def test_a_view_opens_only_a_group_or_the_strips_box_as_its_level() -> None:
    """Dropping the `_LEVEL` check in `check_view` lets a unit or an item stand as the level."""
    unit = Id(kind="unit", value="u")
    for kind in (OverviewRefKind.UNIT, OverviewRefKind.PLACE, OverviewRefKind.FIELDS):
        with pytest.raises(SchemaError, match=r"cannot open a \w+ as its level"):
            _view_of(
                unit,
                OverviewRef(kind=kind, unit=unit if kind != OverviewRefKind.PLACE else None),
                OverviewMode.SEE_THROUGH,
            )
    with pytest.raises(SchemaError, match="needs its unit"):
        _view_of(None, _STRIPS, OverviewMode.SEE_THROUGH)


def test_box_tabs_are_stored_in_index_order() -> None:
    """Removing the `by_index` call in `OverviewBox.__post_init__` leaves tabs as written."""
    tabs = (
        OverviewTab(index=1, x=0, y=3, text_width=4, width=5, height=3),
        OverviewTab(index=0, x=0, y=1, text_width=4, width=5, height=3),
    )
    box = _box(_view(), _item("W1"), tabs=tabs)
    assert [tab.index for tab in box.tabs] == [0, 1]


def test_a_repeated_tab_index_is_refused() -> None:
    """Two tabs with one `index` have no defined order, so the box is refused, naming it."""
    view = _view()
    tabs = (
        OverviewTab(index=0, x=0, y=1, text_width=4, width=5, height=3),
        OverviewTab(index=0, x=0, y=3, text_width=4, width=5, height=3),
    )
    with pytest.raises(SchemaError, match="share the index 0") as excinfo:
        _box(view, _item("W1"), tabs=tabs)
    assert excinfo.value.record_id == make_id(OverviewBox, (*view.key, "box", "W1"))


def test_line_points_are_stored_in_index_order() -> None:
    """Removing the `by_index` call in `OverviewLine.__post_init__` leaves points as written."""
    view = _view()
    one, two = _box(view, _item("W1")), _box(view, _item("W2"))
    points = (RoutePoint(index=1, x=3, y=2), RoutePoint(index=0, x=1, y=2))
    assert [point.index for point in _line(view, one, two, points).points] == [0, 1]


def test_a_repeated_line_point_index_is_refused() -> None:
    """Two points with one `index` have no defined path, so the line is refused."""
    view = _view()
    one, two = _box(view, _item("W1")), _box(view, _item("W2"))
    points = (RoutePoint(index=0, x=1, y=2), RoutePoint(index=0, x=3, y=2))
    with pytest.raises(SchemaError, match="share the index 0"):
        _line(view, one, two, points)


def test_derived_ids_of_the_overview_kinds_are_its_three_kinds_only() -> None:
    """Dropping OVERVIEW_KINDS from the tuple, or passing the wrong `kinds`, changes this list."""
    w1, w2 = _item("W1"), _item("W2")
    view = _view()
    one, two = _box(view, w1), _box(view, w2)
    line = _line(view, one, two, (RoutePoint(index=0, x=1, y=2),))
    sheet = _sheet()
    model = _freeze(w1, w2, view, one, two, line, sheet)
    expected = {view.id, one.id, two.id, line.id}
    assert derived_layout_ids(model, kinds=OVERVIEW_KINDS) == tuple(sorted(expected))
    assert sheet.id not in derived_layout_ids(model, kinds=OVERVIEW_KINDS)


def test_derived_ids_of_the_diagram_kinds_leave_the_overview_records_alone() -> None:
    """Listing DIAGRAM_KINDS names the sheet only; no overview record shows in it."""
    w1, w2 = _item("W1"), _item("W2")
    view = _view()
    one, two = _box(view, w1), _box(view, w2)
    line = _line(view, one, two, (RoutePoint(index=0, x=1, y=2),))
    sheet = _sheet()
    model = _freeze(w1, w2, view, one, two, line, sheet)
    assert derived_layout_ids(model, kinds=DIAGRAM_KINDS) == (sheet.id,)


@pytest.mark.parametrize(
    "make",
    [
        lambda: OverviewView(  # ty: ignore[missing-argument] -- produced_by omitted on purpose
            id=Id(kind="layout.overview_view", value="1" * 32),
            key=("v",),
            unit=None,
            level=None,
            mode=OverviewMode.PLAIN,
            open=None,
            open_at=None,
        ),
        lambda: OverviewBox(  # ty: ignore[missing-argument] -- produced_by omitted on purpose
            id=Id(kind="layout.overview_box", value="2" * 32),
            key=("b",),
            view=Id(kind="layout.overview_view", value="1" * 32),
            ref=OverviewRef(kind=OverviewRefKind.STRIPS),
            stub_of=None,
            dashed=False,
            x=0,
            y=0,
            width=1,
            height=1,
            tabs=(),
        ),
        lambda: OverviewLine(  # ty: ignore[missing-argument] -- produced_by omitted on purpose
            id=Id(kind="layout.overview_line", value="3" * 32),
            key=("l",),
            view=Id(kind="layout.overview_view", value="1" * 32),
            a=Id(kind="layout.overview_box", value="2" * 32),
            b=Id(kind="layout.overview_box", value="2" * 32),
            kind="wire",
            via=None,
            strip=None,
            points=(),
            text_x=0,
            text_y=0,
        ),
    ],
    ids=["view", "box", "line"],
)
def test_an_overview_record_without_produced_by_is_refused(make: Any) -> None:
    """Giving `produced_by` a default lets a result with no pass name through; this then passes."""
    with pytest.raises(TypeError, match="produced_by"):
        make()
