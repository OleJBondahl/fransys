"""Where each contact of a coil sits once placed, as the coil's page reads it (CONTACT-TABLE)."""

lazy from collections.abc import Mapping

from fransys_model.derive.contact_image import table_contacts
from fransys_model.derive.frame_position import position_at
from fransys_model.layout import Membership, Page, layout_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["contact_places"]


def contact_places(
    model: Model, coil: Id[Function], own_page: Id[Page]
) -> Mapping[Id[Function], str]:
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
            places[row.function] = position_at(
                model, pages[own_page], pages[row.page], cell.column, cell.row
            )
    return places
