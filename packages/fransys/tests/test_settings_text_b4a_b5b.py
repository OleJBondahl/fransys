"""A consumer's `[title_block]` and `[words]` keys reach the title block and the page headings."""

lazy from pathlib import Path

import pytest

from fransys_model.derive import continued_heading, page_headings, short_title
from fransys_model.derive.document_sheets import document_sheets_of
from fransys_model.derive.page_headings import schematic_title
from fransys_model.derive.title_band import title_band_need
from fransys_model.vocab import PageKind

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")

_CELLS = "title number revision revision_date customer author page_title scope sheet page"


def _labels(model) -> dict[str, str]:
    return dict(next(iter(document_sheets_of(model).values())).title_text.labels)


def test_the_title_block_band_is_the_consumers(tmp_path: Path) -> None:
    ours = title_band_need(skid_model(), 2.0, 2.5)
    theirs = title_band_need(
        skid_model(consumer_file(tmp_path, "[title_block]\nband_mm = 24.0\n")), 2.0, 2.5
    )
    assert theirs - ours == pytest.approx(4.0)


def test_the_title_block_cells_are_the_consumers(tmp_path: Path) -> None:
    ours = _labels(skid_model())
    assert list(ours) == _CELLS.split()
    cells = _CELLS.replace("scope ", "").split()
    text = "[title_block]\nfields = [" + ", ".join(f'"{c}"' for c in cells) + "]\n"
    assert list(_labels(skid_model(consumer_file(tmp_path, text)))) == cells


def test_a_title_block_label_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\ntitle = "Name"\n'))
    assert _labels(model)["title"] == "Name"
    assert _labels(skid_model())["title"] == "Title"


def test_a_page_heading_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\nschematic = "Diagram"\nbom = "Parts"\n'))
    assert schematic_title(model) == "Diagram"
    assert page_headings(model)[PageKind.BOM] == "Parts"
    assert schematic_title(skid_model()) == "Schematic"
    assert page_headings(skid_model())[PageKind.BOM] == "BOM"


def test_the_continued_word_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\ncontinued = "(forts.)"\n'))
    assert continued_heading(model, "-X1") == "-X1 (forts.)"
    assert continued_heading(skid_model(), "-X1") == "-X1 (cont.)"


def test_a_page_title_range_word_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\nrange_word = "til"\n'))
    assert short_title(model, ("Pump 1", "Pump 3")) == "Pump 1 til 3"
    assert short_title(skid_model(), ("Pump 1", "Pump 3")) == "Pump 1 to 3"
