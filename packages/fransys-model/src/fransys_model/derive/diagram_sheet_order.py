"""The one order of block diagram sheets: the reading (the absolute one first), then number."""

from fransys_model.kernel import render_id
lazy from fransys_model.layout import DiagramSheet

__all__ = ["diagram_sheet_order_key"]


def diagram_sheet_order_key(sheet: DiagramSheet) -> tuple[str, int]:
    """Sort key of a sheet: its reading's render id (`""` for the absolute one), then number."""
    return ("" if sheet.unit is None else render_id(sheet.unit), sheet.number)
