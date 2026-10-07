"""Layout layer: `layout.*` kinds between `vocab` and `derive` (layout-namespace.md, decision 0009).

The records only; the engines that read and write them live outside this repo. Rules
for every kind here: it may reference `core` and `facet` ids and nothing references it
back; an authored kind (hint, rule parameter) has no coordinate or page-number field; a
derived kind (page, placement, route) is written only by a pass and carries
`produced_by`. A new kind goes into `AUTHORED_KINDS`, `DERIVED_KINDS`, `CABLE_KINDS` or
`DIAGRAM_KINDS`, which
is what the tests and `derived_layout_ids` go by.
"""

from .cable_results import CableBlock, CableBox, CoreWire, EndBox, PinCell
from .diagram_results import BoxRef, DiagramBox, DiagramLine, DiagramMarker, DiagramSheet, TabCell
from .enums import (
    BlockRow,
    BoxKind,
    EndStyle,
    LabelKind,
    MarkerSide,
    Orientation,
    PageRole,
    PlacementView,
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
from .harness_results import (
    BoxCell,
    BoxText,
    ConnectorBox,
    FanLeg,
    HarnessFanOut,
    HarnessLine,
)
from .hints import (
    BreakBefore,
    Chain,
    ChainEntry,
    GroupHint,
    KeepTogether,
    OrderHint,
    SideHint,
    SymbolChoice,
)
from .kinds import AUTHORED_KINDS, CABLE_KINDS, DERIVED_KINDS, DIAGRAM_KINDS
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
from .tables import derived_layout_ids, layout_of, profile_of, sheet_for, sheet_format_of

__all__ = [
    "AUTHORED_KINDS",
    "CABLE_KINDS",
    "DERIVED_KINDS",
    "DIAGRAM_KINDS",
    "POWER_SLOT",
    "BlockRow",
    "BoxCell",
    "BoxKind",
    "BoxRef",
    "BoxText",
    "BreakBefore",
    "CableBlock",
    "CableBox",
    "Chain",
    "ChainEntry",
    "ConnectorBox",
    "CoreWire",
    "CrossReferencePartner",
    "DiagramBox",
    "DiagramLine",
    "DiagramMarker",
    "DiagramSheet",
    "DrawingSet",
    "EndBox",
    "EndStyle",
    "FanLeg",
    "GroupHint",
    "HarnessFanOut",
    "HarnessLine",
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
    "PinCell",
    "PlacementView",
    "PowerSymbol",
    "Profile",
    "Route",
    "RoutePoint",
    "SheetFormat",
    "Side",
    "SideHint",
    "StarKind",
    "SymbolChoice",
    "SymbolPlacement",
    "TabCell",
    "a2_sheet_format",
    "default_profile",
    "default_sheet_format",
    "derived_layout_ids",
    "layout_of",
    "page_slice",
    "profile_of",
    "sheet_for",
    "sheet_format_of",
]
