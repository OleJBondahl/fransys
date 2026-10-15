"""Layout: which kinds are authored hints and which are derived results (layout-namespace.md).

A new kind goes into exactly one of the four tuples: the tests and `derived_layout_ids` go
by them. Each pass removes only its own tuple's kinds (CT5, Q3).
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox, OpenCoreWire
from .diagram_results import DiagramBox, DiagramLine, DiagramMarker, DiagramSheet
from .external_results import ExternalOutline
from .formats import Profile, SheetFormat
from .harness_results import ConnectorBox, HarnessFanOut, HarnessLine, StubEnd
from .hints import (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    PageTitle,
    PoleGroup,
    SideHint,
    SymbolChoice,
)
from .overview_results import OverviewBox, OverviewLine, OverviewView
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
    PageTitle,
    PoleGroup,
    Profile,
    SheetFormat,
    SideHint,
    SymbolChoice,
)
DERIVED_KINDS: tuple[type, ...] = (
    ConnectorBox,
    DrawingSet,
    ExternalOutline,
    HarnessFanOut,
    HarnessLine,
    Label,
    LinkMarker,
    Outline,
    Page,
    PowerSymbol,
    Route,
    StubEnd,
    SymbolPlacement,
)
CABLE_KINDS: tuple[type, ...] = (CableBlock, CableBox, CoreWire, EndBox, OpenCoreWire)
DIAGRAM_KINDS: tuple[type, ...] = (DiagramSheet, DiagramBox, DiagramLine, DiagramMarker)
OVERVIEW_KINDS: tuple[type, ...] = (OverviewView, OverviewBox, OverviewLine)
