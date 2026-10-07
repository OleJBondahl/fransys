"""Layout: which kinds are authored hints and which are derived results (layout-namespace.md).

A new kind goes into exactly one of the four tuples: the tests and `derived_layout_ids` go
by them. Each pass removes only its own tuple's kinds (CT5, Q3).
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox
from .diagram_results import DiagramBox, DiagramLine, DiagramMarker, DiagramSheet
from .formats import Profile, SheetFormat
from .harness_results import ConnectorBox, HarnessFanOut, HarnessLine
from .hints import (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    SideHint,
    SymbolChoice,
)
from .results import (
    DrawingSet,
    Label,
    LinkMarker,
    Outline,
    Page,
    PowerSymbol,
    Route,
    SymbolPlacement,
)

AUTHORED_KINDS: tuple[type, ...] = (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    Profile,
    SheetFormat,
    SideHint,
    SymbolChoice,
)
DERIVED_KINDS: tuple[type, ...] = (
    ConnectorBox,
    DrawingSet,
    HarnessFanOut,
    HarnessLine,
    Label,
    LinkMarker,
    Outline,
    Page,
    PowerSymbol,
    Route,
    SymbolPlacement,
)
CABLE_KINDS: tuple[type, ...] = (CableBlock, CableBox, CoreWire, EndBox)
DIAGRAM_KINDS: tuple[type, ...] = (DiagramSheet, DiagramBox, DiagramLine, DiagramMarker)
