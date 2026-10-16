"""The terminal list's Bridge column: jumper lanes of placed Bridge mark images (pdf-0049).

render draws the `line` and the `tick` (render-0021); pdf places them in a row's cell and draws no
line of its own. `%` of the cell height is the row's own because the cell is `breakable: false`.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import bridge_piece_key, jumper_lane_count

from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import BridgePiece, JumperLanes

BRIDGE_COLUMN_WIDTH_MM = 15  # fixed column width


@dataclass(frozen=True, slots=True)
class _BridgeMark:
    """One row's mark in one lane: half-lines `top`/`bottom` (both: through), `tick`."""

    top: bool
    bottom: bool
    tick: bool


def bridge_geometry(
    groups: tuple[int | None, ...], lanes: JumperLanes
) -> tuple[tuple[_BridgeMark | None, ...], ...]:
    """One entry per row, a mark (or `None`) per lane; an empty tuple with no group."""
    rows: list[list[_BridgeMark | None]] = [[None] * jumper_lane_count(lanes) for _ in groups]
    for span in lanes.lanes:
        for index in range(span.first, span.last + 1):
            rows[index][span.lane] = _BridgeMark(
                top=index != span.first,
                bottom=index != span.last,
                tick=groups[index] == span.group,
            )
    return tuple(tuple(row) for row in rows)


def bridge_lane_x_mm(lane_count: int, gap_mm: float) -> tuple[float, ...]:
    """Each lane's x offset (mm): centred in the Bridge column, `gap_mm` (a line's width) apart."""
    centre = BRIDGE_COLUMN_WIDTH_MM / 2
    offset = (lane_count - 1) / 2
    return tuple(centre + (index - offset) * gap_mm for index in range(lane_count))


def piece_of(pieces: Mapping[str, BridgePiece] | None, piece: str) -> BridgePiece:
    """The Bridge mark `piece` render drew; a missing one is a caller error, never a blank."""
    key = bridge_piece_key(piece)
    if pieces is None or key not in pieces:
        msg = (
            f"no Bridge mark piece {key!r}: pass `fransys_render.bridge_pieces()` "
            "as `bridges` to `fransys_pdf.source`"
        )
        raise KeyError(msg)
    return pieces[key]


def _image(piece: BridgePiece, extent: str) -> str:
    return f'image(bytes({literal(piece.svg)}), format: "svg", {extent}, fit: "stretch")'


def _place(dx_mm: float, dy: str, image: str) -> str:
    return f"#place(top+left, dx: {dx_mm:g}mm, dy: {dy}, {image})\n"


def _bridge_mark_typst(
    mark: _BridgeMark | None, x_mm: float, line: BridgePiece, tick: BridgePiece
) -> str:
    """One lane's marks for one row as placed images; line `y` and height are % of the cell."""
    if mark is None:
        return ""
    parts = []
    if mark.top or mark.bottom:
        top, bottom = (0 if mark.top else 50), (100 if mark.bottom else 50)
        extent = f"width: {line.width_mm:g}mm, height: {bottom - top}%"
        parts.append(_place(x_mm - line.width_mm / 2, f"{top}%", _image(line, extent)))
    if mark.tick:
        extent = f"width: {tick.width_mm:g}mm, height: {tick.height_mm:g}mm"
        dy = f"50% - {tick.height_mm / 2:g}mm"
        parts.append(_place(x_mm - tick.width_mm / 2, dy, _image(tick, extent)))
    return "".join(parts)


def bridge_cell_typst(
    row_marks: tuple[_BridgeMark | None, ...], pieces: Mapping[str, BridgePiece] | None
) -> str:
    """One row's Bridge cell (pdf-0007, 0049): `breakable: false` scopes `%` to the row."""
    if not row_marks:
        return 'table.cell(inset: 0pt, text(""))'
    line, tick = piece_of(pieces, "line"), piece_of(pieces, "tick")
    xs = bridge_lane_x_mm(len(row_marks), line.width_mm)
    content = "".join(
        _bridge_mark_typst(mark, x, line, tick) for mark, x in zip(row_marks, xs, strict=True)
    )
    return f"table.cell(inset: 0pt, breakable: false)[{content}]"
