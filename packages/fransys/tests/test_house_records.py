"""The facade writes one house text record per settings table and refuses authored ones (SO3)."""

lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.derive.house_settings import (
    reference_text_of,
    word,
)
from fransys_model.kernel import Draft, Origin, SchemaError
from fransys_model.layout import HOUSE_TEXT_KINDS, Words, layout_of, words

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
    assert dict(layout_of(model, Words)[next(iter(layout_of(model, Words)))].words) == dict(
        s.table("words")
    )
    assert reference_text_of(model).cell_sep == s.table("reference")["cell_sep"]


def test_a_consumer_key_reaches_its_record(tmp_path: Path) -> None:
    model = _build(
        _file(tmp_path, '[reference]\npage_prefix = "s"\n[words]\nside_a = "Side A (field)"\n')
    ).model
    assert reference_text_of(model).page_prefix == "s"
    assert reference_text_of(model).cell_sep == ":"
    assert word(model, "side_a") == "Side A (field)"
    assert word(model, "side_b") == "Side B"


def test_a_consumer_may_not_add_a_default_colour_row(tmp_path: Path) -> None:
    path = _file(tmp_path, '[colours.defaults]\nAC_L4 = ["BK", ""]\n')
    with pytest.raises(fr.SettingsError, match=r"AC_L4.*is not a setting"):
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
    draft.extend([words({"a": "b"})], origin=Origin(file="t.py", line=1, note="planted"))
    with pytest.raises(SchemaError, match="Words record"):
        fr.build(draft)
