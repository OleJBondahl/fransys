"""Geometry layer: units, boxes, the symbol-library adapter and text metrics (geometry.md 5)."""

from .boxes import Box, contains, hull, overlaps, pad, translate, union
from .clear import first_clear, push_clear
from .errors import GeometryError, HintError, LayoutError, SymbolPortError, UnknownSymbolError
from .exits import FACING_STEP, port_exit
from .flow import flow
from .follow import follow
from .legs import legs
from .meet import Span, boxes_meet, contains_point, meets
from .symbols import (
    GENERIC_BOX_KEY,
    OPPOSITE,
    Facing,
    Orientation,
    PortGeometry,
    SlotGeometry,
    SymbolGeometry,
    ThroughPath,
    generic_box_geometry,
    library_version,
    port_page_at,
    symbol_geometry,
)
from .text import text_width
from .units import (
    G_PER_MODULE,
    WIRING_GRID,
    Coord,
    Point,
    on_wiring_grid,
    snap_up,
    to_grid,
)

__all__ = (
    "FACING_STEP",
    "GENERIC_BOX_KEY",
    "G_PER_MODULE",
    "OPPOSITE",
    "WIRING_GRID",
    "Box",
    "Coord",
    "Facing",
    "GeometryError",
    "HintError",
    "LayoutError",
    "Orientation",
    "Point",
    "PortGeometry",
    "SlotGeometry",
    "Span",
    "SymbolGeometry",
    "SymbolPortError",
    "ThroughPath",
    "UnknownSymbolError",
    "boxes_meet",
    "contains",
    "contains_point",
    "first_clear",
    "flow",
    "follow",
    "generic_box_geometry",
    "hull",
    "legs",
    "library_version",
    "meets",
    "on_wiring_grid",
    "overlaps",
    "pad",
    "port_exit",
    "port_page_at",
    "push_clear",
    "snap_up",
    "symbol_geometry",
    "text_width",
    "to_grid",
    "translate",
    "union",
)
