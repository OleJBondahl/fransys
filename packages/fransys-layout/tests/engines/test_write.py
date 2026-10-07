"""`write_layout`: stage results to derived `layout.*` records (engine.md 7, model
layout-namespace.md)

Most cases doctor a real `StageResults` of the cabinet with `dataclasses.replace`, so one
field at a time is what the writer sees.
"""

import dataclasses
import tomllib
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from layout_cabinet import build_cabinet, unit_with_release

from fransys_layout.engines.schematic.defaults import ENGINE_VERSION
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.engines.schematic.write.keys import WriteKeys
from fransys_layout.engines.schematic.write.unique import check_unique
from fransys_layout.geometry import LayoutError, Orientation, library_version
from fransys_layout.stages import Home, LabelKind, MarkerSide, Role
from fransys_layout.stages import Route as StageRoute
from fransys_layout.stages import RoutePoint as StageRoutePoint
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import LabelKind as ModelLabelKind
from fransys_model.layout import MarkerSide as ModelMarkerSide
from fransys_model.layout import Orientation as ModelOrientation
from fransys_model.layout import Page, PageRole
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.vocab import Boundary, Function, FunctionKind, Item, Port

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_model.kernel import Id, Model

_ORIGIN = Origin(file="tests/engines/test_write.py", line=1, note="write tests")
_X2 = ("cabinet", "x2", "1", "fn", "terminal")


