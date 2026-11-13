"""The words that name a document's subject in a title block (model-0066)."""

from fransys_model.vocab import aspect_nodes
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document
lazy from fransys_model.vocab.core import Unit, UnitRelease

from .designation import item_designation, location_node_designation
from .document_unit import document_unit
from .lookups import item_description
from .unit_release import unit_release


def release_name(release: UnitRelease) -> str:
    """A release's title, else its name when the title is empty."""
    return release.title or release.name


def unit_label(model: Model, unit: Id[Unit]) -> str:
    """What a drawing, a cover or a title block prints for a unit.

    The unit's release title (`derive.unit_release`), else its name when the title is empty.
    """
    return release_name(unit_release(model, unit))


__all__ = ["scope_path", "subject_label"]


def subject_label(model: Model, document: Id[Document]) -> str:
    """The heading's subject: location, unit or item label; "" for SYSTEM.

    `document` is the document's id.
    """
    record = documents(model)[document]
    if record.location is not None:
        node = aspect_nodes(model)[record.location]
        return f"{node.label} {node.description}"
    unit = document_unit(model, document)
    if unit is not None:
        return unit_label(model, unit)
    item_id = record.item
    if item_id is None:
        return ""
    return f"{item_designation(model, item_id)} {item_description(model, item_id)}"


def scope_path(model: Model, document: Id[Document]) -> str:
    """The title block's Scope cell: a place's full `+R+S1` path, else the subject.

    The path stands alone; the page title and the heading carry the place's description.

    `document` is the document's id.
    """
    record = documents(model)[document]
    if record.location is None:
        return subject_label(model, document)
    return location_node_designation(model, record.location)
