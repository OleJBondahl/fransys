"""`fr.settings` merges a consumer's TOML file over our defaults, key by key (SETTINGS ST2, ST7)."""

from typing import cast
lazy from pathlib import Path

import fransys as fr
import pytest

pytestmark = pytest.mark.wp("facade")

BLOCK = fr.PageKind.BLOCK_DIAGRAM


def _formats(s: fr.Settings) -> dict[str, dict[str, object]]:
    return cast("dict[str, dict[str, object]]", s.paper["formats"])


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_our_defaults_are_a3_with_the_block_diagram_on_a2() -> None:
    s = fr.settings()
    assert s.paper["default"] == "A3"
    assert dict(s.paper_by_kind) == {BLOCK: "A2"}
    assert s.layout["row_gap"] == 24


def test_a_consumer_file_with_one_key_changes_that_key_only(tmp_path: Path) -> None:
    ours = fr.settings()
    theirs = fr.settings(_file(tmp_path, "[paper.formats.A3]\nframe_columns = 9\n"))
    assert _formats(theirs)["A3"]["frame_columns"] == 9
    changed = {
        key for key, value in _formats(theirs)["A3"].items() if value != _formats(ours)["A3"][key]
    }
    assert changed == {"frame_columns"}
    assert _formats(theirs)["A2"] == _formats(ours)["A2"]
    assert (theirs.pdf, theirs.look, theirs.layout) == (ours.pdf, ours.look, ours.layout)


def test_a_consumer_default_paper_replaces_ours(tmp_path: Path) -> None:
    assert fr.settings(_file(tmp_path, '[paper]\ndefault = "A2"\n')).paper["default"] == "A2"


def test_an_unknown_key_raises_and_names_the_known_keys(tmp_path: Path) -> None:
    path = _file(tmp_path, "[paper.formats.A3]\nwidht_mm = 1\n")
    with pytest.raises(fr.SettingsError, match=r'"widht_mm" is not a setting; known: .*width_mm'):
        fr.settings(path)


def test_an_unknown_table_raises(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match=r"table \[papper\] is not a settings table"):
        fr.settings(_file(tmp_path, "[papper]\nx = 1\n"))


def test_divisions_per_module_raises_with_the_library_data_reason(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match=r"divisions_per_module.*is library data"):
        fr.settings(_file(tmp_path, "[grid]\ndivisions_per_module = 4\n"))


def test_a_per_kind_key_in_the_file_raises(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match=r"fr\.settings\(paper="):
        fr.settings(_file(tmp_path, '[paper]\nblock_diagram = "A2"\n'))


def test_paper_names_a_format_per_kind_and_an_unknown_one_raises() -> None:
    assert dict(fr.settings(paper={BLOCK: "A3"}).paper_by_kind) == {BLOCK: "A3"}
    with pytest.raises(
        fr.SettingsError,
        match=r'fr\.settings\(paper=\) for BLOCK_DIAGRAM "A4" is not a paper format; known: A3, A2',
    ):
        fr.settings(paper={BLOCK: "A4"})


def test_a_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match="does not exist"):
        fr.settings(tmp_path / "nope.toml")


def test_a_model_only_build_takes_settings_and_the_result_carries_them() -> None:
    chosen = fr.settings(paper={BLOCK: "A3"})
    result = fr.build(fr.design("demo_parts"), settings=chosen)
    assert result.settings is chosen
    assert fr.build(fr.design("demo_parts")).settings == fr.settings()


def test_our_pdf_table_holds_the_list_share_and_gutter() -> None:
    assert dict(fr.settings().pdf) == {"list_share_pct": 40, "list_gutter_pct": 20}


def test_contact_tables_is_off_by_default_and_a_file_turns_it_on(tmp_path: Path) -> None:
    """CONTACT-TABLE: a `[layout]` key, overridable like every other (SETTINGS-OPEN SO1)."""
    assert fr.settings().layout["contact_tables"] is False
    assert fr.settings(_file(tmp_path, "[layout]\ncontact_tables = true\n")).layout[
        "contact_tables"
    ]


def test_contact_tables_must_be_true_or_false(tmp_path: Path) -> None:
    with pytest.raises(
        fr.SettingsError, match=r'\[layout\] "contact_tables" must be true or false'
    ):
        fr.settings(_file(tmp_path, '[layout]\ncontact_tables = "yes"\n'))
