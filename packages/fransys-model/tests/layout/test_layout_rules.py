"""WP18 tests: the design/layout-namespace.md tables and construction rules, beyond the
skeletons."""

import dataclasses
import importlib
import json
import pkgutil
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
    check_value,
    dumps,
    freeze,
    loads,
)
from fransys_model.layout import (
    AUTHORED_KINDS,
    CABLE_KINDS,
    DERIVED_KINDS,
    Chain,
    ChainEntry,
    CrossReferencePartner,
    KeepTogether,
    Label,
    LabelKind,
    LinkMarker,
    MarkerSide,
    OrderHint,
    Orientation,
    Page,
    PageGroup,
    PageRole,
    PlacementView,
    Profile,
    Route,
    RoutePoint,
    Side,
    StarKind,
    SymbolChoice,
    default_profile,
    derived_layout_ids,
    layout_of,
    profile_of,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PortRole

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


@pytest.mark.parametrize("enum", list(_ENUMS), ids=lambda e: e.__name__)
def test_a_layout_enum_has_exactly_its_contract_members_and_is_registered(enum: Any) -> None:
    """Member names are a contract with `fransys-layout`; the enum passes `check_value`."""
    assert {member.name for member in enum} == _ENUMS[enum]
    # the values are what a stored model holds, so they are a contract too
    assert all(member.value == member.name.lower() for member in enum)
    for member in enum:
        check_value(member)


# ---- the design/layout-namespace.md field tables
# -----------------------------------------------------------

_COMMON = {"id", "key", "ext"}
_FIELDS: dict[type, set[str]] = {
    layout.Chain: {"entries"},
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
        "sheet_format",
        "column_gap",
        "row_gap",
        "row_spacing",
        "route_margin",
        "text_height",
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
    # I2a (deep dive): a black box's dash-dot outline, drawn by render as layout placed it
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


@pytest.mark.parametrize("cls", list(_FIELDS), ids=lambda c: c.__name__)
def test_a_kind_has_exactly_the_fields_of_its_design_row(cls: Any) -> None:
    """One row per design/layout-namespace.md table row: the designed fields and nothing else."""
    declared = {field.name for field in dataclasses.fields(cls)}
    assert declared == _COMMON | _FIELDS[cls]


def test_every_layout_kind_is_authored_or_derived_and_never_both() -> None:
    """A new kind must be classified, or `derived_layout_ids` would miss it."""
    # every module of the package, not `__all__`: a kind left out of both would be missed
    records = {
        value
        for info in pkgutil.iter_modules(layout.__path__)
        for value in vars(importlib.import_module(f"{layout.__name__}.{info.name}")).values()
        if isinstance(value, type) and str(vars(value).get("__kind__", "")).startswith("layout.")
    }
    assert records == {*AUTHORED_KINDS, *DERIVED_KINDS, *CABLE_KINDS}
    kinds = (set(AUTHORED_KINDS), set(DERIVED_KINDS), set(CABLE_KINDS))
    assert sum(map(len, kinds)) == len(records)
    assert set(_FIELDS) == records


def test_the_profile_has_no_pole_pitch() -> None:
    """Pole pitch is a fact of the symbol library, not a tunable (design/layout-namespace.md)."""
    assert "pole_pitch" not in {field.name for field in dataclasses.fields(Profile)}


_PROFILE_ID: Id[Any] = Id(kind="layout.profile", value="8" * 32)


def test_a_profile_given_only_its_identity_is_the_house_profile() -> None:
    """Every tunable field defaults to its house value (decision model-0060)."""
    bare = Profile(id=_PROFILE_ID, key=("bare",))
    assert dataclasses.replace(bare, id=default_profile().id, key=default_profile().key) == (
        default_profile()
    )


def test_the_house_profile_holds_the_house_numbers() -> None:
    house = default_profile()
    assert house.sheet_format is None
    assert (house.column_gap, house.row_gap, house.row_spacing) == (48, 32, 88)
    assert (house.route_margin, house.text_height, house.marker_padding) == (64, 8, 2)
    assert (house.route_turn_penalty, house.route_crossing_penalty) == (4, 16)
    assert house.band_ranks == frozendict(
        {
            "supply": 0,
            "terminal.first": 0,
            "protection": 1,
            "switch": 2,
            "contact_no": 2,
            "contact_nc": 2,
            "contact_co": 2,
            "sensor": 3,
            "coil": 4,
            "load": 4,
            "actuator": 4,
            "terminal": 4,
            "terminal.last": 5,
        }
    )
    assert house.group_ranks == frozendict()


def test_a_profile_with_no_sheet_format_freezes_and_round_trips() -> None:
    """`sheet_format=None` is the house sheet: no record to refer to, so no reference to check."""
    model = _freeze(Profile(id=_PROFILE_ID, key=("bare",)))
    assert loads(dumps(model)) == model


def test_profile_of_a_model_without_one_is_the_house_profile() -> None:
    assert profile_of(_freeze()) == default_profile()


def test_profile_of_a_model_with_one_is_that_record() -> None:
    authored = Profile(id=_PROFILE_ID, key=("authored",), column_gap=4)
    assert profile_of(_freeze(authored)) == authored


def test_a_link_marker_names_its_port_not_a_net() -> None:
    """The severed net is the physical net of `port`, by closure: it is not stored."""
    assert "net" not in {field.name for field in dataclasses.fields(LinkMarker)}


# ---- ordered entries ----------------------------------------------------------------------


def _chain(*entries: ChainEntry, value: str = "1") -> Chain:
    return Chain(
        id=Id(kind="layout.chain", value=value * 32), key=("chain", value), entries=entries
    )


def test_chain_indices_need_not_be_contiguous_and_only_the_index_orders() -> None:
    """Sorted by `index`, whatever the gaps and whatever the tuple position or function id."""
    late = ChainEntry(function=function_id("1"), index=30)
    early = ChainEntry(function=function_id("f"), index=-5)
    middle = ChainEntry(function=function_id("8"), index=7)
    assert _chain(late, early, middle).entries == (early, middle, late)
    assert _chain(middle, late, early) == _chain(early, middle, late)


def test_an_empty_chain_constructs() -> None:
    """Nothing to order and nothing repeated."""
    assert _chain().entries == ()


def test_two_chains_may_share_a_function() -> None:
    """One function appears once per chain, not once per model."""
    entry = ChainEntry(function=function_id("c"), index=0)
    model = _freeze(*_plant(), _chain(entry, value="1"), _chain(entry, value="2"))
    assert len(layout_of(model, Chain)) == 2


def test_a_chain_refusal_names_the_chain() -> None:
    """The error carries the record id, for `describe`."""
    with pytest.raises(SchemaError) as excinfo:
        _chain(
            ChainEntry(function=function_id("a"), index=0),
            ChainEntry(function=function_id("b"), index=0),
        )
    assert excinfo.value.record_id == Id(kind="layout.chain", value="1" * 32)
    assert excinfo.value.kind == "layout.chain"


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


def test_route_points_reverse_with_the_ends_and_keep_their_index_slots() -> None:
    """Indices 10, 20, 30 stay the slots; the geometry swaps end for end."""
    forward = _route(
        points=(
            RoutePoint(index=10, x=1, y=1),
            RoutePoint(index=20, x=2, y=2),
            RoutePoint(index=30, x=3, y=3),
        )
    )
    backward = _route(
        a=_HIGH,
        b=_LOW,
        points=(
            RoutePoint(index=10, x=3, y=3),
            RoutePoint(index=20, x=2, y=2),
            RoutePoint(index=30, x=1, y=1),
        ),
    )
    assert backward == forward
    assert [(p.index, p.x) for p in backward.points] == [(10, 1), (20, 2), (30, 3)]


def test_route_points_are_sorted_before_they_are_turned_round() -> None:
    """Points listed out of order and with the ends swapped still end up a-to-b."""
    scrambled = _route(
        a=_HIGH,
        b=_LOW,
        points=(
            RoutePoint(index=1, x=1, y=1),
            RoutePoint(index=0, x=9, y=9),
        ),
    )
    assert (scrambled.a, scrambled.b) == (_LOW, _HIGH)
    assert [(p.index, p.x) for p in scrambled.points] == [(0, 1), (1, 9)]


def test_route_between_ports_in_order_is_left_as_it_is() -> None:
    """No swap when `a` already sorts first: the points are not reversed."""
    route = _route()
    assert [(p.x, p.y) for p in route.points] == [(1, 2), (3, 4)]


def test_a_route_with_one_point_or_none_turns_round_without_trouble() -> None:
    """Degenerate polylines are still routes."""
    assert _route(a=_HIGH, b=_LOW, points=()).points == ()
    single = (RoutePoint(index=0, x=5, y=5),)
    assert _route(a=_HIGH, b=_LOW, points=single).points == single


def test_a_route_joins_two_different_ports() -> None:
    """Like a conductor: a polyline from a port to itself is refused, whatever its points."""
    with pytest.raises(SchemaError, match="two different ports") as excinfo:
        _route(a=_LOW, b=_LOW)
    assert excinfo.value.record_id == Id(kind="layout.route", value="6" * 32)
    with pytest.raises(SchemaError, match="two different ports"):
        _route(a=_LOW, b=_LOW, points=_TWO_INTS_IN_A_LIST)


def test_a_route_turned_into_a_self_loop_by_an_alias_is_reported() -> None:
    """The alias rewrite re-runs the constructor, so a self-loop it creates is reported."""
    draft = Draft()
    retired = Id(kind="port", value="7" * 32)
    draft.extend((*_plant(), _route(a=_LOW, b=retired)), origin=_ORIGIN)
    draft.alias(retired, _LOW)
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    assert any("two different ports" in str(error) for error in excinfo.value.errors)


def test_a_route_refusal_names_the_route() -> None:
    """The error carries the record id."""
    with pytest.raises(SchemaError) as excinfo:
        _route(net=Id(kind="net", value="7" * 32))
    assert excinfo.value.record_id == Id(kind="layout.route", value="6" * 32)


def test_page_groups_may_be_any_distinct_indices() -> None:
    """Same rule as a chain: order by `index`, refuse a repeat."""
    a = PageGroup(group=group_node().id, index=4)
    b = PageGroup(group=Id(kind="aspect_node", value="4" * 32), index=-1)
    built = Page(
        id=Id(kind="layout.page", value="f" * 32),
        key=("page",),
        drawing_set=drawing_set().id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=sheet_format().id,
        groups=(a, b),
        produced_by=PRODUCED_BY,
    )
    assert built.groups == (b, a)


# ---- labels -------------------------------------------------------------------------------


def test_each_single_subject_makes_a_label() -> None:
    """A function, a port or a conductor alone constructs."""
    assert _label().function is not None
    assert _label(function=None, port=_LOW, kind=LabelKind.MARKING).port == _LOW
    assert _label(function=None, conductor=_CONDUCTOR, kind=LabelKind.WIRE).conductor == _CONDUCTOR


@pytest.mark.parametrize(
    "changes",
    [
        {"port": _LOW},
        {"conductor": _CONDUCTOR},
        {"port": _LOW, "conductor": _CONDUCTOR},
        {"function": None},
    ],
    ids=["function+port", "function+conductor", "all three", "none"],
)
def test_a_label_with_other_than_one_subject_is_refused(changes: dict[str, Any]) -> None:
    """Every wrong count, not only the two the skeletons try."""
    with pytest.raises(SchemaError, match="exactly one"):
        _label(**changes)


@pytest.mark.parametrize(
    "changes",
    [{}, {"function": None, "port": _LOW}],
    ids=["on a function", "on a port"],
)
def test_a_wire_label_belongs_to_a_conductor(changes: dict[str, Any]) -> None:
    """A net-realised route has no wire label: `WIRE` needs a conductor (layout-namespace.md)."""
    with pytest.raises(SchemaError, match="conductor"):
        _label(kind=LabelKind.WIRE, **changes)


def test_a_non_cross_reference_label_with_a_partner_is_refused() -> None:
    """Only `CROSS_REFERENCE` carries partner text; a `TAG` label may not smuggle one in."""
    partner = CrossReferencePartner(port=_LOW, page=page().id, x=1)
    with pytest.raises(SchemaError, match="only a cross-reference label carries partners"):
        _label(partners=(partner,))


def test_a_cross_reference_label_needs_at_least_one_partner() -> None:
    """The kind promises partner text; an empty tuple leaves nothing to render."""
    with pytest.raises(SchemaError, match="at least one partner"):
        _label(kind=LabelKind.CROSS_REFERENCE)


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


def test_a_route_whose_ends_are_not_ids_is_not_reordered() -> None:
    """The guard leaves both ends and the points exactly as given."""
    route = _route(a="z", b=_LOW)
    assert (route.a, route.b) == ("z", _LOW)
    assert [p.x for p in route.points] == [1, 3]


# ---- from_data ----------------------------------------------------------------------------


def _tampered(model: Model, kind: str, **changes: Any) -> str:
    data = json.loads(dumps(model))
    (record,) = data["tables"][kind]
    record.update(changes)
    return json.dumps(data)


def test_a_broken_record_read_back_surfaces_inside_a_freeze_error() -> None:
    """Rules live in `__post_init__`, so `loads` holds them too (layout-namespace.md)."""
    choice = SymbolChoice(
        id=Id(kind="layout.symbol_choice", value="a" * 32),
        key=("choice",),
        function=None,
        template=None,
        part=None,
        kind=FunctionKind.CONTACT_NO,
        symbol="make-contact",
    )
    model = _freeze(choice)
    assert loads(dumps(model)) == model
    two_selectors = _tampered(model, "layout.symbol_choice", function="function:" + "b" * 32)
    with pytest.raises(FreezeError) as excinfo:
        loads(two_selectors)
    assert any(isinstance(error, SchemaError) for error in excinfo.value.errors)


def test_a_cross_reference_label_with_partners_survives_the_round_trip() -> None:
    """`partners` round-trips through the model, not just as bare dataclass equality."""
    partners = (
        CrossReferencePartner(port=_LOW, page=page().id, x=1),
        CrossReferencePartner(port=_HIGH, page=page().id, x=9),
    )
    label = _label(kind=LabelKind.CROSS_REFERENCE, partners=partners)
    model = _freeze(*_plant(), label)
    assert loads(dumps(model)) == model


def test_a_cross_reference_label_with_no_partners_surfaces_through_from_data() -> None:
    """A hand-edited file cannot smuggle an empty `partners` past the constructor either."""
    partners = (CrossReferencePartner(port=_LOW, page=page().id, x=1),)
    model = _freeze(*_plant(), _label(kind=LabelKind.CROSS_REFERENCE, partners=partners))
    emptied = _tampered(model, "layout.label", partners=[])
    with pytest.raises(FreezeError) as excinfo:
        loads(emptied)
    assert any(isinstance(error, SchemaError) for error in excinfo.value.errors)


def test_a_tag_label_carrying_a_partner_surfaces_through_from_data() -> None:
    """The kind/partners mismatch holds through a hand-edited file, not just at construction."""
    xref_partners = (CrossReferencePartner(port=_LOW, page=page().id, x=1),)
    xref_model = _freeze(*_plant(), _label(kind=LabelKind.CROSS_REFERENCE, partners=xref_partners))
    partner_json = json.loads(dumps(xref_model))["tables"]["layout.label"][0]["partners"]
    tag_model = _freeze(*_plant(), _label())
    tampered = _tampered(tag_model, "layout.label", partners=partner_json)
    with pytest.raises(FreezeError) as excinfo:
        loads(tampered)
    assert any(isinstance(error, SchemaError) for error in excinfo.value.errors)


def test_a_route_read_back_with_swapped_ends_is_normalised() -> None:
    """A hand-edited file cannot smuggle an unordered route past the constructor."""
    route = _route()
    data = json.loads(dumps(_freeze(*_plant(), route)))
    (record,) = data["tables"]["layout.route"]
    record["a"], record["b"] = record["b"], record["a"]
    record["points"] = list(reversed(record["points"]))
    for index, point in enumerate(record["points"]):
        point["index"] = index
    assert layout_of(loads(json.dumps(data)), Route)[route.id] == route


# ---- accessors ----------------------------------------------------------------------------


def test_layout_of_refuses_a_class_outside_the_layout_namespace() -> None:
    """`Item` is a `core` kind; a facet class is not a layout kind either."""
    with pytest.raises(SchemaError, match="not a layout kind"):
        layout_of(_freeze(), Item)


def test_layout_of_is_empty_for_a_model_without_the_kind() -> None:
    """An empty table, not a missing one."""
    assert layout_of(_freeze(), Page) == {}


def test_derived_layout_ids_are_sorted_and_empty_for_an_empty_model() -> None:
    """A pass hands them to `evolve(remove=...)`: order must not depend on the tables."""
    assert derived_layout_ids(_freeze()) == ()
    model = _freeze(*_plant(), _route(), _label())
    ids = derived_layout_ids(model)
    assert list(ids) == sorted(ids)
    assert len(ids) == 4


# ---- guards, one by one -------------------------------------------------------------------

_MIXED: Any = "x"
_UNHASHABLE: Any = []


def test_indices_of_mixed_types_are_left_for_freeze_not_compared() -> None:
    """`0 < "x"` is a `TypeError`: the constructor must not compare what it cannot order."""
    entries = (
        ChainEntry(function=function_id("a"), index=0),
        ChainEntry(function=function_id("b"), index=_MIXED),
    )
    chain = _chain(*entries)
    assert chain.entries == entries
    with pytest.raises(FreezeError):
        _freeze(*_plant(), chain)


def test_an_unhashable_function_in_a_chain_is_left_for_freeze() -> None:
    """The repeat check only runs on ids; anything else is freeze's to report."""
    entries = (
        ChainEntry(function=function_id("c"), index=0),
        ChainEntry(function=_UNHASHABLE, index=1),
    )
    with pytest.raises(FreezeError) as excinfo:
        _freeze(*_plant(), _chain(*entries))
    assert [str(error) for error in excinfo.value.errors] == [
        "Chain.entries.1.function: expected Id, got list"
    ]


def test_an_order_hint_of_the_wrong_shape_is_left_for_freeze() -> None:
    """`[] == []` is true, but that is not a group before itself: freeze names the fields."""
    hint = OrderHint(
        id=Id(kind="layout.order_hint", value="4" * 32),
        key=("o",),
        before=_UNHASHABLE,
        after=_UNHASHABLE,
    )
    with pytest.raises(FreezeError) as excinfo:
        _freeze(*_plant(), hint)
    assert any("OrderHint.before" in str(error) for error in excinfo.value.errors)


def test_a_keep_together_of_mixed_kinds_is_left_for_freeze() -> None:
    """An id and a string cannot be ordered: no `TypeError`, and freeze refuses the field."""
    low = Id(kind="aspect_node", value="1" * 32)
    keep = _keep(low, _MIXED)
    assert keep.groups == (low, "x")
    with pytest.raises(FreezeError):
        _freeze(*_plant(), keep)


@pytest.mark.parametrize("bad_id", ["oops", None, 3])
def test_a_refusal_from_a_record_whose_id_is_not_an_id_names_no_record(bad_id: Any) -> None:
    """`SchemaError.record_id` is an `Id` or `None`, whatever the record held."""
    group = Id(kind="aspect_node", value="1" * 32)
    with pytest.raises(SchemaError) as excinfo:
        KeepTogether(id=bad_id, key=("k",), groups=(group, group))
    assert excinfo.value.record_id is None


def test_derived_layout_ids_do_not_depend_on_the_order_of_the_kind_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sorted here, not by luck of `DERIVED_KINDS` being alphabetical."""
    from fransys_model.layout import tables

    model = _freeze(*_plant(), _route(), _label())
    expected = derived_layout_ids(model)
    monkeypatch.setattr(tables, "DERIVED_KINDS", tuple(reversed(DERIVED_KINDS)))
    assert derived_layout_ids(model) == expected
    assert list(expected) == sorted(expected)
