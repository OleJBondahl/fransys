"""The last pass: a finding about a drawn thing ends in its page and its printed designation."""

from samples import hid, placed

from fransys_layout.lint._harness import NO_INK
from fransys_layout.lint.naming import (
    Where,
    _groups_on,
    _pages_of,
    name_findings,
)
from fransys_layout.stages import Layout
from fransys_model.kernel import Finding, Severity

PORT = hid("port", 7)
FUNCTION = hid("function", 1)
LAYOUT = Layout(
    pages=(),
    placed=(placed(1, x=0, y=0, page=3),),
    routes=(),
    decisions=(),
    markers=(),
    labels=(),
)


def _finding(*subjects, code="X") -> Finding:
    return Finding(code=code, severity=Severity.WARNING, subjects=subjects, message="text")


def _named(finding, labels=None, names=None):
    where = Where(
        pages=_pages_of(LAYOUT, (), NO_INK), groups=_groups_on(LAYOUT), labels=labels or {}
    )
    return name_findings(names or {PORT: "-K1:13"}, where, [finding])[0].message


def test_a_finding_on_a_placed_function_names_its_page_and_designation() -> None:
    names = {FUNCTION: "K1:coil"}
    assert _named(_finding(FUNCTION), names=names) == "text (p1.3: K1:coil)"


def test_the_set_prints_its_location_labels_not_its_number() -> None:
    assert _named(_finding(FUNCTION), labels={1: ("C1",)}, names={}) == "text (+C1p3)"


def test_a_subject_that_is_drawn_nowhere_names_only_its_designation() -> None:
    assert _named(_finding(PORT)) == "text (-K1:13)"


def test_a_finding_with_neither_keeps_its_text() -> None:
    assert _named(_finding(hid("net", 2)), names={}) == "text"
