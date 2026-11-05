"""`style(library)`: the pens, dashes, sizes and grid the drawn values use (el-0004, SW5).

Every number is read from its one home (`print_sizes`, the build's `Library`, `REF_TINTS`) and
converted to a float only here. Only the label text size is listed: it is the one `svg` draws
with; a larger role joins with the switch that draws it.
"""

from typing import TYPE_CHECKING

from electrical_symbols import WIRING_GRID
from fransys_layout.drawing import Style, TextStyle, WireStyle

from .ref_tints import REF_TINTS

if TYPE_CHECKING:
    from electrical_symbols import Library

__all__ = ["style"]


def _dashes(library: Library) -> tuple[tuple[str, tuple[float, ...]], ...]:
    """The library's `[dash]` runs the drawn values name: `long`, the outline's `dash_dot`, the symbol's `dashed`."""
    names = (("long", "long"), ("outline", "dash_dot"), ("symbol", "dashed"))
    return tuple((name, tuple(float(mm) for mm in library.dash[table])) for name, table in names)


def style(library: Library) -> Style:
    """The `Style` of `library`: its font heights, wires, module and divisions (SETTINGS ST4)."""
    font = library.font
    dashes = _dashes(library)
    pens = {weight.name: float(mm) for weight, mm in library.lines.items()}
    return Style(
        tints=REF_TINTS,
        wires=tuple(
            (
                wire.id,
                WireStyle(pens[wire.weight.name], dict(dashes)["symbol"] if wire.style.name == "DASHED" else ()),
            )
            for wire in library.wires
        ),
        texts=(("label", TextStyle(float(font.heights["smallest"]), font.family)),),
        dashes=dashes,
        line_thin_mm=pens["NORMAL"],
        line_thick_mm=pens["THICK"],
        line_rule_mm=pens["RULE"],
        muted_colour="grey",
        module_mm=float(library.grid.module_mm),
        wiring_grid=WIRING_GRID,
        g_per_module=library.grid.divisions_per_module,
    )
