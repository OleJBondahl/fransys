"""Layout layer: `layout.*` kinds between `vocab` and `derive` (layout-namespace.md, decision 0009).

The records only; the engines that read and write them live outside this repo. Rules
for every kind here: it may reference `core` and `facet` ids and nothing references it
back; an authored kind (hint, rule parameter) has no coordinate or page-number field; a
derived kind (page, placement, route) is written only by a pass and carries
`produced_by`. A new kind goes into `AUTHORED_KINDS`, `DERIVED_KINDS`, `CABLE_KINDS`,
`DIAGRAM_KINDS`, `OVERVIEW_KINDS` or `LIBRARY_KINDS`, which is what the tests and
`derived_layout_ids` go by.
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox, OpenCoreWire, PinCell
from .diagram_results import BoxRef, DiagramBox, DiagramLine, DiagramMarker, DiagramSheet, TabCell
from .enums import (
    BlockRow,
    BoxKind,
    Corner,
    EndStyle,
    MarkerSide,
    Orientation,
    PageRole,
    PlacementView,
    SheetKind,
    Shown,
    Side,
    StarKind,
)
from .formats import (
    Profile,
    SheetFormat,
    a2_sheet_format,
    default_profile,
    default_sheet_format,
)
from .hints import (
    BreakBefore,
    Chain,
    ChainEntry,
    GroupHint,
    KeepTogether,
    OrderHint,
    PageTitle,
    PinsBelowHint,
    PoleGroup,
    SideHint,
    SymbolChoice,
)
from .kinds import (
    AUTHORED_KINDS,
    CABLE_KINDS,
    DERIVED_KINDS,
    DIAGRAM_KINDS,
    LIBRARY_KINDS,
    OVERVIEW_KINDS,
    SHEET_KINDS,
)
from .library import DrawingLibrary
from .membership import FrameCell, Membership
from .overview_keys import BoxKey, box_key, line_key, ref_token, view_key
from .overview_ref import OverviewMode, OverviewRef, OverviewRefKind
from .overview_results import OverviewBox, OverviewLine, OverviewTab, OverviewView
from .page_slices import page_slice
from .paper import PaperChoice
from .results import (
    POWER_SLOT,
    CrossReferencePartner,
    DrawingSet,
    LinkMarker,
    Page,
    PageGroup,
    PowerSymbol,
    RoutePoint,
)
from .sheets import LayoutSheet
from .tables import (
    derived_layout_ids,
    layout_of,
    profile_of,
    profile_of_page,
    sheet_for,
    sheet_format_of,
)

__all__ = [
    "AUTHORED_KINDS",
    "CABLE_KINDS",
    "DERIVED_KINDS",
    "DIAGRAM_KINDS",
    "LIBRARY_KINDS",
    "OVERVIEW_KINDS",
    "POWER_SLOT",
    "SHEET_KINDS",
    "BlockRow",
    "BoxKey",
    "BoxKind",
    "BoxRef",
    "BreakBefore",
    "CableBlock",
    "CableBox",
    "Chain",
    "ChainEntry",
    "CoreWire",
    "Corner",
    "CrossReferencePartner",
    "DiagramBox",
    "DiagramLine",
    "DiagramMarker",
    "DiagramSheet",
    "DrawingLibrary",
    "DrawingSet",
    "EndBox",
    "EndStyle",
    "FrameCell",
    "GroupHint",
    "KeepTogether",
    "LayoutSheet",
    "LinkMarker",
    "MarkerSide",
    "Membership",
    "OpenCoreWire",
    "OrderHint",
    "Orientation",
    "OverviewBox",
    "OverviewLine",
    "OverviewMode",
    "OverviewRef",
    "OverviewRefKind",
    "OverviewTab",
    "OverviewView",
    "Page",
    "PageGroup",
    "PageRole",
    "PageTitle",
    "PaperChoice",
    "PinCell",
    "PinsBelowHint",
    "PlacementView",
    "PoleGroup",
    "PowerSymbol",
    "Profile",
    "RoutePoint",
    "SheetFormat",
    "SheetKind",
    "Shown",
    "Side",
    "SideHint",
    "StarKind",
    "SymbolChoice",
    "TabCell",
    "a2_sheet_format",
    "box_key",
    "default_profile",
    "default_sheet_format",
    "derived_layout_ids",
    "layout_of",
    "line_key",
    "page_slice",
    "profile_of",
    "profile_of_page",
    "ref_token",
    "sheet_for",
    "sheet_format_of",
    "view_key",
]