def _authored_sheet(width_mm: int) -> tuple[ModelSheetFormat, ModelProfile]:
    """A sheet `width_mm` wide and the default profile on it: only the width changes."""
    sheet = ModelSheetFormat(
        id=make_id(ModelSheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrow",
        width_mm=width_mm + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = ModelProfile(
        id=make_id(ModelProfile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    return sheet, profile


@cache
def _laid_out(
    *, second_location: bool = False, width_mm: int | None = None
) -> tuple[Model, StageResults, Model]:
    """The frozen cabinet, its stage results, and the model `write_layout` makes of them.

    With `width_mm` the model authors a sheet and a profile that name it.
    """
    draft = build_cabinet(second_location=second_location)
    if width_mm is not None:
        draft.extend(_authored_sheet(width_mm), origin=_ORIGIN)
    model = freeze(draft)
    results, _ = stage_results(model, read_inputs(model))
    return model, results, write_layout(model, results, write_keys(model))


def _table(model: Model, kind: str) -> dict:
    return dict(model.tables[f"layout.{kind}"])


def test_the_engine_version_is_the_package_version() -> None:
    """`produced_by` names the version in `pyproject.toml`, which no code reads at run time."""
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    assert tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"] == (
        ENGINE_VERSION
    )


def test_label_kind_and_marker_side_have_equal_member_names() -> None:
    """`write/labels.py` and `write/markers.py` convert them by member name, as `write/` does
    `Orientation` and `Role`."""
    assert {m.name for m in LabelKind} == {m.name for m in ModelLabelKind}
    assert {m.name for m in MarkerSide} == {m.name for m in ModelMarkerSide}


def test_every_page_names_the_authored_sheet_format_the_profile_names() -> None:
    """The engine creates no `layout.sheet_format`, but a page names the one it is drawn on."""
    model, results, out = _laid_out(width_mm=250)
    sheet_id = make_id(ModelSheetFormat, ("test", "sheet"))
    assert read_inputs(model).sheet_format == sheet_id
    assert results.sheet_format == sheet_id
    pages = _table(out, "page").values()
    assert pages
    assert {page.sheet_format for page in pages} == {sheet_id}


def test_a_page_names_no_sheet_format_when_the_house_sheet_is_used() -> None:
    """Nothing authored: `None` is the house sheet, which is no record (model-0029)."""
    model, results, out = _laid_out()
    assert read_inputs(model).sheet_format is None
    assert results.sheet_format is None
    pages = _table(out, "page").values()
    assert pages
    assert {page.sheet_format for page in pages} == {None}


def test_a_sheet_no_profile_names_is_not_the_sheet_the_pages_are_drawn_on() -> None:
    """engine.md 7 names the sheet only through the profile: an authored sheet alone is ignored."""
    draft = build_cabinet()
    draft.extend((_authored_sheet(250)[0],), origin=_ORIGIN)
    model = freeze(draft)
    results, _ = stage_results(model, read_inputs(model))
    assert {
        page.sheet_format
        for page in _table(write_layout(model, results, write_keys(model)), "page").values()
    } == {None}


def test_a_page_key_is_its_drawing_sets_key_its_first_group_its_role_and_an_ordinal() -> None:
    """The ordinal is `"0"` for a page alone with its first group and role."""
    model, _, out = _laid_out()
    sets = _table(out, "drawing_set")
    for page in _table(out, "page").values():
        drawing_set = sets[page.drawing_set]
        group = model.tables["aspect_node"][page.groups[0].group]
        assert page.key == (*drawing_set.key, *group.key, page.role.value, "0")


def test_the_later_pages_of_a_split_group_get_later_ordinals() -> None:
    """On a narrow sheet a group splits: same first group and role, so the ordinal tells apart."""
    _, _, out = _laid_out(width_mm=150)
    pages = list(_table(out, "page").values())
    ordinals = sorted(page.key[-1] for page in pages)
    assert ordinals[0] == "0"
    assert int(ordinals[-1]) > 0
    assert len({page.id for page in pages}) == len(pages)


def test_the_drawing_set_of_everything_without_a_location_is_keyed_unlocated() -> None:
    """A plan with no location gives `location=None` and the `("unlocated",)` key segment."""
    model, results, _ = _laid_out()
    pages = tuple(dataclasses.replace(plan, location=None) for plan in results.layout.pages)
    layout = dataclasses.replace(results.layout, pages=pages)
    out = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    (drawing_set,) = _table(out, "drawing_set").values()
    assert drawing_set.location is None
    assert drawing_set.key == ("layout", "schematic", "drawing_set", "unlocated")


_DRAWING_SET_KEY_PREFIX_LEN = 3  # ("layout", "schematic", "drawing_set")


def test_a_plan_with_no_unit_gives_the_pre_units_drawing_set_key_byte_for_byte() -> None:
    """Regression pin (units spec U1): `plan.unit=None` adds no key segment at all."""
    _, _, out = _laid_out()
    (drawing_set,) = _table(out, "drawing_set").values()
    assert drawing_set.unit is None
    assert drawing_set.key == ("layout", "schematic", "drawing_set", "c1")


def test_two_units_at_one_location_give_two_drawing_sets_with_distinct_keys() -> None:
    """Units spec U1: the "unit" tag segment keeps two units' drawing sets at one location
    apart, and neither collides with the fixture's own `unit=None` drawing set there."""
    _, results, _ = _laid_out()
    plan = results.layout.pages[0]
    unit_a, release_a = unit_with_release(("cabinet", "unit-a"), name="unit-a")
    unit_b, release_b = unit_with_release(("cabinet", "unit-b"), name="unit-b")
    draft = build_cabinet()
    draft.extend((release_a, release_b, unit_a, unit_b), origin=_ORIGIN)
    with_units = freeze(draft)
    plan_a = dataclasses.replace(plan, unit=unit_a.id, drawing_set=900)
    plan_b = dataclasses.replace(plan, unit=unit_b.id, drawing_set=901)
    layout = dataclasses.replace(results.layout, pages=(*results.layout.pages, plan_a, plan_b))
    out = write_layout(
        with_units, dataclasses.replace(results, layout=layout), write_keys(with_units)
    )
    sets = {s.number: s for s in _table(out, "drawing_set").values()}
    none_set, a_set, b_set = sets[plan.drawing_set], sets[900], sets[901]
    assert none_set.location == a_set.location == b_set.location
    assert len({none_set.key, a_set.key, b_set.key}) == 3
    prefix, where = (
        none_set.key[:_DRAWING_SET_KEY_PREFIX_LEN],
        none_set.key[_DRAWING_SET_KEY_PREFIX_LEN:],
    )
    assert a_set.key == (*prefix, "unit", *unit_a.key, *where)
    assert b_set.key == (*prefix, "unit", *unit_b.key, *where)


def _away_seats(results: StageResults) -> set[tuple[Id[Any], tuple[Any, ...]]]:
    """The `(function, column key)` seats drawn away from their home."""
    return {
        (cell.function, column.key)
        for column in results.columns
        for cell in column.cells
        if cell.home is Home.ELSEWHERE
    }


def _boundary_fixture() -> tuple[Model, Function, StageResults]:
    """A boundary function of a unit nested under a top unit: the home and a black-box replica."""
    top, top_release = unit_with_release(("write-fixture", "top"), name="top")
    child, child_release = unit_with_release(
        ("write-fixture", "child"), name="child", parent=top.id
    )
    item_key = ("write-fixture", "owner")
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag="B1",
        description="boundary fixture item",
        unit=child.id,
    )
    function_key = (*item_key, "fn", "x")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="x",
        kind=FunctionKind.CONNECTOR,
    )
    boundary_record_key = (*child.key, "boundary")
    boundary_record = Boundary(
        id=make_id(Boundary, boundary_record_key),
        key=boundary_record_key,
        unit=child.id,
        function=function.id,
    )
    draft = Draft()
    draft.extend(
        (top_release, child_release, top, child, item, function, boundary_record), origin=_ORIGIN
    )
    model = freeze(draft)
    results, _ = stage_results(model, read_inputs(model))
    return model, function, results


def _placements_of(out: Model, function: Function) -> list:
    return [p for p in _table(out, "symbol_placement").values() if p.function == function.id]


def test_a_boundary_replicas_placement_never_collides_with_its_homes() -> None:
    """Units spec U1's black box: a boundary function drawn in its own unit's set (the home)
    and again in the parent unit's set (the black box) gets two distinct `SymbolPlacement`
    ids and keys -- confirmed here, not assumed, because `replicate_boundaries` gives the
    replica no new `write/placements.py` handling of its own: it relies on the replica discriminator
    (`write.placements.placements`'s `extra`) that `replicas` already gives every replica column.
    """
    model, function, results = _boundary_fixture()
    placements = _placements_of(write_layout(model, results, write_keys(model)), function)
    assert len(placements) == 2
    assert len({p.id for p in placements}) == 2
    assert len({p.key for p in placements}) == 2


def test_replicas_of_one_function_and_group_in_two_drawing_sets_get_two_keys() -> None:
    """Layout-0076: a replica's key holds its drawing set's key (never its number), so the
    same function drawn as a replica of one group in two sets is two records, not one id twice.

    The black box in the parent's set is cloned into the child's set: one function, one column
    (so one group), two drawing sets. The home keeps the bare function key.

    UNDO: `write/placements.py` `placements`, drop the `"drawing_set", ...` part of the replica's
    `extra` (the line after `extra = nodes[group].key ...`): the clone then has the black box's
    key and `write_layout` raises `LayoutError` (the key guard) instead of returning.
    """
    model, function, results = _boundary_fixture()
    placed = results.layout.placed
    away = _away_seats(results)
    replica = next(p for p in placed if (p.function, p.column) in away)
    home = next(p for p in placed if (p.function, p.column) not in away)
    assert replica.drawing_set != home.drawing_set
    clone = dataclasses.replace(replica, drawing_set=home.drawing_set, page=home.page)
    layout = dataclasses.replace(results.layout, placed=(*placed, clone))
    out = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    keys = sorted(p.key for p in _placements_of(out, function))
    assert len(keys) == len(set(keys)) == 3
    home_key = ("layout", "schematic", "symbol_placement", *function.key)
    assert home_key in keys
    replica_keys = [key for key in keys if key != home_key]
    assert all("drawing_set" in key for key in replica_keys)
    assert len({key[key.index("drawing_set") :] for key in replica_keys}) == 2


def test_two_records_of_one_key_raise_a_layout_error_naming_both_and_their_sets() -> None:
    """A placement drawn twice with one key is an engine bug the writer names, not a bare
    `SchemaError` from `evolve`.

    UNDO: `write/__init__.py`, delete the `check_unique(...)` call: the error is then `evolve`'s
    `SchemaError`, not a `LayoutError`, and this test fails.
    """
    model, function, results = _boundary_fixture()
    away = _away_seats(results)
    replica = next(p for p in results.layout.placed if (p.function, p.column) in away)
    layout = dataclasses.replace(results.layout, placed=(*results.layout.placed, replica))
    with pytest.raises(LayoutError, match="two SymbolPlacement records share one key") as raised:
        write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    message = str(raised.value)
    assert message.count(str(function.key)) == 2
    assert message.count("in drawing set ('layout', 'schematic', 'drawing_set', 'unit'") == 2


def test_the_key_guard_passes_distinct_keys_and_trips_on_one_shared_key() -> None:
    """`check_unique` on the written placements: their own keys are distinct and pass; a list
    that holds one twice raises, and a copy with another key does not.

    UNDO: `write/unique.py`, `check_unique`, key `seen` on `(type(record), id(record))` instead of
    `(type(record), record.key)`: the duplicate gets through and the `raises` below fails.
    """
    model, function, results = _boundary_fixture()
    keys = write_keys(model)
    out = write_layout(model, results, keys)
    sets = {s.id: s.key for s in _table(out, "drawing_set").values()}
    set_of_page = {page.id: sets[page.drawing_set] for page in _table(out, "page").values()}
    first, second = _placements_of(out, function)
    check_unique(keys, [first, second], set_of_page)
    with pytest.raises(LayoutError, match="share one key"):
        check_unique(keys, [first, second, dataclasses.replace(first)], set_of_page)
    check_unique(keys, [first, dataclasses.replace(first, key=(*first.key, "other"))], set_of_page)


@dataclasses.dataclass(frozen=True)
class _Stub:
    """A hand-made record: the `Record` members and the fields `check_unique` reads."""

    id: Id
    key: tuple[str, ...]
    ext: Any  # the `Record` protocol asks for a `frozendict`; the guard never reads it
    function: Id | None
    port: Id | None
    page: Id


def test_the_key_guard_names_both_records_from_a_hand_built_key_table() -> None:
    """Two records of one kind and one key raise, and the message takes each record's subject
    from the key table: a function's key, or its port's function's key, and its drawing set.

    UNDO: `write/unique.py`, `check_unique`, call `_describe` with `first` in place of `record` in
    the second half of the message: the two subjects are then the same and the equality fails.
    """
    func_a, func_b = make_id(Function, ("t", "a")), make_id(Function, ("t", "b"))
    port_b = make_id(Port, ("t", "b", "1"))
    page_a, page_b = make_id(Page, ("t", "pa")), make_id(Page, ("t", "pb"))
    keys = WriteKeys(
        function={func_a: ("t", "a"), func_b: ("t", "b")},
        port={port_b: ("t", "b", "1")},
        conductor={},
        item={},
        unit={},
        aspect_node={},
        port_function={port_b: func_b},
        port_name={port_b: "1"},
        item_function={},
    )
    set_of_page = {page_a: ("set", "one"), page_b: ("set", "two")}
    first = _Stub(id=func_a, key=("k",), ext={}, function=func_a, port=None, page=page_a)
    second = _Stub(id=func_b, key=("k",), ext={}, function=None, port=port_b, page=page_b)
    with pytest.raises(LayoutError) as raised:
        check_unique(keys, [first, second], set_of_page)
    assert str(raised.value) == (
        "two _Stub records share one key: ('t', 'a') in drawing set ('set', 'one') "
        "and ('t', 'b') in drawing set ('set', 'two')"
    )


def test_a_page_takes_its_role_and_groups_from_its_plan() -> None:
    """`Role` becomes `PageRole` by name, and the plan's groups keep their index.

    The cabinet declares one control net, so every page is `CONTROL`; the first plan is made
    a power page here to see the conversion tell two roles apart.
    """
    model, results, _ = _laid_out()
    first, *rest = results.layout.pages
    plans = (dataclasses.replace(first, role=Role.POWER), *rest)
    out = write_layout(
        model,
        dataclasses.replace(results, layout=dataclasses.replace(results.layout, pages=plans)),
        write_keys(model),
    )
    by_number = {(p.drawing_set, p.number): p for p in plans}
    sets = {s.id: s.number for s in _table(out, "drawing_set").values()}
    assert {p.role for p in _table(out, "page").values()} == {PageRole.POWER, PageRole.CONTROL}
    for page in _table(out, "page").values():
        plan = by_number[sets[page.drawing_set], page.number]
        assert page.role is PageRole[plan.role.name]
        assert [(g.group, g.index) for g in page.groups] == [
            (g.group, g.index) for g in plan.groups if g.group is not None
        ]


def test_a_placement_turns_the_geometry_orientation_into_the_models_by_name() -> None:
    """R90 in the geometry is `Orientation.R90` in the record."""
    model, results, _ = _laid_out()
    first = results.layout.placed[0]
    turned = dataclasses.replace(
        first, geometry=dataclasses.replace(first.geometry, orientation=Orientation.R90)
    )
    layout = dataclasses.replace(results.layout, placed=(turned, *results.layout.placed[1:]))
    out = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    (found,) = (
        p
        for p in _table(out, "symbol_placement").values()
        if (p.function, p.x, p.y) == (first.function, first.at.x, first.at.y)
    )
    assert found.orientation is ModelOrientation.R90


def test_a_placement_pins_the_symbol_key_poles_and_library_version() -> None:
    """The geometry that computed the position is named in the record."""
    _, results, out = _laid_out()
    placements = _table(out, "symbol_placement").values()
    assert len(placements) == len(results.layout.placed)
    assert {p.library_version for p in placements} == {library_version()}
    assert {(p.symbol, p.poles) for p in placements} == {
        (one.geometry.key, one.geometry.poles) for one in results.layout.placed
    }
    assert 3 in {p.poles for p in placements}


def test_a_label_stores_its_source_and_the_boxs_corner_and_size_and_no_text() -> None:
    """No field for text; x, y is the box's top-left corner, width and height its size."""
    _, results, out = _laid_out()
    labels = _table(out, "label").values()
    fields = {f.name for f in dataclasses.fields(next(iter(labels)))}
    assert fields == {
        "id",
        "key",
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
        "ext",
    }
    assert {(x.x, x.y, x.width, x.height) for x in labels} == {
        (x.box.x, x.box.y, x.box.width, x.box.height) for x in results.layout.labels
    }
    assert len(labels) == len(results.layout.labels)


def test_a_route_written_from_swapped_ends_equals_the_one_written_from_the_ordered_ends() -> None:
    """The model puts `a` and `b` in id order and turns the polyline; the writer adds nothing."""
    model, results, out = _laid_out()
    original = results.layout.routes[0]
    count = len(original.points)
    swapped = StageRoute(
        connection=original.connection,
        physical_net=original.physical_net,
        drawing_set=original.drawing_set,
        page=original.page,
        a=original.b,
        b=original.a,
        points=tuple(
            StageRoutePoint(index=i, at=original.points[count - 1 - i].at) for i in range(count)
        ),
    )
    layout = dataclasses.replace(results.layout, routes=(swapped, *results.layout.routes[1:]))
    again = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    assert _table(again, "route") == _table(out, "route")
    route = next(r for r in _table(out, "route").values() if (r.a, r.b) == (original.a, original.b))
    assert [(p.x, p.y) for p in route.points] == [(p.at.x, p.at.y) for p in original.points]


def test_a_terminal_on_two_pages_keeps_its_home_key_and_the_replica_adds_its_group() -> None:
    """X2:1 is at home in `=SUP` and replicated for `=P1`: two ids, the second ending in `p1`."""
    model, _, out = _laid_out()
    (function,) = (f.id for f in model.tables["function"].values() if f.key == _X2)
    found = sorted(
        (p for p in _table(out, "symbol_placement").values() if p.function == function),
        key=lambda p: p.key,
    )
    base = ("layout", "schematic", "symbol_placement", *_X2)
    assert [p.key for p in found] == [base, (*base, "p1", "drawing_set", "c1")]
    assert len({p.id for p in found}) == 2
    assert len({p.page for p in found}) == 2


def test_a_replica_with_no_group_gets_the_ungrouped_discriminator() -> None:
    """Without one its key would be the home placement's (decision layout-0029)."""
    model, results, _ = _laid_out()
    (function,) = (f.id for f in model.tables["function"].values() if f.key == _X2)
    # V4: the only replica of the cabinet is attached, a cell of its host's column
    hosting = {
        c.key
        for c in results.columns
        for cell in c.cells
        if cell.home is Home.ELSEWHERE and cell.function == function
    }
    columns = tuple(
        dataclasses.replace(c, group=None) if c.key in hosting else c for c in results.columns
    )
    out = write_layout(model, dataclasses.replace(results, columns=columns), write_keys(model))
    base = ("layout", "schematic", "symbol_placement", *_X2)
    keys = {p.key for p in _table(out, "symbol_placement").values()}
    assert (*base, "ungrouped", "drawing_set", "c1") in keys
    assert (*base, "p1", "drawing_set", "c1") not in keys


_SIGNAL = (
    ("cabinet", "k1", "fn", "aux", "port", "14"),
    ("cabinet", "k2", "fn", "aux", "port", "13"),
)


def _signal_ports(model: Model) -> set:
    """The ports of the K1:14 to K2:13 signal: on the 250 mm sheet its wire is cut by a page."""
    return {id_ for id_, port in model.tables["port"].items() if port.key in _SIGNAL}


def test_each_marker_points_at_the_other_end_and_the_other_end_points_back() -> None:
    """A wire cut by a page break (links.md 6.6, which D9 leaves: it is no net of 3 or more ports)
    has a pair: opposite sides, two pages, `partner` of `partner` is itself.

    Across two locations the same conductor is a stub label at each end (D10), so the cut is
    made by the 250 mm sheet's page break.
    """
    model, _, out = _laid_out(width_mm=250)
    signal = _signal_ports(model)
    markers = {id_: m for id_, m in _table(out, "link_marker").items() if m.port in signal}
    assert len(markers) == 2
    for marker in markers.values():
        partner = markers[marker.partner]
        assert markers[partner.partner] is marker
        assert {marker.side, partner.side} == {ModelMarkerSide.OWNER, ModelMarkerSide.USER}
        assert marker.page != partner.page


def test_a_net_of_three_or_more_ports_has_a_reference_marker_and_branch_markers_that_name_it() -> (
    None
):
    """D9: one marker per port; the reference is the net's single terminal point.

    The 24 V rail net has five ports: terminal `-X2:1` (external side) and the contacts and
    lamp `-S0:11`, `-S1:11`, `-S2:11`, `-H1:1`. Its only terminal point is `-X2:1`, so it is the
    reference. Each branch names it, on its own page when the reference stands there (page 1
    has `-S0`, `-S1`, `-S2`, page 2 has `-H1`, and `-X2:1` is on both), and each reference
    marker leads to a branch on its page. The cabinet's other net, K1:13 to S0:22, is a turned
    reference pair (S12, M12), its own ref and branch: it is not this net's and is left out.
    """
    model, results, out = _laid_out()
    port_of = {port.key: id_ for id_, port in model.tables["port"].items()}
    rail = port_of["cabinet", "x2", "1", "fn", "terminal", "port", "external"]
    others = {
        port_of["cabinet", tag, "fn", function, "port", pin]
        for tag, function, pin in (
            ("s0", "nc_1", "11"),
            ("s1", "nc_1", "11"),
            ("s2", "nc_1", "11"),
            ("h1", "lamp", "1"),
        )
    }
    stars = [
        marker
        for marker in results.layout.markers
        if marker.star in ("ref", "branch") and marker.port in others | {rail}
    ]
    assert stars
    assert {marker.port for marker in stars if marker.star == "ref"} == {rail}
    # V4: -X2:1 stands over -S0's pin on page 1, so -S0 needs no branch of the star
    under_the_terminal = port_of["cabinet", "s0", "fn", "nc_1", "port", "11"]
    branches = sorted(marker.port for marker in stars if marker.star == "branch")
    assert branches == sorted(others - {under_the_terminal})
    assert {marker.star_partner for marker in stars if marker.star == "branch"} == {rail}
    records = _table(out, "link_marker")
    named = [record for record in records.values() if record.port in others | {rail}]
    assert len(named) == len(stars)
    for record in named:
        partner = records[record.partner]
        assert partner.page == record.page
        assert (partner.port == rail) if record.port in others else (partner.port in others)


def test_an_owner_marker_without_its_user_marker_raises() -> None:
    """A pair that does not pair up is an engine-assembly fault."""
    model, results, _ = _laid_out(width_mm=250)
    signal = _signal_ports(model)
    owner = next(
        m for m in results.layout.markers if m.port in signal and m.side is MarkerSide.OWNER
    )
    layout = dataclasses.replace(results.layout, markers=(owner,))
    with pytest.raises(LayoutError, match="do not pair up"):
        write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))


