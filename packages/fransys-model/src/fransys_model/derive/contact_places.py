"""Where each contact of a coil, and each conductor end of a document, sits once placed (CONTACT-TABLE, RING-OUT)."""

lazy from collections.abc import Mapping

from fransys_model.derive.contact_image import table_contacts
from fransys_model.derive.document_pages import drawn_pages
from fransys_model.derive.facts.house_settings import frame_form_of, reference_text_of
from fransys_model.derive.frame_labels import cell_labels
from fransys_model.derive.frame_position import position_text
from fransys_model.derive.page_reference_text import pdf_page, position_at
from fransys_model.layout import Membership, Page, Shown, layout_of, sheet_format_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function
lazy from fransys_model.vocab.document import Document

__all__ = ["conductor_places", "contact_places"]


def contact_places(model: Model, coil: Id[Function], own_page: Id[Page]) -> Mapping[Id[Function], str]:
    """The printed place of each contact of `coil`'s item that a page shows, read from `own_page`.

    It reads the `layout.membership` rows a laid model holds; the text is `position_at`'s, so a
    same-page contact prints its cell and another page or set prints its page. A contact no page
    shows has none.
    """
    wanted = set(table_contacts(model, coil))
    pages = layout_of(model, Page)
    places: dict[Id[Function], str] = {}
    for row in layout_of(model, Membership).values():
        if row.function in wanted and row.page is not None and row.function not in places:
            cell = row.cell
            places[row.function] = position_at(model, pages[own_page], pages[row.page], cell.column, cell.row)
    return places


def conductor_places(model: Model, document: Id[Document]) -> Mapping[tuple[Id[Conductor], str], str]:
    """The printed place (`p3:4B`) of each conductor end a drawn page of `document` shows, by (conductor, `render_id` of its port).

    It reads the conductor-end `layout.membership` rows (the port is the key's tag before the conductor id); a drawn
    end wins over a reference marker. An end no page of the document shows has none.
    """
    pages = {page.id: page for page in drawn_pages(model, document)}
    refs, frame = reference_text_of(model), frame_form_of(model)
    rows = [row for row in layout_of(model, Membership).values() if row.conductor is not None and row.page in pages]
    places: dict[tuple[Id[Conductor], str], str] = {}
    for wanted in (Shown.DRAWN, Shown.REFERENCE):
        for row in rows:
            if row.shown is wanted and row.conductor is not None and row.page is not None:
                page = pages[row.page]
                labels = cell_labels(frame, sheet_format_of(model, page.sheet_format).frame_rows, row.cell.column, row.cell.row)
                places.setdefault((row.conductor, row.key[-3]), position_text(refs, pdf_page(model, page), labels))
    return places
