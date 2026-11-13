"""Geometry layer: units, boxes, the facing sides and text metrics."""

from .adapter import text_width_g
from .boxes import Box, contains, overlaps, translate
from .errors import GeometryError, HintError, LayoutError, UnknownSymbolError
from .exits import FACING_STEP, port_exit
from .facing import OPPOSITE, Facing
from .flow import flow
from .follow import follow
from .legs import legs
from .meet import Span, contains_point, meets, through
from .units import (
    PAGE_PAD,
    WIRING_GRID,
    Point,
)

__all__ = (
    "FACING_STEP",
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
    "contains",
    "contains_point",
    "flow",
    "follow",
    "legs",
    "meets",
    "overlaps",
    "port_exit",
    "text_width_g",
    "through",
    "translate",
)
