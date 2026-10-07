"""The public reader of mates: one row per `Mate` of the model, at every level (model-0147)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import mates as mates_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

from .designation import connector_designation
from .natural_order import natural_key
from .rows import MateRow


def mates(model: Model) -> tuple[MateRow, ...]:
    """One `MateRow` per mate in `model`, sorted by `(a_designation, b_designation)`.

    A mate joins two connector or terminal functions, kept in the authored order of `d.mate`. A
    mate on a board and one between a plug and a unit's interface connector both appear, where
    `connector_rows` covers board connectors only. Each designation is the text the connector list
    prints at system level. Reach an item through the function.

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


@digest_cached(DIGEST_CACHE_SIZE)
def mate_partners(model: Model) -> frozendict[Id[Function], tuple[Id[Function], ...]]:
    """Each mated connector function with the functions mated to it, smallest id first."""
    found: dict[Id[Function], list[Id[Function]]] = {}
    for mate in mates_table(model).values():
        found.setdefault(mate.a, []).append(mate.b)
        found.setdefault(mate.b, []).append(mate.a)
    return frozendict({key: tuple(sorted(value)) for key, value in found.items()})
