"""A consumer's list words and the title-block centre gap reach the printed forms."""

lazy from pathlib import Path

import pytest

from fransys_model.derive.page_titles import _more_form, page_title_forms
from fransys_model.derive.title_band import title_band_need
from fransys_model.layout import Page, layout_of

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def test_the_centre_gap_scales_the_band_need(tmp_path: Path) -> None:
    ours = title_band_need(skid_model(), 4.0, 5.0)
    wide = skid_model(consumer_file(tmp_path, "[title_block]\ncentre_gap_mm = 6.0\n"))
    assert title_band_need(wide, 4.0, 5.0) > ours


def test_the_list_words_are_the_consumers(tmp_path: Path) -> None:
    text = '[words]\nlist_join = " + "\nand_word = "og"\nmore_word = "til"\n'
    ours, theirs = skid_model(), skid_model(consumer_file(tmp_path, text))
    page = next(p for p in layout_of(ours, Page).values() if len(page_title_forms(ours, p)) == 1)
    assert page_title_forms(ours, page)[0].count(", ") == 1
    assert page_title_forms(theirs, page)[0].count(" + ") == 1
    assert _more_form(ours, ("Pump", "A", "B")) == "Pump and 2 more"
    assert _more_form(theirs, ("Pump", "A", "B")) == "Pump og 2 til"
