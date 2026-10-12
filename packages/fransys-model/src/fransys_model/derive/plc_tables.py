"""The PLC list as tables: one per rack item, controller first, then its modules (model-0194)."""

from itertools import groupby

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Unit

from .designation import printed_designation
from .reports import plc_channel_pairs
from .rows import PlcTable


def plc_tables(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[PlcTable, ...]:
    """The rows of `plc_channel_rows`, one `PlcTable` per carrying item, in the same order.

    A controller's own channels form its table, then each module's follow in rack order; the
    items in no rack come last, one table each. An item with no channel has no table.
    `unit` and `context` are `plc_channel_rows`'s.

    Raises:
        SchemaError: as `plc_channel_rows`.
    """
    return tuple(
        PlcTable(
            item=item,
            designation=printed_designation(model, item, unit=unit),
            rows=tuple(row for _, row in group),
        )
        for item, group in groupby(
            plc_channel_pairs(model, unit=unit, context=context), key=lambda pair: pair[0]
        )
    )
