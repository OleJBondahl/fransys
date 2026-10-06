"""Unit identity checks on the real build (UNIT-ID acceptance 1, 2, 4, 5 and 8).

The example authors the identity of its units and of the project: the cabinet unit is "Pump
cabinet", `SKX-PC-2`, revision `03`; the relay board unit is "Relay interface board",
`SKX-RIB-2`, revision `02`; the project is "Two-pump station", `EX-1`, customer "Example works".
This file pins where that identity shows up:

- Acceptance 1: every title block of each document carries the document's Title, Number,
  Revision and Customer, read from the `.typ` source of the `built` fixture (the PDF compresses
  its page content). "Every" means all cells with one label in the file hold one value.
- Acceptance 2: the PDF metadata title, the `#set document(title: ...)` of each `.typ`.
- Acceptance 4: nothing of the board's own set (`out/board/`) or its document names the board
  tag `U2`; the board's own BOM names the bare board without a designation.
- Acceptance 5: the system BOM has one line for the cabinet unit (number in `mpn`, title in
  `description`, location in `designations`), in the derived rows and in the system document.
- Acceptance 8: `fr.check` holds no ERROR and no WARNING, except exactly the six layout warnings
  of `LAYOUT_WARNINGS` (GAPS.md G29); no `LONE_CELL` is among them.

Each check function has a twin that runs it on a mutated copy of the real text, files or
findings and expects an `AssertionError`.
"""

import csv
import re
import shutil
from pathlib import Path

import fransys as fr
import pytest

Built = tuple[fr.BuildResult, Path, Path]

DOCUMENTS = {
    "relay-board.typ": {
        "Title": "Relay interface board",
        "Number": "SKX-RIB-2",
        "Revision": "1.3",
        "Customer": "",
    },
    "cabinet.typ": {
        "Title": "Pump cabinet",
        "Number": "SKX-PC-2",
        "Revision": "1.5",
        "Customer": "",
    },
    "system.typ": {
        "Title": "Two-pump station",
        "Number": "EX-1",
        "Revision": "1.1",
        "Customer": "Example works",
    },
}
BOARD_TAG = "-U2"
TEXT_SUFFIXES = {".csv", ".xml", ".html"}  # not .pdf: compressed bytes can hold "-U2" by chance
CABINET_ROW = (
    'text("SKX-PC-2"), text("1.5"), text(""), text("Pump cabinet"), text("1"), box(text("-U1"))'
)


def cell_values(typ_text: str, label: str) -> set[str]:
    """The values of every title-block cell labelled `label`: `Title` is the big bold cell."""
    pattern = rf'text\(size: 8pt, "{label}"\), text\(size: \d+pt, (?:strong\()?text\("([^"]*)"\)'
    return set(re.findall(pattern, typ_text))


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
    cell = f'text(size: 8pt, "Number"), text(size: 10pt, text("{DOCUMENTS[name]["Number"]}"))'
    assert cell in real
    with pytest.raises(AssertionError):
        assert_title_blocks(
            real.replace(cell, cell.replace(DOCUMENTS[name]["Number"], "X-9"), 1), DOCUMENTS[name]
        )
    with pytest.raises(AssertionError):
        assert_title_blocks("", DOCUMENTS[name])


@pytest.mark.parametrize("name", DOCUMENTS)
def test_pdf_metadata_title_is_the_document_title(built: Built, name: str) -> None:
    """Acceptance 2: `#set document(title: ...)` holds the unit's (or project's) title."""
    assert document_title(read_typ(built[2], name)) == DOCUMENTS[name]["Title"]


def test_document_title_check_fails_on_another_title(built: Built) -> None:
    """Can-fail proof: the title read from a mutated copy differs from the expected one."""
    real = read_typ(built[2], "cabinet.typ")
    assert document_title(real) == "Pump cabinet"
    assert document_title(
        real.replace('#set document(title: "Pump cabinet"', '#set document(title: ""')
    ) != ("Pump cabinet")
    assert document_title("") is None


def assert_no_board_tag(board_dir: Path, board_typ: str) -> None:
    """Assert no file name, no text file and not the board document names `-U2`."""
    files = [path for path in board_dir.rglob("*") if path.is_file()]
    assert files, f"{board_dir} holds no file"
    named = [path.name for path in files if BOARD_TAG in path.name]
    assert not named, f"file names with {BOARD_TAG}: {named}"
    holding = [
        path.name
        for path in files
        if path.suffix in TEXT_SUFFIXES and BOARD_TAG in path.read_text(encoding="utf-8")
    ]
    assert not holding, f"text files with {BOARD_TAG}: {holding}"
    assert BOARD_TAG not in board_typ, f"the board document names {BOARD_TAG}"


