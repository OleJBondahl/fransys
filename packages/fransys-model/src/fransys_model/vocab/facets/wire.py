"""Facet: panel-wire attributes on a `Conductor` (design/facets.md)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.connectivity import Conductor


@record(kind="facet.wire", subject="subject", unique=True)
class WireFacet:
    """Colour, gauge, length and label of a `wire`-kind `Conductor`.

    Example: the panel wire from the relay coil's `A1` port to a terminal carries
    `colour="BU", gauge_mm2=Decimal("0.75"), length_mm=250, label="W1"`. Read by
    `derive.queries.wire_rows`.
    """

    id: Id[WireFacet]
    key: AuthoringKey
    subject: Id[Conductor]
    colour: str
    gauge_mm2: Decimal
    length_mm: int | None
    label: str | None
    ext: frozendict[str, Value] = frozendict()
