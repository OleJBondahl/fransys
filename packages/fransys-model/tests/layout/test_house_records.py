"""The house text records: each builder, the kinds, and the one accessor of each (SO3)."""

import tomllib
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from derive_helpers import house_records

from fransys_model.derive.facts.house_settings import (
    designation_form_of,
    diagram_count_of,
    export_form_of,
    frame_form_of,
    front_count_of,
    harness_text_of,
    lists_of,
    ratings_form_of,
    reference_text_of,
    revision_form_of,
    revision_table_form_of,
    stub_text_of,
    title_block_form_of,
    wire_label_text_of,
    word,
)
from fransys_model.kernel import Draft, Origin, SchemaError, freeze, make_id
from fransys_model.layout import (
    HOUSE_TEXT_KINDS,
    LIBRARY_KINDS,
    SheetFormat,
    TitleBlockForm,
    front_pages_records,
    paper_choice,
    sheet_format_record,
)
from fransys_model.layout import (
    house_records as build_records,
)
from fransys_model.layout.house_text import FrontPages
from fransys_model.vocab import Document, DocumentPreset

_ORIGIN = Origin(file="test_house_records.py", line=1, note="fixture")
ACCESSORS = (
    reference_text_of,
    frame_form_of,
    stub_text_of,
    wire_label_text_of,
    harness_text_of,
    title_block_form_of,
    revision_table_form_of,
    revision_form_of,
    lists_of,
    ratings_form_of,
    designation_form_of,
    export_form_of,
)


def _model(records: tuple[Any, ...] = ()):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_fifteen_kinds_are_facade_written_library_kinds() -> None:
    assert len(HOUSE_TEXT_KINDS) == 15
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
            "profile",
            "title_block",
            "revision_table",
            "revision",
            "words",
            "lists",
            "export",
            "designation",
            "ratings",
        )
    }
    assert {type(r) for r in records} == set(HOUSE_TEXT_KINDS) - {FrontPages}


def test_a_mm_key_is_an_exact_decimal_of_the_float_and_a_list_is_a_tuple() -> None:
    """`band_mm = 20` (an int in the file) is `Decimal("20.0")`: the old builders went through `float`."""
    path = Path(__file__).parents[3] / "fransys" / "src" / "fransys" / "settings.toml"
    tables = tomllib.loads(path.read_text(encoding="utf-8"))
    tables["profile"] = tomllib.loads(path.parents[3].joinpath("fransys-layout/src/fransys_layout/layout.toml").read_text(encoding="utf-8"))[
        "profile"
    ]
    tables["title_block"].update(band_mm=20, centre_gap_mm=0.1, fields=["a", "b"], label_height_mm=2, value_height_mm=3)
    block = next(r for r in build_records(tables) if isinstance(r, TitleBlockForm))
    assert (str(block.band_mm), str(block.centre_gap_mm), block.fields, str(block.label_height_mm)) == ("20.0", "0.1", ("a", "b"), "2.0")


def test_the_accessors_read_what_the_builders_wrote() -> None:
    model = _model(house_records())
    assert reference_text_of(model).page_prefix == "p"
    assert frame_form_of(model).row_labels == "letters"
    assert stub_text_of(model).arrow_in == "←"
    assert wire_label_text_of(model).show_ends is True
    assert harness_text_of(model).branch_sep == "."
    assert title_block_form_of(model).band_mm == Decimal("20.0")
    assert revision_table_form_of(model).columns[0] == "revision"
    assert revision_form_of(model).format == "{version}.{revision}"
    assert word(model, "side_a") == "Side A"
    assert lists_of(model).columns["bom"][0] == "mpn"
    assert lists_of(model).pdf_words["bom"][0] == "head_mpn"
    assert lists_of(model).csv_words["wires"][0] == "wire_from"
    assert lists_of(model).pdf_columns["terminal"][-1] == "external_ends"
    assert "bom" not in lists_of(model).pdf_columns
    assert designation_form_of(model).number_start == 1
    assert ratings_form_of(model).max_solves > 0
    form = export_form_of(model)
    assert form.reports == ("bom", "plc", "wires", "designations", "cables", "cores")
    assert (form.name_join, form.version_sign, form.ref_sign) == ("-", "-v", "-")
    assert (form.data_dir, form.data_suffixes) == ("data", (".csv", ".xml"))
    assert (form.csv_delimiter, form.csv_encoding) == (",", "utf-8")
    assert (form.csv_quoting, form.csv_newline) == ("minimal", "\n")


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


def _document(name: str) -> Document:
    key = ("document", name)
    return Document(id=make_id(Document, key), key=key, preset=DocumentPreset.SYSTEM, location=None, cover="c", notes=None, unit=None)


def test_a_documents_front_count_is_its_stored_value_and_a_missing_one_raises_naming_it() -> None:
    document, other = _document("d1"), _document("d2")
    model = _model((document, other, *front_pages_records({document.id: 2}, {document.id: 3})))
    assert (front_count_of(model, document.id), diagram_count_of(model, document.id)) == (2, 3)
    with pytest.raises(SchemaError, match=r"no layout.front_pages record for document .*fransys.build"):
        front_count_of(model, other.id)
    with pytest.raises(SchemaError, match=r"no layout.front_pages record for document .*fransys.build"):
        diagram_count_of(model, other.id)
