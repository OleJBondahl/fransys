"""WP "drawing text": `derive.drawing_text` (render spec D2, decision model-0032).

Hand-built records only, on the model's synthetic plant: every formatter case and every
branch of every reader (`marker_text`, `cross_reference_text`, `label_text`, `page_title`).
"""

import itertools
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from derive_helpers import add_all

from fransys_model.derive.drawing_text import (
    _placements_by_function_page,
    _position_between,
    content_extent,
    cross_reference_text,
    external_note,
    frame_column,
    frame_row,
    label_text,
    marker_text,
    outline_title,
    page_title,
    page_title_groups,
    partner_position_text,
    port_marking,
    position_text,
    unit_label,
    wire_label_text,
)
from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, freeze, make_id
from fransys_model.layout import (
    CrossReferencePartner,
    DrawingSet,
    Label,
    LabelKind,
    LinkMarker,
    MarkerSide,
    Orientation,
    Page,
    PageGroup,
    PageRole,
    SheetFormat,
    StarKind,
    SymbolPlacement,
    default_sheet_format,
    layout_of,
)
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import Aspect, ConductorKind, FunctionKind, PortRole
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from collections.abc import Callable

PRODUCED_BY = "test-engine 0.0.0"

# The house-conventions sheet, in grid units, used by every test: content_width_mm=400,
# module_mm=2.5 -> 400 * 8 // 2.5 = 1280 grid units of content width, 8 frame columns.
CONTENT_WIDTH_GRID = 1280
FRAME_COLUMNS = 8
# The row twin: content_height_mm=257, module_mm=2.5 -> 257 * 8 // 2.5 = 822 grid units of
# content height, 6 frame rows.
CONTENT_HEIGHT_GRID = 822
FRAME_ROWS = 6


def _ids() -> Callable[[str], Id[Any]]:
    """A fresh id maker: distinct `kind`s may safely reuse the same numeric value."""
    counter = itertools.count(1)

    def make(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    return make


def _key(id_: Id[Any], *tail: str) -> tuple[str, ...]:
    return (str(id_.value)[:8], *tail)


def _sheet(new_id: Callable[[str], Id[Any]]) -> SheetFormat:
    id_ = new_id("layout.sheet_format")
    return SheetFormat(
        id=id_,
        key=_key(id_),
        name="test sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=FRAME_COLUMNS,
        frame_rows=FRAME_ROWS,
        module_mm=Decimal("2.5"),
    )


def _drawing_set(
    new_id: Callable[[str], Id[Any]], *, number: int, location: Id[AspectNode] | None = None
) -> DrawingSet:
    id_ = new_id("layout.drawing_set")
    return DrawingSet(
        id=id_, key=_key(id_), location=location, number=number, produced_by=PRODUCED_BY
    )


def _page(
    new_id: Callable[[str], Id[Any]],
    *,
    drawing_set: Id[DrawingSet],
    number: int,
    sheet_format: Id[SheetFormat] | None,
) -> Page:
    id_ = new_id("layout.page")
    return Page(
        id=id_,
        key=_key(id_),
        drawing_set=drawing_set,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format,
        groups=(),
        produced_by=PRODUCED_BY,
    )


def _item(new_id: Callable[[str], Id[Any]], *, designation: str) -> Item:
    id_ = new_id("item")
    return Item(
        id=id_,
        key=_key(id_),
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="an invented item",
    )


def _function(
    new_id: Callable[[str], Id[Any]], *, item: Id[Item], kind: FunctionKind = FunctionKind.COIL
) -> Function:
    id_ = new_id("function")
    return Function(id=id_, key=_key(id_), item=item, template=None, name="fn", kind=kind)


def _port(
    new_id: Callable[[str], Id[Any]],
    *,
    function: Id[Function],
    name: str = "1",
    marking: str | None = None,
) -> Port:
    id_ = new_id("port")
    return Port(
        id=id_,
        key=_key(id_),
        function=function,
        template=None,
        name=name,
        role=PortRole.GENERIC,
        marking=marking,
    )


def _conductor(new_id: Callable[[str], Id[Any]], *, a: Id[Port], b: Id[Port]) -> Conductor:
    id_ = new_id("conductor")
    return Conductor(id=id_, key=_key(id_), a=a, b=b, kind=ConductorKind.WIRE, carrier=None)


def _placement(
    new_id: Callable[[str], Id[Any]], *, function: Id[Function], page: Id[Page], y: int = 0
) -> SymbolPlacement:
    """A partner's `SymbolPlacement` on `page`: `_partner_row` reads its `y` (drawing_text.py)."""
    id_ = new_id("layout.symbol_placement")
    return SymbolPlacement(
        id=id_,
        key=_key(id_),
        function=function,
        page=page,
        x=0,
        y=y,
        orientation=Orientation.R0,
        poles=1,
        symbol="generic",
        library_version="0.0.0",
        produced_by=PRODUCED_BY,
    )


# --------------------------------------------------------------------------------------
# frame_column, position_text: pure formatters
# --------------------------------------------------------------------------------------


def test_frame_column_clamps_below_the_first_column() -> None:
    """A negative `x` still clamps to column 1."""
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, -100) == 1


def test_frame_column_clamps_above_the_last_column() -> None:
    """An `x` past the content box clamps to the last column."""
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 100_000) == FRAME_COLUMNS


def test_frame_column_divides_the_content_box_evenly() -> None:
    """A column in the middle of the box comes from the even division, 1-based."""
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 0) == 1
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, CONTENT_WIDTH_GRID // 2) == 5


