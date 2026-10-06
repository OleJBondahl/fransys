"""Layout layer: `layout.*` kinds between `vocab` and `derive` (layout-namespace.md, decision 0009).

The records only; the engines that read and write them live outside this repo. Rules
for every kind here: it may reference `core` and `facet` ids and nothing references it
back; an authored kind (hint, rule parameter) has no coordinate or page-number field; a
derived kind (page, placement, route) is written only by a pass and carries
`produced_by`. A new kind goes into `AUTHORED_KINDS` or `DERIVED_KINDS`, which is what
the tests and `derived_layout_ids` go by.
"""

from .enums import LabelKind, MarkerSide, Orientation, PageRole, PlacementView, Side, StarKind
from .formats import Profile, SheetFormat, default_profile, default_sheet_format
from .hints import (
    BreakBefore,
    Chain,
    ChainEntry,
    GroupHint,
    KeepTogether,
    OrderHint,
    SymbolChoice,
)
from .kinds import AUTHORED_KINDS, DERIVED_KINDS
from .page_slices import page_slice
from .results import (
    POWER_SLOT,
    CrossReferencePartner,
    DrawingSet,
    Label,
    LinkMarker,
    Outline,
    Page,
    PageGroup,
    PowerSymbol,
    Route,
    RoutePoint,
    SymbolPlacement,
)
from .tables import derived_layout_ids, layout_of, profile_of, sheet_format_of

__all__ = [
    "AUTHORED_KINDS",
    "DERIVED_KINDS",
    "POWER_SLOT",
    "BreakBefore",
    "Chain",
    "ChainEntry",
    "CrossReferencePartner",
    "DrawingSet",
    "GroupHint",
    "KeepTogether",
    "Label",
    "LabelKind",
    "LinkMarker",
    "MarkerSide",
    "OrderHint",
    "Orientation",
    "Outline",
    "Page",
    "PageGroup",
    "PageRole",
    "PlacementView",
    "PowerSymbol",
    "Profile",
    "Route",
    "RoutePoint",
    "SheetFormat",
    "Side",
    "StarKind",
    "SymbolChoice",
    "SymbolPlacement",
    "default_profile",
    "default_sheet_format",
    "derived_layout_ids",
    "layout_of",
    "page_slice",
    "profile_of",
    "sheet_format_of",
]
