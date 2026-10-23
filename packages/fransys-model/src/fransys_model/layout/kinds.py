"""Layout: which kinds are authored hints and which are derived results (layout-namespace.md).

A new kind goes into exactly one of the tuples: the tests and `derived_layout_ids` go
by them. Each pass removes only its own tuple's kinds (CT5, Q3).
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox, OpenCoreWire
from .diagram_results import DiagramBox, DiagramLine, DiagramMarker, DiagramSheet
from .formats import Profile, SheetFormat
from .hints import (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    PageTitle,
    PinsBelowHint,
    PoleGroup,
    SideHint,
    SymbolChoice,
)
from .house_text import (
    ColourCodes,
    FrameForm,
    HarnessText,
    ReferenceText,
    RevisionForm,
    RevisionTableForm,
    StubText,
    TitleBlockForm,
    WireLabelText,
    Words,
)
from .library import DrawingLibrary
from .membership import Membership
from .overview_results import OverviewBox, OverviewLine, OverviewView
from .paper import PaperChoice
from .results import DrawingSet, LinkMarker, Page, PowerSymbol
from .sheets import LayoutSheet

AUTHORED_KINDS: tuple[type, ...] = (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    PageTitle,
    PinsBelowHint,
    PoleGroup,
    Profile,
    SheetFormat,
    SideHint,
    SymbolChoice,
)
DERIVED_KINDS: tuple[type, ...] = (DrawingSet, LinkMarker, Page, PowerSymbol)
CABLE_KINDS: tuple[type, ...] = (CableBlock, CableBox, CoreWire, EndBox, OpenCoreWire)
DIAGRAM_KINDS: tuple[type, ...] = (DiagramSheet, DiagramBox, DiagramLine, DiagramMarker)
OVERVIEW_KINDS: tuple[type, ...] = (OverviewView, OverviewBox, OverviewLine)
# Written once by the facade (the symbol library, the settings tables), never authored, kept.
HOUSE_TEXT_KINDS: tuple[type, ...] = (
    ColourCodes,
    FrameForm,
    HarnessText,
    ReferenceText,
    RevisionForm,
    RevisionTableForm,
    StubText,
    TitleBlockForm,
    WireLabelText,
    Words,
)
LIBRARY_KINDS: tuple[type, ...] = (DrawingLibrary, PaperChoice, *HOUSE_TEXT_KINDS)
# Sheets and frame membership rows: written by the facade's switches, never authored (model-0355).
# Not in DERIVED_KINDS: the schematic pass removes that tuple wholesale (write/__init__.py:57).
SHEET_KINDS: tuple[type, ...] = (LayoutSheet, Membership)
