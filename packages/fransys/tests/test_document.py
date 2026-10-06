"""F7: `document`'s subject resolution, cover/notes handling, and key-from-stem dedup/clash."""

import re

import fransys as fr
import fransys_author
import pytest

from fransys_model.kernel import Id, MergeConflict, merge
from fransys_model.vocab import Document as ModelDocument
from fransys_model.vocab import DocumentPreset


@pytest.fixture
def parts():
    return fr.parts("demo_parts")


@pytest.fixture
def design(parts):
    return fransys_author.Design(parts)


def _cover(tmp_path, name="cabinet.md", text="# Demo\n"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _only_record(draft) -> ModelDocument:
    (record,) = draft.records()
    assert isinstance(record, ModelDocument)
    return record


def test_location_handle_fills_location(design, tmp_path):
    c1 = design.location("C1", "Demo cabinet")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=_cover(tmp_path))
    record = _only_record(draft)
    assert record.location == c1.id
    assert record.item is None


def test_item_handle_fills_item(design, tmp_path):
    item = design.item(None, tag="WH1")
    draft = fr.document(DocumentPreset.HARNESS_DRAWING, item, cover=_cover(tmp_path))
    record = _only_record(draft)
    assert record.item == item.id
    assert record.location is None


def test_aspect_node_id_subject_fills_location(tmp_path):
    subject = Id(kind="aspect_node", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=_cover(tmp_path))
    record = _only_record(draft)
    assert record.location == subject
    assert record.item is None


def test_item_id_subject_fills_item(tmp_path):
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.HARNESS_DRAWING, subject, cover=_cover(tmp_path))
    record = _only_record(draft)
    assert record.item == subject
    assert record.location is None


def test_id_of_another_kind_raises_type_error(tmp_path):
    subject = Id(kind="part", value="demo")
    with pytest.raises(TypeError, match="part"):
        fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=_cover(tmp_path))


def test_name_subject_fills_unit_name(tmp_path):
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, "relay-board", cover=_cover(tmp_path))
    record = _only_record(draft)
    assert record.unit_name == "relay-board"
    assert record.unit is None
    assert record.location is None
    assert record.item is None


def test_two_names_get_distinct_keys(tmp_path):
    first = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, "relay-board", cover=_cover(tmp_path, name="a.md")
    )
    second = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, "power-board", cover=_cover(tmp_path, name="b.md")
    )
    assert _only_record(first).key != _only_record(second).key


def test_a_name_and_a_scope_get_distinct_keys(design, tmp_path):
    c1 = design.location("C1", "Demo cabinet")
    name_doc = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, "relay-board", cover=_cover(tmp_path, name="a.md")
    )
    scope_doc = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, c1, cover=_cover(tmp_path, name="b.md")
    )
    assert _only_record(name_doc).key != _only_record(scope_doc).key


def test_a_name_and_a_unit_id_with_one_stem_clash(tmp_path):
    cover = _cover(tmp_path)
    name_doc = fr.document(DocumentPreset.CABINET_SCHEMATIC, "relay-board", cover=cover)
    unit_doc = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, Id(kind="unit", value="demo"), cover=cover
    )
    with pytest.raises(MergeConflict):
        merge(name_doc, unit_doc)


def test_a_group_handle_raises_type_error(design, tmp_path):
    group = design.group("SUP", "Supply")
    with pytest.raises(TypeError, match="Group"):
        fr.document(DocumentPreset.CABINET_SCHEMATIC, group, cover=_cover(tmp_path))


def test_missing_cover_names_the_path(tmp_path):
    cover = tmp_path / "does-not-exist.md"
    subject = Id(kind="item", value="demo")
    with pytest.raises(FileNotFoundError, match=re.escape(cover.name)):
        fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)


def test_notes_file_present_is_read(tmp_path):
    cover = _cover(tmp_path)
    (tmp_path / "cabinet.notes.md").write_text("notes text", encoding="utf-8")
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    record = _only_record(draft)
    assert record.notes == "notes text"


def test_notes_file_absent_is_none(tmp_path):
    cover = _cover(tmp_path)
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    record = _only_record(draft)
    assert record.notes is None


def test_logo_absent_is_none(tmp_path):
    cover = _cover(tmp_path)
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    record = _only_record(draft)
    assert record.logo is None


def test_logo_file_present_is_read(tmp_path):
    cover = _cover(tmp_path)
    logo = tmp_path / "logo.svg"
    logo.write_text("<svg></svg>", encoding="utf-8")
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover, logo=logo)
    record = _only_record(draft)
    assert record.logo == "<svg></svg>"


def test_missing_logo_names_the_path(tmp_path):
    cover = _cover(tmp_path)
    logo = tmp_path / "does-not-exist.svg"
    subject = Id(kind="item", value="demo")
    with pytest.raises(FileNotFoundError, match=re.escape(logo.name)):
        fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover, logo=logo)


def test_key_comes_from_the_cover_stem(tmp_path):
    cover = _cover(tmp_path, name="my-panel.md")
    subject = Id(kind="item", value="demo")
    draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    (record,) = draft.records()
    assert record.key == ("document", "my-panel")


def test_two_documents_with_one_stem_and_equal_content_dedupe(tmp_path):
    cover = _cover(tmp_path)
    subject = Id(kind="item", value="demo")
    first = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    second = fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    merged = merge(first, second)
    assert len(merged.records()) == 1


def test_two_documents_with_one_stem_and_different_content_clash(tmp_path):
    cover = _cover(tmp_path)
    first = fr.document(DocumentPreset.CABINET_SCHEMATIC, Id(kind="item", value="a"), cover=cover)
    second = fr.document(DocumentPreset.CABINET_SCHEMATIC, Id(kind="item", value="b"), cover=cover)
    with pytest.raises(MergeConflict):
        merge(first, second)
