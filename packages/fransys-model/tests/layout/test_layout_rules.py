"""The layout field tables and construction rules, beyond the
skeletons."""

from typing import Any

from layout_examples import (
    drawing_set,
    drawn_function,
    function_id,
    group_node,
    page,
    sheet_format,
)

from fransys_model import layout
from fransys_model.kernel import (
    Draft,
    Id,
    Model,
    Origin,
    freeze,
)
from fransys_model.layout import (
    MarkerSide,
    Orientation,
    PageRole,
    PlacementView,
    Side,
    StarKind,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import ConductorKind, PortBoundary

_ORIGIN = Origin(file="test_layout_rules.py", line=1, note="fixture")
_LOW: Id[Any] = Id(kind="port", value="1" * 32)
_HIGH: Id[Any] = Id(kind="port", value="9" * 32)
_CONDUCTOR: Id[Any] = Id(kind="conductor", value="3" * 32)


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _plant() -> tuple[Any, ...]:
    """The engineering and layout records the derived test records refer to."""
    ports = tuple(
        Port(
            id=port,
            key=("plant", "port", str(number)),
            function=function_id("c"),
            template=None,
            name=str(number),
            boundary=PortBoundary.GENERIC,
        )
        for number, port in enumerate((_LOW, _HIGH))
    )
    conductor = Conductor(
        id=_CONDUCTOR,
        key=("plant", "wire"),
        a=_LOW,
        b=_HIGH,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    return (
        *drawn_function(),
        *ports,
        conductor,
        group_node(),
        sheet_format(),
        drawing_set(),
        page(),
    )


# ---- enums --------------------------------------------------------------------------------

_ENUMS = {
    Orientation: {"R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"},
    PageRole: {"POWER", "CONTROL", "SIGNAL"},
    MarkerSide: {"OWNER", "USER"},
    PlacementView: {"FUNCTION", "ITEM", "PIN"},
    StarKind: {"OFF", "REF", "BRANCH"},
    Side: {"N", "E", "S", "W"},
}


# ---- the layout field tables
# -----------------------------------------------------------

_COMMON = {"id", "key", "ext"}
_FIELDS: dict[type, set[str]] = {
    layout.OverviewView: {"unit", "strip", "produced_by"},
    layout.OverviewBox: {
        "view",
        "subject",
        "stub",
        "dashed",
        "x",
        "y",
        "width",
        "height",
        "tabs",
        "produced_by",
    },
    layout.OverviewLine: {
        "view",
        "a",
        "b",
        "kind",
        "via",
        "points",
        "text_x",
        "text_y",
        "produced_by",
    },
    layout.GroupHint: {"function", "group"},
    layout.OrderHint: {"before", "after"},
    layout.PoleGroup: {"functions", "selector"},
    layout.SymbolChoice: {"function", "template", "part", "kind", "symbol", "port_map"},
    layout.SheetFormat: {
        "name",
        "width_mm",
        "height_mm",
        "content_x_mm",
        "content_y_mm",
        "content_width_mm",
        "content_height_mm",
        "frame_columns",
        "frame_rows",
        "module_mm",
    },
    layout.Profile: {
        "unit",
        "sheet_format",
        "hide_unused_pins",
    },
    layout.DrawingSet: {"location", "unit", "number", "produced_by"},
    layout.Page: {"drawing_set", "number", "role", "sheet_format", "groups", "produced_by"},
    layout.LinkMarker: {
        "page",
        "port",
        "side",
        "partner",
        "x",
        "y",
        "width",
        "height",
        "produced_by",
        "box_x",
        "lead",
        "stub_extra",
        "via_x",
        "via_y",
        "star",
        "far",
        "carrier",
        "facing",
        "vertical",
        "wrap_at",
    },
    layout.PowerSymbol: {
        "port",
        "page",
        "symbol",
        "x",
        "y",
        "orientation",
        "produced_by",
    },
}


_PROFILE_ID: Id[Any] = Id(kind="layout.profile", value="8" * 32)


# ---- ordered entries ----------------------------------------------------------------------


# ---- labels -------------------------------------------------------------------------------


# ---- input of the wrong shape is left for freeze ------------------------------------------


# ---- from_data ----------------------------------------------------------------------------


# ---- accessors ----------------------------------------------------------------------------


# ---- guards, one by one -------------------------------------------------------------------

_MIXED: Any = "x"
