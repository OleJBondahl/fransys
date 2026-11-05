"""The TERMINAL_LIST table with its drawn Bridge column (pdf-0007, 0008, 0011)."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    ends_without_jumpers,
    jumper_lanes,
    list_pdf_columns,
    list_pdf_heading,
)

from ._bridge import bridge_cell_typst, bridge_geometry
from ._lists_cells import _cell_typst, _kept_columns, _widths
from ._sizes import rule_of
from ._tables import table_source
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import BridgePieceRow, TerminalRow
    from fransys_model.kernel import Model

    from ._bridge import _BridgeMark
    from ._doc import BridgeInputs

_TERMINAL_SIDES = ("internal_ends", "external_ends")  # both unbounded text: `1fr` each (pdf-0008)


def _bridge_marks(rows: tuple[TerminalRow, ...]) -> tuple[tuple[_BridgeMark | None, ...], ...]:
    """The Bridge column's marks: derive's lanes for the rows' jumper groups, drawn."""
    groups = tuple(row.jumper_group for row in rows)
    return bridge_geometry(groups, jumper_lanes(groups))


def _row_values(model: Model, row: TerminalRow, data: tuple[str, ...]) -> tuple[object, ...]:
    """The cells of `row` under the printed `data` columns, the ends without their jumpers."""
    ends = dict(zip(_TERMINAL_SIDES, ends_without_jumpers(model, row), strict=True))
    return tuple(ends.get(name, getattr(row, name)) for name in data)


def _body(
    values: list[tuple[object, ...]],
    geometry: tuple[tuple[_BridgeMark | None, ...], ...],
    kept: tuple[int, ...],
    bridge: tuple[Mapping[str, BridgePieceRow] | None, float] | None,
) -> list[list[str]]:
    """The body cells: the kept data columns, then the Bridge cell (pieces, column width in mm) when `bridge`."""
    body = []
    for row_values, row_marks in zip(values, geometry, strict=True):
        cells = [_cell_typst(row_values[i]) for i in kept]
        if bridge:
            cells.append(bridge_cell_typst(row_marks, *bridge))
        body.append(cells)
    return body


def _terminal_table(
    model: Model,
    rows: tuple[TerminalRow, ...],
    headings: tuple[str, str],
    heading: tuple[str, str],
    bridge_inputs: BridgeInputs,
) -> str:
    """The TERMINAL_LIST table: data columns, then a Bridge column of placed marks (pdf-0049)."""
    if not rows:
        return ""
    data = list_pdf_columns(model, "terminal")
    geometry = _bridge_marks(rows)
    side_label = {"internal_ends": headings[0], "external_ends": headings[1]}
    values = [_row_values(model, row, data) for row in rows]
    kept = _kept_columns(values, len(data))  # empty columns are not drawn (pdf-0011)
    bridge = any(geometry)  # a strip with no jumper group has an all-empty Bridge column
    if not kept and not bridge:
        return ""
    headers = [side_label.get(data[i]) or list_pdf_heading(model, "terminal", data[i]) for i in kept] + ([bridge_inputs[0]] if bridge else [])
    body = _body(values, geometry, kept, bridge_inputs[1:] if bridge else None)
    widths = _widths([data[i] in _TERMINAL_SIDES for i in kept])
    if bridge:
        widths.append(f"{bridge_inputs[2]:g}mm")
    heads = [f"strong(text({literal(h)}))" for h in headers]
    return table_source(widths, heads, body, rule=rule_of(model), heading=heading)
