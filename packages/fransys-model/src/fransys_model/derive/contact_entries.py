"""A coil's contact image entries (C19): what each contact lists, their order, the bare ones.

`derive.drawing_text` builds the image and `contact_marks` from these.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.accessory_blocks import CONTACT_KINDS
from fransys_model.derive.contacts import changeover_throws, owned_contacts
from fransys_model.derive.unused import function_is_unused
from fransys_model.vocab import function_poles, unlinked_poles
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions, internal_links, port_templates, ports

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item, Port

# What a contact image prints where a contact is drawn nowhere (V1)
NO_PLACE = "N/A"

# A contact image entry `(main, key, mark)` (`image_order`)
type Entry = tuple[bool, int | str, str]


def contact_entries(model: Model, function: Function) -> tuple[list[Entry], list[Entry]]:
    """One contact function's NO and NC entries as `(main, key, mark)`, see `image_order`."""
    no, nc = list[Entry](), list[Entry]()
    if function.kind not in CONTACT_KINDS:  # a spares-only table's lone partner is its coil
        return no, nc
    if function.kind is FunctionKind.CONTACT_CO:
        # a changeover in both columns, by the part's throw roles (CS5): the common with each
        # make port (NO) and with each break port (NC), the names as the part prints them
        for throws in changeover_throws(model, function.id):
            common = printed_name(model, throws.common)
            key = int(common) if common.isdigit() else common
            for column, ends in ((no, throws.makes), (nc, throws.breaks)):
                column.extend((True, key, f"{common}-{printed_name(model, e)}") for e in ends)
        return no, nc
    pairs = _poles(model, function)
    target = nc if function.kind is FunctionKind.CONTACT_NC else no
    target.extend((_is_main(a, b), _key(a), f"{a}-{b}") for a, b in pairs)
    return no, nc


def _is_main(line: str, load: str) -> bool:
    """A pole is main when both pins are single-digit numbers (IEC 60947-1), else auxiliary."""
    return len(line) == 1 and len(load) == 1 and line.isdigit() and load.isdigit()


def _key(name: str) -> int | str:
    """A printed terminal number as an int, any other printed name as it is."""
    return int(name) if name.isdigit() else name


def _poles(model: Model, function: Function) -> list[tuple[str, str]]:
    """A contact's printed `(line, load)` pole names (F4); with no pole link, marking order."""
    own = {p.template: p for p in ports(model).values() if p.function == function.id}
    templates = {t: port_templates(model)[t] for t in own if t is not None}
    links = [
        link
        for link in internal_links(model).values()
        if link.a in templates and link.b in templates
    ]
    found = function_poles(function.kind, links, templates)
    if found:
        return [
            (printed_name(model, own[a.id].id), printed_name(model, own[b.id].id))
            for a, b in (pole.ends for pole in found)
        ]
    digits = {
        p.template: printed_name(model, p.id)
        for p in own.values()
        if p.template is not None and printed_name(model, p.id).isdigit()
    }
    return [
        (digits[pole.ends[0].id], digits[pole.ends[1].id])
        for pole in unlinked_poles(templates[t] for t in digits)
    ]


def printed_name(model: Model, port: Id[Port]) -> str:
    """A contact port's name as a contact image prints it: the "/L1"-style suffix stripped."""
    return ports(model)[port].name.split("/")[0]


def image_order(entry: Entry) -> tuple[bool, bool, int, str, str]:
    """A contact image entry's order: main first, then numbered terminals, then named commons."""
    # an entry is `(main, key, text)`; `key` is the terminal number, or the common's name when it
    # is no number: named commons sort after every numbered one, by name, then by text
    main, key, text = entry
    return (not main, isinstance(key, str), key if isinstance(key, int) else 0, str(key), text)


def spare_entries(
    model: Model, item: Id[Item], shown: Collection[Id[Function]]
) -> tuple[list[Entry], list[Entry]]:
    """V1: the entries, `<mark> NO_PLACE`, of the bare contacts `item` owns not in `shown`."""
    no, nc = list[Entry](), list[Entry]()
    for function in (functions(model)[f] for f in owned_contacts(model, item) if f not in shown):
        if function_is_unused(model, function.id):
            spare_no, spare_nc = contact_entries(model, function)
            no.extend((main, key, f"{mark} {NO_PLACE}") for main, key, mark in spare_no)
            nc.extend((main, key, f"{mark} {NO_PLACE}") for main, key, mark in spare_nc)
    return no, nc
