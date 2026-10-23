"""The house text records: each builder, the kinds, and the one accessor of each (SO3)."""

from decimal import Decimal

import pytest
from derive_helpers import house_records

from fransys_model.derive.house_settings import (
    colour_codes_of,
    frame_form_of,
    harness_text_of,
    reference_text_of,
    revision_form_of,
    revision_table_form_of,
    stub_text_of,
    title_block_form_of,
    wire_label_text_of,
    word,
)
from fransys_model.kernel import Draft, Origin, SchemaError, freeze
from fransys_model.layout import (
    HOUSE_TEXT_KINDS,
    LIBRARY_KINDS,
    SheetFormat,
    paper_choice,
    sheet_format_record,
)

_ORIGIN = Origin(file="test_house_records.py", line=1, note="fixture")
ACCESSORS = (
    reference_text_of,
    frame_form_of,
    stub_text_of,
    wire_label_text_of,
    harness_text_of,
    colour_codes_of,
    title_block_form_of,
    revision_table_form_of,
    revision_form_of,
)


def _model(records: tuple = ()):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_eleven_kinds_are_facade_written_library_kinds() -> None:
    assert len(HOUSE_TEXT_KINDS) == 10
    assert set(HOUSE_TEXT_KINDS) <= set(LIBRARY_KINDS)


def test_each_builder_keys_its_record_by_its_table() -> None:
    records = house_records()
    assert {r.key for r in records} == {
        ("build", t)
        for t in (
            "reference",
            "frame",
            "stub",
            "wire_label",
            "harness",
            "colours",
            "title_block",
            "revision_table",
            "revision",
            "words",
        )
    }
    assert {type(r) for r in records} == set(HOUSE_TEXT_KINDS)


def test_the_accessors_read_what_the_builders_wrote() -> None:
    model = _model(house_records())
    assert reference_text_of(model).page_prefix == "p"
    assert frame_form_of(model).row_labels == "letters"
    assert stub_text_of(model).arrow_in == "←"
    assert wire_label_text_of(model).show_ends is True
    assert harness_text_of(model).branch_sep == "."
    assert colour_codes_of(model).defaults["AC_N"] == ("BU", "")
    assert title_block_form_of(model).band_mm == Decimal("20.0")
    assert revision_table_form_of(model).columns[0] == "revision"
    assert revision_form_of(model).format == "{version}.{revision}"
    assert word(model, "side_a") == "Side A"


@pytest.mark.parametrize("accessor", ACCESSORS)
def test_a_model_with_no_record_raises_naming_the_table(accessor) -> None:
    with pytest.raises(SchemaError, match=r"carries no layout\.\w+ record"):
        accessor(_model())


def test_an_absent_word_raises_naming_the_key() -> None:
    with pytest.raises(SchemaError, match='no key "nope"'):
        word(_model(house_records()), "nope")
    with pytest.raises(SchemaError, match=r"layout\.words"):
        word(_model(), "side_a")


def test_the_paper_builders_build_what_the_facade_writes() -> None:
    numbers = dict.fromkeys(
        (
            "width_mm",
            "height_mm",
            "content_x_mm",
            "content_y_mm",
            "content_width_mm",
            "content_height_mm",
            "frame_columns",
            "frame_rows",
        ),
        3,
    )
    sheet = sheet_format_record(("t", "s"), "Tiny", numbers, Decimal("2.5"))
    assert isinstance(sheet, SheetFormat)
    assert (sheet.name, sheet.key, sheet.frame_rows) == ("Tiny", ("t", "s"), 3)
    choice = paper_choice(("t", "p"), default=sheet.id, by_kind={"schematic": sheet.id})
    assert choice.default == sheet.id
    assert choice.by_kind["schematic"] == sheet.id
