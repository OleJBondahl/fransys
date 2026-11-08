"""`[export]`: which reports are written, how files are named, placed and encoded (SO-C part B)."""

import io
import itertools
import xml.etree.ElementTree as ET
import zipfile
from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.derive import cable_list_rows, cable_rows, document_rows, document_unit, terminal_rows, wire_rows

from ._settings_text_builds import consumer_file, skid_result

pytestmark = pytest.mark.wp("facade")

_REPORT_STEMS = ("bom", "plc", "wires", "designations", "cables", "cores")


def _written(tmp_path: Path, text: str | None) -> dict[str, bytes]:
    """Every file `fr.write` makes for the skid under the settings `text`, by relative path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = None if text is None else consumer_file(tmp_path, text)
    out = tmp_path / "out"
    fr.write(skid_result(path), out)
    return {str(p.relative_to(out)): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


def _csv_names(files: dict[str, bytes]) -> list[str]:
    return [name for name in files if name.endswith(".csv")]


def test_the_default_form_writes_the_six_reports_under_data(tmp_path: Path) -> None:
    files = _written(tmp_path, None)
    stems = {name.split("-")[-1].removesuffix(".csv") for name in _csv_names(files)}
    assert set(_REPORT_STEMS) <= stems
    assert all(name.startswith("data/") for name in _csv_names(files))
    assert all(not name.startswith("data/") for name in files if name.endswith(".pdf"))


def test_a_reports_subset_writes_the_listed_reports_only(tmp_path: Path) -> None:
    files = _written(tmp_path, '[export]\nreports = ["bom", "cores"]\n')
    stems = {name.split("-")[-1].removesuffix(".csv") for name in _csv_names(files)}
    assert not {"plc", "wires", "designations", "cables"} & stems
    assert {"bom", "cores"} <= stems


def test_a_report_kind_that_is_not_one_is_refused_naming_the_kinds(tmp_path: Path) -> None:
    path = consumer_file(tmp_path, '[export]\nreports = ["bom", "nope"]\n')
    with pytest.raises(fr.SettingsError, match=r'"reports" is \'nope\'; known: bom, plc, wires'):
        skid_result(path)


def test_the_name_signs_are_the_consumers(tmp_path: Path) -> None:
    text = '[export]\nname_join = "_"\nversion_sign = "_r"\nref_sign = "~"\n'
    names = set(_written(tmp_path, text))
    assert "data/P-1_r1.1_bom.csv" in names
    assert "data/P-1_r1.1_terminals.csv" in names
    assert "demo-skid_r1.1.pdf" in names


@pytest.mark.rule("EXPORT-FILES")
def test_the_default_signs_name_the_files_as_before(tmp_path: Path) -> None:
    names = set(_written(tmp_path, None))
    assert "data/P-1-v1.1-bom.csv" in names
    assert "data/P-1-v1.1-terminals.csv" in names


def test_the_data_folder_is_the_consumers(tmp_path: Path) -> None:
    files = _written(tmp_path, '[export]\ndata_dir = "tables"\n')
    assert "tables/P-1-v1.1-bom.csv" in files
    assert not any(name.startswith("data/") for name in files)


def test_a_file_outside_the_data_suffixes_stays_on_top(tmp_path: Path) -> None:
    files = _written(tmp_path, '[export]\ndata_suffixes = [".xml"]\n')
    assert "P-1-v1.1-bom.csv" in files
    assert not any(name.startswith("data/") for name in files)


@pytest.mark.rule("EXPORT-FILES")
def test_the_csv_form_is_the_consumers_in_every_csv(tmp_path: Path) -> None:
    ours = _written(tmp_path / "a", None)
    text = '[export]\ncsv_delimiter = ";"\ncsv_encoding = "utf-8-sig"\ncsv_newline = "\\r\\n"\n'
    theirs = _written(tmp_path / "b", text)
    name = "data/P-1-v1.1-bom.csv"
    assert theirs[name] != ours[name]
    assert theirs[name].startswith(b"\xef\xbb\xbf")
    assert not ours[name].startswith(b"\xef\xbb\xbf")
    first = theirs[name].decode("utf-8-sig").split("\r\n")[0]
    assert ";" in first
    assert "," not in first
    assert all(theirs[n].startswith(b"\xef\xbb\xbf") for n in _csv_names(theirs))


def test_only_a_csv_takes_the_csv_encoding(tmp_path: Path) -> None:
    files = _written(tmp_path, '[export]\ncsv_encoding = "utf-8-sig"\n')
    for name, data in files.items():
        if not name.endswith(".csv"):
            assert not data.startswith(b"\xef\xbb\xbf"), name


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ('csv_quoting = "sometimes"', r'"csv_quoting" is \'sometimes\'; known: minimal, all'),
        ('csv_delimiter = ";;"', r'"csv_delimiter" is \';;\': use one character'),
        ('csv_encoding = "klingon"', r'"csv_encoding" is \'klingon\': not a Python codec'),
    ],
)
def test_an_unusable_csv_setting_is_refused_at_build(tmp_path: Path, line: str, message: str) -> None:
    path = consumer_file(tmp_path, f"[export]\n{line}\n")
    with pytest.raises(fr.SettingsError, match=message):
        skid_result(path)


def test_csv_quoting_all_quotes_every_cell(tmp_path: Path) -> None:
    files = _written(tmp_path, '[export]\ncsv_quoting = "all"\n')
    bom = next(data for name, data in files.items() if name.endswith("bom.csv"))
    assert bom.decode("utf-8").splitlines()[0].startswith('"')


_RING = '[export]\nreports = ["ring_out"]\n'
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _sheet_rows(data: bytes) -> list[list[str]]:
    """The cell texts of the first sheet of an `.xlsx`, row by row, read from its zip and XML."""
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        strings = ET.fromstring(book.read("xl/sharedStrings.xml"))  # noqa: S314 -- our own output
        shared = ["".join(t.text or "" for t in si.iter(f"{_NS}t")) for si in strings.iter(f"{_NS}si")]
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))  # noqa: S314 -- our own output
    rows = []
    for row in sheet.iter(f"{_NS}row"):
        cells = {}
        for cell in row.iter(f"{_NS}c"):
            value = cell.find(f"{_NS}v")
            if value is not None and value.text is not None:
                text = value.text
                cells[cell.get("r", "")] = shared[int(text)] if cell.get("t") == "s" else text
        width = 11
        rows.append([cells.get(f"{chr(65 + i)}{row.get('r')}", "") for i in range(width)])
    return rows


def _ring_files(tmp_path: Path, text: str = _RING) -> dict[str, bytes]:
    return {name: data for name, data in _written(tmp_path, text).items() if name.endswith(".xlsx")}


def test_ring_out_is_off_by_default(tmp_path: Path) -> None:
    assert not _ring_files(tmp_path, '[export]\nreports = ["bom"]\n')
    assert not [name for name in _written(tmp_path / "d", None) if name.endswith(".xlsx")]


def test_ring_out_writes_one_sheet_per_pdf_with_its_stem(tmp_path: Path) -> None:
    files = _written(tmp_path, _RING)
    pdfs = {name.removesuffix(".pdf") for name in files if name.endswith(".pdf")}
    assert pdfs
    assert {name.removesuffix(".xlsx") for name in files if name.endswith(".xlsx")} == pdfs


def test_ring_out_bytes_are_the_same_in_two_writes(tmp_path: Path) -> None:
    assert _ring_files(tmp_path / "a") == _ring_files(tmp_path / "b")


class _NoInterface(NamedTuple):
    """The interface of the ring-out unit: nothing is reached from outside."""


@fr.unit("ring-cab", revision=1, interface_version=1, date="2026-10-15", text="First issue", by="OJB", title="Ring", number="R-1")
def _ring_cab(d: fr.Design) -> _NoInterface:
    """A wire, a cable core to a motor and a bridged strip: one join of each kind."""
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    d.terminal_strip("X2", "DEMO-TB-2.5", 4).run("P", 4, bridged=True)
    d.series(strip[1], d.cable("W1", "DEMO-CBL-4G1.5"), d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    d.series(strip[2], strip[3], wire=(BK, 2.5))
    return _NoInterface()


def _ring_cab_result(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Ring", number="R-1", customer="Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    d.add(_ring_cab, "U1", place="CAB")
    cover = tmp_path / "cover.md"
    cover.write_text("# Ring\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "ring-cab", cover=cover)
    return fr.build(d, document, settings=fr.settings(consumer_file(tmp_path, _RING)))


def test_every_join_of_the_model_is_one_row_of_the_sheet(tmp_path: Path) -> None:
    result = _ring_cab_result(tmp_path)
    model = result.model
    (record,) = document_rows(model)
    unit = document_unit(model, record.id)
    expected = [("Wire", w.from_, w.to) for w in wire_rows(model, unit=unit, context=record.location)]
    expected += [
        ("Core", c.end_a_designation, c.end_b_designation) for u in cable_list_rows(model, unit=unit) for c in cable_rows(model, u.cable, unit=unit)
    ]
    groups: dict[int, list[str]] = {}
    for t in terminal_rows(model, unit=unit, context=record.location):
        if t.jumper_group is not None:
            groups.setdefault(t.jumper_group, []).append(t.designation)
    expected += [("Bridge", a, b) for g in groups.values() for a, b in itertools.pairwise(g)]
    fr.write(result, tmp_path / "out")
    (path,) = (tmp_path / "out").glob("*.xlsx")
    lines = [r for r in _sheet_rows(path.read_bytes()) if len(r) > 3 and r[0].isdigit()]
    assert sorted((r[1], r[2], r[3]) for r in lines) == sorted(expected)
    assert {kind for kind, _, _ in expected} == {"Wire", "Core", "Bridge"}
    assert all(r[7].startswith("p") for r in lines if r[1] in {"Wire", "Core"})
    assert all(r[7] == "" for r in lines if r[1] == "Bridge")


def test_a_ring_out_word_is_the_consumers(tmp_path: Path) -> None:
    (ours,) = _ring_files(tmp_path / "a").values()
    (theirs,) = _ring_files(tmp_path / "b", _RING + '[words]\nring_status = "State"\n').values()
    assert "Status" in _sheet_rows(ours)[1]
    assert "State" in _sheet_rows(theirs)[1]
    assert "Status" not in _sheet_rows(theirs)[1]
