"""The layout field tables and construction rules, beyond the
skeletons."""

from typing import Any

import pytest
from layout_examples import (
    PRODUCED_BY,
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
    FreezeError,
    Id,
    Model,
    Origin,
    SchemaError,
    freeze,
)
from fransys_model.layout import (
    Chain,
    ChainEntry,
    KeepTogether,
    Label,
    LabelKind,
    MarkerSide,
    Orientation,
    PageRole,
    PlacementView,
    Route,
    RoutePoint,
    Side,
    StarKind,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import ConductorKind, PortRole

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
            role=PortRole.GENERIC,
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


def _route(**changes: Any) -> Route:
    fields: dict[str, Any] = {
        "id": Id(kind="layout.route", value="6" * 32),
        "key": ("layout", "route"),
        "page": page().id,
        "conductor": _CONDUCTOR,
        "net": None,
        "a": _LOW,
        "b": _HIGH,
        "points": (RoutePoint(index=0, x=1, y=2), RoutePoint(index=1, x=3, y=4)),
        "produced_by": PRODUCED_BY,
    }
    return Route(**{**fields, **changes})


def _label(**changes: Any) -> Label:
    fields: dict[str, Any] = {
        "id": Id(kind="layout.label", value="5" * 32),
        "key": ("layout", "label"),
        "page": page().id,
        "function": function_id("c"),
        "port": None,
        "conductor": None,
        "kind": LabelKind.TAG,
        "slot": "tag",
        "x": 1,
        "y": 2,
        "width": 8,
        "height": 4,
        "produced_by": PRODUCED_BY,
        "partners": (),
    }
    return Label(**{**fields, **changes})


# ---- enums --------------------------------------------------------------------------------

_ENUMS = {
    Orientation: {"R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"},
    PageRole: {"POWER", "CONTROL", "SIGNAL"},
    MarkerSide: {"OWNER", "USER"},
    LabelKind: {"TAG", "MARKING", "WIRE", "CROSS_REFERENCE"},
    PlacementView: {"FUNCTION", "ITEM", "PIN"},
    StarKind: {"OFF", "REF", "BRANCH"},
    Side: {"N", "E", "S", "W"},
    layout.BlockRow: {"TOP", "BOTTOM"},
    layout.BoxKind: {"CABLE", "HARNESS"},
    layout.EndStyle: {"SOLID", "DASHED", "BLANK"},
}


# ---- the layout field tables
# -----------------------------------------------------------

_COMMON = {"id", "key", "ext"}
_FIELDS: dict[type, set[str]] = {
    layout.Chain: {"entries", "beside"},
    layout.DiagramSheet: {"unit", "number", "produced_by"},
    layout.DiagramBox: {
        "sheet",
        "subject",
        "dashed",
        "x",
        "y",
        "width",
        "height",
        "tabs",
        "produced_by",
    },
    layout.DiagramLine: {
        "sheet",
        "cable",
        "a",
        "b",
        "points",
        "text_x",
        "text_y",
        "produced_by",
    },
    layout.DiagramMarker: {"sheet", "line", "at_sheet", "x", "y", "produced_by"},
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
    layout.CableBlock: {
        "subject",
        "unit",
        "width",
        "height",
        "pitch",
        "sheet_format",
        "produced_by",
    },
    layout.CableBox: {
        "block",
        "item",
        "kind",
        "external",
        "x",
        "y",
        "width",
        "height",
        "produced_by",
    },
    layout.CoreWire: {
        "block",
        "conductor",
        "run_a",
        "run_b",
        "text_x",
        "text_y",
        "stub_a",
        "stub_b",
        "produced_by",
    },
    layout.EndBox: {
        "block",
        "item",
        "row",
        "style",
        "x",
        "y",
        "width",
        "height",
        "pins",
        "produced_by",
    },
    layout.GroupHint: {"function", "group"},
    layout.KeepTogether: {"groups"},
    layout.BreakBefore: {"group"},
    layout.OrderHint: {"before", "after"},
    layout.SideHint: {"function", "side"},
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
        "column_gap",
        "row_gap",
        "row_spacing",
        "route_margin",
        "text_height_mm",
        "marker_padding",
        "route_turn_penalty",
        "route_crossing_penalty",
        "hide_unused_pins",
        "band_ranks",
        "group_ranks",
    },
    layout.DrawingSet: {"location", "unit", "number", "produced_by"},
    layout.Page: {"drawing_set", "number", "role", "sheet_format", "groups", "produced_by"},
    layout.SymbolPlacement: {
        "function",
        "page",
        "x",
        "y",
        "orientation",
        "poles",
        "symbol",
        "library_version",
        "produced_by",
        "view",
        "ports",
        "sides",
        "port_offsets",
    },
    layout.HarnessLine: {"page", "harness", "branch", "points", "text_x", "text_y", "produced_by"},
    layout.ConnectorBox: {
        "page",
        "function",
        "x",
        "y",
        "width",
        "height",
        "texts",
        "cells",
        "produced_by",
    },
    layout.HarnessFanOut: {
        "page",
        "harness",
        "branch",
        "x",
        "y",
        "legs",
        "produced_by",
    },
    layout.StubEnd: {"marker", "index", "port", "page", "x", "y", "produced_by"},
    layout.Route: {"page", "conductor", "net", "a", "b", "points", "produced_by"},
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
        "pin_x",
        "pin_y",
        "orientation",
        "produced_by",
    },
    # A black box's dash-dot outline, drawn by render as layout placed it
    layout.Outline: {"unit", "page", "x", "y", "width", "height", "produced_by"},
    layout.Label: {
        "page",
        "function",
        "port",
        "conductor",
        "kind",
        "slot",
        "x",
        "y",
        "width",
        "height",
        "produced_by",
        "partners",
    },
}