def test_board_set_never_names_its_own_tag(built: Built) -> None:
    """Acceptance 4: no `-U2` in the board's files or document; the bare board is still listed."""
    _, out_dir, intermediates = built
    assert_no_board_tag(out_dir / "board", read_typ(intermediates, "relay-board.typ"))

    board_lines = [
        row
        for row in read_csv(out_dir / "board" / "relay-interface-board-v1.3-bom.csv")
        if row["mpn"] == "SKX-RIB-2"
    ]
    assert len(board_lines) == 1, f"the board's bom.csv lines for SKX-RIB-2: {board_lines}"
    assert board_lines[0]["description"].startswith("Relay interface board")
    assert board_lines[0]["designations"] == "", "the board's own BOM must name no designation"
    designations = {
        row["designation"]
        for row in read_csv(out_dir / "board" / "relay-interface-board-v1.3-designations.csv")
    }
    assert {"-K1", "-K2", "-J1", "-J2"} <= designations, sorted(designations)
    parent_lines = [
        row
        for row in read_csv(out_dir / "cabinet" / "pump-cabinet-v1.5-bom.csv")
        if row["mpn"] == "SKX-RIB-2"
    ]
    assert [row["designations"] for row in parent_lines] == ["-U2"], (
        "the parent's BOM must print -U2"
    )


def test_board_tag_check_fails_on_a_tag_in_a_name_a_file_or_the_document(
    built: Built, tmp_path: Path
) -> None:
    """Can-fail proof: `-U2` added to a file name, a CSV or the document text makes it raise."""
    _, out_dir, intermediates = built
    board_typ = read_typ(intermediates, "relay-board.typ")
    for mutation in ("name", "csv", "document"):
        copy = tmp_path / mutation
        shutil.copytree(out_dir / "board", copy)
        typ = board_typ
        if mutation == "name":
            (copy / "relay-interface-board-v1.3-bom.csv").rename(
                copy / "relay-interface-board-v1.3-bom-U2.csv"
            )
        elif mutation == "csv":
            with (copy / "relay-interface-board-v1.3-bom.csv").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write("-U2\n")
        else:
            typ += "-U2"
        with pytest.raises(AssertionError):
            assert_no_board_tag(copy, typ)


def assert_cabinet_unit_line(lines: tuple, system_typ: str) -> None:
    """Assert the cabinet's one line in the derived top-level BOM rows and in the document."""
    found = [
        (line.part, line.mpn, line.revision, line.manufacturer, line.description, line.count)
        + (line.designations,)
        for line in lines
        if line.mpn == "SKX-PC-2"
    ]
    assert found == [(None, "SKX-PC-2", "1.5", "", "Pump cabinet", 1, ("-U1",))], found
    assert CABINET_ROW in system_typ, "the system document's BOM lacks the cabinet row"


def test_system_bom_has_one_line_for_the_cabinet_unit(built: Built) -> None:
    """Acceptance 5: number in `mpn`, title in `description`, in the rows and in the document."""
    result, _, intermediates = built
    lines = fr.derive.bom_lines(result.model, fr.derive.TOP_LEVEL)
    assert_cabinet_unit_line(lines, read_typ(intermediates, "system.typ"))


def test_cabinet_unit_line_check_fails_when_the_line_or_the_row_is_missing(built: Built) -> None:
    """Can-fail proof: the line dropped from the rows, and the row changed in the text, raise."""
    result, _, intermediates = built
    lines = fr.derive.bom_lines(result.model, fr.derive.TOP_LEVEL)
    typ = read_typ(intermediates, "system.typ")
    assert CABINET_ROW in typ
    with pytest.raises(AssertionError):
        assert_cabinet_unit_line(tuple(x for x in lines if x.mpn != "SKX-PC-2"), typ)
    with pytest.raises(AssertionError):
        assert_cabinet_unit_line(
            lines, typ.replace(CABINET_ROW, CABINET_ROW.replace("-U1", "-U1X"))
        )


# The 0.6 layout draws a power symbol on a pin and keeps it clear of its neighbours; the two
# auxiliary-contact pins of each pump's 24 V rail cannot be cleared (six warnings). v0.6.1 placed
# the ground symbol at -J1:3 (layout-0117, GAPS.md G29). Exactly these
# remain, counted by code. They are layout notes, not wiring faults.
LAYOUT_WARNINGS = {"POWER_SYMBOL_UNPLACED": 3, "SYMBOL_OVERLAP": 3}


def assert_no_error_or_warning(findings: tuple[fr.Finding, ...]) -> None:
    bad = [f for f in findings if f.severity in (fr.Severity.ERROR, fr.Severity.WARNING)]
    counts = {code: sum(f.code == code for f in bad) for code in LAYOUT_WARNINGS}
    assert counts == LAYOUT_WARNINGS, f"layout warnings: {counts}"
    other = [f for f in bad if f.code not in LAYOUT_WARNINGS]
    assert not other, f"findings above INFO: {[(f.code, f.severity.value) for f in other]}"


def test_check_holds_no_error_and_no_warning(built: Built) -> None:
    """Acceptance 8: the example's findings are INFO only."""
    assert_no_error_or_warning(fr.check(built[0]))


def test_findings_check_fails_on_a_warning(built: Built) -> None:
    """Can-fail proof: the same check raises once a made-up WARNING is appended."""
    made_up = fr.Finding(
        code="MADE_UP", severity=fr.Severity.WARNING, subjects=(), message="made up"
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
    )
    with pytest.raises(AssertionError):
        assert_no_error_or_warning((*fr.check(built[0]), other))
