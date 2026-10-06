"""Tests for `validators.documents` (spec unit-subject-by-name UN3)."""

from typing import Any

import pytest

from fransys_model.kernel import (
    Draft,
    Model,
    Origin,
    Record,
    Severity,
    freeze,
    key_text,
    make_id,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit, UnitRelease
from fransys_model.vocab.document import Document
from fransys_model.vocab.enums import Aspect, DocumentPreset
from fransys_model.vocab.validators import ALL_VALIDATORS, check_documents
from fransys_model.vocab.validators.documents import DOCUMENT_UNIT_UNRESOLVED


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_documents.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _release(*, name: str = "relay-board", version: int = 1, revision: int = 1) -> UnitRelease:
    key = ("unit_release", name, str(version), str(revision))
    return UnitRelease(
        id=make_id(UnitRelease, key),
        key=key,
        name=name,
        version=version,
        revision=revision,
        interface="1",
    )


def _instance(key: str, release: UnitRelease) -> Unit:
    """One instance of `release`, told apart by its key."""
    return Unit(id=make_id(Unit, (key,)), key=(key,), release=release.id, parent=None)


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


def _unresolved(model: Model) -> list[Any]:
    return [f for f in check_documents(model) if f.code == DOCUMENT_UNIT_UNRESOLVED]


def test_a_unit_name_naming_exactly_one_instance_yields_no_finding() -> None:
    """Clean twin: `unit_name` resolves to exactly one unit (UN3)."""
    release = _release(name="relay-board")
    unit = _instance("relay-board-a", release)
    document = _document(unit_name="relay-board")
    model = _freeze((release, unit, document))
    assert not _unresolved(model)


def test_two_instances_of_the_named_release_yield_one_document_unit_unresolved() -> None:
    """Case (c): several instances match; the message names each with its key (UN3)."""
    release = _release(name="relay-board")
    a = _instance("relay-board-a", release)
    b = _instance("relay-board-b", release)
    document = _document(unit_name="relay-board")
    model = _freeze((release, a, b, document))
    findings = _unresolved(model)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].subjects == (document.id,)
    assert key_text(a) in findings[0].message
    assert key_text(b) in findings[0].message


def test_a_unit_name_with_no_matching_release_yields_one_document_unit_unresolved() -> None:
    """Case (a): no `UnitRelease` is named `unit_name` (UN3)."""
    document = _document(unit_name="ghost-board")
    model = _freeze((document,))
    findings = _unresolved(model)
    assert len(findings) == 1
    assert findings[0].subjects == (document.id,)
    assert "no unit release is named 'ghost-board'" in findings[0].message


@pytest.mark.parametrize("subject_kind", ["unit", "location", "item"])
def test_a_document_whose_subject_is_not_unit_name_is_never_checked(subject_kind: str) -> None:
    """The guard: only a `unit_name` document is checked, whatever the model otherwise holds.

    The model also holds two instances of a release named `"relay-board"` (an ambiguous
    match if a `unit_name` document named it) to prove the guard is not vacuous.
    """
    release = _release(name="relay-board")
    a = _instance("relay-board-a", release)
    b = _instance("relay-board-b", release)
    records: list[Any] = [release, a, b]
    if subject_kind == "unit":
        document = _document(unit=a.id)
    elif subject_kind == "location":
        location = AspectNode(
            id=make_id(AspectNode, ("c1",)),
            key=("c1",),
            aspect=Aspect.LOCATION,
            parent=None,
            label="C1",
            description="Invented",
        )
        records.append(location)
        document = _document(location=location.id)
    else:
        item = Item(
            id=make_id(Item, ("jb1",)),
            key=("jb1",),
            part=None,
            parent=None,
            position=None,
            tag=None,
            description="Invented",
        )
        records.append(item)
        document = _document(location=None, item=item.id, preset=DocumentPreset.HARNESS_DRAWING)
    records.append(document)
    model = _freeze(tuple(records))
    assert not _unresolved(model)


def test_check_documents_is_registered_in_all_validators() -> None:
    """`ALL_VALIDATORS` includes `check_documents`, appended last as `check_revisions` was."""
    assert check_documents in ALL_VALIDATORS
