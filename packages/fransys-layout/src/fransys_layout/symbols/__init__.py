"""Layout's symdef layer (SB11, layout-0316): the one place `fransys_layout` reads symdef.

It measures a symbol once per allowed orientation, copies the fields into the core's plain
values and does no arithmetic of its own. The placement core stays on integers.
"""

from .frame import frame_cell, frame_extent
from .markers import fitted_marker, fitted_marker_views, marker_rule, marker_views, with_marker
from .outline import outline_room
from .shape import LibrarySymbol, Shape, SymbolLibrary, library_symbol, ports_at_one_node, stretched_body, symbol_shape
from .slots import ink_boxes, measured_slots
from .table import TableAsk
from .text import line_pitch, text_room_on, text_width_g
from .views import Ask, Views, symbol_views, turned_view

__all__ = (
    "Ask",
    "LibrarySymbol",
    "Shape",
    "SymbolLibrary",
    "TableAsk",
    "Views",
    "fitted_marker",
    "fitted_marker_views",
    "frame_cell",
    "frame_extent",
    "ink_boxes",
    "library_symbol",
    "line_pitch",
    "marker_rule",
    "marker_views",
    "measured_slots",
    "outline_room",
    "ports_at_one_node",
    "stretched_body",
    "symbol_shape",
    "symbol_views",
    "text_room_on",
    "text_width_g",
    "turned_view",
    "with_marker",
)
