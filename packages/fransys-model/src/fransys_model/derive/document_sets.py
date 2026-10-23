"""The one document that prints each drawing set (R331): exactly one, never two.

Over units only (R361, R363): (1) a set prints on the nearest documented enclosing unit, the design
root counting as one (a top-level set prints on the document whose subject is its own place, and
never climbs through places); (2) else on the documented unit that feeds it; (3) else it has no
printer and `check_unprinted_sets` warns. A set in a documented unit never takes a place document.
"""

from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab.tables import documents, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Unit
lazy from fransys_model.vocab.document import Document

from .document_fed import fed_items
from .document_unit import record_unit
from .lookups import item_location, unit_chain
from .memo import Memo

__all__ = ["printing_document", "set_group", "set_printers", "set_unit"]


def set_unit(drawing_set: DrawingSet) -> Id[Unit] | None:
    """The unit `drawing_set` draws; none at the top level."""
    return drawing_set.unit


def _subjects(
    model: Model,
) -> tuple[dict[Id[Unit], Id[Document]], dict[Id[AspectNode], Id[Document]]]:
    """The first document of each unit and of each location (a location document wins)."""
    by_unit: dict[Id[Unit], Id[Document]] = {}
    by_location: dict[Id[AspectNode], Id[Document]] = {}
    for document in documents(model).values():
        if document.location is not None:
            by_location.setdefault(document.location, document.id)
        elif (unit := record_unit(model, document)) is not None:
            by_unit.setdefault(unit, document.id)
    return by_unit, by_location


def _printer_of_unit(
    model: Model, unit: Id[Unit], by_unit: dict[Id[Unit], Id[Document]]
) -> Id[Document] | None:
    """The document of the nearest unit above `unit` (itself first) that has one."""
    return next((by_unit[u] for u in unit_chain(model, unit) if u in by_unit), None)


def _fed_locations(
    model: Model, by_unit: dict[Id[Unit], Id[Document]]
) -> dict[Id[AspectNode], Id[Document]]:
    """Each location of an item some unit's strips feed, to the first document that prints it."""
    found: dict[Id[AspectNode], Id[Document]] = {}
    for unit in units(model):
        document = _printer_of_unit(model, unit, by_unit)
        if document is None:
            continue
        for item in fed_items(model, unit):
            if (location := item_location(model, item)) is not None:
                found.setdefault(location, document)
    return found


type _Printing = tuple[
    dict[Id[Unit], Id[Document]],
    dict[Id[AspectNode], Id[Document]],
    dict[Id[AspectNode], Id[Document]],
]


def _context(model: Model) -> _Printing:
    """The documents of units, of locations, and of the locations fed from a unit's strips."""
    by_unit, by_location = _subjects(model)
    return by_unit, by_location, _fed_locations(model, by_unit)


_context_of = Memo(_context)


def _unit_printer(model: Model, unit: Id[Unit]) -> Id[Document] | None:
    """The document of the nearest unit above `unit` (itself first) that has one."""
    return _printer_of_unit(model, unit, _context_of(model)[0])


def printing_document(
    model: Model, unit: Id[Unit] | None, location: Id[AspectNode] | None
) -> Id[Document] | None:
    """The one document printing the set of `unit` at `location`; none if no document does."""
    _, by_location, fed = _context_of(model)
    if unit is not None:
        return _unit_printer(model, unit)
    return by_location.get(location) or fed.get(location)


def set_group(
    model: Model, unit: Id[Unit] | None, location: Id[AspectNode] | None
) -> Id[Document] | Id[Unit] | None:
    """What a set's rank counts among (R331): the unit document that prints it, else its unit.

    A set a location document prints keeps `None` (the top-level sets count together), so a
    document prints only sets of one group and no page label repeats in its PDF.
    """
    _, by_location, fed = _context_of(model)
    if unit is not None:
        return _unit_printer(model, unit) or unit
    return None if location in by_location else fed.get(location)


def _printers(model: Model) -> dict[Id[DrawingSet], Id[Document]]:
    """Each drawing set that a document prints, to that document."""
    found: dict[Id[DrawingSet], Id[Document]] = {}
    for drawing_set in layout_of(model, DrawingSet).values():
        document = printing_document(model, set_unit(drawing_set), drawing_set.location)
        if document is not None:
            found[drawing_set.id] = document
    return found


set_printers = Memo(_printers)