@pytest.mark.parametrize(
    ("x", "column"),
    [(0, 1), (159, 1), (160, 2), (1279, 8), (1280, 8), (5000, 8), (-100, 1)],
)
def test_frame_column_edges_of_an_8_column_sheet(x: int, column: int) -> None:
    """160 G per column; the right edge and beyond cite column 8, left of the sheet column 1.

    Moved here from layout's `test_links.py` when `LinkMarker.partner_column` was dropped
    (S20 4b6d): the rule lives in `frame_column`, read at print time (layout-0089).
    """
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, x) == column


@pytest.mark.parametrize(("x", "column"), [(117, 1), (118, 1), (119, 2), (949, 8), (950, 8)])
def test_frame_column_divides_by_the_exact_width_not_a_rounded_one(x: int, column: int) -> None:
    """950 G over 8 columns is 118.75 G each: column 2 starts at 119, not at 118."""
    assert frame_column(950, 8, x) == column


def test_frame_column_count_comes_from_the_sheet() -> None:
    """The same x on a 4-column sheet is column 3, not 5."""
    assert frame_column(CONTENT_WIDTH_GRID, 4, 704) == 3
    assert frame_column(CONTENT_WIDTH_GRID, 8, 704) == 5


def test_content_extent_floors_millimetres_to_whole_grid_units() -> None:
    """297 mm is 950.4 G at module 2.5 mm: the extent is 950, never 951."""
    assert content_extent(400, Decimal("2.5")) == 1280
    assert content_extent(297, Decimal("2.5")) == 950


def test_content_extent_is_exact_on_a_whole_multiple_and_floors_otherwise() -> None:
    """20 mm is exactly 64 G; 1 mm is 3.2 G and gives 3; 298 mm is 953.6 G and gives 953."""
    assert content_extent(20, Decimal("2.5")) == 64
    assert content_extent(1, Decimal("2.5")) == 3
    assert content_extent(298, Decimal("2.5")) == 953  # a round would give 954
    assert content_extent(0, Decimal("2.5")) == 0
    assert type(content_extent(297, Decimal("2.5"))) is int


def test_external_note_is_by_others() -> None:
    """Y3's own text, model-0112: the one home a table heading or a future symbol label
    reads, never a copy of its own."""
    assert external_note() == "by others"


def test_position_text_without_a_location_label() -> None:
    """No prefix when `location_labels` is empty."""
    assert position_text(2, 5, "C", ()) == "p2:5C"


def test_position_text_with_a_location_label() -> None:
    """`+<location>` in front when one location label is given."""
    assert position_text(2, 5, "C", ("C1",)) == "+C1p2:5C"


def test_position_text_with_two_location_labels() -> None:
    """`+<label>+<label>` in front when two are given, root first (units spec U7)."""
    assert position_text(2, 5, "C", ("AR", "C1")) == "+AR+C1p2:5C"


def test_position_text_names_the_set_when_the_prefix_is_empty() -> None:
    """C18: an empty prefix into another drawing set names the set instead:
    `p<set>.<page>:<column><row>`."""
    assert position_text(2, 5, "C", (), 3) == "p3.2:5C"


def test_position_text_prints_the_cell_only_on_the_readers_own_page() -> None:
    """The same page prints the cell; another page, a set number or a prefix keeps the full form."""
    assert position_text(2, 5, "C", (), own_page=2) == "5C"
    assert position_text(2, 5, "C", (), own_page=3) == "p2:5C"
    assert position_text(2, 5, "C", (), 3, own_page=2) == "p3.2:5C"
    assert position_text(2, 5, "C", ("C1",), own_page=2) == "+C1p2:5C"


# --------------------------------------------------------------------------------------
# marker_text
# --------------------------------------------------------------------------------------


