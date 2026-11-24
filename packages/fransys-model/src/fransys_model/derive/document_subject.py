"""The words that name a document's subject in a title block (model-0066)."""

from fransys_model.vocab import aspect_nodes
from fransys_model.vocab.tables import documents, projects
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document
lazy from fransys_model.vocab.core import Unit, UnitRelease

from .designation import location_node_designation
from .document_unit import document_unit
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
    """The heading's subject: location or unit label; the Project's title for SYSTEM ("" with no Project).

    `document` is the document's id.
    """
    record = documents(model)[document]
    if record.location is not None:
        node = aspect_nodes(model)[record.location]
        return f"{node.label} {node.description}"
    unit = document_unit(model, document)
    if unit is not None:
        return unit_label(model, unit)
    return next((project.title for project in projects(model).values()), "")


def scope_path(model: Model, document: Id[Document]) -> str:
    """The title block's Scope cell: a place's full `+R+S1` path, a unit's label, else empty.

    The path stands alone; the page title and the heading carry the place's description. A system
    document's scope is empty: the title cell already prints the Project's title.

    `document` is the document's id.
    """
    record = documents(model)[document]
    if record.location is None:
        return "" if document_unit(model, document) is None else subject_label(model, document)
    return location_node_designation(model, record.location)
