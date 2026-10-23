"""A consumer's `[revision]`, `[revision_table]` and `[words]` keys reach what is printed (SO2)."""

lazy from pathlib import Path

import pytest

from fransys_model.checks.revisions import _date_regex, check_revisions
from fransys_model.derive import pdf_texts, revision_text
from fransys_model.derive.facts.revision_label import revision_label
from fransys_model.derive.house_settings import revision_form_of
from fransys_model.derive.title_block import project_facts

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def test_the_default_printed_revision_is_the_identity_form() -> None:
    form = revision_form_of(skid_model())
    assert revision_label(form, 1, 10) == revision_text(1, 10) == "1.10"


@pytest.mark.rule("REVISION-FORM")
def test_a_revision_format_changes_the_printed_revision_only(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[revision]\nformat = "{version}-{revision}"\n'))
    ours = project_facts(skid_model())[3]
    assert project_facts(model)[3] == ours.replace(".", "-")
    assert revision_text(1, 2) == "1.2"  # the folder and baseline name never follow the format


def test_a_date_format_decides_the_date_check(tmp_path: Path) -> None:
    ours = {f.code for f in check_revisions(skid_model())}
    model = skid_model(consumer_file(tmp_path, '[revision]\ndate_format = "DD.MM.YYYY"\n'))
    found = [f for f in check_revisions(model) if f.code == "REVISION_DATE_FORMAT"]
    assert "REVISION_DATE_FORMAT" not in ours
    assert found
    assert "is not DD.MM.YYYY" in found[0].message


@pytest.mark.parametrize(
    ("pattern", "good", "bad"),
    [
        ("YYYY-MM-DD", "2026-10-23", "26-10-23"),
        ("DD.MM.YYYY", "23.10.2026", "2026.10.23"),
        ("YYYY/MM", "2026/10", "2026-10"),
        ("MM", "10", "1"),
    ],
)
def test_a_date_pattern_compiles_letter_groups_and_escapes_the_rest(
    pattern: str, good: str, bad: str
) -> None:
    regex = _date_regex(pattern)
    assert regex.fullmatch(good)
    assert not regex.fullmatch(bad)


def test_initials_may_be_left_out(tmp_path: Path) -> None:
    ours = skid_model()
    off = skid_model(consumer_file(tmp_path, "[revision]\ninitials_required = false\n"))
    assert not [f for f in check_revisions(off) if f.code == "REVISION_INITIALS_MISSING"]
    assert revision_form_of(ours).initials_required


def test_a_table_width_and_a_column_word_reach_the_pdf_values(tmp_path: Path) -> None:
    text = '[revision_table]\ndescription_mm = 90.0\n[words]\ncreated = "Drawn"\n'
    ours = pdf_texts(skid_model())
    ruled = pdf_texts(skid_model(consumer_file(tmp_path, text)))
    assert ours["description_mm"] == 120.0
    assert ours["revision_headers"] == (
        "Revision",
        "Date",
        "Description",
        "Created",
        "Checked",
        "Approved",
    )
    assert ruled["description_mm"] == 90.0
    assert ruled["revision_headers"][3] == "Drawn"


def test_the_bridge_word_reaches_the_pdf_values(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\nbridge = "Jumper"\n'))
    assert pdf_texts(skid_model())["words"]["bridge"] == "Bridge"
    assert pdf_texts(model)["words"]["bridge"] == "Jumper"
