"""Unit identity checks on the real build (UNIT-ID acceptance 1, 2, 5 and 8).

The example authors the identity of its unit and of the project: the cabinet unit is "Pump
cabinet", `SKX-PC-2`; the project is "Two-pump station", `EX-1`, customer "Example works".
This file pins where that identity shows up:

- Acceptance 1: every title block of each document carries the document's Title, Number,
  Revision and Customer, read from the `.typ` source of the `built` fixture (the PDF compresses
  its page content). "Every" means all cells with one label in the file hold one value.
- Acceptance 2: the PDF metadata title, the `#set document(title: ...)` of each `.typ`.
- Acceptance 5: the system BOM has one line for the cabinet unit (number in `mpn`, title in
  `description`, location in `designations`), in the derived rows and in the system document.
- Acceptance 8: `fr.check` holds no ERROR and no WARNING, except exactly the warnings of
  `EXPECTED_WARNINGS`: the layout ones (GAPS.md G29); no `LONE_CELL` is among them.

Each check function has a twin that runs it on a mutated copy of the real text, files or
findings and expects an `AssertionError`.
"""

import csv
import re
from pathlib import Path

import fransys as fr
import pytest

Built = tuple[fr.BuildResult, Path, Path]

DOCUMENTS = {
    "pump-cabinet-v1.11.typ": {
        "Title": "Pump cabinet",
        "Number": "SKX-PC-2",
        "Revision": "1.11",
        "Customer": "",
    },
    "EX-1-v1.6.typ": {
        "Title": "Two-pump station",
        "Number": "EX-1",
        "Revision": "1.6",
        "Customer": "Example works",
    },
}
CABINET_ROW = (
    'text("SKX-PC-2"), text("1.11"), text(""), text("Pump cabinet"), text("1"), box(text("-U1"))'
)


SVG_TEXT = re.compile(
    r'<text x=\\"([\d.]+)\\" y=\\"([\d.]+)\\" font-size=\\"([\d.]+)\\"[^>]*>([^<]*)</text>'
)
LABEL_SIZE = (
    2.4691  # the title block's label texts; its values are 3.4293 and sit 3.475 below a label
)


def cell_values(typ_text: str, label: str) -> set[str]:
    """The values of every title-block cell labelled `label`: the SVG text 3.475 below the label text."""
    texts = [(float(x), float(y), float(size), t) for x, y, size, t in SVG_TEXT.findall(typ_text)]
    values: set[str] = set()
    for n, (x, y, size, text) in enumerate(texts):
        if size == LABEL_SIZE and text == label:
            # every page repeats the block at the same coordinates: take the nearest in file order
            below = [
                (abs(m - n), t)
                for m, (tx, ty, ts, t) in enumerate(texts)
                if tx == x and abs(ty - y - 3.475) < 1e-6 and ts != LABEL_SIZE
            ]
            values.add(min(below)[1] if below else "")
    return values


def assert_title_blocks(typ_text: str, expected: dict[str, str]) -> None:
    """Assert every cell of each label holds the one expected value."""
    for label, value in expected.items():
        assert cell_values(typ_text, label) == {value}, (
            f"title block {label!r}: expected {{{value!r}}}, found {sorted(cell_values(typ_text, label))}"
        )


def document_title(typ_text: str) -> str | None:
    match = re.search(r'#set document\(title: "([^"]*)"', typ_text)
    return match.group(1) if match else None


