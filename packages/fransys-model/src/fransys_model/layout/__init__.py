"""Layout layer: `layout.*` kinds between `vocab` and `derive` (layout-namespace.md, decision 0009).

The records only; the engines that read and write them live outside this repo. Rules
for every kind here: it may reference `core` and `facet` ids and nothing references it
back; an authored kind (hint, rule parameter) has no coordinate or page-number field; a
derived kind (page, placement, route) is written only by a pass and carries
`produced_by`. A new kind goes into `AUTHORED_KINDS`, `DERIVED_KINDS`,
`OVERVIEW_KINDS` or `LIBRARY_KINDS`, which is what the tests and
`derived_layout_ids` go by.
"""

from .enums import (
    Corner,
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
    GroupHint,
    OrderHint,
    PoleGroup,
    SymbolChoice,
)
from .house_builders import HOUSE_TABLES, house_records
from .house_export import CSV_QUOTINGS, DesignationForm, ExportForm
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
from .kinds import (
    AUTHORED_KINDS,
    DERIVED_KINDS,
    HOUSE_TEXT_KINDS,
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
from .paper import PaperChoice, paper_choice, sheet_format_record
from .results import (
    POWER_SLOT,
    CrossReferencePartner,
    DrawingSet,
    LinkMarker,
    MarkerPair,
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
    tuning_of,
)

__all__ = [
    "AUTHORED_KINDS",
    "CSV_QUOTINGS",
    "DERIVED_KINDS",
    "HOUSE_TABLES",
    "HOUSE_TEXT_KINDS",
    "LIBRARY_KINDS",
    "OVERVIEW_KINDS",
    "POWER_SLOT",
    "SHEET_KINDS",
    "BoxKey",
    "Corner",
    "CrossReferencePartner",
    "DesignationForm",
    "DrawingLibrary",
    "DrawingSet",
    "ExportForm",
    "FrameCell",
    "FrameForm",
    "GroupHint",
    "HarnessText",
    "HouseProfile",
    "LayoutSheet",
    "LinkMarker",
    "Lists",
    "MarkerPair",
    "MarkerSide",
    "Membership",
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
    "PaperChoice",
    "PlacementView",
    "PoleGroup",
    "PowerSymbol",
    "Profile",
    "ReferenceText",
    "RevisionForm",
    "RevisionTableForm",
    "RoutePoint",
    "SheetFormat",
    "SheetKind",
    "Shown",
    "Side",
    "StarKind",
    "StubText",
    "SymbolChoice",
    "TitleBlockForm",
    "WireLabelText",
    "Words",
    "a2_sheet_format",
    "box_key",
    "default_profile",
    "default_sheet_format",
    "derived_layout_ids",
    "house_records",
    "layout_of",
    "line_key",
    "page_slice",
    "paper_choice",
    "profile_of",
    "profile_of_page",
    "ref_token",
    "sheet_for",
    "sheet_format_of",
    "sheet_format_record",
    "tuning_of",
    "view_key",
]
