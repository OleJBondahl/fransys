"""The `document_scope` probe shared by the two RO-1 selection tests: a `Document` per label, fields as names."""

from typing import Any
lazy from collections.abc import Iterable

from fransys_model.derive.bom import TOP_LEVEL
from fransys_model.derive.document_scope import DocumentScope
from fransys_model.derive.document_scope import (
    _document_scope as document_scope,
)  # probes are not model records
from fransys_model.kernel import Id, Model, make_id, natural_key
from fransys_model.vocab import Document, DocumentPreset
from fransys_model.vocab.tables import aspect_nodes, items, units


def name(model: Model, id_: Id[Any] | None) -> str | None:
    """The authoring key of an item, unit or aspect node id, joined by `/`."""
    if id_ is None:
        return None
    table = {"item": items, "unit": units, "aspect_node": aspect_nodes}[id_.kind]
    return "/".join(str(k) for k in table(model)[id_].key)


def names(model: Model, ids: Iterable[Id[Any]]) -> tuple[str | None, ...]:
    return tuple(name(model, i) for i in ids)


def document(
    label: str, preset: DocumentPreset, *, location: Id[Any] | None = None, item: Id[Any] | None = None, unit: Id[Any] | None = None
) -> Document:
    key = ("probe", label)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=preset,
        location=location,
        item=item,
        cover="",
        notes=None,
        unit=unit,
    )


def subject(model: Model, label: str) -> Document:
    """The probe's `Document` for `label`: `system`, or `unit:`, `location:`, `item:` + key."""
    kind, _, key = label.partition(":")
    if kind == "system":
        return document(label, DocumentPreset.SYSTEM)
    table = {"unit": units, "location": aspect_nodes, "item": items}[kind]
    found = next(i for i, r in table(model).items() if "/".join(str(k) for k in r.key) == key)
    return document(
        label,
        DocumentPreset.CABINET_SCHEMATIC,
        location=found if kind == "location" else None,
        item=found if kind == "item" else None,
        unit=found if kind == "unit" else None,
    )


def field(model: Model, scope: DocumentScope, field_name: str) -> object:
    value = getattr(scope, field_name)
    if field_name == "unit":
        return name(model, value)
    if field_name == "bom_scope":
        return "TOP_LEVEL" if value is TOP_LEVEL else name(model, value)
    if field_name == "cables":
        return names(model, [c.cable for c in value])
    if field_name == "strips":
        return tuple(sorted(names(model, value), key=lambda n: (natural_key((n or "").rsplit("/", 1)[-1]), n or "")))  # equal designations tie by id
    return tuple(sorted(names(model, value), key=str)) if field_name == "connector_items" else names(model, value)


def cases(expected: dict[str, Any], field_name: str, built: set[str]) -> list[tuple[str, str, Any]]:
    return [(m, d, sel[field_name]) for m, docs in expected.items() for d, sel in docs.items() if m in built]


def check(models: dict[str, Model], model_name: str, label: str, field_name: str, want: object) -> None:
    model = models[model_name]
    got = field(model, document_scope(model, subject(model, label)), field_name)
    want = tuple(want) if isinstance(want, list) else want
    if got != want:
        raise AssertionError((model_name, label, field_name, got, want))
