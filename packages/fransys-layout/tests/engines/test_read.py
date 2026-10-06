"""WP13 unit tests for the `read/` package alone: poles, tags, group hints, authored profile
(docs/design/engine.md 7).

`test_schematic.py` holds the acceptance skeletons shared with the rest of WP13; this file
covers `read_inputs` behaviour that fixture's skeletons do not reach. Items and functions are
found by authoring key, never by designation.
"""

import dataclasses
from decimal import Decimal

from layout_cabinet import build_cabinet, unit_with_release

from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_SHEET
from fransys_layout.stages import LabelKind, PolePair, Role
from fransys_model.kernel import Draft, Origin, evolve, freeze, make_id
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.vocab import AspectNode, Boundary, Item, Unit
from fransys_model.vocab.tables import items as items_table

_ORIGIN = Origin(file="tests/engines/test_read.py", line=1, note="read.py unit tests")


def _function(model, item_key: tuple[str, ...], name: str):
    key = (*item_key, "fn", name)
    (function,) = (f for f in model.tables["function"].values() if f.key == key)
    return function


def _spec(model, item_key: tuple[str, ...], name: str):
    function = _function(model, item_key, name)
    inputs = read_inputs(model)
    (spec,) = (s for s in inputs.functions if s.function == function.id)
    return spec


def test_a_three_pole_contact_has_three_poles_and_three_pole_pairs() -> None:
    """Contactor `K1`'s `main` function links ports 1-2, 3-4, 5-6: three poles."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "k1"), "main")
    assert spec.poles == 3
    assert spec.pole_pairs == (
        PolePair(index=0, first="1", second="2"),
        PolePair(index=1, first="3", second="4"),
        PolePair(index=2, first="5", second="6"),
    )


def test_a_single_pole_contact_has_one_pole_and_one_pair() -> None:
    """Contactor `K1`'s `aux` function links 13-14: one pole, one pair."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "k1"), "aux")
    assert spec.poles == 1
    assert spec.pole_pairs == (PolePair(index=0, first="13", second="14"),)


def test_a_function_with_no_internal_link_has_one_pole_and_no_pairs() -> None:
    """A coil has no internal link between `A1` and `A2`: one pole, no pairs (open-questions.md
    13.7)."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "k1"), "coil")
    assert spec.poles == 1
    assert spec.pole_pairs == ()


def test_tag_text_of_a_normal_function_is_the_item_designation() -> None:
    """A non-terminal function's TAG text is the item designation only, "-K1" (D12 amended,
    layout-0066: no aspect segments, top level included)."""
    model = freeze(build_cabinet())
    function = _function(model, ("cabinet", "k1"), "coil")
    inputs = read_inputs(model)
    (tag,) = (t for t in inputs.label_texts if t.subject == function.id and t.kind is LabelKind.TAG)
    assert tag.text == "-K1"


def test_tag_text_of_a_terminal_function_is_strip_colon_marking() -> None:
    """A terminal function's TAG text is the strip designation, a colon, its marking (6b(i)),
    always dash-prefixed (decision model-0052)."""
    model = freeze(build_cabinet())
    function = _function(model, ("cabinet", "x1", "1"), "terminal")
    inputs = read_inputs(model)
    (tag,) = (t for t in inputs.label_texts if t.subject == function.id and t.kind is LabelKind.TAG)
    assert tag.text == "-X1:1"


def test_group_hint_is_read_from_the_authored_hint() -> None:
    """`S0`'s `nc_2` function carries a `layout.group_hint` to `=P1`."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "s0"), "nc_2")
    assert spec.group_hint == make_id(AspectNode, ("p1",))


def test_group_hint_is_none_when_no_hint_is_authored() -> None:
    """`S0`'s `nc_1` function carries no hint."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "s0"), "nc_1")
    assert spec.group_hint is None


def test_group_and_location_paths_come_from_the_items_placements() -> None:
    """A function placed at `=P1` and `+C1` reports both paths root to leaf."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "k1"), "coil")
    assert spec.group_path == (make_id(AspectNode, ("p1",)),)
    assert spec.location_path == (make_id(AspectNode, ("c1",)),)


def test_a_function_specs_unit_is_none_with_no_units_authored() -> None:
    """The default cabinet authors no `Unit`: every spec's `unit` is `None` (units spec U1)."""
    model = freeze(build_cabinet())
    spec = _spec(model, ("cabinet", "k1"), "coil")
    assert spec.unit is None
    assert read_inputs(model).units == ()


