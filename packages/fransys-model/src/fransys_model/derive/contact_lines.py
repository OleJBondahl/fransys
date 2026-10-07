"""Crimp contacts: a connector item's used pins and the contact parts fitted in them."""

from fransys_model.vocab.enums import ConductorKind, FunctionKind
from fransys_model.vocab.facets import ContactsFacet
from fransys_model.vocab.tables import conductors, facets_of, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port
lazy from fransys_model.vocab.templates import Part

from .indexes import build_indexes

_LANDING = frozenset({ConductorKind.WIRE, ConductorKind.CORE, ConductorKind.LEAD})


def used_pins(model: Model, item: Id[Item]) -> tuple[Id[Port], ...]:
    """The ports of `item`'s connector functions where a WIRE, CORE or LEAD lands, in id order.

    The one definition of a used pin: a contact is crimped on the end of a wire, core or lead.
    """
    idx = build_indexes(model)
    table = conductors(model)
    return tuple(
        port
        for function in idx.functions_by_item.get(item, ())
        if functions(model)[function].kind is FunctionKind.CONNECTOR
        for port in idx.ports_by_function.get(function, ())
        if any(table[c].kind in _LANDING for c in idx.conductors_by_port.get(port, ()))
    )


def _fitted(facet: ContactsFacet, pin: str) -> Id[Part] | None:
    """The part fitted in pin `pin`: a fit that names the pin beats the one for every pin."""
    named = {fit.pin: fit.part for fit in facet.fits}
    return named.get(pin, named.get(None))


def contact_counts(model: Model) -> dict[Id[Part], dict[Id[Item], int]]:
    """Per contact part, per housing item, the number of used pins it is fitted in."""
    counts: dict[Id[Part], dict[Id[Item], int]] = {}
    for facet in facets_of(model, ContactsFacet).values():
        for port in used_pins(model, facet.subject):
            part = _fitted(facet, ports(model)[port].name)
            if part is not None:
                per_item = counts.setdefault(part, {})
                per_item[facet.subject] = per_item.get(facet.subject, 0) + 1
    return counts
