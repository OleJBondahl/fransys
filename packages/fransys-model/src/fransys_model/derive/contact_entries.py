"""A coil's contact image entries: what each contact lists, their order, the bare ones.

`derive.drawing_text` builds the image and `contact_marks` from these.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.contacts import changeover_throws, link_state, owned_contacts
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.pole_lists import poles_of
from fransys_model.derive.unused import function_is_unused
from fransys_model.vocab import function_poles, marking_key
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions, internal_links, port_templates, ports
lazy from fransys_model.derive.facts.roles import function_role, link_role
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Port

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.vocab.templates import PortTemplate

# What a contact image prints where a contact is drawn nowhere
NO_PLACE = "N/A"

# A contact with up to this many ports is a pair (or one pole), listed after a larger one
PAIR = 2

# A contact image entry `(main, key, mark)` (`image_order`)
type Entry = tuple[bool, int | str, str]

# An entry's `image_order` key
type EntryOrder = tuple[bool, tuple[tuple[int, int, str], ...], str]

# `contact_list_key`'s value: three poles or more first, then the first entry's order
type ListKey = tuple[bool, EntryOrder | tuple[()]]


def contact_entries(model: Model, function: Function) -> tuple[list[Entry], list[Entry]]:
    """One contact function's NO and NC entries as `(main, key, mark)`, see `image_order`."""
    no, nc = list[Entry](), list[Entry]()
    role = function_role(model, function.id)
    if role.contact and not role.plain_contact:  # a switch
        return _switch_entries(model, function)
    if not role.plain_contact:  # a spares-only table's lone partner is its coil
        return no, nc
    if role.changeover:
        # a changeover in both columns, by the part's throw roles: the common with each
        # make port (NO) and with each break port (NC), the names as the part prints them
        for throws in changeover_throws(model, function.id):
            common = printed_name(model, throws.common)
            key = int(common) if common.isdigit() else common
            for column, ends in ((no, throws.makes), (nc, throws.breaks)):
                column.extend((True, key, f"{common}-{printed_name(model, e)}") for e in ends)
        return no, nc
    pairs = _poles(model, function)
    target = nc if function.kind is FunctionKind.CONTACT_NC else no
    target.extend((_is_main(a, b), _key(a), a if a == b else f"{a}-{b}") for a, b in pairs)
    return no, nc


def _switch_entries(model: Model, function: Function) -> tuple[list[Entry], list[Entry]]:
    """A switch's entries: a pole closed at rest lists under NC, any other under NO (model-0237)."""
    no, nc = list[Entry](), list[Entry]()
    own = _own_templates(model, function)
    templates = {t: port_templates(model)[t] for t in own if t is not None}
    for link in internal_links(model).values():
        if (
            link.a not in templates
            or link.b not in templates
            or not link_role(model, link.id).switched
        ):
            continue
        (pole,) = function_poles(function.kind, [link], templates)
        a, b = (printed_name(model, own[end.id].id) for end in pole.ends)
        closed = link_state(model, function.id, link.id) == "rest"
        (nc if closed else no).append((_is_main(a, b), _key(a), f"{a}-{b}"))
    return no, nc


def _own_templates(model: Model, function: Function) -> dict[Id[PortTemplate] | None, Port]:
    """The function's ports by their port template."""
    return {p.template: p for p in ports(model).values() if p.function == function.id}


def _is_main(line: str, load: str) -> bool:
    """A pole is main when both pins are single-digit numbers (IEC 60947-1), else auxiliary."""
    return len(line) == 1 and len(load) == 1 and line != load and line.isdigit() and load.isdigit()


def _key(name: str) -> int | str:
    """A printed terminal number as an int, any other printed name as it is."""
    return int(name) if name.isdigit() else name


def _poles(model: Model, function: Function) -> list[tuple[str, str]]:
    """A contact's printed `(line, load)` pole names; a one-pin pole repeats its pin."""
    own = _own_templates(model, function)
    templates = {t: port_templates(model)[t] for t in own if t is not None}
    return [
        (printed_name(model, own[a.id].id), printed_name(model, own[b.id].id))
        for a, b in (pole.ends for pole in poles_of(model, templates))
    ]


def printed_name(model: Model, port: Id[Port]) -> str:
    """A contact port's name as a contact image prints it: the "/L1"-style suffix stripped."""
    return ports(model)[port].name.split("/")[0]


def image_order(entry: Entry) -> EntryOrder:
    """A contact image entry's order: main first, then numbered terminals, then named commons."""
    # an entry is `(main, key, text)`; `key` is the terminal number, or the common's name when it
    # is no number: named commons sort after every numbered one, by name, then by text
    main, key, text = entry
    return (not main, marking_key(str(key)), text)


def spare_entries(
    model: Model, item: Id[Item], shown: Collection[Id[Function]]
) -> tuple[list[Entry], list[Entry]]:
    """The entries, `<mark> NO_PLACE`, of the bare contacts `item` owns not in `shown`."""
    no, nc = list[Entry](), list[Entry]()
    for function in (functions(model)[f] for f in owned_contacts(model, item) if f not in shown):
        if function_is_unused(model, function.id):
            spare_no, spare_nc = contact_entries(model, function)
            no.extend((main, key, f"{mark} {NO_PLACE}") for main, key, mark in spare_no)
            nc.extend((main, key, f"{mark} {NO_PLACE}") for main, key, mark in spare_nc)
    return no, nc


def contact_list_key(model: Model, function: Id[Function]) -> ListKey:
    """The key a contact list sorts its contacts by: a 3-pole-plus first, then the first entry.

    The caller breaks a tie by the function id.
    """
    no, nc = contact_entries(model, functions(model)[function])
    first = min(map(image_order, (*no, *nc)), default=())
    return (len(build_indexes(model).ports_by_function.get(function, ())) <= PAIR, first)
