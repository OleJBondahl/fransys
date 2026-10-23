"""A coil's contact image and a cross-reference label's partner places."""

from fransys_model.derive.contact_entries import (
    NO_PLACE,
    Entry,
    contact_entries,
    image_order,
)
from fransys_model.derive.contacts import owned_contacts
from fransys_model.derive.tag_text import item_tag_text
from fransys_model.derive.unused import function_is_unused
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Unit

CONTACTS_HEADED = "contacts.headed"  # a contact table sharing its column foot: heading line (0170)


def _in_image_order(entries: list[Entry]) -> list[str]:
    """The text of each contact entry, in image order."""
    return [text for *_, text in sorted(entries, key=image_order)]


def coil_heading(model: Model, coil: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """The heading line of the contact table of item `coil`: layout measures it first.

    It is the coil's own tag in the set drawn (`unit`), so heading and coil read the same.
    """
    return item_tag_text(model, coil, unit=unit)


def contact_marks(model: Model, function: Id[Function]) -> tuple[list[str], list[str]]:
    """The terminal pairs one contact function lists under NO and under NC, in image order.

    The marks of a contact image before the place is appended ("13-14", "COM-NO"): the one rule
    of which pairs a contact prints and in which column, so layout sizes a contact image over
    exactly the entries render prints.
    """
    no, nc = contact_entries(model, functions(model)[function])
    return _in_image_order(no), _in_image_order(nc)


def coil_image_cells(model: Model, coil: Id[Function]) -> tuple[list[str], list[str]]:
    """The NO and NC cells of `coil`'s contact table in image order.

    A contact no conductor reaches prints `<mark> NO_PLACE`, a reached
    contact prints its mark alone.
    """
    no, nc = list[Entry](), list[Entry]()
    for contact in owned_contacts(model, functions(model)[coil].item):
        suffix = f" {NO_PLACE}" if function_is_unused(model, contact) else ""
        one_no, one_nc = contact_entries(model, functions(model)[contact])
        no.extend((main, key, f"{mark}{suffix}") for main, key, mark in one_no)
        nc.extend((main, key, f"{mark}{suffix}") for main, key, mark in one_nc)
    return _in_image_order(no), _in_image_order(nc)
