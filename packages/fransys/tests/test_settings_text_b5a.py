"""A consumer's `[words]` contact titles and spare word reach the printed text (SO2)."""

lazy from pathlib import Path

import pytest

from fransys_model.derive import coil_table_texts
from fransys_model.derive.house_settings import word
from fransys_model.derive.open_core_ends import open_core_text
from fransys_model.derive.rows_cores import OpenCoreRow
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.tables import functions

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def _first_contact_table(model) -> tuple[tuple[str, ...], ...]:
    return next(t for f in functions(model) if (t := coil_table_texts(model, f)))


def test_a_contact_table_title_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[words]\nno = "Make"\n'))
    assert _first_contact_table(skid_model())[0] == ("NO", "NC")
    assert _first_contact_table(model)[0] == ("Make", "NC")


def test_the_spare_word_is_the_consumers(tmp_path: Path) -> None:
    ours = skid_model()
    model = skid_model(consumer_file(tmp_path, '[words]\nspare = "free"\n'))
    cable = make_id(Item, ("w", "1"))
    row = OpenCoreRow(
        cable=cable,
        cable_designation="-W1",
        index=3,
        colour="GY",
        at=None,
        at_designation="",
        spare=True,
    )
    assert open_core_text(word(ours, "spare"), row) == "3 GY spare"
    assert open_core_text(word(model, "spare"), row) == "3 GY free"
