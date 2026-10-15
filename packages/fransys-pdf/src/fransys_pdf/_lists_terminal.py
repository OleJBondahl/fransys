"""The TERMINAL_LIST table with its drawn Bridge column (pdf-0007, 0008, 0011)."""

from typing import TYPE_CHECKING

from fransys_model.derive import TERMINAL_COLUMNS, TERMINAL_LABELS, ends_without_jumpers

from ._bridge import BRIDGE_COLUMN_WIDTH_MM, bridge_cell_typst, bridge_geometry, bridge_lane_x_mm
from ._lists_cells import _cell_typst, _humanise, _kept_columns, _widths
from ._tables import table_source
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.derive import TerminalRow
    from fransys_model.kernel import Model

_TERMINAL_DATA = TERMINAL_COLUMNS[:-1]  # designation, group, index, internal_ends, external_ends
_TERMINAL_SIDES = ("internal_ends", "external_ends")  # both unbounded text: `1fr` each (pdf-0008)


def _terminal_table(
    model: Model,
    rows: tuple[TerminalRow, ...],
    headings: tuple[str, str] = (
        TERMINAL_LABELS["internal_ends"],
        TERMINAL_LABELS["external_ends"],
    ),
    *,
    title: str = "",
    label: str = "",
) -> str:
    """The TERMINAL_LIST table: data columns, then a drawn Bridge column (pdf-0007, 0008, 0011)."""
    if not rows:
        return ""
    geometry = bridge_geometry(tuple(row.jumper_group for row in rows))
    side_label = {"internal_ends": headings[0], "external_ends": headings[1]}
    values = []
    for row in rows:
        ends = dict(
            zip(("internal_ends", "external_ends"), ends_without_jumpers(model, row), strict=True)
        )
        values.append(tuple(ends.get(name, getattr(row, name)) for name in _TERMINAL_DATA))
    kept = _kept_columns(values, len(_TERMINAL_DATA))  # empty columns are not drawn (pdf-0011)
    bridge = any(geometry)  # a strip with no jumper group has an all-empty Bridge column
    if not kept and not bridge:
        return ""
    headers = [side_label.get(_TERMINAL_DATA[i]) or _humanise(_TERMINAL_DATA[i]) for i in kept] + (
        ["Bridge"] if bridge else []
    )
    body = []
    for row_values, row_marks in zip(values, geometry, strict=True):
        cells = [_cell_typst(row_values[i]) for i in kept]
        if bridge:
            cells.append(bridge_cell_typst(row_marks, bridge_lane_x_mm(len(row_marks))))
        body.append(cells)
    widths = _widths([_TERMINAL_DATA[i] in _TERMINAL_SIDES for i in kept])
    if bridge:
        widths.append(f"{BRIDGE_COLUMN_WIDTH_MM}mm")
    heads = [f"strong(text({literal(h)}))" for h in headers]
    return table_source(widths, heads, body, title=title, label=label)
