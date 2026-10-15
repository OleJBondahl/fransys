"""`tall_column` and `too_tall_finding`: the column that overfills the sheet, and its INFO."""

from fransys_layout.engines.diagram.frame import tall_column
from fransys_layout.engines.diagram.read.findings import DIAGRAM_COLUMN_TOO_TALL, too_tall_finding
from fransys_layout.engines.diagram.values import BoxFacts, DiagramFacts, LineFacts
from fransys_model.kernel import Id, Severity


def _id(name: str) -> Id:
    return Id(kind="item", value=name)


def _star(leaves: int) -> DiagramFacts:
    names = [f"l{i}" for i in range(leaves)]
    boxes = [BoxFacts(box=_id(n), text_widths=(40,), dashed=False) for n in ("hub", *names)]
    lines = [
        LineFacts(
            cable=_id(f"w-{n}"), a=_id("hub"), b=_id(n), label_width=20, tab_a=None, tab_b=None
        )
        for n in names
    ]
    return DiagramFacts(
        unit=None,
        boxes=tuple(boxes),
        lines=tuple(lines),
        text_height=8,
        turn_penalty=1,
        crossing_penalty=1,
        width=1868,
        height=1248,
    )


def test_a_column_of_twenty_boxes_gives_its_number_count_and_fit() -> None:
    facts = _star(20)
    column, boxes, fit = tall_column(facts) or (0, 0, 0)
    assert (column, boxes) == (2, 20)
    assert 0 < fit < 20
    finding = too_tall_finding(None, facts.lines[0].cable, column, boxes, fit)
    assert (finding.code, finding.severity) == (DIAGRAM_COLUMN_TOO_TALL, Severity.INFO)
    assert finding.subjects == (facts.lines[0].cable,)
    assert f"column 2 holds 20 boxes and one sheet holds {fit}." in finding.message
    assert finding.message.startswith("The system diagram is not drawn:")


def test_a_column_that_fits_gives_no_finding() -> None:
    assert tall_column(_star(3)) is None


def test_a_unit_diagram_names_its_unit() -> None:
    finding = too_tall_finding(_id("U1"), _id("w"), 1, 30, 17)
    assert finding.message.startswith("The diagram of unit ")
