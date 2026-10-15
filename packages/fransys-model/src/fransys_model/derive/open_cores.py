"""Open cores of a cable as rows (CC1, CC7; model-0204)."""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .core_pairs import _product_colours, open_core_is_spare
from .designation import port_designation, printed_designation, unit_list_context
from .far_ends import end_text
from .lookups import require
from .open_core_ends import _open_by_cable
from .rows_cores import OpenCoreRow
lazy from .reports import _require_unit


def open_core_rows(
    model: Model, cable: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[OpenCoreRow, ...]:
    """One `OpenCoreRow` per open core of `cable`, by core number.

    Args:
        model: The frozen model to read.
        cable: The cable item whose spares and one-ended screens to list.
        unit: The unit whose own document draws the cable, keyword-only; `None` is the whole model.

    Returns:
        The rows, sorted by core number; `()` for a cable with none.

    Raises:
        SchemaError: `cable` is no item, or `unit` is no unit of `model`.
    """
    require(items(model).get(cable), "item", cable)
    _require_unit(model, unit)
    context = unit_list_context(model, unit, None)
    colours = _product_colours(model, cable)
    rows = []
    for facet in _open_by_cable(model).get(cable, ()):
        colour = colours[facet.index - 1] if 1 <= facet.index <= len(colours) else ""
        if facet.at is None:
            text = ""
        elif unit is None:
            text = port_designation(model, facet.at)
        else:
            text = end_text(model, facet.at, context, unit)
        rows.append(
            OpenCoreRow(
                cable=cable,
                cable_designation=printed_designation(model, cable, unit=unit),
                index=facet.index,
                colour=colour,
                at=facet.at,
                at_designation=text,
                spare=open_core_is_spare(model, colour, facet.at),
            )
        )
    return tuple(rows)
