"""overview-0010: a finding counts on the nearest drawn box, or on the line it names."""

from overview_builders import item_id, unit_plant

from fransys_model.derive import (
    FindingHold,
    ViewBox,
    ViewRows,
    finding_marks,
    overview_view_rows,
)
from fransys_model.kernel import Finding, Severity
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab import conductors


def _finding(severity, *subjects):
    return Finding(
        code="DEMO", severity=severity, subjects=subjects, message="demo", fix="Write: x"
    )


def _unit_view():
    """The plain view of unit `u`: boxes -K1, -K2, the nested unit -U2, strip -X1, stub -B1."""
    model, outer, nested = unit_plant()
    return model, nested, overview_view_rows(model, outer)[0]


def _boxes(rows, marks):
    """Each marked box by its first text line, with the findings it holds."""
    return {rows.boxes[m.at].lines[0]: [h.finding for h in m.held] for m in marks if not m.on_line}


def test_an_item_inside_a_nested_unit_counts_on_the_nearest_drawn_unit_box():
    """Breaks if the finding rolls up to the enclosing unit, or is dropped where only -U2 shows."""
    model, _nested, rows = _unit_view()
    marks = finding_marks(model, rows, (_finding(Severity.ERROR, item_id("z1")),))
    assert _boxes(rows, marks) == {"-U2": [0]}
    assert marks[0].held == (FindingHold(finding=0, severity=Severity.ERROR),)


def test_a_drawn_item_counts_on_its_own_box():
    """Breaks if a drawn item rolls up to a box above its own."""
    model, _nested, rows = _unit_view()
    marks = finding_marks(model, rows, (_finding(Severity.WARNING, item_id("k1")),))
    assert _boxes(rows, marks) == {"-K1": [0]}


def test_a_finding_with_two_subjects_on_one_box_holds_once():
    """Breaks if a finding counts once per subject on the same box."""
    model, nested, rows = _unit_view()
    marks = finding_marks(model, rows, (_finding(Severity.WARNING, item_id("z1"), nested),))
    assert _boxes(rows, marks) == {"-U2": [0]}


def test_a_conductor_counts_on_the_line_joining_its_ends_and_not_on_a_box():
    """Breaks if a conductor's finding lands on a box, or on a line that does not join its ends."""
    model, _nested, rows = _unit_view()
    wire = next(c for c in conductors(model).values() if c.key == ("w6",)).id
    marks = finding_marks(model, rows, (_finding(Severity.ERROR, wire),))
    assert [m.on_line for m in marks] == [True]
    line = rows.lines[marks[0].at]
    ends = {rows.boxes[i].lines[0] for i, b in enumerate(rows.boxes) if b.key in {line.a, line.b}}
    assert ends == {"-K1", "-K2"}


def test_no_finding_means_no_marks():
    model, _nested, rows = _unit_view()
    assert finding_marks(model, rows, ()) == ()


def test_a_subject_drawn_and_inside_a_drawn_unit_counts_on_its_own_box_only():
    """Breaks if the roll-up picks the outermost drawn box, not the nearest one."""
    model, nested, _rows = _unit_view()
    own = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("z1"))
    unit = OverviewRef(kind=OverviewRefKind.UNIT, unit=nested)
    boxes = tuple(
        ViewBox(key=BoxKey(ref=r), lines=(n,), dashed=False) for r, n in ((unit, "U"), (own, "Z"))
    )
    rows = ViewRows(
        unit=None, level=None, mode=OverviewMode.PLAIN, open=None, boxes=boxes, lines=()
    )
    marks = finding_marks(model, rows, (_finding(Severity.INFO, item_id("z1")),))
    assert _boxes(rows, marks) == {"Z": [0]}
