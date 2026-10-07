"""Layout: which kinds are authored hints and which are derived results (layout-namespace.md).

A new kind goes into exactly one of the three tuples: the tests and `derived_layout_ids` go
by them. Each pass removes only its own tuple's kinds (CT5, Q3).
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox
from .formats import Profile, SheetFormat
from .hints import BreakBefore, Chain, GroupHint, KeepTogether, OrderHint, SymbolChoice
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
    SymbolChoice,
)
DERIVED_KINDS: tuple[type, ...] = (
    DrawingSet,
    Label,
    LinkMarker,
    Outline,
    Page,
    PowerSymbol,
    Route,
    SymbolPlacement,
)
CABLE_KINDS: tuple[type, ...] = (CableBlock, CableBox, CoreWire, EndBox)