def test_marker_text_same_drawing_set_has_no_location_prefix(origin: Origin) -> None:
    """A marker whose partner is in the same drawing set has no `+<location>` prefix."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page_a = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    page_b = _page(new_id, drawing_set=ds.id, number=2, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    fn_a = _function(new_id, item=item.id)
    fn_b = _function(new_id, item=item.id)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    marker_a_id = new_id("layout.link_marker")
    marker_b_id = new_id("layout.link_marker")
    marker_a = LinkMarker(
        id=marker_a_id,
        key=_key(marker_a_id),
        page=page_a.id,
        port=port_a.id,
        side=MarkerSide.OWNER,
        partner=marker_b_id,
        x=200,
        y=10,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    marker_b = LinkMarker(
        id=marker_b_id,
        key=_key(marker_b_id),
        page=page_b.id,
        port=port_b.id,
        side=MarkerSide.USER,
        partner=marker_a_id,
        x=300,
        y=10,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    add_all(
        draft,
        sheet,
        ds,
        page_a,
        page_b,
        item,
        fn_a,
        fn_b,
        port_a,
        port_b,
        marker_a,
        marker_b,
        origin=origin,
    )
    model = freeze(draft)
    expected_col = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 300)
    expected_row = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 10)
    # The only reference group in the model, so its rank (`#n`) is 1.
    assert marker_text(model, marker_a) == f"#1-p2:{expected_col}{expected_row}"


def test_marker_text_across_drawing_sets_with_a_location(origin: Origin) -> None:
    """A marker whose partner is in a located drawing set gets the `+<location>` prefix."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    location = AspectNode(
        id=new_id("aspect_node"),
        key=("loc",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="invented cabinet",
    )
    ds_a = _drawing_set(new_id, number=1)
    ds_b = _drawing_set(new_id, number=2, location=location.id)
    page_a = _page(new_id, drawing_set=ds_a.id, number=1, sheet_format=sheet.id)
    page_b = _page(new_id, drawing_set=ds_b.id, number=3, sheet_format=None)
    item = _item(new_id, designation="K1")
    fn_a = _function(new_id, item=item.id)
    fn_b = _function(new_id, item=item.id)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    marker_a_id = new_id("layout.link_marker")
    marker_b_id = new_id("layout.link_marker")
    marker_a = LinkMarker(
        id=marker_a_id,
        key=_key(marker_a_id),
        page=page_a.id,
        port=port_a.id,
        side=MarkerSide.OWNER,
        partner=marker_b_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    marker_b = LinkMarker(
        id=marker_b_id,
        key=_key(marker_b_id),
        page=page_b.id,
        port=port_b.id,
        side=MarkerSide.USER,
        partner=marker_a_id,
        x=50,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    add_all(
        draft,
        sheet,
        location,
        ds_a,
        ds_b,
        page_a,
        page_b,
        item,
        fn_a,
        fn_b,
        port_a,
        port_b,
        marker_a,
        marker_b,
        origin=origin,
    )
    model = freeze(draft)
    # `page_b` has no authored sheet: this also exercises the house-sheet branch of
    # `_sheet_format`, whose content box (400 mm / 2.5 mm module) is the same grid width.
    house = default_sheet_format()
    expected_col = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 50)
    expected_row = frame_row(
        content_extent(house.content_height_mm, house.module_mm), house.frame_rows, 0
    )
    # The only reference group in the model, so its rank (`#n`) is 1.
    assert marker_text(model, marker_a) == f"#1-+C1p3:{expected_col}{expected_row}"


def _nested_pair(
    origin: Origin, *, leaf_a: tuple[str, str, str], leaf_b: tuple[str, str, str]
) -> tuple[Model, LinkMarker, LinkMarker]:
    """Two markers, each on its own drawing set: `leaf_a`/`leaf_b` are `(root key, root
    label, leaf label)`, the leaf a child of a root node of its own (units spec U7).
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    root_a_key, root_a_label, leaf_a_label = leaf_a
    root_b_key, root_b_label, leaf_b_label = leaf_b
    root_a = AspectNode(
        id=new_id("aspect_node"),
        key=(root_a_key,),
        aspect=Aspect.LOCATION,
        parent=None,
        label=root_a_label,
        description="invented root",
    )
    root_b = (
        root_a
        if root_b_key == root_a_key
        else AspectNode(
            id=new_id("aspect_node"),
            key=(root_b_key,),
            aspect=Aspect.LOCATION,
            parent=None,
            label=root_b_label,
            description="invented root",
        )
    )
    leaf_a_node = AspectNode(
        id=new_id("aspect_node"),
        key=(root_a_key, "a"),
        aspect=Aspect.LOCATION,
        parent=root_a.id,
        label=leaf_a_label,
        description="invented leaf a",
    )
    leaf_b_node = AspectNode(
        id=new_id("aspect_node"),
        key=(root_b_key, "b"),
        aspect=Aspect.LOCATION,
        parent=root_b.id,
        label=leaf_b_label,
        description="invented leaf b",
    )
    ds_a = _drawing_set(new_id, number=1, location=leaf_a_node.id)
    ds_b = _drawing_set(new_id, number=2, location=leaf_b_node.id)
    page_a = _page(new_id, drawing_set=ds_a.id, number=1, sheet_format=sheet.id)
    page_b = _page(new_id, drawing_set=ds_b.id, number=3, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    fn_a = _function(new_id, item=item.id)
    fn_b = _function(new_id, item=item.id)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    marker_a_id = new_id("layout.link_marker")
    marker_b_id = new_id("layout.link_marker")
    marker_a = LinkMarker(
        id=marker_a_id,
        key=_key(marker_a_id),
        page=page_a.id,
        port=port_a.id,
        side=MarkerSide.OWNER,
        partner=marker_b_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    marker_b = LinkMarker(
        id=marker_b_id,
        key=_key(marker_b_id),
        page=page_b.id,
        port=port_b.id,
        side=MarkerSide.USER,
        partner=marker_a_id,
        x=50,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    add_all(
        draft,
        sheet,
        root_a,
        *(() if root_b is root_a else (root_b,)),
        leaf_a_node,
        leaf_b_node,
        ds_a,
        ds_b,
        page_a,
        page_b,
        item,
        fn_a,
        fn_b,
        port_a,
        port_b,
        marker_a,
        marker_b,
        origin=origin,
    )
    return freeze(draft), marker_a, marker_b


def test_marker_text_across_nested_locations_prefixes_below_the_shared_ancestor(
    origin: Origin,
) -> None:
    """`+ER+C1` to `+ER+FLD`: the prefix is `+FLD`, not the shared `+ER+FLD` (units spec U7)."""
    model, marker_a, marker_b = _nested_pair(
        origin, leaf_a=("er", "ER", "C1"), leaf_b=("er", "ER", "FLD")
    )
    col_b, col_a = (
        frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 50),
        frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 0),
    )
    row = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0)
    # The only reference group in the model, so its rank (`#n`) is 1.
    assert marker_text(model, marker_a) == f"#1-+FLDp3:{col_b}{row}"
    assert marker_text(model, marker_b) == f"#1-+C1p1:{col_a}{row}"


def test_marker_text_across_unrelated_roots_writes_the_full_path(origin: Origin) -> None:
    """`+ER+C1` to `+AR+C1`: no shared ancestor at all, so the full partner path is written --
    the ambiguity U7 fixes: two `C1` nodes are told apart (`+AR+C1`, `+ER+C1`), not the bare
    `+C1` a leaf-only prefix would give both.
    """
    model, marker_a, marker_b = _nested_pair(
        origin, leaf_a=("er", "ER", "C1"), leaf_b=("ar", "AR", "C1")
    )
    col_b, col_a = (
        frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 50),
        frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 0),
    )
    row = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0)
    # The only reference group in the model, so its rank (`#n`) is 1.
    assert marker_text(model, marker_a) == f"#1-+AR+C1p3:{col_b}{row}"
    assert marker_text(model, marker_b) == f"#1-+ER+C1p1:{col_a}{row}"


def test_marker_text_across_drawing_sets_without_a_location(origin: Origin) -> None:
    """A marker into a different, unlocated drawing set has no `+label` prefix, but names its
    set instead of leaving the page ambiguous (C18): `p<set>.<page>:<column><row>`."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds_a = _drawing_set(new_id, number=1)
    ds_b = _drawing_set(new_id, number=2)
    page_a = _page(new_id, drawing_set=ds_a.id, number=1, sheet_format=sheet.id)
    page_b = _page(new_id, drawing_set=ds_b.id, number=1, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    fn_a = _function(new_id, item=item.id)
    fn_b = _function(new_id, item=item.id)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    marker_a_id = new_id("layout.link_marker")
    marker_b_id = new_id("layout.link_marker")
    marker_a = LinkMarker(
        id=marker_a_id,
        key=_key(marker_a_id),
        page=page_a.id,
        port=port_a.id,
        side=MarkerSide.OWNER,
        partner=marker_b_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    marker_b = LinkMarker(
        id=marker_b_id,
        key=_key(marker_b_id),
        page=page_b.id,
        port=port_b.id,
        side=MarkerSide.USER,
        partner=marker_a_id,
        x=10,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    add_all(
        draft,
        sheet,
        ds_a,
        ds_b,
        page_a,
        page_b,
        item,
        fn_a,
        fn_b,
        port_a,
        port_b,
        marker_a,
        marker_b,
        origin=origin,
    )
    model = freeze(draft)
    expected_col = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 10)
    expected_row = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0)
    # The only reference group in the model, so its rank (`#n`) is 1.
    assert marker_text(model, marker_a) == (
        f"#1-p{ds_b.number}.{page_b.number}:{expected_col}{expected_row}"
    )


# --------------------------------------------------------------------------------------
# page_title
# --------------------------------------------------------------------------------------


def test_page_title_joins_group_descriptions_in_index_order(origin: Origin) -> None:
    """Descriptions join by `', '`, in `index` order, whatever order they were authored in."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    node_a = AspectNode(
        id=new_id("aspect_node"),
        key=("a",),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="A1",
        description="first group",
    )
    node_b = AspectNode(
        id=new_id("aspect_node"),
        key=("b",),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="B1",
        description="second group",
    )
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    page = Page(
        id=page.id,
        key=page.key,
        drawing_set=page.drawing_set,
        number=page.number,
        role=page.role,
        sheet_format=page.sheet_format,
        groups=(PageGroup(group=node_b.id, index=1), PageGroup(group=node_a.id, index=0)),
        produced_by=PRODUCED_BY,
    )
    add_all(draft, sheet, ds, node_a, node_b, page, origin=origin)
    model = freeze(draft)
    assert page_title(model, page) == "first group, second group"


def test_page_title_groups_drops_a_foreign_units_group(origin: Origin) -> None:
    """RW1 model-0097: only the page's own unit's group survives; the other unit's is dropped.

    Two units, each with a real, non-cable item placed (`Placement`) at its own
    `Aspect.FUNCTION` node, so `own_nodes` genuinely owns one node per unit (F9: an
    item of the OTHER unit, not merely an item-less node, proves real foreign ownership).
    The page's drawing set belongs to unit A; its `groups` list both nodes, as layout's page
    builder does with no unit filter.
    """
    new_id = _ids()
    draft = Draft()

    def _unit_release(name: str) -> UnitRelease:
        key = ("unit_release", name, "1", "1")
        return UnitRelease(
            id=make_id(UnitRelease, key),
            key=key,
            name=name,
            version=1,
            revision=1,
            interface="1",
            title="",
        )

    release_a = _unit_release("unit-a")
    release_b = _unit_release("unit-b")
    unit_a_id = new_id("unit")
    unit_b_id = new_id("unit")
    unit_a = Unit(id=unit_a_id, key=_key(unit_a_id), release=release_a.id, parent=None)
    unit_b = Unit(id=unit_b_id, key=_key(unit_b_id), release=release_b.id, parent=None)

    own_node = AspectNode(
        id=new_id("aspect_node"),
        key=("own",),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="A1",
        description="unit a's own group",
    )
    foreign_node = AspectNode(
        id=new_id("aspect_node"),
        key=("foreign",),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="B1",
        description="unit b's own group",
    )

    def _owned_item(designation: str, *, unit: Id[Unit]) -> Item:
        id_ = new_id("item")
        return Item(
            id=id_,
            key=_key(id_),
            part=None,
            parent=None,
            position=None,
            tag=designation,
            description="an invented item",
            unit=unit,
        )

    item_a = _owned_item("A1", unit=unit_a.id)
    item_b = _owned_item("B1", unit=unit_b.id)

    def _placement(item: Id[Item], node: Id[AspectNode]) -> Placement:
        id_ = new_id("placement")
        return Placement(id=id_, key=_key(id_), item=item, node=node)

    placement_a = _placement(item_a.id, own_node.id)
    placement_b = _placement(item_b.id, foreign_node.id)

    sheet = _sheet(new_id)
    ds_id = new_id("layout.drawing_set")
    ds = DrawingSet(
        id=ds_id, key=_key(ds_id), location=None, unit=unit_a.id, number=1, produced_by=PRODUCED_BY
    )
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    page = Page(
        id=page.id,
        key=page.key,
        drawing_set=page.drawing_set,
        number=page.number,
        role=page.role,
        sheet_format=page.sheet_format,
        groups=(PageGroup(group=own_node.id, index=0), PageGroup(group=foreign_node.id, index=1)),
        produced_by=PRODUCED_BY,
    )
    add_all(
        draft,
        release_a,
        release_b,
        unit_a,
        unit_b,
        item_a,
        item_b,
        own_node,
        foreign_node,
        placement_a,
        placement_b,
        sheet,
        ds,
        page,
        origin=origin,
    )
    model = freeze(draft)

    assert page_title_groups(model, page) == (PageGroup(group=own_node.id, index=0),)


# --------------------------------------------------------------------------------------
# unit_label, outline_title and page_title's unit fallback (decision model-0066)
# --------------------------------------------------------------------------------------


def _unit_model(origin: Origin, *, title: str) -> tuple[Model, Unit, Page]:
    """A frozen model of one unit, its own drawing set and one page with no groups."""
    new_id = _ids()
    unit_id = new_id("unit")
    release_key = ("unit_release", "relay-interface-board", "1", "1")
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name="relay-interface-board",
        version=1,
        revision=1,
        interface="1",
        title=title,
    )
    unit = Unit(id=unit_id, key=_key(unit_id), release=release.id, parent=None)
    sheet = _sheet(new_id)
    ds_id = new_id("layout.drawing_set")
    ds = DrawingSet(
        id=ds_id,
        key=_key(ds_id),
        location=None,
        unit=unit.id,
        number=1,
        produced_by=PRODUCED_BY,
    )
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    draft = Draft()
    add_all(draft, release, unit, sheet, ds, page, origin=origin)
    return freeze(draft), unit, page


def test_unit_label_is_the_title_when_the_title_is_set(origin: Origin) -> None:
    model, unit, _page_record = _unit_model(origin, title="Relay interface board")
    assert unit_label(model, unit.id) == "Relay interface board"


def test_unit_label_is_the_name_when_the_title_is_empty(origin: Origin) -> None:
    model, unit, _page_record = _unit_model(origin, title="")
    assert unit_label(model, unit.id) == "relay-interface-board"


def test_outline_title_prints_the_units_title_and_revision(origin: Origin) -> None:
    model, unit, _page_record = _unit_model(origin, title="Relay interface board")
    assert outline_title(model, unit.id) == "Relay interface board rev 1.1"


def test_outline_title_prints_the_name_when_the_title_is_empty(origin: Origin) -> None:
    model, unit, _page_record = _unit_model(origin, title="")
    assert outline_title(model, unit.id) == "relay-interface-board rev 1.1"


def test_page_title_of_a_unit_page_with_no_groups_is_the_units_title(origin: Origin) -> None:
    model, _unit_record, page = _unit_model(origin, title="Relay interface board")
    assert page_title(model, page) == "Relay interface board"


def test_page_title_of_a_unit_page_with_no_groups_is_the_name_when_the_title_is_empty(
    origin: Origin,
) -> None:
    model, _unit_record, page = _unit_model(origin, title="")
    assert page_title(model, page) == "relay-interface-board"


# --------------------------------------------------------------------------------------
# label_text
# --------------------------------------------------------------------------------------


def _labelled_model(origin: Origin) -> tuple[Callable[[str], Id[Any]], Draft, Page]:
    """A one-page model with a plain function, a terminal function and a labelled wire."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    add_all(draft, sheet, ds, page, origin=origin)
    return new_id, draft, page


def test_label_text_tag_of_a_plain_function_is_the_item_reference(origin: Origin) -> None:
    """A non-terminal function's TAG text is its item's `reference_designation`."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    add_all(draft, item, fn, origin=origin)
    model = freeze(draft)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.TAG,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    assert label_text(model, label) == "-K1"


def test_label_text_tag_of_a_terminal_function_is_its_lowest_port(origin: Origin) -> None:
    """A terminal function's TAG text is the designation of its lowest-handle port."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="X1")
    fn = _function(new_id, item=item.id, kind=FunctionKind.TERMINAL)
    port_1 = _port(new_id, function=fn.id, name="1")
    port_2 = _port(new_id, function=fn.id, name="2")
    add_all(draft, item, fn, port_1, port_2, origin=origin)
    model = freeze(draft)
    lowest = min(port_1.id, port_2.id)
    expected = "-X1:1" if lowest == port_1.id else "-X1:2"
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.TAG,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    assert label_text(model, label) == expected


def test_label_text_tag_with_no_function_raises(origin: Origin) -> None:
    """A malformed TAG label (no `function`, despite the schema allowing it) raises."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    port = _port(new_id, function=fn.id)
    add_all(draft, item, fn, port, origin=origin)
    model = freeze(draft)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=None,
        port=port.id,
        conductor=None,
        kind=LabelKind.TAG,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    with pytest.raises(SchemaError):
        label_text(model, label)


def test_label_text_marking_is_the_port_name(origin: Origin) -> None:
    """A MARKING label's text is the model port's name."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    port = _port(new_id, function=fn.id, name="A1")
    add_all(draft, item, fn, port, origin=origin)
    model = freeze(draft)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=None,
        port=port.id,
        conductor=None,
        kind=LabelKind.MARKING,
        slot="marking.1",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    assert label_text(model, label) == "A1"


def test_port_marking_prints_the_parts_own_marking_when_set(origin: Origin) -> None:
    """model-0053 (F2): a port whose part sets an explicit marking prints that text, not its
    name."""
    new_id = _ids()
    draft = Draft()
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    port = _port(new_id, function=fn.id, name="A1", marking="X9")
    add_all(draft, item, fn, port, origin=origin)
    model = freeze(draft)
    assert port_marking(model, port.id) == "X9"


def test_port_marking_is_empty_when_the_part_prints_none(origin: Origin) -> None:
    """model-0053 (F2): `marking=""` prints nothing, never falling back to the port's name."""
    new_id = _ids()
    draft = Draft()
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    port = _port(new_id, function=fn.id, name="A1", marking="")
    add_all(draft, item, fn, port, origin=origin)
    model = freeze(draft)
    assert port_marking(model, port.id) == ""


def test_label_text_marking_with_no_port_raises(origin: Origin) -> None:
    """A malformed MARKING label (no `port`) raises."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    add_all(draft, item, fn, origin=origin)
    model = freeze(draft)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.MARKING,
        slot="marking.1",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    with pytest.raises(SchemaError):
        label_text(model, label)


def test_wire_label_text_joins_the_two_ends_with_one_space() -> None:
    """V8: `wire_label_text` is the one join: `-B12:96 -Q11:A1`."""
    assert wire_label_text("-B12:96", "-Q11:A1") == "-B12:96 -Q11:A1"


def test_label_text_wire_is_the_two_end_designations(origin: Origin) -> None:
    """V8: a WIRE label's text is the conductor's two end designations, one space between."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn_a = _function(new_id, item=item.id)
    fn_b = _function(new_id, item=item.id)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    conductor = _conductor(new_id, a=port_a.id, b=port_b.id)
    facet_id = new_id("facet.wire")
    facet = WireFacet(
        id=facet_id,
        key=_key(facet_id),
        subject=conductor.id,
        colour="blue",
        gauge_mm2=Decimal("0.75"),
        length_mm=None,
        label="W1",
    )
    add_all(draft, item, fn_a, fn_b, port_a, port_b, conductor, facet, origin=origin)
    model = freeze(draft)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=None,
        port=None,
        conductor=conductor.id,
        kind=LabelKind.WIRE,
        slot="",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
    )
    assert label_text(model, label) == "-K1:1 -K1:1"


def test_label_text_cross_reference_delegates_to_cross_reference_text(origin: Origin) -> None:
    """A CROSS_REFERENCE label's text is `cross_reference_text`'s."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    other_page = _page(
        new_id, drawing_set=page.drawing_set, number=2, sheet_format=page.sheet_format
    )
    other_fn = _function(new_id, item=item.id)
    other_port = _port(new_id, function=other_fn.id)
    placement = _placement(new_id, function=other_fn.id, page=other_page.id, y=0)  # row A
    add_all(draft, item, fn, other_page, other_fn, other_port, placement, origin=origin)
    model = freeze(draft)
    partner = CrossReferencePartner(port=other_port.id, page=other_page.id, x=100)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.CROSS_REFERENCE,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
        partners=(partner,),
    )
    expected = "p2:1A"
    assert label_text(model, label) == cross_reference_text(model, label) == expected


def test_label_text_cross_reference_with_no_function_raises(origin: Origin) -> None:
    """A malformed CROSS_REFERENCE label (no `function`) raises, even with a valid partner."""
    new_id, draft, page = _labelled_model(origin)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    port = _port(new_id, function=fn.id)
    other_page = _page(
        new_id, drawing_set=page.drawing_set, number=2, sheet_format=page.sheet_format
    )
    other_fn = _function(new_id, item=item.id)
    other_port = _port(new_id, function=other_fn.id)
    add_all(draft, item, fn, port, other_page, other_fn, other_port, origin=origin)
    model = freeze(draft)
    partner = CrossReferencePartner(port=other_port.id, page=other_page.id, x=100)
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=page.id,
        function=None,
        port=port.id,
        conductor=None,
        kind=LabelKind.CROSS_REFERENCE,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
        partners=(partner,),
    )
    with pytest.raises(SchemaError):
        label_text(model, label)


# --------------------------------------------------------------------------------------
# cross_reference_text
# --------------------------------------------------------------------------------------
#
# The old model-0032 conductor-walking tests no longer apply under the new `Label`-taking
# signature (spec X3): `cross_reference_text` no longer looks up a function, so there is
# nothing "unknown" for it to raise on; and it no longer walks conductors to find whether a
# function is placed, so there is no "unplaced function" path either -- it only formats
# `label.partners`, which `Label.__post_init__` (task 1) already guarantees is non-empty for
# every `CROSS_REFERENCE` label, so an "empty" case is not constructible any more. Both old
# tests are dropped rather than forced to keep a scenario that can no longer happen; this
# mirrors `marker_text`, whose partner is likewise trusted from persisted, referentially
# valid records and carries no "unknown" test of its own.


def test_cross_reference_text_formats_stored_partners_in_order(origin: Origin) -> None:
    """Same-set partner: no prefix. Cross-set partner: `+<location>` prefix. Duplicate
    formatted texts collapse to one. Partners are read in stored (non-canonical) order,
    not re-sorted by drawing set, page or column.
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    location = AspectNode(
        id=new_id("aspect_node"),
        key=("loc",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="invented cabinet",
    )
    ds_a = _drawing_set(new_id, number=1)  # the label's own set, unlocated
    ds_b = _drawing_set(new_id, number=2, location=location.id)
    own_page = _page(new_id, drawing_set=ds_a.id, number=1, sheet_format=sheet.id)
    same_set_page = _page(new_id, drawing_set=ds_a.id, number=2, sheet_format=sheet.id)
    other_set_page = _page(new_id, drawing_set=ds_b.id, number=1, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    fn_same = _function(new_id, item=item.id)
    fn_other = _function(new_id, item=item.id)
    fn_other_dup = _function(new_id, item=item.id)
    port_same = _port(new_id, function=fn_same.id)
    port_other = _port(new_id, function=fn_other.id)
    port_other_dup = _port(new_id, function=fn_other_dup.id)
    # Same row (A) for every placement: `fn_other` and `fn_other_dup` must land in the same
    # cell for their formatted texts to actually dedup.
    placement_same = _placement(new_id, function=fn_same.id, page=same_set_page.id, y=0)
    placement_other = _placement(new_id, function=fn_other.id, page=other_set_page.id, y=0)
    placement_other_dup = _placement(new_id, function=fn_other_dup.id, page=other_set_page.id, y=0)
    add_all(
        draft,
        sheet,
        location,
        ds_a,
        ds_b,
        own_page,
        same_set_page,
        other_set_page,
        item,
        fn,
        fn_same,
        fn_other,
        fn_other_dup,
        port_same,
        port_other,
        port_other_dup,
        placement_same,
        placement_other,
        placement_other_dup,
        origin=origin,
    )
    model = freeze(draft)

    x_same, x_other = 100, 500
    col_same = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, x_same)
    col_other = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, x_other)
    row = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0)
    text_other = position_text(1, col_other, row, ("C1",))
    text_same = position_text(2, col_same, row, ())

    # Stored out of canonical (drawing set, page, column) order, with a duplicate: the
    # other-set partner and its duplicate come first, the same-set partner last.
    partners = (
        CrossReferencePartner(port=port_other.id, page=other_set_page.id, x=x_other),
        CrossReferencePartner(port=port_other_dup.id, page=other_set_page.id, x=x_other),
        CrossReferencePartner(port=port_same.id, page=same_set_page.id, x=x_same),
    )
    label_id = new_id("layout.label")
    label = Label(
        id=label_id,
        key=_key(label_id),
        page=own_page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.CROSS_REFERENCE,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
        partners=partners,
    )
    assert cross_reference_text(model, label) == f"{text_other} {text_same}"


