"""WP18 tests: derived layout kinds, cross-record rules (ROADMAP WP18,
design/layout-namespace.md)."""

import dataclasses
import json
from decimal import Decimal

import pytest
from layout_examples import (
    PAGE_KEY,
    PRODUCED_BY,
    drawing_set,
    drawn_function,
    function_id,
    group_node,
    page,
    placement,
    sheet_format,
)

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    Model,
    Origin,
    Record,
    SchemaError,
    dumps,
    freeze,
    loads,
    make_id,
)
from fransys_model.layout import (
    BreakBefore,
    Chain,
    ChainEntry,
    DrawingSet,
    GroupHint,
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
    PowerSymbol,
    Profile,
    Route,
    RoutePoint,
    SheetFormat,
    Side,
    StarKind,
    SymbolChoice,
    default_sheet_format,
    derived_layout_ids,
    layout_of,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port, Unit, UnitRelease
from fransys_model.vocab.enums import Aspect, ConductorKind, FunctionKind, PartCategory, PortRole
from fransys_model.vocab.templates import FunctionTemplate, Part

_LOW_PORT: Id[Port] = Id(kind="port", value="1" * 32)
_HIGH_PORT: Id[Port] = Id(kind="port", value="2" * 32)
_CONDUCTOR: Id[Conductor] = Id(kind="conductor", value="3" * 32)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_results.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _ports() -> tuple[Port, Port]:
    return (
        Port(
            id=_LOW_PORT,
            key=("examples", "pump1", "contactor", "fn", "main", "port", "1"),
            function=function_id("c"),
            template=None,
            name="1",
            role=PortRole.GENERIC,
        ),
        Port(
            id=_HIGH_PORT,
            key=("examples", "pump1", "contactor", "fn", "main", "port", "2"),
            function=function_id("c"),
            template=None,
            name="2",
            role=PortRole.GENERIC,
        ),
    )


def _conductor() -> Conductor:
    return Conductor(
        id=_CONDUCTOR,
        key=("examples", "pump1", "wire", "1"),
        a=_LOW_PORT,
        b=_HIGH_PORT,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _other_group() -> AspectNode:
    return AspectNode(
        id=Id(kind="aspect_node", value="4" * 32),
        key=("examples", "function", "pump2"),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="PUMP2",
        description="Invented pump 2",
    )


def _label(*, function: bool, port: bool, conductor: bool) -> Label:
    return Label(
        id=Id(kind="layout.label", value="5" * 32),
        key=("layout", "example-engine", "label", "examples", "pump1", "contactor", "tag", "tag"),
        page=page().id,
        function=function_id("c") if function else None,
        port=_LOW_PORT if port else None,
        conductor=_CONDUCTOR if conductor else None,
        kind=LabelKind.TAG,
        slot="tag",
        x=72,
        y=96,
        width=16,
        height=8,
        produced_by=PRODUCED_BY,
    )


def _route(
    *,
    conductor: bool = True,
    net: bool = False,
    a: Id[Port] = _LOW_PORT,
    b: Id[Port] = _HIGH_PORT,
    points: tuple[RoutePoint, ...] = (
        RoutePoint(index=0, x=64, y=96),
        RoutePoint(index=1, x=64, y=160),
    ),
) -> Route:
    return Route(
        id=Id(kind="layout.route", value="6" * 32),
        key=("layout", "example-engine", "route", "examples", "pump1", "wire", "1"),
        page=page().id,
        conductor=_CONDUCTOR if conductor else None,
        net=Id(kind="net", value="7" * 32) if net else None,
        a=a,
        b=b,
        points=points,
        produced_by=PRODUCED_BY,
    )


def _marker_key(port_name: str, partner_name: str, side: MarkerSide) -> tuple[str, ...]:
    """design/layout-namespace.md: the port key, the side and the partner port key."""
    port_key = ("examples", "port", port_name)
    partner_key = ("examples", "port", partner_name)
    return ("layout", "example-engine", "link_marker", *port_key, side.value, *partner_key)


def _marker(  # noqa: PLR0913 -- one param per LinkMarker field a test needs to vary
    value: str,
    partner: str,
    *,
    port: Id[Port],
    names: tuple[str, str],
    side: MarkerSide,
    width: int,
    height: int,
) -> LinkMarker:
    return LinkMarker(
        id=Id(kind="layout.link_marker", value=value * 32),
        key=_marker_key(*names, side),
        page=page().id,
        port=port,
        side=side,
        partner=Id(kind="layout.link_marker", value=partner * 32),
        x=64,
        y=200,
        width=width,
        height=height,
        produced_by=PRODUCED_BY,
    )


def _marker_pair() -> tuple[LinkMarker, LinkMarker]:
    return (
        _marker(
            "8", "9", port=_LOW_PORT, names=("1", "2"), side=MarkerSide.OWNER, width=13, height=8
        ),
        _marker(
            "9", "8", port=_HIGH_PORT, names=("2", "1"), side=MarkerSide.USER, width=13, height=8
        ),
    )


def _profile(value: str) -> Profile:
    return Profile(
        id=Id(kind="layout.profile", value=value * 32),
        key=("examples", "layout", "profile", value),
        sheet_format=sheet_format().id,
        column_gap=48,
        row_gap=32,
        route_margin=16,
        text_height=8,
        marker_padding=2,
        route_turn_penalty=5,
        route_crossing_penalty=20,
    )


def _group_hint(value: str) -> GroupHint:
    return GroupHint(
        id=Id(kind="layout.group_hint", value=value * 32),
        key=("examples", "layout", "group_hint", value),
        function=function_id("c"),
        group=group_node().id,
    )


def _engineering() -> tuple[Record, ...]:
    return (*drawn_function(), *_ports(), _conductor(), group_node(), _other_group())


def test_label_with_one_subject_is_accepted() -> None:
    """A label naming only a `function` constructs."""
    assert _label(function=True, port=False, conductor=False).port is None


@pytest.mark.parametrize(
    ("function", "port", "conductor"),
    [(True, True, False), (False, False, False)],
)
def test_label_without_exactly_one_subject_is_a_schema_error(
    *, function: bool, port: bool, conductor: bool
) -> None:
    """Two subjects, or none, leave the text source undefined, so construction raises."""
    with pytest.raises(SchemaError):
        _label(function=function, port=port, conductor=conductor)


def test_route_with_a_conductor_alone_is_accepted() -> None:
    """A route drawing one `Conductor` constructs."""
    assert _route(conductor=True, net=False).net is None


@pytest.mark.parametrize(("conductor", "net"), [(True, True), (False, False)])
def test_route_without_exactly_one_of_conductor_and_net_is_a_schema_error(
    *, conductor: bool, net: bool
) -> None:
    """A route draws a conductor or a leg of a net, never both and never neither."""
    with pytest.raises(SchemaError):
        _route(conductor=conductor, net=net)


def test_route_ends_normalise_to_id_order_and_points_reverse_with_them() -> None:
    """Authored `b`-to-`a`, the route is stored `a`-to-`b` with its polyline turned round."""
    top, bottom = (64, 96), (64, 160)
    swapped = _route(
        a=_HIGH_PORT,
        b=_LOW_PORT,
        points=(
            RoutePoint(index=0, x=bottom[0], y=bottom[1]),
            RoutePoint(index=1, x=top[0], y=top[1]),
        ),
    )
    assert (swapped.a, swapped.b) == (_LOW_PORT, _HIGH_PORT)
    assert swapped == _route()


def test_route_points_are_stored_sorted_by_index() -> None:
    """`Route.points` is ordered by `index`, whatever order it was constructed in."""
    first, second = RoutePoint(index=0, x=64, y=96), RoutePoint(index=1, x=64, y=160)
    assert _route(points=(second, first)).points == (first, second)


def test_route_with_a_duplicate_point_index_is_a_schema_error() -> None:
    """Two points with one `index` cannot be ordered, so construction raises."""
    with pytest.raises(SchemaError):
        _route(points=(RoutePoint(index=0, x=64, y=96), RoutePoint(index=0, x=64, y=160)))


def _page_with(*groups: PageGroup) -> Page:
    return Page(
        id=Id(kind="layout.page", value="f" * 32),
        key=PAGE_KEY,
        drawing_set=drawing_set().id,
        number=1,
        role=PageRole.POWER,
        sheet_format=sheet_format().id,
        groups=groups,
        produced_by=PRODUCED_BY,
    )


def test_page_groups_are_stored_sorted_by_index() -> None:
    """`Page.groups` is ordered by `index`, whatever order it was constructed in."""
    first = PageGroup(group=group_node().id, index=0)
    second = PageGroup(group=_other_group().id, index=1)
    assert _page_with(second, first).groups == (first, second)


def test_page_with_a_duplicate_group_index_is_a_schema_error() -> None:
    """Two groups with one `index` cannot be ordered, so construction raises."""
    with pytest.raises(SchemaError):
        _page_with(
            PageGroup(group=group_node().id, index=0),
            PageGroup(group=_other_group().id, index=0),
        )


def test_a_drawing_set_with_a_unit_round_trips() -> None:
    """`unit` names the drawing set's unit (units spec U1); comes back equal and reachable."""
    release_key = ("unit_release", "board", "1", "1")
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name="board",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(
        id=Id(kind="unit", value="d" * 32),
        key=("examples", "board"),
        release=release.id,
        parent=None,
    )
    with_unit = dataclasses.replace(drawing_set(), unit=unit.id)
    model = _freeze((release, unit, with_unit))
    assert loads(dumps(model)) == model
    assert layout_of(model, DrawingSet)[with_unit.id].unit == unit.id


def test_a_drawing_set_with_no_unit_matches_todays_shape_plus_the_new_key() -> None:
    """`unit=None` (the default) is exactly what a model with no unit produced before U1.

    `drawing_set()` sets no `unit=`, the same fixture every other test in this file freezes;
    the new `"unit": null` key is the only change to its canonical JSON.
    """
    model = _freeze((drawing_set(),))
    text = dumps(model)
    assert '"unit": null' in text
    assert loads(text) == model
    assert layout_of(model, DrawingSet)[drawing_set().id].unit is None


def test_a_page_without_a_sheet_format_freezes_and_round_trips() -> None:
    """`sheet_format=None` is the house sheet: no record is referenced and none is needed."""
    bare = dataclasses.replace(page(), sheet_format=None)
    model = _freeze((drawing_set(), group_node(), bare))
    assert loads(dumps(model)) == model


def test_a_page_naming_a_sheet_format_that_is_not_in_the_model_is_a_freeze_error() -> None:
    """The near-identical input: a named sheet must exist, so `None` is what says "the default"."""
    with pytest.raises(FreezeError):
        _freeze((drawing_set(), group_node(), page()))
    _freeze((drawing_set(), group_node(), sheet_format(), page()))


def test_the_house_sheet_is_a_constant_and_not_a_record_of_any_model() -> None:
    """A3 landscape, content 410 x 267 mm at (5, 5), 8 x 6 frame, module 2.5 mm (spec R11.1)."""
    house = default_sheet_format()
    assert isinstance(house, SheetFormat)
    assert house == default_sheet_format()
    assert (house.width_mm, house.height_mm) == (420, 297)
    assert (house.content_x_mm, house.content_y_mm) == (5, 5)
    assert (house.content_width_mm, house.content_height_mm) == (410, 267)
    assert (house.frame_columns, house.frame_rows) == (8, 6)
    assert house.module_mm == Decimal("2.5")
    assert house.id not in _freeze((drawing_set(), group_node(), page_without_sheet())).tables.get(
        "layout.sheet_format", {}
    )


def test_the_house_margin_is_5_mm_on_every_side_with_a_20_mm_title_block_band() -> None:
    """Spec page-frame R11.1: margin halved to 5 mm; the band stays 20 mm (decision model-0051)."""
    house = default_sheet_format()
    assert house.content_x_mm == 5
    assert house.content_y_mm == 5
    assert house.width_mm - (house.content_x_mm + house.content_width_mm) == 5
    band = house.height_mm - house.content_y_mm - (house.content_y_mm + house.content_height_mm)
    assert band == 20


def page_without_sheet() -> Page:
    """`page()` with the house sheet."""
    return dataclasses.replace(page(), sheet_format=None)


def test_one_profile_freezes_and_a_second_is_a_freeze_error() -> None:
    """`Profile` is a singleton kind: one is fine, two fail `freeze()`."""
    _freeze((sheet_format(), _profile("a")))
    with pytest.raises(FreezeError):
        _freeze((sheet_format(), _profile("a"), _profile("b")))


def test_one_group_hint_freezes_and_a_second_for_the_function_is_a_freeze_error() -> None:
    """`GroupHint` is unique per function: one is fine, two fail `freeze()`."""
    _freeze((*_engineering(), _group_hint("a")))
    with pytest.raises(FreezeError):
        _freeze((*_engineering(), _group_hint("a"), _group_hint("b")))


def test_a_pair_of_link_markers_referencing_each_other_freezes() -> None:
    """Reference resolution accepts the two-record cycle a marker pair forms."""
    owner, user = _marker_pair()
    model = _freeze((*_engineering(), sheet_format(), drawing_set(), page(), owner, user))
    assert layout_of(model, LinkMarker)[owner.id].partner == user.id


def test_link_marker_with_a_missing_partner_is_a_freeze_error() -> None:
    """One marker of a pair alone has a dangling `partner`."""
    owner, _ = _marker_pair()
    with pytest.raises(FreezeError):
        _freeze((*_engineering(), sheet_format(), drawing_set(), page(), owner))


def test_a_link_marker_with_a_positive_box_size_is_accepted() -> None:
    """A marker's reserved box size constructs when both `width` and `height` are positive."""
    owner, _ = _marker_pair()
    assert (owner.width, owner.height) == (13, 8)


@pytest.mark.parametrize(("width", "height"), [(0, 8), (-1, 8), (8, 0), (8, -1)])
def test_a_link_marker_with_a_non_positive_box_size_is_a_schema_error(
    *, width: int, height: int
) -> None:
    """A zero or negative `width`/`height` cannot be a reserved box, so construction raises."""
    with pytest.raises(SchemaError):
        _marker(
            "8",
            "9",
            port=_LOW_PORT,
            names=("1", "2"),
            side=MarkerSide.OWNER,
            width=width,
            height=height,
        )


def test_a_link_marker_with_a_non_positive_box_size_from_data_is_a_freeze_error() -> None:
    """The same refusal, surfacing through `loads` as `from_data`'s callers see it (WP18)."""
    owner, user = _marker_pair()
    model = _freeze((*_engineering(), sheet_format(), drawing_set(), page(), owner, user))
    data = json.loads(dumps(model))
    data["tables"]["layout.link_marker"][0]["width"] = 0
    with pytest.raises(FreezeError):
        loads(json.dumps(data))


def test_model_with_one_record_of_every_layout_kind_round_trips() -> None:
    """`loads(dumps(m)) == m` for a model holding every authored and derived layout kind."""
    authored: tuple[Record, ...] = (
        sheet_format(),
        _profile("a"),
        Chain(
            id=Id(kind="layout.chain", value="a" * 31 + "1"),
            key=("examples", "layout", "pump1", "power"),
            entries=(ChainEntry(function=function_id("c"), index=0),),
        ),
        _group_hint("b"),
        KeepTogether(
            id=Id(kind="layout.keep_together", value="a" * 31 + "2"),
            key=("examples", "layout", "keep", "pumps"),
            groups=(group_node().id, _other_group().id),
        ),
        BreakBefore(
            id=Id(kind="layout.break_before", value="a" * 31 + "3"),
            key=("examples", "layout", "break", "pump2"),
            group=_other_group().id,
        ),
        OrderHint(
            id=Id(kind="layout.order_hint", value="a" * 31 + "4"),
            key=("examples", "layout", "order", "pump1-pump2"),
            before=group_node().id,
            after=_other_group().id,
        ),
        SymbolChoice(
            id=Id(kind="layout.symbol_choice", value="a" * 31 + "5"),
            key=("examples", "layout", "choice", "contact"),
            function=None,
            template=None,
            part=None,
            kind=FunctionKind.CONTACT_NO,
            symbol="make-contact",
        ),
    )
    derived: tuple[Record, ...] = (
        drawing_set(),
        page(),
        placement(),
        _route(),
        *_marker_pair(),
        _label(function=True, port=False, conductor=False),
    )
    model = _freeze((*_engineering(), *authored, *derived))
    assert loads(dumps(model)) == model


def test_a_symbol_choice_selecting_by_template_round_trips() -> None:
    """`loads(dumps(m)) == m` for a `SymbolChoice` whose selector is `template` (model-0030).

    The other round-trip test above uses `kind` for its one `SymbolChoice`, which needs no
    referenced record; `template` does (`Id[FunctionTemplate]`), so this test builds one.
    """
    part = Part(
        id=Id(kind="part", value="7" * 32),
        key=("examples", "part"),
        mpn="EX-1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.GENERIC,
        class_code="X",
    )
    template = FunctionTemplate(
        id=Id(kind="function_template", value="8" * 32),
        key=("examples", "part", "function", "main"),
        part=part.id,
        name="main",
        kind=FunctionKind.GENERIC,
    )
    choice = SymbolChoice(
        id=Id(kind="layout.symbol_choice", value="9" * 32),
        key=("examples", "layout", "choice", "template"),
        function=None,
        template=template.id,
        part=None,
        kind=None,
        symbol="make-contact",
    )
    model = _freeze((part, template, choice))
    assert loads(dumps(model)) == model
    assert layout_of(model, SymbolChoice)[choice.id].template == template.id


# ---- typed fields of SymbolPlacement, LinkMarker and Label (deep dive F1) -----------------


def test_an_item_placement_with_ports_and_sides_is_accepted() -> None:
    """`view=ITEM` with parallel `ports` and `sides` constructs and keeps them."""
    item = dataclasses.replace(
        placement(), view=PlacementView.ITEM, ports=("1", "2"), sides=(Side.N, Side.S)
    )
    assert (item.view, item.ports, item.sides) == (
        PlacementView.ITEM,
        ("1", "2"),
        (Side.N, Side.S),
    )


def test_a_function_placement_has_no_ports_and_sides_by_default() -> None:
    """The defaults keep every existing construction valid."""
    plain = placement()
    assert (plain.view, plain.ports, plain.sides) == (PlacementView.FUNCTION, (), ())


def test_a_non_item_placement_may_carry_ports_and_sides() -> None:
    """The pair is not tied to `view`: a generic box of another view may carry it (C5)."""
    box = dataclasses.replace(placement(), view=PlacementView.PIN, ports=("1",), sides=(Side.S,))
    assert box.ports == ("1",)


@pytest.mark.parametrize(
    ("ports", "sides"),
    [
        (("1",), ()),
        ((), (Side.N,)),
        (("1", "2"), (Side.N,)),
        (("1",), (Side.E,)),
        (("1",), (Side.W,)),
    ],
    ids=["ports-only", "sides-only", "lengths-differ", "side-e", "side-w"],
)
def test_a_placement_with_unpaired_ports_and_sides_or_a_bad_side_is_a_schema_error(
    ports: tuple[str, ...], sides: tuple[Side, ...]
) -> None:
    """`ports` and `sides` come together, one side per port, each `Side.N` or `Side.S`."""
    with pytest.raises(SchemaError):
        dataclasses.replace(placement(), ports=ports, sides=sides)


@pytest.mark.parametrize(
    "offsets",
    [(0, 16), (0, 16, 32, 48), (0, 0, 16), (8, 0, 4)],
    ids=["too-few", "too-many", "equal-on-one-side", "falling-on-one-side"],
)
def test_a_placement_with_bad_port_offsets_is_a_schema_error(offsets: tuple[int, ...]) -> None:
    """model-0129: offsets are one per port and strictly rise along each side."""
    # UNDO: layout/results.py `_check_offsets`, the length test `!=` -> `<` and the rise test
    #     `b <= a` -> `b < a`: a short list and an equal pair are accepted
    ports = ("1", "2", "3")
    sides = (Side.N, Side.N, Side.S)
    with pytest.raises(SchemaError):
        dataclasses.replace(placement(), ports=ports, sides=sides, port_offsets=offsets)


def test_port_offsets_rise_along_each_side_alone() -> None:
    """A north port at x 24 and a south port at x 0 are no pair: the sides are checked apart."""
    made = dataclasses.replace(
        placement(),
        ports=("1", "2", "3"),
        sides=(Side.N, Side.S, Side.N),
        port_offsets=(0, 0, 24),
    )
    assert made.port_offsets == (0, 0, 24)
    assert dataclasses.replace(placement()).port_offsets == ()


def test_a_link_marker_that_is_not_the_lead_of_a_box_is_accepted_with_a_box_x() -> None:
    """`lead=False` names a marker of a shared box, which is then given by `box_x`."""
    owner, _ = _marker_pair()
    follower = dataclasses.replace(owner, box_x=40, lead=False)
    assert (follower.box_x, follower.lead) == (40, False)


@pytest.mark.parametrize(
    "changes",
    [
        {"lead": False},
        {"via_x": 3},
        {"via_y": 3},
        {"stub_extra": -1},
        {"wrap_at": 0},
    ],
    ids=[
        "non-lead-without-box",
        "via_x-alone",
        "via_y-alone",
        "negative-stub",
        "no-word-on-line-1",
    ],
)
def test_a_link_marker_with_inconsistent_new_fields_is_a_schema_error(
    changes: dict[str, int | bool],
) -> None:
    """A boxless non-lead, half a via point, or a negative stub extension cannot be drawn."""
    owner, _ = _marker_pair()
    with pytest.raises(SchemaError):
        dataclasses.replace(owner, **changes)


def test_a_link_marker_with_both_via_coordinates_is_accepted() -> None:
    """`via_x` and `via_y` are set together."""
    owner, _ = _marker_pair()
    via = dataclasses.replace(owner, via_x=3, via_y=4, stub_extra=0)
    assert (via.via_x, via.via_y) == (3, 4)


@pytest.mark.parametrize("star", list(StarKind))
def test_a_link_marker_accepts_every_star_kind(star: StarKind) -> None:
    """`star` takes any `StarKind`, or `None`; an off stub also carries its far and facing."""
    owner, _ = _marker_pair()
    assert owner.star is None
    off = star is StarKind.OFF
    far, facing = (_HIGH_PORT, Side.N) if off else (None, None)
    assert dataclasses.replace(owner, star=star, far=far, facing=facing).star is star


def _off_stub() -> LinkMarker:
    owner, _ = _marker_pair()
    return dataclasses.replace(
        owner,
        star=StarKind.OFF,
        far=_HIGH_PORT,
        carrier=Id(kind="item", value="b" * 32),
        facing=Side.S,
    )


def test_an_off_stub_with_far_carrier_and_facing_is_accepted() -> None:
    """The three off-stub fields construct together and are kept as given."""
    stub = _off_stub()
    assert (stub.far, stub.carrier, stub.facing) == (
        _HIGH_PORT,
        Id(kind="item", value="b" * 32),
        Side.S,
    )


def test_an_off_stub_needs_no_carrier() -> None:
    """A stub of a plain wire has a far and a facing and no carrier."""
    assert dataclasses.replace(_off_stub(), carrier=None).carrier is None


@pytest.mark.parametrize(
    "changes",
    [
        {"far": None},
        {"facing": None},
        {"star": None},
        {"star": StarKind.REF},
        {"star": StarKind.BRANCH},
        {"far": None, "facing": None},
    ],
    ids=[
        "off-without-far",
        "off-without-facing",
        "far-and-facing-on-no-star",
        "on-ref",
        "on-branch",
        "off-bare",
    ],
)
def test_an_off_stub_without_far_and_facing_or_them_on_another_marker_is_a_schema_error(
    changes: dict[str, object],
) -> None:
    """`star is OFF` if and only if `far` is set if and only if `facing` is set."""
    with pytest.raises(SchemaError):
        dataclasses.replace(_off_stub(), **changes)


def test_a_carrier_without_a_far_is_a_schema_error() -> None:
    """A carrier is the carrier of the far conductor: no far, no carrier."""
    owner, _ = _marker_pair()
    with pytest.raises(SchemaError):
        dataclasses.replace(owner, carrier=Id(kind="item", value="b" * 32))


def test_a_label_with_a_positive_box_size_is_accepted() -> None:
    """A label's stored box size constructs when both `width` and `height` are positive."""
    label = _label(function=True, port=False, conductor=False)
    assert (label.width, label.height) == (16, 8)


@pytest.mark.parametrize(("width", "height"), [(0, 4), (8, -1)])
def test_a_label_with_a_non_positive_box_size_is_a_schema_error(*, width: int, height: int) -> None:
    """A zero or negative `width`/`height` cannot be a reserved box, so construction raises."""
    with pytest.raises(SchemaError):
        dataclasses.replace(
            _label(function=True, port=False, conductor=False), width=width, height=height
        )


def test_records_with_every_new_field_set_round_trip() -> None:
    """Enums and `int | None` encode by schema alone: `loads(dumps(m)) == m`, no hand code."""
    owner, user = _marker_pair()
    full = dataclasses.replace(
        owner,
        box_x=40,
        lead=False,
        stub_extra=2,
        via_x=3,
        via_y=4,
        star=StarKind.OFF,
        far=_HIGH_PORT,
        carrier=Id(kind="item", value="b" * 32),
        facing=Side.W,
    )
    item = dataclasses.replace(
        placement(), view=PlacementView.ITEM, ports=("1", "2"), sides=(Side.N, Side.S)
    )
    label = _label(function=True, port=False, conductor=False)
    model = _freeze(
        (*_engineering(), sheet_format(), drawing_set(), page(), item, full, user, label)
    )
    assert loads(dumps(model)) == model
    stored = layout_of(loads(dumps(model)), LinkMarker)[full.id]
    assert (stored.star, stored.box_x, stored.lead) == (StarKind.OFF, 40, False)
    assert (stored.far, stored.carrier, stored.facing) == (
        _HIGH_PORT,
        Id(kind="item", value="b" * 32),
        Side.W,
    )


def test_a_link_marker_with_defaults_is_stored_with_the_default_values() -> None:
    """A marker that sets none of the new fields stores their defaults and loads equal."""
    owner, user = _marker_pair()
    model = _freeze((*_engineering(), sheet_format(), drawing_set(), page(), owner, user))
    row = next(
        row
        for row in json.loads(dumps(model))["tables"]["layout.link_marker"]
        if row["id"] == f"{owner.id.kind}:{owner.id.value}"
    )
    assert {
        name: row[name]
        for name in (
            "box_x",
            "lead",
            "stub_extra",
            "via_x",
            "via_y",
            "star",
            "far",
            "carrier",
            "facing",
        )
    } == {
        "box_x": None,
        "lead": True,
        "stub_extra": 0,
        "via_x": None,
        "via_y": None,
        "star": None,
        "far": None,
        "carrier": None,
        "facing": None,
    }
    assert loads(dumps(model)) == model


def _power_symbol(port: Id[Port] = _LOW_PORT) -> PowerSymbol:
    return PowerSymbol(
        id=Id(kind="layout.power_symbol", value="a" * 32),
        key=("layout", "example-engine", "power_symbol", "examples", "port", "1"),
        port=port,
        page=page().id,
        symbol="power-supply",
        x=64,
        y=48,
        pin_x=64,
        pin_y=72,
        orientation=Orientation.R0,
        produced_by=PRODUCED_BY,
    )


def test_a_power_symbol_is_a_derived_kind_that_round_trips() -> None:
    """The new kind is registered: found by `layout_of`, listed as derived, equal after a load."""
    symbol = _power_symbol()
    model = _freeze((*_engineering(), sheet_format(), drawing_set(), page(), symbol))
    assert layout_of(model, PowerSymbol)[symbol.id] == symbol
    assert symbol.id in derived_layout_ids(model)
    assert loads(dumps(model)) == model


def test_a_power_symbol_on_a_port_that_is_not_there_is_a_freeze_error() -> None:
    """Its `port` is a checked reference."""
    absent = Id(kind="port", value="9" * 32)
    with pytest.raises(FreezeError):
        _freeze((*_engineering(), sheet_format(), drawing_set(), page(), _power_symbol(absent)))
