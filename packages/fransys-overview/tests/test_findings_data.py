"""O18: a box's badge counts the distinct findings of its worst severity; it lists all of them."""

from fransys_overview._app import APP_JS
from fransys_overview._data import _Tables
from fransys_overview._data_findings import findings_data

from fransys_model.derive import ViewBox, ViewRows
from fransys_model.kernel import Finding, Severity, make_id
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab.core import Item


def _item(key):
    return make_id(Item, (key,))


def _data(model, findings):
    cab = _item("a1")
    box = ViewBox(
        key=BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=cab)),
        lines=("A1",),
        dashed=False,
    )
    rows = ViewRows(
        unit=None, level=None, mode=OverviewMode.PLAIN, open=None, boxes=(box,), lines=()
    )
    return findings_data(_Tables(model), [rows], findings)


def _mixed():
    """Two warnings (one names three children of A1) and two infos, all rolling up to A1."""
    k1, k2, g1, k3, f1 = (_item(k) for k in ("k1", "k2", "g1", "k3", "f1"))
    return (
        Finding(code="INFO_ONE", severity=Severity.INFO, subjects=(k3,), message="info one"),
        Finding(
            code="WARN_MANY", severity=Severity.WARNING, subjects=(k1, k2, g1), message="warn many"
        ),
        Finding(code="INFO_TWO", severity=Severity.INFO, subjects=(f1,), message="info two"),
        Finding(code="WARN_ONE", severity=Severity.WARNING, subjects=(k1,), message="warn one"),
    )


def test_the_number_counts_distinct_findings_of_the_worst_severity(demo_cabinet):
    boxes = _data(demo_cabinet, _mixed())[0][0]
    assert [b[:3] for b in boxes] == [[0, "warning", 2]]


def test_the_panel_list_holds_each_code_once_with_its_count_worst_first(demo_cabinet):
    """Breaks if a code repeats per finding, loses its count, or lists a milder code first."""
    held = _data(demo_cabinet, _mixed())[0][0][0][3]
    assert held == [
        ["warning", "WARN_MANY", 1],
        ["warning", "WARN_ONE", 1],
        ["info", "INFO_ONE", 1],
        ["info", "INFO_TWO", 1],
    ]


def test_two_findings_of_one_code_list_once_with_a_count_of_two(demo_cabinet):
    twin = tuple(f for f in _mixed() if f.code in {"INFO_ONE", "INFO_TWO"})
    twin = tuple(
        Finding(code="SAME", severity=f.severity, subjects=f.subjects, message=f.message)
        for f in twin
    )
    assert _data(demo_cabinet, twin)[0][0][0][3] == [["info", "SAME", 2]]


def test_a_box_with_only_info_reads_info(demo_cabinet):
    only = tuple(f for f in _mixed() if f.severity is Severity.INFO)
    assert _data(demo_cabinet, only)[0][0][0][:3] == [0, "info", 2]


def test_the_page_script_lists_the_findings_in_the_panel():
    assert "drawFindings(view, 0, at)" in APP_JS


def test_the_page_data_holds_no_message_text(demo_cabinet):
    """Breaks if a message (which prints names, A10) reaches the findings data."""
    one = Finding(
        code="X_Y", severity=Severity.INFO, subjects=(_item("k1"),), message="secret-name"
    )
    assert "secret-name" not in repr(_data(demo_cabinet, (one,)))