def test_cross_reference_text_changes_when_a_partner_x_crosses_a_column_boundary(
    origin: Origin,
) -> None:
    """Can-fail twin: moving one partner's `x` across a `frame_column` boundary changes the
    formatted text, proving the reader is sensitive to `x` and not just to structure.
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    location = AspectNode(
        id=new_id("aspect_node"),
        key=("loc",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="invented cabinet",
    )
    ds_a = _drawing_set(new_id, number=1)
    ds_b = _drawing_set(new_id, number=2, location=location.id)
    own_page = _page(new_id, drawing_set=ds_a.id, number=1, sheet_format=sheet.id)
    same_set_page = _page(new_id, drawing_set=ds_a.id, number=2, sheet_format=sheet.id)
    other_set_page = _page(new_id, drawing_set=ds_b.id, number=1, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    fn_same = _function(new_id, item=item.id)
    fn_other = _function(new_id, item=item.id)
    port_same = _port(new_id, function=fn_same.id)
    port_other = _port(new_id, function=fn_other.id)
    # Placements fixed in row A: only `x` varies below, so the test still proves the reader
    # is sensitive to `x`, not to a row change riding along with it.
    placement_same = _placement(new_id, function=fn_same.id, page=same_set_page.id, y=0)
    placement_other = _placement(new_id, function=fn_other.id, page=other_set_page.id, y=0)
    add_all(
        draft,
        sheet,
        location,
        ds_a,
        ds_b,
        own_page,
        same_set_page,
        other_set_page,
        item,
        fn,
        fn_same,
        fn_other,
        port_same,
        port_other,
        placement_same,
        placement_other,
        origin=origin,
    )
    model = freeze(draft)

    x_other = 500
    x_same_before, x_same_after = 100, 200
    assert frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, x_same_before) != frame_column(
        CONTENT_WIDTH_GRID, FRAME_COLUMNS, x_same_after
    )

    def _text(x_same: int) -> str:
        partners = (
            CrossReferencePartner(port=port_other.id, page=other_set_page.id, x=x_other),
            CrossReferencePartner(port=port_same.id, page=same_set_page.id, x=x_same),
        )
        label_id = new_id("layout.label")
        label = Label(
            id=label_id,
            key=_key(label_id),
            page=own_page.id,
            function=fn.id,
            port=None,
            conductor=None,
            kind=LabelKind.CROSS_REFERENCE,
            slot="tag",
            x=0,
            y=0,
            width=4,
            height=2,
            produced_by=PRODUCED_BY,
            partners=partners,
        )
        return cross_reference_text(model, label)

    assert _text(x_same_before) != _text(x_same_after)


def test_a_replicas_colliding_function_is_never_a_cross_reference_partner(origin: Origin) -> None:
    """`_placements_by_function_page`'s known ambiguity (layout-0076 replicas) never lands on a
    function a cross-reference or contact-image label names as a partner (step4 Part 3
    measurement): across every fixture measured -- the three usecase goldens, the units worked
    example (7 collisions) and a synthetic 16-unit scale build (48 collisions) -- the colliding
    functions and the partner functions were disjoint sets every time, and every collision was
    a terminal (`FunctionKind.CONNECTOR`) replica, never a coil or a severed cut's own end (the
    only things a partner ever names). This fixture reproduces that shape directly: `fn_dup` is
    placed twice on `page` (the replica collision), `fn_coil`'s port is a genuine partner on an
    unrelated `page_b` -- the two never share a function, so `_partner_row` never has to pick
    between two placements for a partner it actually reads.
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    page_b = _page(new_id, drawing_set=ds.id, number=2, sheet_format=sheet.id)
    item_dup = _item(new_id, designation="X1")
    item_coil = _item(new_id, designation="K1")
    fn_dup = _function(new_id, item=item_dup.id, kind=FunctionKind.CONNECTOR)
    fn_coil = _function(new_id, item=item_coil.id)
    port_coil = _port(new_id, function=fn_coil.id)
    # Two placements of `fn_dup` on the same page (a replica's own discriminator, layout-0076):
    # the exact ambiguity `_placements_by_function_page`'s docstring names.
    placement_dup_1 = _placement(new_id, function=fn_dup.id, page=page.id, y=0)
    placement_dup_2 = _placement(new_id, function=fn_dup.id, page=page.id, y=100)
    placement_coil = _placement(new_id, function=fn_coil.id, page=page_b.id, y=0)
    add_all(
        draft,
        sheet,
        ds,
        page,
        page_b,
        item_dup,
        item_coil,
        fn_dup,
        fn_coil,
        port_coil,
        placement_dup_1,
        placement_dup_2,
        placement_coil,
        origin=origin,
    )
    model = freeze(draft)

    colliding = {
        function
        for function, _page in _placements_by_function_page(model)
        if sum(1 for p in layout_of(model, SymbolPlacement).values() if p.function == function) > 1
    }
    label = Label(
        id=new_id("layout.label"),
        key=_key(new_id("layout.label")),
        page=page.id,
        function=fn_coil.id,
        port=None,
        conductor=None,
        kind=LabelKind.CROSS_REFERENCE,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=PRODUCED_BY,
        partners=(CrossReferencePartner(port=port_coil.id, page=page_b.id, x=0),),
    )
    partner_functions = {ports(model)[partner.port].function for partner in label.partners}

    assert fn_dup.id in colliding
    assert partner_functions.isdisjoint(colliding)


