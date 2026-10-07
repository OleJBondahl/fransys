"""Tests for the authored `Document`, `DocumentPreset` and `PageKind` (design/vocabulary.md 6,
decision 0023)."""

import json
from typing import Any

import pytest
from plant import Plant

from fransys_model.kernel import (
    Draft,
    FreezeError,
    MergeConflict,
    Model,
    Origin,
    SchemaError,
    dumps,
    field_specs,
    loads,
    make_id,
)
from fransys_model.kernel.ids import render_id
from fransys_model.kernel.schema import annotations_of
from fransys_model.layout import DrawingSet
from fransys_model.vocab import documents
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit, UnitRelease
from fransys_model.vocab.document import Document
from fransys_model.vocab.enums import Aspect, DocumentPreset, PageKind

_K = PageKind
_ORIGIN = Origin(file="test_document.py", line=1, note="fixture")
_LOCATION = make_id(AspectNode, ("c1",))
_ITEM = make_id(Item, ("jb1",))
_UNIT = make_id(Unit, ("board",))


def _document(**fields: Any) -> Document:
    base: dict[str, Any] = {
        "id": make_id(Document, ("cabinet",)),
        "key": ("cabinet",),
        "preset": DocumentPreset.CABINET_SCHEMATIC,
        "location": _LOCATION,
        "item": None,
        "add": (),
        "remove": (),
        "cover": "# Invented cabinet",
        "notes": None,
    }
    return Document(**{**base, **fields})


def _model(*extra: Any) -> Model:
    plant = Plant()
    plant.item("jb1", designation="JB1")
    plant.add(
        AspectNode(
            id=_LOCATION,
            key=("c1",),
            aspect=Aspect.LOCATION,
            parent=None,
            label="C1",
            description="Invented",
        ),
        *extra,
    )
    return plant.model()


def test_a_document_about_a_location_freezes_and_is_in_its_table() -> None:
    """The subject is the location; the record is reachable through `documents(model)`."""
    document = _document()
    model = _model(document)
    assert documents(model)[document.id] == document


def test_a_document_about_an_item_freezes() -> None:
    """A harness or a board is an item subject."""
    document = _document(location=None, item=_ITEM, preset=DocumentPreset.HARNESS_DRAWING)
    assert documents(_model(document))[document.id].item == _ITEM


def test_a_document_about_a_unit_round_trips() -> None:
    """`unit` may be a unit's own id (units spec U3); comes back equal and reachable."""
    release_key = ("unit_release", "board", "1", "1")
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name="board",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(id=_UNIT, key=("board",), release=release.id, parent=None)
    document = _document(location=None, item=None, unit=_UNIT, preset=DocumentPreset.PCB_SCHEMATIC)
    model = _model(document, release, unit)
    text = dumps(model)
    assert loads(text) == model
    assert documents(model)[document.id].unit == _UNIT


def test_a_system_document_with_no_subject_round_trips() -> None:
    """The `SYSTEM` preset is the one document with none of `location`, `item` and `unit`."""
    document = _document(
        id=make_id(Document, ("system",)),
        key=("system",),
        location=None,
        item=None,
        unit=None,
        preset=DocumentPreset.SYSTEM,
    )
    # examined: the system document really carries no subject at all
    assert (document.location, document.item, document.unit) == (None, None, None)
    model = _model(document)
    text = dumps(model)
    assert loads(text) == model
    assert documents(model)[document.id].preset is DocumentPreset.SYSTEM


def test_a_system_document_with_a_subject_is_refused() -> None:
    """Can-fail: the `SYSTEM` preset must have zero subjects, not one."""
    with pytest.raises(SchemaError, match="not 1"):
        _document(location=_LOCATION, item=None, unit=None, preset=DocumentPreset.SYSTEM)


def test_a_document_about_a_unit_release_name_builds_and_round_trips() -> None:
    """`unit_name` alone is a subject (spec unit-subject-by-name UN1); it is plain text."""
    document = _document(location=None, unit_name="board", preset=DocumentPreset.PCB_SCHEMATIC)
    assert document.unit_name == "board"
    model = _model(document)
    assert loads(dumps(model)) == model
    assert documents(model)[document.id].unit_name == "board"


def test_a_document_without_unit_name_stores_null_and_round_trips() -> None:
    """The default is stored as an explicit `null` (every field is written) and comes back."""
    model = _model(_document())
    data = json.loads(dumps(model))
    assert data["tables"]["document"][0]["unit_name"] is None
    assert loads(json.dumps(data)) == model
    assert documents(model)[make_id(Document, ("cabinet",))].unit_name is None


