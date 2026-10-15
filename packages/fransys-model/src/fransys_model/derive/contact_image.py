"""A coil's contact image and a cross-reference label's partner places."""

from typing import cast
lazy from collections.abc import Mapping

from fransys_model.derive.contact_entries import (
    Entry,
    contact_entries,
    image_order,
    spare_entries,
)
from fransys_model.derive.frame_position import cell, position_between
from fransys_model.derive.tag_text import item_tag_text
from fransys_model.derive.view_placements import placements_by_function_page
from fransys_model.kernel import Id, Model
from fransys_model.layout import (
    CrossReferencePartner,
    DrawingSet,
    Label,
    Page,
    layout_of,
)
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.tables import functions, ports

CONTACTS_HEADED = "contacts.headed"  # a contact table sharing its column foot: heading line (0170)
CONTACT_SLOTS = ("contacts", CONTACTS_HEADED)


def _partner_row(model: Model, page: Page, port: Id[Port]) -> str:
    """`port`'s function's placement row on `page`, standing in for the function's own `y`.

    Neither partner record stores a `y`, so this is a coarse frame cell, not a precise position.
    It is the function's own placement, not the exact port's, so callers read the same one.
    """
    function = ports(model)[port].function
    placement = placements_by_function_page(model)[function, page.id]
    return cell(model, page, 0, placement.y)[1]


def _partner_place(
    model: Model, pages: Mapping[Id[Page], Page], own_page: Page, partner: CrossReferencePartner
) -> str:
    """Where `partner` stands as `own_page` reads it: its page and `x`, its function's row."""
    page = pages[partner.page]
    return position_between(
        model, own_page, page, partner.x, _partner_row(model, page, partner.port)
    )


def cross_reference_text(model: Model, label: Label) -> str:
    """What `label` says about its cross-reference partners.

    Read from the persisted `label.partners`, which carry the `x` and `page` layout resolved.
    Across drawing sets the prefix is the partner's location path below `label`'s; texts dedupe.
    """
    pages = layout_of(model, Page)
    own_page = pages[label.page]
    return " ".join(
        dict.fromkeys(_partner_place(model, pages, own_page, p) for p in label.partners)
    )


def _in_image_order(entries: list[Entry]) -> list[str]:
    """The text of each contact entry, in image order."""
    return [text for *_, text in sorted(entries, key=image_order)]


def contact_image(model: Model, label: Label) -> tuple[list[str], list[str]]:
    """A coil's contact image, its NO and NC entries.

    Per contact of the coil's item, its terminal pairs by number ("13-14", the "/L1" suffixes
    stripped) and where it is drawn ("/3.7"); main contacts (more than one pair) first, then
    by terminal number. A changeover's entries come from its throw roles (`changeover_throws`),
    the names as printed, named commons after numbered ones. A contact no conductor reaches
    is listed too, its pair and `NO_PLACE`, whatever `hide_unused_pins` says.
    """
    no, nc = image_entries(model, label)
    return [text for text, _ in no], [text for text, _ in nc]


def image_entries(
    model: Model, label: Label
) -> tuple[list[tuple[str, Id[Port] | None]], list[tuple[str, Id[Port] | None]]]:
    """`contact_image`'s entries, each with the partner port whose contact it names (model-0216).

    A spare contact's entry has no partner (`None`). This is the one build of the image: the text
    lists of `contact_image` and the rows of `derive.contact_rows` are both read from it.
    """
    pages = layout_of(model, Page)
    own_page = pages[label.page]
    no, nc = list[tuple[Entry, Id[Port] | None]](), list[tuple[Entry, Id[Port] | None]]()
    for partner in label.partners:
        function = functions(model)[ports(model)[partner.port].function]
        where = _partner_place(model, pages, own_page, partner)
        no_marks, nc_marks = contact_entries(model, function)
        no.extend(((main, key, f"{mark} {where}"), partner.port) for main, key, mark in no_marks)
        nc.extend(((main, key, f"{mark} {where}"), partner.port) for main, key, mark in nc_marks)
    shown = {ports(model)[partner.port].function for partner in label.partners}
    spare_no, spare_nc = spare_entries(
        model, functions(model)[cast("Id[Function]", label.function)].item, shown
    )
    no.extend((entry, None) for entry in spare_no)
    nc.extend((entry, None) for entry in spare_nc)
    return _in_order_with_ports(no), _in_order_with_ports(nc)


def _in_order_with_ports(
    entries: list[tuple[Entry, Id[Port] | None]],
) -> list[tuple[str, Id[Port] | None]]:
    """The text and partner port of each contact entry, in image order."""
    return [(entry[2], port) for entry, port in sorted(entries, key=lambda e: image_order(e[0]))]


def contact_heading(model: Model, label: Label) -> str:
    """The heading line of a contact table that shares its column foot: its coil's tag, "-K1".

    A lone table has none (""): layout marks the tables of one foot with the `CONTACTS_HEADED` slot.
    """
    if label.slot != CONTACTS_HEADED:
        return ""
    coil = functions(model)[cast("Id[Function]", label.function)].item
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[label.page].drawing_set].unit
    return coil_heading(model, coil, unit=unit)


def coil_heading(model: Model, coil: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """The text `contact_heading` prints for the table of item `coil`: layout measures it first.

    It is the coil's own tag in the set drawn (`unit`), so heading and coil read the same.
    """
    return item_tag_text(model, coil, unit=unit)


def contact_marks(model: Model, function: Id[Function]) -> tuple[list[str], list[str]]:
    """The terminal pairs one contact function lists under NO and under NC, in image order.

    The marks of `contact_image` before the place is appended ("13-14", "COM-NO"): the one rule
    of which pairs a contact prints and in which column, so layout sizes a contact image over
    exactly the entries render prints.
    """
    no, nc = contact_entries(model, functions(model)[function])
    return _in_image_order(no), _in_image_order(nc)