def test_a_pair_whose_owner_is_not_on_the_earlier_page_raises() -> None:
    """`links` puts the owner on the earlier page: a pair with its sides swapped breaches that."""
    model, results, _ = _laid_out(width_mm=250)
    signal = _signal_ports(model)
    swapped = tuple(
        dataclasses.replace(
            marker, side=MarkerSide.USER if marker.side is MarkerSide.OWNER else MarkerSide.OWNER
        )
        if marker.port in signal
        else marker
        for marker in results.layout.markers
    )
    layout = dataclasses.replace(results.layout, markers=swapped)
    with pytest.raises(LayoutError, match="earlier page"):
        write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))


def test_a_run_leaves_the_engineering_digests_alone_and_repeats_its_own() -> None:
    """`core` and `facet` are untouched; two writes of one result give one `layout` digest."""
    model, results, out = _laid_out()
    assert out.digests["core"] == model.digests["core"]
    assert out.digests["facet"] == model.digests["facet"]
    assert out.digests["layout"] != model.digests["layout"]
    again = write_layout(model, results, write_keys(model))
    assert again.digests["layout"] == out.digests["layout"]


def test_no_page_carries_a_wire_label_while_tags_and_markings_are_still_written() -> None:
    """V8: the wire label is in the wire list and the sleeves only; pages print none."""
    _, _, out = _laid_out()
    kinds = {x.kind for x in _table(out, "label").values()}
    assert ModelLabelKind.WIRE not in kinds
    assert {ModelLabelKind.TAG, ModelLabelKind.MARKING} <= kinds
