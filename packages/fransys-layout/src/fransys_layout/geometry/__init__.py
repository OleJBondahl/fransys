"""Geometry layer: units, boxes, the facing sides and text metrics."""

from .adapter import text_width_g
from .boxes import Box, contains, hull, overlaps, pad, translate, union
from .errors import GeometryError, HintError, LayoutError, UnknownSymbolError
from .exits import FACING_STEP, port_exit
from .facing import OPPOSITE, Facing
from .flow import flow
from .follow import follow
from .legs import legs
from .meet import Span, boxes_meet, contains_point, meets, through
from .units import (
    G_PER_MODULE,
    PAGE_PAD,
    WIRING_GRID,
    Point,
    to_grid,
)

__all__ = (
    "FACING_STEP",
    "G_PER_MODULE",
    "OPPOSITE",
    "PAGE_PAD",
    "WIRING_GRID",
    "Box",
    "Facing",
    "GeometryError",
    "HintError",
    "LayoutError",
    "Point",
    "Span",
    "UnknownSymbolError",
    "boxes_meet",
    "contains",
    "contains_point",
    "flow",
    "follow",
    "hull",
    "legs",
    "meets",
    "overlaps",
    "pad",
    "port_exit",
    "text_width_g",
    "through",
    "to_grid",
    "translate",
    "union",
)
