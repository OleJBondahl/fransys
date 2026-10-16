"""The words that name a document's subject in a title block (model-0066)."""

from fransys_model.vocab import DocumentPreset, aspect_nodes
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

from .designation import item_designation, location_node_designation
from .document_unit import document_unit
from .drawing_text import unit_label
from .lookups import item_description

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
    if record.preset is DocumentPreset.SYSTEM:
        return ""
    item_id = record.item
    assert item_id is not None  # noqa: S101 -- Document.__post_init__ requires one of the three, or SYSTEM
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
