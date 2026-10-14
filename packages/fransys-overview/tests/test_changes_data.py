"""O19: a change off the drawn level marks its nearest drawn box; removed rows are listed."""

import dataclasses

from fransys_overview._app import APP_JS
from fransys_overview._data import _Tables
from fransys_overview._data_changes import changes_data
from fransys_overview._js_changes import JS_CHANGES

from fransys_model.derive import ViewBox, ViewLine, ViewRows
from fransys_model.derive.baseline import change_subjects, diff
from fransys_model.derive.baseline_listing import listing
from fransys_model.kernel import make_id
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab.core import Item
from fransys_model.vocab.project import Project


def _models(plant):
    """The demo plant with ZZ9, and the same with ZZ9 gone and K1 and R1 not installed."""
    project = Project(
        id=make_id(Project, ("p",)),
        key=("p",),
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="A",
    )
    plant.records = [
        dataclasses.replace(r, tag=r.tag or "S1") if isinstance(r, Item) else r
        for r in [*plant.records, project]
    ]
    kept = list(plant.records)
    plant.item("zz9", "ZZ9", mpn="SIM-RELAY-24V")
    old = plant.freeze()
    off = {("k1",), ("jb1-r1",)}
    plant.records = [
        dataclasses.replace(r, installed=False) if isinstance(r, Item) and r.key in off else r
        for r in kept
    ]
    return old, plant.freeze()


def _changes(plant, *, drawn=True):
    old, new = _models(plant)
    tables = _Tables(new)
    cab = make_id(Item, ("a1",))
    box = ViewBox(
        key=BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=cab)),
        lines=("A1",),
        dashed=False,
    )
    rows = ViewRows(
        unit=None, level=None, mode=OverviewMode.PLAIN, open=None, boxes=(box,), lines=()
    )
    return changes_data(
        tables, [rows] if drawn else [], diff(listing(old, None), listing(new, None))
    )


def test_a_change_inside_a_folded_box_marks_the_box(demo_plant):
    assert _changes(demo_plant)["views"] == [[[[0, "changed"]], []]]


def test_the_list_holds_the_removed_designation_and_the_change_no_box_carries(demo_plant):
    """-K1 sits in the drawn box A1 and is marked; -R1 sits in none and is listed."""
    assert _changes(demo_plant)["rest"] == [["removed", "-ZZ9"], ["changed", "-R1"]]


def test_a_change_with_no_box_on_any_view_is_listed_under_its_kind_never_dropped(demo_plant):
    """Breaks if a changed or added subject nothing draws is dropped instead of listed."""
    rest = _changes(demo_plant, drawn=False)["rest"]
    assert rest[0] == ["removed", "-ZZ9"]
    assert {kind for kind, _ in rest} >= {"changed"}
    assert len(rest) > 1


def test_a_marked_box_gets_no_text_prefix():
    assert "CHANGE_MARK" not in APP_JS
    assert "d.label = " not in JS_CHANGES


def test_the_legend_names_the_marks_while_the_switch_is_on():
    assert "legendChanges();" in APP_JS
    assert "green border added, orange border changed" in JS_CHANGES


def test_a_removed_row_reads_as_its_designation_alone():
    assert "el('li', r[1])" in JS_CHANGES


def test_an_added_cable_marks_its_line_and_is_not_listed(demo_plant):
    """A cable item has no box; it is drawn as lines (`via`). Breaks if its change is listed."""
    _old, new = _models(demo_plant)
    now = listing(new, None)
    cable = make_id(Item, ("w1",))
    subjects = change_subjects(new, None)
    text = next(t for (section, t), one in subjects.items() if section == "items" and one == cable)
    prev = dataclasses.replace(now, items=tuple(r for r in now.items if r.designation != text))
    keys = [
        BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=make_id(Item, (k,))))
        for k in ("a1", "y10")
    ]
    boxes = tuple(ViewBox(key=k, lines=("B",), dashed=False) for k in keys)
    line = ViewLine(a=keys[0], b=keys[1], kind="cable", via=cable, strip=None, text="W1")
    rows = ViewRows(
        unit=None, level=None, mode=OverviewMode.PLAIN, open=None, boxes=boxes, lines=(line,)
    )
    data = changes_data(_Tables(new), [rows], diff(prev, now))
    assert data is not None
    assert data["views"] == [[[], [[0, "added"]]]]
    assert [text] not in [[t] for _, t in data["rest"]]
