"""Facet: engineering-unit scaling of an analog PLC function (facets.md and examples.md)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Function


@record(kind="facet.scaling", subject="subject", unique=True)
class ScalingFacet:
    """The raw-to-engineering-unit range of an analog `Function`.

    Example: the design/examples.md 11 transmitter scales raw `4..20` to
    `eng_min=Decimal("0"), eng_max=Decimal("5")` metres, `unit="m"`. Read by
    `derive.queries.plc_channel_rows`.
    """

    id: Id[ScalingFacet]
    key: AuthoringKey
    subject: Id[Function]
    unit: str
    raw_min: int
    raw_max: int
    eng_min: Decimal
    eng_max: Decimal
    ext: frozendict[str, Value] = frozendict()
