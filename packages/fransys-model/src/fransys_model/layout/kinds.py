"""Layout: which kinds are authored hints and which are derived results (layout-namespace.md).

A new kind goes into exactly one of the tuples: the tests and `derived_layout_ids` go
by them. Each pass removes only its own tuple's kinds (CT5, Q3).
"""

from .formats import Profile, SheetFormat
from .hints import (
    GroupHint,
    OrderHint,
    PoleGroup,
    SymbolChoice,
)
from .house_export import DesignationForm, ExportForm
from .house_lists import Lists
from .house_text import (
    FrameForm,
    HarnessText,
    HouseProfile,
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
    GroupHint,
    OrderHint,
    PoleGroup,
    Profile,
    SheetFormat,
    SymbolChoice,
)
DERIVED_KINDS: tuple[type, ...] = (DrawingSet, LinkMarker, Page, PowerSymbol)
OVERVIEW_KINDS: tuple[type, ...] = (OverviewView, OverviewBox, OverviewLine)
# Written once by the facade (the symbol library, the settings tables), never authored, kept.
HOUSE_TEXT_KINDS: tuple[type, ...] = (
    DesignationForm,
    ExportForm,
    FrameForm,
    HarnessText,
    HouseProfile,
    Lists,
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