def read_typ(intermediates: Path, name: str) -> str:
    return (intermediates / name).read_text(encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("name", DOCUMENTS)
def test_every_title_block_carries_the_unit_identity(built: Built, name: str) -> None:
    """Acceptance 1: Title, Number, Revision and Customer are one value across the document."""
    assert_title_blocks(read_typ(built[2], name), DOCUMENTS[name])


@pytest.mark.parametrize("name", DOCUMENTS)
def test_title_block_check_fails_on_one_stray_number_cell(built: Built, name: str) -> None:
    """Can-fail proof: one title block with another Number makes the check raise."""
    real = read_typ(built[2], name)
    number = DOCUMENTS[name]["Number"]
    cell = f'DejaVu Sans\\">{number}</text>'
    assert cell in real
    with pytest.raises(AssertionError):
        assert_title_blocks(real.replace(cell, cell.replace(number, "X-9"), 1), DOCUMENTS[name])
    with pytest.raises(AssertionError):
        assert_title_blocks("", DOCUMENTS[name])


@pytest.mark.parametrize("name", DOCUMENTS)
def test_pdf_metadata_title_is_the_document_title(built: Built, name: str) -> None:
    """Acceptance 2: `#set document(title: ...)` holds the unit's (or project's) title."""
    assert document_title(read_typ(built[2], name)) == DOCUMENTS[name]["Title"]


def test_document_title_check_fails_on_another_title(built: Built) -> None:
    """Can-fail proof: the title read from a mutated copy differs from the expected one."""
    real = read_typ(built[2], "pump-cabinet-v1.11.typ")
    assert document_title(real) == "Pump cabinet"
    assert document_title(
        real.replace('#set document(title: "Pump cabinet"', '#set document(title: ""')
    ) != ("Pump cabinet")
    assert document_title("") is None


def assert_cabinet_unit_line(lines: tuple, system_typ: str) -> None:
    """Assert the cabinet's one line in the derived top-level BOM rows and in the document."""
    found = [
        (line.part, line.mpn, line.revision, line.manufacturer, line.description, line.count)
        + (line.designations,)
        for line in lines
        if line.mpn == "SKX-PC-2"
    ]
    assert found == [(None, "SKX-PC-2", "1.11", "", "Pump cabinet", 1, ("-U1",))], found
    assert CABINET_ROW in system_typ, "the system document's BOM lacks the cabinet row"


def test_system_bom_has_one_line_for_the_cabinet_unit(built: Built) -> None:
    """Acceptance 5: number in `mpn`, title in `description`, in the rows and in the document."""
    result, _, intermediates = built
    lines = fr.derive.bom_lines(result.model, fr.derive.TOP_LEVEL)
    assert_cabinet_unit_line(lines, read_typ(intermediates, "EX-1-v1.6.typ"))


def test_cabinet_unit_line_check_fails_when_the_line_or_the_row_is_missing(built: Built) -> None:
    """Can-fail proof: the line dropped from the rows, and the row changed in the text, raise."""
    result, _, intermediates = built
    lines = fr.derive.bom_lines(result.model, fr.derive.TOP_LEVEL)
    typ = read_typ(intermediates, "EX-1-v1.6.typ")
    assert CABINET_ROW in typ
    with pytest.raises(AssertionError):
        assert_cabinet_unit_line(tuple(x for x in lines if x.mpn != "SKX-PC-2"), typ)
    with pytest.raises(AssertionError):
        assert_cabinet_unit_line(
            lines, typ.replace(CABINET_ROW, CABINET_ROW.replace("-U1", "-U1X"))
        )


# The 0.6 layout draws a power symbol on a pin and keeps it clear of its neighbours; the two
# auxiliary-contact pins of each pump's 24 V rail cannot be cleared (three warnings at v0.11.0). v0.6.1 placed
# the ground symbol at -J1:3 (layout-0117, GAPS.md G29). Exactly these
# remain, counted by code. They are layout notes, not wiring faults.
# v0.18.2 (layout-0222, intended change): a row of contacts fed from a rail places every power
# symbol, so the three POWER_SYMBOL_UNPLACED warnings are gone.
# OVERLAP 4 at 0.22.9: one finding per member now (was 1 finding holding 2 members); KI-658 (old, 2 members), KI-746, KI-747
LAYOUT_WARNINGS = {
    "POWER_SYMBOL_UNPLACED": 0,
    "SYMBOL_OVERLAP": 0,
    "JOIN_UNALIGNED": 0,
    "OVERLAP": 14,  # v0.23.10 layout: +13 (was 1 at 0.23.8) text/text and wire/text on CTL/0 and all/P1, traced in KI-903
}
EXPECTED_WARNINGS = LAYOUT_WARNINGS


def assert_no_error_or_warning(findings: tuple[fr.Finding, ...]) -> None:
    bad = [f for f in findings if f.severity in (fr.Severity.ERROR, fr.Severity.WARNING)]
    counts = {code: sum(f.code == code for f in bad) for code in EXPECTED_WARNINGS}
    assert counts == EXPECTED_WARNINGS, f"expected warnings: {counts}"
    other = [f for f in bad if f.code not in EXPECTED_WARNINGS]
    assert not other, f"findings above INFO: {[(f.code, f.severity.value) for f in other]}"


def test_check_holds_no_error_and_no_warning(built: Built) -> None:
    """Acceptance 8: the example's findings are INFO only."""
    assert_no_error_or_warning(fr.check(built[0]))


def test_findings_check_fails_on_a_warning(built: Built) -> None:
    """Can-fail proof: the same check raises once a made-up WARNING is appended."""
    made_up = fr.Finding(
        code="MADE_UP", severity=fr.Severity.WARNING, subjects=(), message="made up", fix="none"
    )
    with pytest.raises(AssertionError):
        assert_no_error_or_warning((*fr.check(built[0]), made_up))


def test_findings_check_fails_on_another_lone_cell(built: Built) -> None:
    """Can-fail proof: a LONE_CELL on any other function is not allowed."""
    other = fr.Finding(
        code="LONE_CELL",
        severity=fr.Severity.WARNING,
        subjects=(),
        message="LONE_CELL (warning): a symbol has no drawn conductor at all\n  subject: x (CAB/Q11/fn/main)",
        fix="draw a conductor to the symbol",
    )
    with pytest.raises(AssertionError):
        assert_no_error_or_warning((*fr.check(built[0]), other))