def test_a_function_specs_unit_is_copied_from_its_items_own_unit() -> None:
    """`unit` on `FunctionSpec` is copied straight from the item's own `unit` (units spec U1)."""
    model = freeze(build_cabinet())
    item_id = make_id(Item, ("cabinet", "k1"))
    unit, release = unit_with_release(("cabinet", "unit-k1"), name="unit-k1")
    item = items_table(model)[item_id]
    with_unit = evolve(
        model,
        remove=(item_id,),
        put=(dataclasses.replace(item, unit=unit.id), release, unit),
        origin=_ORIGIN,
    )
    spec = _spec(with_unit, ("cabinet", "k1"), "coil")
    assert spec.unit == unit.id
    assert unit.id in {info.unit for info in read_inputs(with_unit).units}


def test_read_uses_an_authored_profile_and_the_sheet_format_it_names() -> None:
    """An authored `layout.profile` and the sheet it names override the house defaults."""
    sheet_key = ("test", "sheet")
    sheet = ModelSheetFormat(
        id=make_id(ModelSheetFormat, sheet_key),
        key=sheet_key,
        name="invented sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=200,
        content_height_mm=100,
        frame_columns=4,
        frame_rows=2,
        module_mm=Decimal("2.5"),
    )
    profile_key = ("test", "profile")
    profile = ModelProfile(
        id=make_id(ModelProfile, profile_key),
        key=profile_key,
        sheet_format=sheet.id,
        column_gap=40,
        row_gap=24,
        route_margin=48,
        text_height=6,
        marker_padding=3,
        route_turn_penalty=2,
        route_crossing_penalty=8,
    )
    draft = Draft()
    draft.extend((sheet, profile), origin=_ORIGIN)
    model = freeze(draft)

    inputs = read_inputs(model)

    assert inputs.profile.column_gap == 40
    assert inputs.profile.row_gap == 24
    assert inputs.profile.route_margin == 48
    assert inputs.profile.text_height == 6
    assert inputs.profile.marker_padding == 3
    assert inputs.profile.route_turn_penalty == 2
    assert inputs.profile.route_crossing_penalty == 8
    assert inputs.sheet.name == "invented sheet"
    assert inputs.sheet.frame_columns == 4
    assert inputs.sheet.frame_rows == 2
    # content_extent: floor(mm * 8 / module_mm) = floor(200 * 8 / 2.5) = 640
    assert inputs.sheet.content_width == 640
    assert inputs.sheet.content_height == 320


def _authored(**numbers) -> Draft:
    """A draft with one `layout.profile` of `numbers`, naming no sheet, and no sheet record."""
    key = ("test", "profile")
    draft = Draft()
    draft.extend((ModelProfile(id=make_id(ModelProfile, key), key=key, **numbers),), origin=_ORIGIN)
    return draft


def test_read_an_authored_profile_with_no_sheet_reads_the_house_sheet_and_no_sheet_id() -> None:
    """`sheet_format=None` names no record: the authored numbers, the house sheet, no sheet id."""
    inputs = read_inputs(freeze(_authored(column_gap=40)))

    assert inputs.profile.column_gap == 40
    assert inputs.sheet == DEFAULT_SHEET
    assert inputs.sheet_format is None


def test_read_an_authored_row_spacing_reaches_the_stage_profile() -> None:
    """`Profile.row_spacing` is a field the reader converts, not an engine constant."""
    assert read_inputs(freeze(_authored(row_spacing=96))).profile.row_spacing == 96
    assert read_inputs(freeze(_authored())).profile.row_spacing == 88


def _boundary(unit: Unit, function_id) -> Boundary:
    key = (*unit.key, "boundary")
    return Boundary(id=make_id(Boundary, key), key=key, unit=unit.id, function=function_id)


