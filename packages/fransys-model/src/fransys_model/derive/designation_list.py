"""The designation list: one row per item, terminals included, by printed designation."""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .designation import is_own_unit_root, printed_designation, reference_designation
from .designation_label import takes_parents_designation
from .lookups import item_description
from .order import natural_key
from .report_scope import _item_belongs, _require_unit
from .rows import DesignationRow


def designation_list(model: Model, *, unit: Id[Unit] | None = None) -> tuple[DesignationRow, ...]:
    """One `DesignationRow` per `Item`, terminals included, sorted by `(designation, id)`.

    `designation` is `printed_designation` (`"-X1:L1:1"`, `"-K1"`); `reference` is
    `reference_designation`. An accessory (`takes_parents_designation`) has no row.

    Args:
        model: The frozen model to read.
        unit: Keep only rows of this unit, keyword-only; its sole root has no row.

    Returns:
        One `DesignationRow` per item, sorted by `(designation, id)`.

    Raises:
        SchemaError: an item has no designation, or `unit` names no unit of `model`.
    """
    _require_unit(model, unit)
    rows = [
        DesignationRow(
            item=item.id,
            designation=printed_designation(model, item.id, unit=unit),
            reference=reference_designation(model, item.id, unit=unit),
            description=item_description(model, item.id),
        )
        for item in items(model).values()
        if (unit is None or _item_belongs(model, item.id, unit))
        and not takes_parents_designation(model, item.id)
        and not is_own_unit_root(model, item.id, unit)
    ]
    # a harness and its cable print one designation: the printed text breaks the tie, the id last
    return tuple(
        sorted(rows, key=lambda row: (natural_key(row.designation), row.description, row.item))
    )
