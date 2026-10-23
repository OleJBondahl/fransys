"""`style(library)`: the pens, dashes, sizes and grid the drawn values use (el-0004, SW5).

Every number is read from its one home (`print_sizes`, the build's `Library`, `REF_TINTS`) and
converted to a float only here. Only the label text size is listed: it is the one `svg` draws
with; a larger role joins with the switch that draws it.
"""

from typing import TYPE_CHECKING

from electrical_symbols import WIRING_GRID
from fransys_layout.drawing import Style, TextStyle, WireStyle
from fransys_model.derive.print_sizes import (
    DASH_GAP_MM,
    DASH_LONG_MM,
    JUNCTION_DOT_MM,
    LINE_RULE_MM,
    LINE_THICK_MM,
    LINE_THIN_MM,
    OUTLINE_DASHES_MM,
    SYMBOL_DASH_GAP_MM,
    SYMBOL_DASH_MM,
)

from .ref_tints import REF_TINTS

if TYPE_CHECKING:
    from electrical_symbols import Library

__all__ = ["style"]

_PEN_MM = {"NORMAL": float(LINE_THIN_MM), "THICK": float(LINE_THICK_MM)}  # by symdef Weight name
_SYMBOL_DASH = (float(SYMBOL_DASH_MM), float(SYMBOL_DASH_GAP_MM))


def _dashes() -> tuple[tuple[str, tuple[float, ...]], ...]:
    return (
        ("long", (float(DASH_LONG_MM), float(DASH_GAP_MM))),
        ("outline", tuple(float(dash) for dash in OUTLINE_DASHES_MM)),
        ("symbol", _SYMBOL_DASH),
    )


def style(library: Library) -> Style:
    """The `Style` of `library`: its font heights, wires, module and divisions (SETTINGS ST4)."""
    font = library.font
    assert font is not None  # noqa: S101 -- a build's library always carries its font
    return Style(
        tints=REF_TINTS,
        wires=tuple(
            (
                wire.id,
                WireStyle(
                    _PEN_MM[wire.weight.name], _SYMBOL_DASH if wire.style.name == "DASHED" else ()
                ),
            )
            for wire in library.wires
        ),
        texts=(("label", TextStyle(float(font.heights["smallest"]), font.family)),),
        dashes=_dashes(),
        line_thin_mm=float(LINE_THIN_MM),
        line_thick_mm=float(LINE_THICK_MM),
        line_rule_mm=float(LINE_RULE_MM),
        junction_dot_mm=float(JUNCTION_DOT_MM),
        muted_colour="grey",
        module_mm=float(library.grid.module_mm),
        wiring_grid=WIRING_GRID,
        g_per_module=library.grid.divisions_per_module,
    )