def _star_text(origin: Origin, branch_xs: tuple[int, ...]) -> str:
    """The reference marker's text for a star whose branches stand at `branch_xs` on one page."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page_a, page_b = (
        _page(new_id, drawing_set=ds.id, number=n, sheet_format=sheet.id) for n in (1, 2)
    )
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    ref_id = new_id("layout.link_marker")
    ref_port = _port(new_id, function=fn.id, name="0")
    markers = [
        LinkMarker(
            id=ref_id,
            key=_key(ref_id),
            page=page_a.id,
            port=ref_port.id,
            side=MarkerSide.OWNER,
            partner=ref_id,
            star=StarKind.REF,
            x=0,
            y=0,
            width=13,
            height=8,
            produced_by=PRODUCED_BY,
        )
    ]
    ports = [_port(new_id, function=fn.id, name=str(i + 1)) for i in range(len(branch_xs))]
    for port, x in zip(ports, branch_xs, strict=True):
        id_ = new_id("layout.link_marker")
        markers.append(
            LinkMarker(
                id=id_,
                key=_key(id_),
                page=page_b.id,
                port=port.id,
                side=MarkerSide.USER,
                partner=ref_id,
                star=StarKind.BRANCH,
                x=x,
                y=0,
                width=13,
                height=8,
                produced_by=PRODUCED_BY,
            )
        )
    add_all(draft, sheet, ds, page_a, page_b, item, fn, ref_port, *ports, *markers, origin=origin)
    return marker_text(freeze(draft), markers[0])


def test_marker_text_prints_identical_lines_once(origin: Origin) -> None:
    """Two branches in one cell give one line, not two (model-0137)."""
    assert len(_star_text(origin, (10, 10)).split("\n")) == 1


def test_marker_text_keeps_two_different_lines(origin: Origin) -> None:
    """Branches in two cells stay two distinct targets: the first and `+1` (model-0139)."""
    assert _star_text(origin, (10, 10, 400)).split("\n") == ["#1-p2:1A +1"]  # C2: first and a count


# `partner_position_text` (RW9)
# --------------------------------------------------------------------------------------

_NODE_IDS = _ids()
_PATH_CAB: tuple[tuple[Id[Any], str], ...] = ((_NODE_IDS("aspect_node"), "C1"),)


def test_partner_position_text_same_set_prints_the_cell_on_its_own_page() -> None:
    """Same set: the cell alone on the reader's page, `p<page>:<cell>` on another (model-0136)."""
    own = (1, 2, _PATH_CAB)
    assert partner_position_text(own, (1, 2, _PATH_CAB), 3, "B") == "3B"
    assert partner_position_text(own, (1, 5, _PATH_CAB), 3, "B") == "p5:3B"


