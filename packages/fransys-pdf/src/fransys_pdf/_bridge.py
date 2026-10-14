"""The terminal list's Bridge column: jumper groups as lanes of lines and ticks (pdf-0007)."""

from dataclasses import dataclass

from ._sizes import RULE

BRIDGE_COLUMN_WIDTH_MM = 15  # fixed column width
_BRIDGE_LANE_GAP_MM = 3  # lanes centred in the column, this far apart
_BRIDGE_TICK_HALF_WIDTH_MM = 1


@dataclass(frozen=True, slots=True)
class _BridgeMark:
    """One row's mark in one lane: half-lines `top`/`bottom` (both: through), `tick`."""

    top: bool
    bottom: bool
    tick: bool


def _bridge_spans(groups: tuple[int | None, ...]) -> dict[int, tuple[int, int]]:
    """Each jumper group's (first, last) row index in `groups`, 0-based."""
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for index, group in enumerate(groups):
        if group is None:
            continue
        first.setdefault(group, index)
        last[group] = index
    return {group: (first[group], last[group]) for group in first}


def _bridge_lanes(spans: dict[int, tuple[int, int]]) -> dict[int, int]:
    """Each group's lane in group-number order; overlapping row spans never share one."""
    lane_ends: list[int] = []  # lane_ends[lane] is the last row index that lane is used through
    lanes: dict[int, int] = {}
    for group in sorted(spans):
        first, last = spans[group]
        lane = next((i for i, end in enumerate(lane_ends) if end < first), None)
        if lane is None:
            lane = len(lane_ends)
            lane_ends.append(last)
        else:
            lane_ends[lane] = last
        lanes[group] = lane
    return lanes


def bridge_geometry(groups: tuple[int | None, ...]) -> tuple[tuple[_BridgeMark | None, ...], ...]:
    """One entry per row, a mark (or `None`) per lane; an empty tuple with no group."""
    spans = _bridge_spans(groups)
    lanes = _bridge_lanes(spans)
    lane_count = len(set(lanes.values()))  # distinct lanes used, not `len(lanes)` (one per group)
    rows: list[list[_BridgeMark | None]] = [[None] * lane_count for _ in groups]
    for group, (first, last) in spans.items():
        lane = lanes[group]
        for index in range(first, last + 1):
            rows[index][lane] = _BridgeMark(
                top=index != first, bottom=index != last, tick=groups[index] == group
            )
    return tuple(tuple(row) for row in rows)


def bridge_lane_x_mm(lane_count: int) -> tuple[float, ...]:
    """Each lane's x offset (mm): centred in the Bridge column, `_BRIDGE_LANE_GAP_MM` apart."""
    centre = BRIDGE_COLUMN_WIDTH_MM / 2
    offset = (lane_count - 1) / 2
    return tuple(centre + (index - offset) * _BRIDGE_LANE_GAP_MM for index in range(lane_count))


def _mm(value: float) -> str:
    """`value` as a Typst mm length: `10` not `10.0`, deterministic (source purity)."""
    return f"{value:g}"


def _bridge_mark_typst(mark: _BridgeMark | None, x_mm: float) -> str:
    """One lane's marks for one row as `#place(...)` lines; `y` is % of the cell."""
    if mark is None:
        return ""
    x = _mm(x_mm)
    segments = []
    if mark.top:
        segments.append(
            f"place(top+left, line(start: ({x}mm, 0%), end: ({x}mm, 50%), stroke: {RULE}))"
        )
    if mark.bottom:
        segments.append(
            f"place(top+left, line(start: ({x}mm, 50%), end: ({x}mm, 100%), stroke: {RULE}))"
        )
    if mark.tick:
        left, right = _mm(x_mm - _BRIDGE_TICK_HALF_WIDTH_MM), _mm(x_mm + _BRIDGE_TICK_HALF_WIDTH_MM)
        segments.append(
            f"place(top+left, line(start: ({left}mm, 50%), end: ({right}mm, 50%), stroke: {RULE}))"
        )
    return "".join(f"#{segment}\n" for segment in segments)


def bridge_cell_typst(row_marks: tuple[_BridgeMark | None, ...], lane_xs: tuple[float, ...]) -> str:
    """One row's Bridge cell (pdf-0007): `breakable: false` scopes `%` to the row; `inset: 0pt`."""
    if not row_marks:
        return 'table.cell(inset: 0pt, text(""))'
    content = "".join(
        _bridge_mark_typst(mark, x) for mark, x in zip(row_marks, lane_xs, strict=True)
    )
    return f"table.cell(inset: 0pt, breakable: false)[{content}]"