_PROFILE_ID: Id[Any] = Id(kind="layout.profile", value="8" * 32)


# ---- ordered entries ----------------------------------------------------------------------


def _chain(*entries: ChainEntry, value: str = "1") -> Chain:
    return Chain(
        id=Id(kind="layout.chain", value=value * 32), key=("chain", value), entries=entries
    )


def _keep(*groups: Id[Any]) -> KeepTogether:
    return KeepTogether(
        id=Id(kind="layout.keep_together", value="2" * 32), key=("keep",), groups=groups
    )


def test_keep_together_is_a_set_stored_in_id_order() -> None:
    """Two orders are one record."""
    low, high = Id(kind="aspect_node", value="1" * 32), Id(kind="aspect_node", value="9" * 32)
    assert _keep(high, low).groups == (low, high)
    assert _keep(high, low) == _keep(low, high)


def test_keep_together_refuses_a_group_listed_twice() -> None:
    """A set has no repeats; refusing beats dropping what the author wrote."""
    group = Id(kind="aspect_node", value="1" * 32)
    with pytest.raises(SchemaError, match="twice") as excinfo:
        _keep(group, group)
    assert excinfo.value.record_id == Id(kind="layout.keep_together", value="2" * 32)


def test_a_route_with_one_point_or_none_turns_round_without_trouble() -> None:
    """Degenerate polylines are still routes."""
    assert _route(a=_HIGH, b=_LOW, points=()).points == ()
    single = (RoutePoint(index=0, x=5, y=5),)
    assert _route(a=_HIGH, b=_LOW, points=single).points == single


def test_a_route_refusal_names_the_route() -> None:
    """The error carries the record id."""
    with pytest.raises(SchemaError) as excinfo:
        _route(net=Id(kind="net", value="7" * 32))
    assert excinfo.value.record_id == Id(kind="layout.route", value="6" * 32)


# ---- labels -------------------------------------------------------------------------------


# ---- input of the wrong shape is left for freeze ------------------------------------------


_A_LIST: Any = []
_A_LIST_OF_STR: Any = ["x"]
_TWO_INTS_IN_A_LIST: Any = [1, 2]


def _bad_chain() -> Chain:
    return Chain(id=Id(kind="layout.chain", value="1" * 32), key=("c",), entries=_A_LIST)


def _bad_keep() -> KeepTogether:
    return KeepTogether(
        id=Id(kind="layout.keep_together", value="2" * 32), key=("k",), groups=_A_LIST_OF_STR
    )


@pytest.mark.parametrize(
    ("make", "field"),
    [
        (_bad_chain, "Chain.entries"),
        (_bad_keep, "KeepTogether.groups"),
        (lambda: _route(points=_TWO_INTS_IN_A_LIST), "Route.points"),
        (lambda: _route(a="x", b=3), "Route.a"),
        (lambda: _route(a=_UNHASHABLE, b=_UNHASHABLE), "Route.a"),
        (lambda: _label(kind="tag"), "Label.kind"),
    ],
    ids=["chain-list", "keep-list", "route-points", "route-ends", "route-equal-ends", "label-kind"],
)
def test_wrongly_shaped_input_is_left_for_freeze_to_report(make: Any, field: str) -> None:
    """No `TypeError` escapes a constructor; freeze refuses the field, by name, in a full plant."""
    assert _freeze(*_plant())
    with pytest.raises(FreezeError) as excinfo:
        _freeze(*_plant(), make())
    assert any(field in str(error) for error in excinfo.value.errors)


# ---- from_data ----------------------------------------------------------------------------


# ---- accessors ----------------------------------------------------------------------------


# ---- guards, one by one -------------------------------------------------------------------

_MIXED: Any = "x"
_UNHASHABLE: Any = []