@pytest.mark.parametrize(
    "extra",
    [{"location": _LOCATION}, {"item": _ITEM}, {"unit": _UNIT}],
    ids=["location", "item", "unit"],
)
def test_a_unit_name_with_another_subject_is_refused(extra: dict[str, Any]) -> None:
    """Can-fail: `unit_name` counts as a subject, so a second one makes two."""
    fields: dict[str, Any] = {"location": None, "item": None, "unit": None, "unit_name": "board"}
    with pytest.raises(SchemaError, match="not 2"):
        _document(**{**fields, **extra})


def test_a_system_document_with_a_unit_name_is_refused() -> None:
    """Can-fail: the `SYSTEM` preset has none of the four, `unit_name` included."""
    with pytest.raises(SchemaError, match="not 1"):
        _document(location=None, unit_name="board", preset=DocumentPreset.SYSTEM)


def test_a_document_with_no_subject_is_refused_naming_the_four() -> None:
    """No subject at all is refused, and the message names all four kinds of subject."""
    with pytest.raises(SchemaError, match="a unit release name, not 0"):
        _document(location=None, item=None, unit=None, unit_name=None)


@pytest.mark.parametrize("subjects", [{"location": None, "item": None}, {"item": _ITEM}])
def test_a_document_needs_exactly_one_subject(subjects: dict[str, Any]) -> None:
    """No subject and two subjects are both refused at construction."""
    with pytest.raises(SchemaError):
        _document(**subjects)


def test_the_two_subject_refusal_names_the_record() -> None:
    """The error carries the record it is about, for `describe`."""
    with pytest.raises(SchemaError) as excinfo:
        _document(item=_ITEM)
    assert excinfo.value.record_id == make_id(Document, ("cabinet",))


def test_a_system_document_with_a_subject_error_has_kind_document() -> None:
    """The error's `kind` is "document", a fact `match=` on the message alone does not pin."""
    with pytest.raises(SchemaError) as excinfo:
        _document(location=_LOCATION, item=None, unit=None, preset=DocumentPreset.SYSTEM)
    assert excinfo.value.kind == "document"
    assert str(excinfo.value) == "the system document has no subject, not 1"


def test_the_two_subject_refusal_error_has_kind_document() -> None:
    """Same `kind` contract for the ordinary (non-`SYSTEM`) subject-count refusal."""
    with pytest.raises(SchemaError) as excinfo:
        _document(item=_ITEM)
    assert excinfo.value.kind == "document"
    assert str(excinfo.value) == (
        "a document is about exactly one of a location, an item, a unit and a unit "
        "release name, not 2"
    )


def test_the_refusal_holds_through_from_data() -> None:
    """A stored document with two subjects fails inside `freeze()`'s `FreezeError`."""
    data = json.loads(dumps(_model(_document())))
    data["tables"]["document"][0]["item"] = render_id(_ITEM)
    with pytest.raises(FreezeError):
        loads(json.dumps(data))


def test_add_and_remove_are_stored_in_canonical_page_order() -> None:
    """Authored as `bom, cover`, stored as `cover, bom`: order is not a fact."""
    document = _document(add=(_K.BOM, _K.COVER), remove=(_K.WIRE_LABEL_LIST, _K.NOTES))
    assert document.add == (_K.COVER, _K.BOM)
    assert document.remove == (_K.NOTES, _K.WIRE_LABEL_LIST)
    assert _document(add=(_K.COVER, _K.BOM)) == _document(add=(_K.BOM, _K.COVER))


def test_a_page_kind_listed_twice_is_refused() -> None:
    """A set, so a repeat is an authoring slip, as a port listed twice in a net."""
    with pytest.raises(SchemaError):
        _document(add=(_K.BOM, _K.BOM))
    with pytest.raises(SchemaError):
        _document(remove=(_K.NOTES, _K.NOTES))


def test_a_page_kind_listed_twice_error_names_kind_and_the_field() -> None:
    """The duplicate-kind refusal has the same `kind` and its message names which field."""
    with pytest.raises(SchemaError) as excinfo:
        _document(add=(_K.BOM, _K.BOM))
    assert excinfo.value.kind == "document"
    assert str(excinfo.value) == "a document lists a page kind twice in add"
    assert excinfo.value.record_id == make_id(Document, ("cabinet",))

    with pytest.raises(SchemaError) as excinfo:
        _document(remove=(_K.NOTES, _K.NOTES))
    assert excinfo.value.kind == "document"
    assert str(excinfo.value) == "a document lists a page kind twice in remove"


