"""Facet: a wire whose row the author could not state (model-0260)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.connectivity import Conductor


@value
class RowSpec:
    """A wiring row's colour and, when the table states one, its cross-section in mm2."""

    colour: str
    gauge_mm2: Decimal | None


@record(kind="facet.wire_row_hint", subject="subject", unique=True)
class WireRowHint:
    """A `wire`-kind `Conductor` with no `WireFacet` yet: the table its row is read from.

    Example: a series from a PLC terminal to a channel reaches no rail when written, so it hints
    `rows` (the wiring table in force, keyed by `WiringRow` value) and no facet; the
    `resolve_wire_rows` pass picks the row from the nets and writes the `WireFacet`, or reports
    `WIRE_ROW_UNRESOLVED`. `gauge_mm2` is a size the call gave for every wire (it wins over a
    row's size); `label` goes to the facet. The pass removes no record: it adds the facet.
    """

    id: Id[WireRowHint]
    key: AuthoringKey
    subject: Id[Conductor]
    rows: frozendict[str, RowSpec]
    gauge_mm2: Decimal | None = None
    label: str | None = None
    ext: frozendict[str, Value] = frozendict()
