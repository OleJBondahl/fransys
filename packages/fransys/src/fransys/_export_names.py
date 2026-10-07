"""The one home of the file name `fr.write` gives each export (decision 0033, root 0117)."""

from typing import TYPE_CHECKING

from fransys_model.derive import document_unit, location_node_designation
from fransys_model.vocab import DocumentPreset

from . import _subjects

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Document
    from fransys_model.vocab import Unit as ModelUnit


def export_name(
    model: Model,
    unit: Id[ModelUnit] | None,
    extension: str,
    *,
    kind: str | None = None,
    fragment: str | None = None,
) -> str:
    """`<prefix>[-<kind>][-<fragment>].<extension>` (decision 0033); an empty part is left out.

    The one place prefix, kind and fragment are joined; the prefix is `_subjects.export_prefix`.
    """
    joined = "-".join(
        part for part in (_subjects.export_prefix(model, unit), kind, fragment) if part
    )
    return f"{joined}.{extension}"


def document_export_name(model: Model, unit: Id[ModelUnit] | None, record: Document) -> str:
    """One document's PDF name, from its own subject, never its cover (decision 0033).

    Unit subject (`record.unit`, or `record.unit_name` via `derive.document_unit`): its own prefix.
    Location, item, SYSTEM: the write scope's; empty prefix gives bare `<cover-stem>.pdf` here.
    """
    document_own_unit = document_unit(model, record)
    if document_own_unit is not None:
        kind = "harness" if record.preset is DocumentPreset.HARNESS_DRAWING else None
        return export_name(model, document_own_unit, "pdf", kind=kind)
    if not _subjects.export_prefix(model, unit):
        return export_name(model, unit, "pdf", fragment=record.key[1])
    if record.location is not None:
        fragment = _subjects.fragment(location_node_designation(model, record.location))
        return export_name(model, unit, "pdf", fragment=fragment)
    if record.item is not None:
        return export_name(
            model, unit, "pdf", fragment=_subjects.export_ref(model, record.item, unit)
        )
    return export_name(model, unit, "pdf")
