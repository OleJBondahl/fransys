"""The diagram engine's reader: facts of each reading and the findings of the diagram (BD3, BD6)."""

import pytest
from diagram_models import chain, fanout, loose, one_box, station

from fransys_layout.engines.diagram.read import read_diagrams, read_findings
from fransys_layout.geometry import text_width
from fransys_model.derive.block_diagram import (
    DIAGRAM_CABLE_FANOUT,
    DIAGRAM_CABLE_ONE_BOX,
    DIAGRAM_LOOSE_WIRE,
    box_dashed,
    box_lines,
    box_order,
    diagram_lines,
)
from fransys_model.derive.drawing_text import content_extent
from fransys_model.kernel import Severity
from fransys_model.layout.tables import profile_of, sheet_for
from fransys_model.vocab.enums import PageKind


def test_the_station_system_reading_has_four_lines_over_five_boxes():
    """Only the system reading has lines; the cabinet's own reading has none, so one fact set."""
    (facts,) = read_diagrams(station())
    assert facts.unit is None
    assert (len(facts.lines), len(facts.boxes)) == (4, 5)


def test_box_widths_dashes_and_order_follow_the_model_text():
    model = station()
    (facts,) = read_diagrams(model)
    height = profile_of(model).text_height
    boxes = [b.box for b in facts.boxes]
    assert boxes == sorted(boxes, key=lambda box: box_order(model, box, None))
    for placed in facts.boxes:
        texts = box_lines(model, placed.box, None)
        assert placed.text_widths == tuple(text_width(t, height=height) for t in texts)
        assert placed.dashed == box_dashed(model, placed.box, None)
    assert sum(b.dashed for b in facts.boxes) == 2


def test_lines_keep_line_order_with_label_and_tab_widths():
    model = station()
    (facts,) = read_diagrams(model)
    height = profile_of(model).text_height
    lines = diagram_lines(model, None)
    assert [(f.cable, f.a, f.b) for f in facts.lines] == [(x.cable, x.a, x.b) for x in lines]
    for fact, line in zip(facts.lines, lines, strict=True):
        assert fact.label_width == text_width(line.designation, height=height)
        for width, tab in ((fact.tab_a, line.tab_a), (fact.tab_b, line.tab_b)):
            assert width == (None if tab is None else text_width(tab, height=height))
    assert any(f.tab_a is None or f.tab_b is None for f in facts.lines)


def test_penalties_and_sheet_come_from_the_profile_and_the_a2_sheet():
    model = station()
    (facts,) = read_diagrams(model)
    profile, sheet = profile_of(model), sheet_for(model, PageKind.BLOCK_DIAGRAM)
    assert (facts.text_height, facts.turn_penalty, facts.crossing_penalty) == (
        profile.text_height,
        profile.route_turn_penalty,
        profile.route_crossing_penalty,
    )
    assert facts.width == content_extent(sheet.content_width_mm, sheet.module_mm)
    assert facts.height == content_extent(sheet.content_height_mm, sheet.module_mm)


@pytest.mark.parametrize("n", [2, 5])
def test_a_chain_is_a_path_graph(n):
    (facts,) = read_diagrams(chain(n))
    assert (len(facts.boxes), len(facts.lines)) == (n, n - 1)


@pytest.mark.parametrize("model", [one_box(), loose()])
def test_a_reading_with_no_line_gives_no_facts(model):
    assert read_diagrams(model) == ()


@pytest.mark.parametrize(
    ("model", "code", "severity"),
    [
        (one_box(), DIAGRAM_CABLE_ONE_BOX, Severity.INFO),
        (fanout(), DIAGRAM_CABLE_FANOUT, Severity.WARNING),
        (loose(), DIAGRAM_LOOSE_WIRE, Severity.INFO),
    ],
)
def test_each_diagram_fact_becomes_one_finding_of_its_severity(model, code, severity):
    (finding,) = read_findings(model)
    assert (finding.code, finding.severity) == (code, severity)
    assert len(finding.subjects) == 1
    assert finding.message.endswith(".")


@pytest.mark.parametrize("model", [chain(3), station()])
def test_clean_models_give_no_findings(model):
    assert read_findings(model) == ()


def test_findings_are_sorted_by_code_and_subjects():
    findings = read_findings(fanout())
    assert list(findings) == sorted(findings, key=lambda f: (f.code, f.subjects))