def test_a_kind_in_both_add_and_remove_is_kept_in_both() -> None:
    """The record stays as authored; whoever resolves the pages lets `remove` win."""
    document = _document(add=(_K.BOM,), remove=(_K.BOM,))
    assert (document.add, document.remove) == ((_K.BOM,), (_K.BOM,))


def test_input_of_the_wrong_shape_is_left_for_freeze_to_report() -> None:
    """A list where a tuple is due does not raise a `TypeError` from the constructor."""
    document = _document(add=["bom"])
    with pytest.raises(FreezeError):
        _model(document)


def test_a_tuple_with_a_non_page_kind_element_is_left_untouched_and_the_loop_continues() -> None:
    """`_canonical` needs a tuple of all `PageKind`s; one bad element (a real tuple, unlike
    the list case above) voids reordering for that field, and the loop moves on to the next
    field rather than stopping there (`continue`, not `break`)."""
    document = _document(add=(_K.BOM, "cover"), remove=(_K.BOM, _K.COVER))
    assert document.add == (_K.BOM, "cover")
    assert document.remove == (_K.COVER, _K.BOM)
    with pytest.raises(FreezeError):
        _model(document)


def test_a_document_round_trips_through_canonical_form_with_its_texts() -> None:
    """Preset, kinds, cover and notes come back equal; enums are written by value."""
    document = _document(add=(_K.BOM,), notes="Invented notes", cover="Invented cover")
    model = _model(document)
    text = dumps(model)
    assert loads(text) == model
    assert '"cabinet_schematic"' in text
    assert '"bom"' in text


def test_a_location_that_is_not_a_node_is_a_freeze_error() -> None:
    """`location` names an aspect node; an id nothing holds is a dangling reference."""
    with pytest.raises(FreezeError):
        _model(_document(location=make_id(AspectNode, ("nowhere",))))


def test_the_page_kinds_are_the_closed_set_in_canonical_order() -> None:
    """Root decision 0006: cover, notes, contents, ..., bom last."""
    assert [kind.value for kind in PageKind] == [
        "cover",
        "notes",
        "contents",
        "block_diagram",
        "schematic",
        "harness_drawing",
        "plc_list",
        "terminal_list",
        "connector_list",
        "wire_label_list",
        "designation_list",
        "cable_list",
        "bom",
    ]
    assert [preset.value for preset in DocumentPreset] == [
        "cabinet_schematic",
        "harness_drawing",
        "pcb_schematic",
        "system",
    ]


def test_the_enum_fields_resolve_to_their_enums_at_runtime() -> None:
    """An enum imported only for type checking would leave the field with no shape (5.3)."""
    assert annotations_of(Document)["preset"] is DocumentPreset


def test_a_document_references_only_engineering_records() -> None:
    """The subject is an aspect node, an item or a unit; nothing points at a layout kind."""
    kinds = {spec.ref_kind for spec in field_specs(Document) if spec.ref_kind is not None}
    assert kinds == {"aspect_node", "item", "unit"}


def test_a_document_and_a_drawing_set_are_not_joined_by_reference() -> None:
    """Neither side holds an id of the other: the join is by location."""
    assert all(spec.ref_kind != "document" for spec in field_specs(DrawingSet))
    assert all(
        spec.ref_kind is None or not spec.ref_kind.startswith("layout.")
        for spec in field_specs(Document)
    )


def test_a_document_defaults_to_no_logo_and_round_trips_svg_text() -> None:
    """`logo` is `None` unless authored; spec page-frame R11.3, decision model-0051."""
    bare = _document()
    assert bare.logo is None
    document = _document(logo="<svg></svg>")
    model = _model(document)
    text = dumps(model)
    assert loads(text) == model
    assert documents(model)[document.id].logo == "<svg></svg>"


def test_two_documents_with_one_id_and_different_text_conflict() -> None:
    """The draft refuses a second cover under one key, as it refuses any record clash."""
    draft = Draft()
    draft.add(_document(), origin=_ORIGIN)
    with pytest.raises(MergeConflict):
        draft.add(_document(cover="# Another"), origin=_ORIGIN)
