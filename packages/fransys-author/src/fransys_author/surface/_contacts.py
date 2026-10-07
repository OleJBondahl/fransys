"""`d.device(..., contacts=)`: the crimp contacts fitted in a connector device (HA8)."""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_author._keys import scoped, spliced
from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_model.kernel import make_id
from fransys_model.vocab import ContactFit, ContactsFacet, FunctionKind

if TYPE_CHECKING:
    from fransys_author.handles import Item
    from fransys_author.surface.design import Design


def _pins(design: Design, mpn: str) -> list[str]:
    """The pin names of the connector functions of housing `mpn`; a refusal when it has none."""
    catalogue = design._engine._design._catalogue
    bundle = catalogue.bundle(catalogue.find(mpn))
    kinds = {f.id: f.kind for f in bundle.function_templates}
    ports = bundle.port_templates
    pins = sorted(p.name for p in ports if kinds[p.function] is FunctionKind.CONNECTOR)
    if not pins:
        msg = f"contacts= needs a connector part; {mpn!r} has no connector function"
        raise AuthorError(msg)
    return pins


def validate(design: Design, mpn: str, contacts: str | Mapping[str, str] | None) -> None:
    """Refuse `contacts` that the housing `mpn` cannot take, before the device is made."""
    if contacts is None:
        return
    pins = _pins(design, mpn)
    find = design._engine._design._catalogue.find
    if isinstance(contacts, str):
        find(contacts)
        return
    if not contacts:
        msg = "contacts= is an empty mapping; give an MPN, or a pin to MPN mapping"
        raise AuthorError(msg)
    bad = sorted(set(contacts) - set(pins))
    if bad:
        msg = f"contacts= names pin {bad[0]!r}, which {mpn!r} lacks; pins: {', '.join(pins)}"
        raise AuthorError(msg)
    for contact in contacts.values():
        find(contact)


def fit(design: Design, item: Item, contacts: str | Mapping[str, str] | None) -> None:
    """Write the `ContactsFacet` of `item` for `contacts`; nothing for `None`."""
    if contacts is None:
        return
    scope = design._engine
    find = scope._design._catalogue.find
    pairs = [(None, contacts)] if isinstance(contacts, str) else sorted(contacts.items())
    fits = tuple(ContactFit(pin=pin, part=find(mpn).id) for pin, mpn in pairs)
    key = scoped(scope._prefix, "contacts", spliced(item.key))
    facet = ContactsFacet(id=make_id(ContactsFacet, key), key=key, subject=item.id, fits=fits)
    scope._design._add(facet, caller_origin())
