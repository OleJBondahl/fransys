"""Facet: supplier sourcing data on a `Part` (design/facets.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.templates import Part


@record(kind="facet.supply", subject="subject", unique=False)
class SupplyFacet:
    """One supplier's sourcing record for a `Part`; many per part are allowed.

    Example: the relay example `Part` carries one `SupplyFacet` for one distributor's
    part number and another for a second distributor. design/facets.md names this cardinality
    exception explicitly, unlike every other facet.
    """

    id: Id[SupplyFacet]
    key: AuthoringKey
    subject: Id[Part]
    supplier: str
    supplier_part_number: str
    note: str
    ext: frozendict[str, Value] = frozendict()
