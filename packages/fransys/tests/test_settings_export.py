"""`[export]`: which reports are written, how files are named, placed and encoded (SO-C part B)."""

lazy from pathlib import Path

import fransys as fr
import pytest

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
