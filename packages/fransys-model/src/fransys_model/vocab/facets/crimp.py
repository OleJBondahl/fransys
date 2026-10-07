"""Facet: the crimp contacts fitted in a connector item's used pins (decision model-0170)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.core import Item
from fransys_model.vocab.templates import Part


@value
class ContactFit:
    """One contact part and the pin name it is fitted in; `pin=None` means every used pin."""

    pin: str | None
    part: Id[Part]


@record(kind="facet.contacts", subject="subject", unique=True)
class ContactsFacet:
    """The crimp contacts of a connector `Item`: one part for every used pin, or per pin name.

    Example: `d.device("P1", "DEMO-HSG-4M", contacts="DEMO-CRIMP-M")` carries one fit with
    `pin=None`. A fit that names a pin beats the `pin=None` fit for that pin. A contact part is
    a `Part` with no function, as a fuse link is.

    Which pins are used is never stored: `derive.contact_lines` reads the conductors that land
    (model-0170). Read by `bom_lines`, which counts a contact part once per used pin.
    """

    id: Id[ContactsFacet]
    key: AuthoringKey
    subject: Id[Item]
    fits: tuple[ContactFit, ...]
    ext: frozendict[str, Value] = frozendict()
