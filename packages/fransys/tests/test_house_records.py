"""The facade writes one house text record per settings table and refuses authored ones (SO3)."""

lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.derive.facts.house_settings import (
    reference_text_of,
    word,
)
from fransys_model.kernel import Draft, Origin, SchemaError, make_id
from fransys_model.layout import HOUSE_TABLES, HOUSE_TEXT_KINDS, Words, house_records, layout_of

pytestmark = pytest.mark.wp("facade")


def _build(path: Path | None = None) -> fr.BuildResult:
    return fr.build(fr.design("demo_parts"), settings=fr.settings(path))


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_build_carries_one_record_of_each_house_text_kind() -> None:
    model = _build().model
    for kind in HOUSE_TEXT_KINDS:
        assert len(layout_of(model, kind)) == 1, kind.__name__


def test_the_records_hold_the_settings_tables() -> None:
    model = _build().model
    s = fr.settings()
    assert dict(layout_of(model, Words)[next(iter(layout_of(model, Words)))].words) == dict(s.table("words"))
    assert reference_text_of(model).cell_sep == s.table("reference")["cell_sep"]


def test_a_consumer_key_reaches_its_record(tmp_path: Path) -> None:
    model = _build(_file(tmp_path, '[words]\nside_a = "Side A (field)"\n')).model
    assert word(model, "side_a") == "Side A (field)"
    assert word(model, "side_b") == "Side B"


def test_a_colours_table_is_no_setting(tmp_path: Path) -> None:
    path = _file(tmp_path, '[colours]\npe = "GNYE"\n')
    with pytest.raises(fr.SettingsError, match=r"colours.*is not a settings table"):
        fr.settings(path)


def test_a_conductors_table_is_no_setting(tmp_path: Path) -> None:
    """R498: `[conductors]` and its aliases left the settings; a consumer's file is refused."""
    with pytest.raises(fr.SettingsError, match=r"conductors.*is not a setting"):
        fr.settings(_file(tmp_path, '[conductors.aliases]\nR = "L1"\n'))


def test_a_rails_table_is_no_setting(tmp_path: Path) -> None:
    """R513: `[rails]` left the settings; a consumer's file is refused."""
    with pytest.raises(fr.SettingsError, match=r"rails.*is not a setting"):
        fr.settings(_file(tmp_path, '[rails]\ndc_zero = "0V0"\n'))


def test_an_authored_house_record_is_refused() -> None:
    draft = Draft()
    draft.extend(
        [Words(id=make_id(Words, ("t", "w")), key=("t", "w"), words=frozendict({"a": "b"}))], origin=Origin(file="t.py", line=1, note="planted")
    )
    with pytest.raises(SchemaError, match="Words record"):
        fr.build(draft)


def test_a_list_column_row_without_its_key_names_the_list_and_the_key() -> None:
    row = {"field": "a", "pdf": "A"}
    with pytest.raises(SchemaError, match=r"\[lists\.bom\.columns\] row 2 has no `csv` key"):
        house_records({**{n: fr.settings().table(n) for n in HOUSE_TABLES}, "lists": {"bom": {"columns": [{**row, "csv": "a"}, row]}}})


def test_the_colours_refusal_names_the_fix(tmp_path: Path) -> None:
    path = _file(tmp_path, '[colours]\npe = "GNYE"\n')
    with pytest.raises(fr.SettingsError, match=r"the \[colours\] table was removed in 0\.22; delete it"):
        fr.settings(path)
