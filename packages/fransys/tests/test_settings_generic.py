"""SETTINGS-OPEN X1, A1, A2 (R468): the merge is generic; mixed lists are records; open tables."""

from typing import cast

import fransys as fr
import pytest
from fransys._settings_merge import merged_tables
from fransys._settings_types import fits

pytestmark = pytest.mark.wp("facade")

PAPER = {"default": "A3", "formats": {"A3": {"w": 1}}}
OURS = {
    "paper": PAPER,
    "extra": {"pair": ["a", 1]},
    "designation": {"classes": {"K": ["relay", 1], "Q": ["switch", 2]}},
    "colours": {"rows": {"wire": "#000000"}},
}


def test_a_table_no_code_names_merges() -> None:
    got = merged_tables(OURS, {"extra": {"pair": ["b", 2]}}, "f")
    assert got["extra"]["pair"] == ["b", 2]


def test_a_mixed_list_of_the_wrong_length_is_refused() -> None:
    assert not fits(["a", 1], ["b"])
    assert not fits(["a", 1], ["b", 2, 3])
    with pytest.raises(fr.SettingsError, match="must be a list"):
        merged_tables(OURS, {"extra": {"pair": ["b"]}}, "f")


def test_a_mixed_list_with_a_wrong_element_type_is_refused() -> None:
    assert not fits(["a", 1], [1, 1])
    with pytest.raises(fr.SettingsError, match="must be a list"):
        merged_tables(OURS, {"extra": {"pair": [2, "b"]}}, "f")
    assert not fits(["a", 1], ["a", "b"])
    with pytest.raises(fr.SettingsError, match="must be a list"):
        merged_tables(OURS, {"extra": {"pair": ["a", "b"]}}, "f")


def test_a_list_of_one_type_still_differs_in_length() -> None:
    assert fits([0, 8, 16], [1])


def test_a_new_class_letter_is_accepted_and_type_checked() -> None:
    got = merged_tables(OURS, {"designation": {"classes": {"F": ["fuse", 3]}}}, "f")
    classes = cast("dict[str, object]", got["designation"]["classes"])
    assert classes["F"] == ["fuse", 3]
    with pytest.raises(fr.SettingsError, match=r"\[designation.classes\] \"F\" must be a list"):
        merged_tables(OURS, {"designation": {"classes": {"F": "fuse"}}}, "f")
    with pytest.raises(fr.SettingsError, match=r"\"F\" must be a list"):
        merged_tables(OURS, {"designation": {"classes": {"F": ["fuse"]}}}, "f")


def test_a_new_key_in_colours_is_refused() -> None:
    with pytest.raises(fr.SettingsError, match=r"\[colours.rows\] \"new\" is not a setting"):
        merged_tables(OURS, {"colours": {"rows": {"new": "#ffffff"}}}, "f")


def test_the_settings_table_accessor_gives_a_merged_table() -> None:
    s = fr.settings()
    assert s.table("pdf") == s.pdf
    with pytest.raises(fr.SettingsError, match="not a settings table"):
        s.table("nope")