def test_partner_position_text_other_set_carries_the_prefix_or_the_set_number() -> None:
    """Another set: the prefix below the common ancestor (U7), else `p<set>.<page>:` (C18)."""
    other = ((_NODE_IDS("aspect_node"), "C2"),)
    assert partner_position_text((1, 2, ()), (2, 4, _PATH_CAB), 3, "B") == "+C1p4:3B"
    assert partner_position_text((1, 2, _PATH_CAB), (2, 4, _PATH_CAB), 3, "B") == "p2.4:3B"
    assert partner_position_text((1, 2, _PATH_CAB), (3, 4, other), 1, "A") == "+C2p4:1A"


def test_position_between_is_partner_position_text_on_a_built_model(origin: Origin) -> None:
    """The model reader only looks the plain values up: both spellings agree, both sets and one."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    location = AspectNode(
        id=new_id("aspect_node"),
        key=("loc",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="invented cabinet",
    )
    ds_a = _drawing_set(new_id, number=1)
    ds_b = _drawing_set(new_id, number=2, location=location.id)
    pages = [
        _page(new_id, drawing_set=ds.id, number=n, sheet_format=sheet.id)
        for ds, n in ((ds_a, 1), (ds_a, 2), (ds_b, 1))
    ]
    add_all(draft, sheet, location, ds_a, ds_b, *pages, origin=origin)
    model = freeze(draft)
    column = frame_column(CONTENT_WIDTH_GRID, FRAME_COLUMNS, 500)
    for own, partner, expected in (
        (pages[0], pages[1], f"p2:{column}A"),
        (pages[0], pages[0], f"{column}A"),
        (pages[0], pages[2], f"+C1p1:{column}A"),
        (pages[2], pages[0], f"p1.1:{column}A"),
    ):
        assert _position_between(model, own, partner, 500, "A") == expected
