"""The one order of block diagram sheets: the reading (the absolute one first), then number."""

from fransys_model.kernel import render_id
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Unit

lazy from .rows_sheet import DiagramSheet

__all__ = ["diagram_sheet_order_key", "diagram_unit"]


def diagram_unit(sheet: DiagramSheet) -> Id[Unit] | None:
    """The reading of `sheet`: its unit, `None` for the absolute one; the one read of the field."""
    return sheet.unit


def diagram_sheet_order_key(sheet: DiagramSheet) -> tuple[str, int]:
    """Sort key of a sheet: its reading's render id (`""` for the absolute one), then number."""
    unit = diagram_unit(sheet)
    return ("" if unit is None else render_id(unit), sheet.number)
