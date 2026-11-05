"""SETTINGS-OPEN SO1: a project file sets only words, lists and export; the engine, pdf, look and line tables are internal."""

from typing import Any
lazy from pathlib import Path

import fransys as fr
import pytest

pytestmark = pytest.mark.wp("facade")


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "table",
    [
        "layout",
        "profile",
        "pdf",
        "look",
        "lines",
        "dash",
        "reference",
        "frame",
        "stub",
        "wire_label",
        "harness",
        "title_block",
        "revision_table",
        "revision",
        "designation",
    ],
)
def test_an_internal_table_in_a_consumer_file_is_refused(tmp_path: Path, table: str) -> None:
    with pytest.raises(fr.SettingsError, match=rf"\[{table}\] is fixed in 0.22; remove it from your settings"):
        fr.settings(_file(tmp_path, f"[{table}]\nx = 1\n"))


def test_a_lists_table_merges_into_ours_key_by_key(tmp_path: Path) -> None:
    text = '[[lists.terminal.columns]]\nfield = "index"\npdf = "head_index"\ncsv = "csv_index"\n'
    table: Any = fr.settings(_file(tmp_path, text)).table("lists")["terminal"]
    ours: Any = fr.settings().table("lists")["terminal"]
    assert [c["field"] for c in table["columns"]] == ["index"]
    assert table["pdf_columns"] == ours["pdf_columns"]


def test_an_unknown_list_or_key_in_lists_is_refused(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match=r'\[lists\] "nope" is not a setting'):
        fr.settings(_file(tmp_path, "[lists.nope]\npdf_columns = []\n"))
    with pytest.raises(fr.SettingsError, match=r'\[lists.bom\] "widths" is not a setting'):
        fr.settings(_file(tmp_path, "[lists.bom]\nwidths = [1]\n"))


def test_an_export_key_merges_and_an_unknown_one_is_refused(tmp_path: Path) -> None:
    merged = fr.settings(_file(tmp_path, '[export]\ncsv_delimiter = ";"\n'))
    assert merged.table("export")["csv_delimiter"] == ";"
    assert merged.table("export")["data_dir"] == "data"
    with pytest.raises(fr.SettingsError, match=r'\[export\] "delimiter" is not a setting'):
        fr.settings(_file(tmp_path, '[export]\ndelimiter = ";"\n'))
