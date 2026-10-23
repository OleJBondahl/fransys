"""A coil's contact image and a cross-reference label's partner places."""

lazy from collections.abc import Mapping

from fransys_model.derive.actuated import actuated_group, lead_switch
from fransys_model.derive.contact_entries import (
    NO_PLACE,
    Entry,
    contact_entries,
    image_order,
)
from fransys_model.derive.contacts import owned_contacts
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.tag_text import item_tag_text
from fransys_model.derive.unused import function_is_unused
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Unit

CONTACTS_HEADED = "contacts.headed"  # a contact table sharing its column foot: heading line (0170)


def _in_image_order(entries: list[Entry]) -> list[str]:
    """The text of each contact entry, in image order."""
    return [text for *_, text in sorted(entries, key=image_order)]


def table_contacts(model: Model, function: Id[Function]) -> tuple[Id[Function], ...]:
    """The contacts the table under `function` lists: a coil's own, a lead switch's actuated group.

    The lead of an actuated group (`lead_switch`) owns the table of the group, as a coil does its
    contacts' (R468 T2); any other function owns none.
    """
    group = actuated_group(model, function)
    if group:
        return group if lead_switch(model, function) == function else ()
    if function_role(model, function).operator:
        return owned_contacts(model, functions(model)[function].item)
    return ()


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


def coil_image_cells(
    model: Model, coil: Id[Function], places: Mapping[Id[Function], str] | None = None
) -> tuple[list[str], list[str]]:
    """The NO and NC cells of `coil`'s contact table in image order.

    A contact no conductor reaches prints `<mark> NO_PLACE`. A reached contact prints its mark,
    then its place from `places` (`contact_places`) when it has one: before placement it has none.
    """
    no, nc = list[Entry](), list[Entry]()
    for contact in table_contacts(model, coil):
        suffix = f" {NO_PLACE}" if function_is_unused(model, contact) else ""
        if not suffix and places and contact in places:
            suffix = f" {places[contact]}"
        one_no, one_nc = contact_entries(model, functions(model)[contact])
        no.extend((main, key, f"{mark}{suffix}") for main, key, mark in one_no)
        nc.extend((main, key, f"{mark}{suffix}") for main, key, mark in one_nc)
    return _in_image_order(no), _in_image_order(nc)
