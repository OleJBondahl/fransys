"""A consumer's `[words]` keys reach what is printed (SO2)."""

lazy from pathlib import Path

import pytest

from fransys_model.checks.revisions import _date_regex
from fransys_model.derive import pdf_texts, revision_text
from fransys_model.derive.facts.house_settings import revision_form_of
from fransys_model.derive.facts.revision_label import revision_label

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def test_the_default_printed_revision_is_the_identity_form() -> None:
    form = revision_form_of(skid_model())
    assert revision_label(form, 1, 10) == revision_text(1, 10) == "1.10"


@pytest.mark.parametrize(
    ("pattern", "good", "bad"),
    [
        ("YYYY-MM-DD", "2026-10-23", "26-10-23"),
        ("DD.MM.YYYY", "23.10.2026", "2026.10.23"),
        ("YYYY/MM", "2026/10", "2026-10"),
        ("MM", "10", "1"),
    ],
)
def test_a_date_pattern_compiles_letter_groups_and_escapes_the_rest(pattern: str, good: str, bad: str) -> None:
    regex = _date_regex(pattern)
    assert regex.fullmatch(good)
    assert not regex.fullmatch(bad)


def test_a_column_word_reaches_the_pdf_values(tmp_path: Path) -> None:
    ours = pdf_texts(skid_model())
    ruled = pdf_texts(skid_model(consumer_file(tmp_path, '[words]\ncreated = "Drawn"\n')))
    assert ours["revision_headers"] == (
        "Revision",
        "Date",
        "Description",
        "Created",
        "Checked",
        "Approved",
    )
    assert ruled["revision_headers"][3] == "Drawn"


def test_the_bridge_word_reaches_the_pdf_values(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\nbridge = "Jumper"\n'))
    assert pdf_texts(skid_model())["words"]["bridge"] == "Bridge"
    assert pdf_texts(model)["words"]["bridge"] == "Jumper"