def test_a_board_that_is_the_sole_root_of_its_unit_keeps_its_own_home_page() -> None:
    """OLD premise (`board_only_units`/`drop_board_unit_homes`, deleted this work order): a
    unit whose direct items are all on a board held nothing the schematic engine drew of its
    own, so its home-set `PagePlan` was dropped entirely -- board spec B1 excluded everything
    but the board's own `CONNECTOR` function, and `replicate_boundaries` redrew that connector
    in the parent unit's set, so home was empty by construction.

    NEW premise (units spec U1's board-unit ruling, model-0041): this same board (`A1`, with
    child fuse `F10`) is the *sole* root item of its own unit, so it is itself a nested unit,
    not board-inside-a-unit furniture -- `schematic_functions` now draws the fuse's function
    too, not only the board's edge connector, so the unit's home set is no longer empty and
    must not be dropped.

    NEW assertion: `run_stages` produces a `PagePlan` for this unit (`layout.pages` has one
    whose `unit` is the unit's id) and that page actually places both the board's `edge`
    connector and the fuse's `element` function -- not merely "a page exists", but that its
    real content survived.
    """
    model = freeze(build_cabinet())
    parent, parent_release = unit_with_release(
        ("read-fixture", "board-unit-parent"), name="board-unit-parent"
    )
    unit, release = unit_with_release(
        ("read-fixture", "board-unit"), name="board-unit", parent=parent.id
    )
    table = items_table(model)
    board = table[make_id(Item, ("cabinet", "a1"))]
    fuse = table[make_id(Item, ("cabinet", "a1", "f1"))]
    edge = _function(model, ("cabinet", "a1"), "edge")
    element = _function(model, ("cabinet", "a1", "f1"), "element")
    with_units = evolve(
        model,
        remove=(board.id, fuse.id),
        put=(
            parent_release,
            release,
            parent,
            unit,
            dataclasses.replace(board, unit=unit.id),
            dataclasses.replace(fuse, unit=unit.id),
            _boundary(unit, edge.id),
        ),
        origin=_ORIGIN,
    )
    inputs = read_inputs(with_units)
    assert element.id in {spec.function for spec in inputs.functions}

    layout, _drawn, _findings = run_stages(with_units, inputs)
    own_pages = [page for page in layout.pages if page.unit == unit.id]
    assert len(own_pages) == 1
    (own_page,) = own_pages
    placed_here = {
        placed.function
        for placed in layout.placed
        if placed.drawing_set == own_page.drawing_set and placed.page == own_page.number
    }
    # R7 A (deep dive): the edge connector is drawn as its pin views
    edge_pins = {s.function for s in inputs.functions if s.pin_function == edge.id}
    assert edge_pins
    assert edge_pins <= placed_here
    assert element.id in placed_here


def test_a_net_group_role_comes_from_its_net_class() -> None:
    """The `LATCH` net is `NetClass.CONTROL`, so its `NetGroup` role is `CONTROL`."""
    model = freeze(build_cabinet())
    inputs = read_inputs(model)
    (group,) = inputs.net_groups
    assert group.role is Role.CONTROL


def test_a_jumper_is_no_layout_connection_and_is_never_routed() -> None:
    """Terminal bridges spec T3: a `jumper` conductor is not drawn, routed or labelled and
    joins no net for discovery, while a wire between the same two ports would be. Can-fail:
    make the conductor a `wire` and both assertions fail."""
    from fransys_layout.engines import lay_out_schematic
    from fransys_model.layout import Route, layout_of
    from fransys_model.vocab import Conductor, ConductorKind
    from fransys_model.vocab.tables import conductors

    model = freeze(build_cabinet())
    wire = min(conductors(model).values(), key=lambda c: c.id)
    key = ("read-fixture", "jumper")
    jumper = Conductor(
        id=make_id(Conductor, key),
        key=key,
        a=wire.a,
        b=wire.b,
        kind=ConductorKind.JUMPER,
        carrier=None,
    )
    bridged = evolve(model, put=(jumper,), origin=_ORIGIN)

    assert jumper.id not in {c.handle for c in read_inputs(bridged).connections}
    written, _findings = lay_out_schematic(bridged)
    assert jumper.id not in {r.conductor for r in layout_of(written, Route).values()}


def test_a_port_the_part_marks_with_nothing_gets_no_marking_label() -> None:
    """I4 R1: a port whose part prints no marking (`Port.marking == ""`) gets no MARKING
    label; one with a marking prints it in place of its name. Can-fail: read the port's name
    again and the first assertion fails."""
    from fransys_layout.engines import lay_out_schematic
    from fransys_model.derive.drawing_text import label_text
    from fransys_model.layout import Label, LabelKind, layout_of
    from fransys_model.vocab.tables import ports

    model = freeze(build_cabinet())
    coil = _function(model, ("cabinet", "k1"), "coil")
    a1, a2 = sorted(
        (p for p in ports(model).values() if p.function == coil.id), key=lambda p: p.name
    )
    marked = evolve(
        model,
        remove=(a1.id, a2.id),
        put=(
            dataclasses.replace(a1, marking=""),
            dataclasses.replace(a2, marking="X9"),
        ),
        origin=_ORIGIN,
    )
    written, _findings = lay_out_schematic(marked)
    markings = {
        label.port: label_text(written, label)
        for label in layout_of(written, Label).values()
        if label.kind is LabelKind.MARKING and label.port in (a1.id, a2.id)
    }
    assert a1.id not in markings
    assert set(markings.values()) == {"X9"}
