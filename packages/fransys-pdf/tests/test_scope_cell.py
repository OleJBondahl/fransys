"""The Scope cell of a drawing page prints the full location path (model-0301)."""

from _build import document, location, model
from test_signed_scope import _nested_cabinet, _schematic_background

from fransys_model.derive import scope_path
from fransys_model.vocab import DocumentPreset, documents


def _doc(subject):
    return document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=subject, cover="# Cover")


def test_a_sub_place_page_prints_the_full_path_in_the_scope_cell():
    room, cabinet = _nested_cabinet()
    svg = _schematic_background(room, cabinet)
    assert ">+ER+C1</text>" in svg
    assert ">C1</text>" not in svg


def test_a_top_level_place_page_prints_its_one_label_signed():
    room = location("ER", "Electrical room")
    assert ">+ER</text>" in _schematic_background(room)


def test_scope_path_of_a_sub_place_is_the_path_alone():
    room, cabinet = _nested_cabinet()
    doc = _doc(cabinet)
    m = model(room, cabinet, doc)
    record = documents(m)[doc.id]
    assert scope_path(m, record.id) == "+ER+C1"


def test_scope_path_of_a_top_level_place_is_exactly_its_label():
    room = location("ER", "Electrical room")
    doc = _doc(room)
    m = model(room, doc)
    assert scope_path(m, doc.id) == "+ER"
