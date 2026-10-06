"""The public reader of mates: one row per `Mate` of the model, at every level (model-0147)."""

from fransys_model.vocab.tables import mates as mates_table
lazy from fransys_model.kernel import Model

from .designation import connector_designation
from .natural_order import natural_key
from .rows import MateRow


def mates(model: Model) -> tuple[MateRow, ...]:
    """One `MateRow` per mate in `model`, sorted by `(a_designation, b_designation)`.

    A mate joins two connector functions, kept in the authored order of `d.mate`. A mate on a board
    and one between a plug and a unit's interface connector both appear, where `connector_rows`
    covers board connectors only. Each designation is the text the connector list prints at system
    level. Reach an item through the function.

    Raises:
        SchemaError: a mated function is not of `model`, or its item has no designation.
    """
    rows = (
        MateRow(
            a=record.a,
            b=record.b,
            a_designation=connector_designation(model, record.a),
            b_designation=connector_designation(model, record.b),
        )
        for record in mates_table(model).values()
    )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                natural_key(row.a_designation),
                natural_key(row.b_designation),
                row.a,
                row.b,
            ),
        )
    )
