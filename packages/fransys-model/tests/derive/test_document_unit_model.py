"""Tests for `derive.document_unit`, the one reader of a document's subject unit (UN1, UN2)."""

from typing import Any

from plant import Plant

from fransys_model.derive import document_unit
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.document import Document
from fransys_model.vocab.enums import DocumentPreset


def _document(**fields: Any) -> Document:
    base: dict[str, Any] = {
        "id": make_id(Document, ("doc",)),
        "key": ("doc",),
        "preset": DocumentPreset.PCB_SCHEMATIC,
        "location": None,
        "item": None,
        "add": (),
        "remove": (),
        "cover": "# Invented",
        "notes": None,
    }
    return Document(**{**base, **fields})


def test_a_unit_name_resolving_to_one_unit_returns_its_id() -> None:
    """UN2: a `unit_name` naming exactly one instance resolves to it."""
    plant = Plant()
    unit = plant.unit("a", name="relay-board")
    model = plant.model()
    document = _document(unit_name="relay-board")
    assert document_unit(model, document) == unit


def test_a_set_unit_wins_over_unit_name() -> None:
    """`document.unit` wins when set; `unit_name` is never consulted."""
    other = make_id(Unit, ("elsewhere",))
    document = _document(unit=other, unit_name=None)
    assert document_unit(Plant().model(), document) == other


def test_an_unknown_name_is_none() -> None:
    """No release of that name in the model: zero matches, `None`."""
    plant = Plant()
    plant.unit("a", name="relay-board")
    model = plant.model()
    document = _document(unit_name="ghost")
    assert document_unit(model, document) is None


def test_two_instances_of_one_release_are_none() -> None:
    """Two `Unit`s sharing one release: several matches, `None` (silently, UN2)."""
    plant = Plant()
    plant.unit("a", name="board")
    plant.unit("b", name="board")
    model = plant.model()
    document = _document(unit_name="board")
    assert document_unit(model, document) is None


def test_two_releases_of_one_name_one_instance_each_are_none() -> None:
    """`1.1` and `1.2` of the same name, one instance each: still several matches, `None`."""
    plant = Plant()
    plant.unit("a", name="board", version=1, revision=1)
    plant.unit("b", name="board", version=1, revision=2)
    model = plant.model()
    document = _document(unit_name="board")
    assert document_unit(model, document) is None


def test_a_release_with_no_instance_is_none() -> None:
    """A release exists, but no `Unit` in the model is one of its instances: `None`."""
    plant = Plant()
    plant.release(name="board")
    model = plant.model()
    document = _document(unit_name="board")
    assert document_unit(model, document) is None


def test_neither_field_set_is_none() -> None:
    """A subject-less document (never authored in practice) has no unit to read."""
    document = _document(unit=None, unit_name=None, preset=DocumentPreset.SYSTEM)
    assert document_unit(Plant().model(), document) is None
