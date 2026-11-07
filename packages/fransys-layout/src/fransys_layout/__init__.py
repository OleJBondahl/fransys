"""Layout engines for Fransys: geometry <- stages <- lint <- engines."""

from .geometry import Facing, HintError
from .options import LayoutOptions, Side, TextKind, TextPlacement
lazy from .engines.cable import CableLayout, PlacedBlock, PlacedEnd, PlacedWire, lay_out_cables
lazy from .engines.diagram import (
    DiagramBox,
    DiagramLayout,
    DiagramLine,
    DiagramTab,
    PlacedDiagram,
    PlacedMarker,
    PlacedSheet,
    lay_out_diagrams,
)
lazy from .engines.overview import lay_out_overview
lazy from .lint.codes import FINDING_CODES

__all__ = (
    "FINDING_CODES",
    "CableLayout",
    "DiagramBox",
    "DiagramLayout",
    "DiagramLine",
    "DiagramTab",
    "Facing",
    "HintError",
    "LayoutOptions",
    "PlacedBlock",
    "PlacedDiagram",
    "PlacedEnd",
    "PlacedMarker",
    "PlacedSheet",
    "PlacedWire",
    "Side",
    "TextKind",
    "TextPlacement",
    "lay_out_cables",
    "lay_out_diagrams",
    "lay_out_overview",
)
