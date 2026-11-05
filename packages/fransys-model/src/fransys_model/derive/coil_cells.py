"""A coil's contact table as texts: the cells the layout measures and the rows the el prints."""

from itertools import zip_longest
lazy from collections.abc import Mapping

from fransys_model.derive.contact_image import coil_image_cells, contact_marks, table_contacts
from fransys_model.derive.facts.house_settings import reference_text_of, word
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["coil_cells", "coil_table_texts"]


def _marks(model: Model, function: Id[Function]) -> tuple[list[str], list[str]]:
    """The NO and NC marks of every contact the coil's item owns."""
    no, nc = list[str](), list[str]()
    for contact in table_contacts(model, function):
        contact_no, contact_nc = contact_marks(model, contact)
        no.extend(contact_no)
        nc.extend(contact_nc)
    return no, nc


def _owns_table(model: Model, function: Id[Function]) -> bool:
    """Whether `function` owns a contact table: the one place the coil cells ask."""
    return bool(table_contacts(model, function))


def coil_cells(model: Model, function: Id[Function]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """A table owner's NO and NC cells, "{mark} {width_sample}" each; none for another function."""
    if not _owns_table(model, function):
        return (), ()
    no, nc = _marks(model, function)
    sample = reference_text_of(model).width_sample
    return tuple(f"{m} {sample}" for m in no), tuple(f"{m} {sample}" for m in nc)


def coil_table_texts(model: Model, coil: Id[Function], places: Mapping[Id[Function], str] | None = None) -> tuple[tuple[str, ...], ...]:
    """A coil's contact table as texts: the column titles, then a (NO, NC) cell pair per row.

    `places` (`contact_places`) gives each reached contact its printed place; none before placement.

    A column that ran out leaves an empty cell; a coil with no cells has none (an empty tuple).
    """
    if not _owns_table(model, coil):
        return ()
    no, nc = coil_image_cells(model, coil, places)
    rows = [(a, b) for a, b in zip_longest(no, nc, fillvalue="")]
    return ((word(model, "no"), word(model, "nc")), *rows) if rows else ()
