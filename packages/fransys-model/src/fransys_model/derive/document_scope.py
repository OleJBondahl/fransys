"""A document's scope: the one reader of what a `Document` selects from its model (model-0268).

The unit, location and item branches live here once; the pdf lists and drawings read the fields.
"""

from fransys_model.vocab.enums import DocumentPreset
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import DrawingSet
lazy from fransys_model.vocab.core import Item, Unit
lazy from fransys_model.vocab.document import Document

from .bom import bom_lines
from .cable_drawing import drawn_blocks
from .connectors import connector_items, unit_connector_items
from .document_sets import set_printers
from .document_undrawn import undrawn_items
from .document_unit import record_unit
from .drawn_wires import wire_harness_subjects
from .harness import harness_cables, reading_cables
from .memo import Memo
from .report_scope import unit_strips
from .rows_document import DocumentScope
from .structure import boards, items_at
from .wiring import terminal_strips
lazy from .rows import BomLine, HarnessCable

__all__ = ["document_bom_lines", "document_scope"]


def _cables(model: Model, document: Document, unit: Id[Unit] | None) -> tuple[HarnessCable, ...]:
    """The drawings' cables: the system's top-level, a unit's own, an item's, else none."""
    if document.preset is DocumentPreset.SYSTEM:
        return reading_cables(model, None)
    if unit is not None:
        return reading_cables(model, unit)
    return harness_cables(model, document.item) if document.item is not None else ()


def _harnesses(
    model: Model, document: Document, unit: Id[Unit] | None, cables: tuple[HarnessCable, ...]
) -> tuple[Id[Item], ...]:
    """The wired harnesses a unit document has, or an item document that has no cable."""
    if document.preset is DocumentPreset.SYSTEM:
        return ()
    if unit is None and (document.item is None or cables):
        return ()
    wired = set(wire_harness_subjects(model))
    return tuple(
        subject
        for block_unit, subject in drawn_blocks(model)
        if block_unit == unit
        and subject in wired
        and (unit is not None or subject == document.item)
    )


def _at_location(
    model: Model, document: Document, found: tuple[Id[Item], ...]
) -> tuple[Id[Item], ...]:
    """`found` kept to the items at the document's location, in `found`'s order."""
    if document.location is None:
        return ()
    at_location = set(items_at(model, document.location))
    return tuple(item for item in found if item in at_location)


def _strips(model: Model, document: Document, unit: Id[Unit] | None) -> tuple[Id[Item], ...]:
    """A unit's own strips, never a nested unit's, else the location's."""
    if unit is not None:
        return unit_strips(model, unit)
    return _at_location(model, document, terminal_strips(model))


def _connector_items(
    model: Model, document: Document, unit: Id[Unit] | None, undrawn: tuple[Id[Item], ...]
) -> tuple[Id[Item], ...]:
    """A unit's own connector items, else the location's less the undrawn; none for an item."""
    if document.item is not None:
        return ()
    if unit is not None:
        return unit_connector_items(model, unit)
    left_out = set(undrawn)
    found = _at_location(model, document, connector_items(model))
    return tuple(item for item in found if item not in left_out)


def _boards(model: Model, document: Document) -> tuple[Id[Item], ...]:
    """A board document's board; none for any other document."""
    item = document.item
    return (item,) if item is not None and item in boards(model) else ()


def _drawing_sets(model: Model, document: Document) -> tuple[Id[DrawingSet], ...]:
    """The drawing sets `document` prints, by set id: the one printer of each set (R331)."""
    return tuple(s for s, printer in set_printers(model).items() if printer == document.id)


def _document_scope(model: Model, document: Document) -> DocumentScope:
    """What `document` selects from `model`: its unit, cables, harnesses, BOM scope and lists."""
    unit = record_unit(model, document)
    cables = _cables(model, document, unit)
    harnesses = _harnesses(model, document, unit, cables)
    undrawn = undrawn_items(model, document, unit, harnesses)
    return DocumentScope(
        unit=unit,
        cables=cables,
        harnesses=harnesses,
        bom_location=document.location,
        bom_item=document.item,
        bom_without=undrawn,
        top_level=unit is None and document.preset is DocumentPreset.SYSTEM,
        strips=_strips(model, document, unit),
        connector_items=_connector_items(model, document, unit, undrawn),
        boards=_boards(model, document),
        drawing_sets=_drawing_sets(model, document),
    )


def _scope_of(model: Model, document: Id[Document]) -> DocumentScope:
    """What the document `document` (its id) selects from `model`: see `_document_scope`."""
    return _document_scope(model, documents(model)[document])


document_scope = Memo(_scope_of)


def document_bom_lines(model: Model, document: Id[Document]) -> tuple[BomLine, ...]:
    """The BOM lines of `document`: its `bom_scope` less the harness items it does not draw.

    `document` is the document's id.
    """
    scope = document_scope(model, document)
    return bom_lines(model, scope=scope.bom_scope, without=scope.bom_without)
