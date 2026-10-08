"""HL11 to HL13 and HL20: a middle unit's stripped columns, groups, bands and folded outline."""

from dataclasses import dataclass, replace
from fractions import Fraction
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from samples import PROFILE, hid, page_plan, placed

from fransys_layout.stages import Cell, Column, Role
from fransys_layout.stages.edges import InterfaceEdge
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.middle import (
    MiddleGroup,
    MiddleInterface,
    MiddleUnit,
    draws_in,
    group_index,
    middle_groups,
    strip_columns,
)
from fransys_layout.stages.middle_cut import fold_overfull
from fransys_layout.stages.middle_fold import GroupShape, fold_page, shape_boxes
from fransys_layout.stages.middle_reach import line_reach
from fransys_layout.stages.middle_tall import Cut, recut, tall_groups
from fransys_layout.stages.place import PAGE_OVERFULL
from fransys_model.derive import natural_key
from fransys_model.kernel import Finding, Id, Severity

if TYPE_CHECKING:
    from fransys_layout.geometry import Box
    from fransys_model.kernel import AuthoringKey

LINES = ("DEMO-HSG-4M",)  # 72 wide at text height 8
MIDDLE = hid("unit", 1)
OTHER = hid("unit", 2)
J1, J2, J3 = (hid("function", n) for n in (1, 2, 3))
PLUG = hid("function", 4)


def key(name: str) -> AuthoringKey:
    return ("invented", name)


def edge(function, *, line: bool = True, share: int = 0) -> InterfaceEdge:
    designation = f"-U1-{function.value[-1]}"
    return InterfaceEdge(
        function, designation, natural_key(designation), None, line=line, share=Fraction(share)
    )


def interface(function, *, views=(), plug=None, plug_views=(), share=0, line=True, far=()):  # noqa: PLR0913 - a test builder with one keyword per fact
    return MiddleInterface(
        edge=edge(function, line=line, share=share),
        views=tuple(views),
        plug=plug,
        plug_views=tuple(plug_views),
        lines=LINES,
        plug_lines=LINES if plug is not None else (),
        far=frozenset(far),
        conductors=frozenset({Id(kind="conductor", value=function.value)}) if line else frozenset(),
    )


def cols(name: str, functions: tuple[int, ...], unit, location=None) -> Column:
    cells = tuple(Cell(function=hid("function", n), index=i) for i, n in enumerate(functions))
    return Column(
        key=key(name), cells=cells, group=None, role=Role.CONTROL, location=location, unit=unit
    )


def test_a_column_of_another_unit_loses_the_line_views_and_renumbers_its_rows() -> None:
    line = interface(J1, views=[hid("function", 10)], plug_views=[hid("function", 11)])
    plain = interface(J2, views=[hid("function", 20)], line=False)
    unit = MiddleUnit(MIDDLE, (line, plain), frozenset())
    other = cols("other", (10, 12, 11, 13), OTHER)
    own = cols("own", (10, 11), MIDDLE)
    empty = cols("empty", (10,), OTHER)
    kept = cols("kept", (20, 21), OTHER)
    reach, units = line_reach([other, own, empty, kept], [unit])
    out, reach = strip_columns([other, own, empty, kept], units, reach)
    by_key = {column.key: column for column in out}
    assert [column.key for column in out] == [key("other"), key("own"), key("kept")]
    assert [(c.function, c.index) for c in by_key[key("other")].cells] == [
        (hid("function", 12), 0),
        (hid("function", 13), 1),
    ]
    assert by_key[key("own")].cells == own.cells
    assert by_key[key("kept")].cells == kept.cells
    assert reach == {J1: (key("other"),)}


def test_a_far_end_reaches_only_on_its_interfaces_drawing_set() -> None:
    """J1's views stand alone (+A), its far end 30 stands in +A; J2's far end 40 only in +B."""
    here, there = hid("aspect_node", 1), hid("aspect_node", 2)
    j1 = interface(J1, views=[hid("function", 10)], far=[hid("function", 30)])
    j2 = interface(J2, views=[hid("function", 20)], far=[hid("function", 40)])
    unit = MiddleUnit(MIDDLE, (j1, j2), frozenset(), "U1")
    columns = [
        cols("j1", (10,), None, here),
        cols("j2", (20,), None, here),
        cols("far1", (30, 31), None, here),
        cols("far2", (40,), None, there),
    ]
    reach, (kept,) = line_reach(columns, [unit])
    # J2's line reaches no column of +A: it leaves (HL18), its own column its group's anchor
    assert reach == {J1: (key("far1"),), J2: (key("j2"),)}
    assert kept.interfaces == (j1, replace(j2, leaving=True))


def test_a_unit_whose_only_line_reaches_nowhere_is_a_middle_unit_with_a_leaving_line() -> None:
    """Condition 1: reached or not, a unit with a line interface is a middle unit.

    UNDO: P2b's rule, a unit with no reached line interface is dropped from the units.
    """
    here, there = hid("aspect_node", 1), hid("aspect_node", 2)
    j2 = interface(J2, views=[hid("function", 20)], far=[hid("function", 40)])
    columns = [cols("j2", (20,), None, here), cols("far2", (40,), None, there)]
    reach, (kept,) = line_reach(columns, [MiddleUnit(MIDDLE, (j2,), frozenset())])
    assert reach == {J2: (key("j2"),)}
    assert kept.interfaces == (replace(j2, leaving=True),)


def two_line_unit() -> MiddleUnit:
    return MiddleUnit(
        MIDDLE, (interface(J1, share=1), interface(J2, share=0)), frozenset(), title="-U1"
    )


def groups_of_two() -> tuple[MiddleGroup, ...]:
    reach = {J1: (key("a"),), J2: (key("b"), key("c"))}
    widths = {key("a"): 72, key("b"): 72, key("c"): 72}
    return middle_groups([two_line_unit()], [], reach, widths, PROFILE.text_height)


def test_the_supply_interface_goes_on_top_and_the_share_zero_one_stays_below() -> None:
    (group,) = groups_of_two()
    assert group.top == frozenset({J1})
    assert group.upper == frozenset({key("a")})
    assert group.lower == frozenset({key("b"), key("c")})
    assert group.reach == {J1: (key("a"),), J2: (key("b"), key("c"))}


def test_each_band_column_maps_to_its_group() -> None:
    (group,) = groups_of_two()
    assert group_index([group]) == {key("a"): (group,), key("b"): (group,), key("c"): (group,)}
    assert group_index([]) == {}


def fold_group() -> MiddleGroup:
    unit = MiddleUnit(
        MIDDLE,
        (interface(J1, plug=PLUG, share=1), interface(J2)),
        frozenset(),
        title="-U1",
    )
    reach = {J1: (key("a"),), J2: (key("b"),)}
    return MiddleGroup(unit, frozenset({J1}), reach, frozenset({key("a")}), frozenset({key("b")}))


def three_columns():
    return (
        placed(1, x=96, y=96, name="a"),
        placed(2, x=96, y=152, name="b"),
        placed(3, x=296, y=96, name="c"),
    )


def test_a_page_with_no_groups_is_returned_unchanged_with_no_shapes() -> None:
    page = three_columns()
    assert fold_page(page, page_plan(("a", "b", "c")), {}, PROFILE) == (page, ())


def right(box: Box) -> int:
    return box.x + box.width


def bottom(box: Box) -> int:
    return box.y + box.height


def inside(inner: Box, outer: Box) -> bool:
    return (
        outer.x <= inner.x
        and right(inner) <= right(outer)
        and outer.y <= inner.y
        and bottom(inner) <= bottom(outer)
    )


def test_a_folded_outline_lies_between_its_bands_with_its_boxes_on_it() -> None:
    group = fold_group()
    page = three_columns()
    index = {key("a"): (group,), key("b"): (group,)}
    moved, (shape,) = fold_page(page, page_plan(("a", "b", "c")), index, PROFILE)
    a_old, b_old, c_old = (placed_keepout(one) for one in page)
    a_new, b_new, c_new = (placed_keepout(one) for one in moved)
    outline = shape.outline
    assert (shape.unit, shape.lead, shape.page) == (MIDDLE, J1, 1)
    assert a_new == a_old
    assert outline.y >= bottom(a_new)
    assert b_new.y >= bottom(outline)
    assert b_new.y > b_old.y
    interface_boxes = [one.box for one in shape.boxes if one.function in (J1, J2)]
    plug_boxes = [one.box for one in shape.boxes if one.function == PLUG]
    assert len(interface_boxes) == 2
    assert all(inside(box, outline) for box in interface_boxes)
    assert len(plug_boxes) == 1
    assert bottom(plug_boxes[0]) <= outline.y
    assert c_new.x >= right(outline)
    assert c_new.x >= max(right(a_new), right(b_new))
    assert c_new.y == c_old.y


def test_two_groups_stand_side_by_side_and_a_shared_column_stays_with_the_first() -> None:
    """HL20: B shares column b with A (a line between them); b stays in A's band, B goes right."""
    first = fold_group()
    unit = MiddleUnit(OTHER, (interface(J3, share=1),), frozenset(), title="-U2")
    reach = {J3: (key("c"), key("b"))}
    second = MiddleGroup(unit, frozenset({J3}), reach, frozenset({key("c"), key("b")}))
    page = three_columns()
    plan = page_plan(("a", "b", "c"))
    moved, (one, two) = fold_page(page, plan, group_index([first, second]), PROFILE)
    a_new, b_new, c_new = (placed_keepout(each) for each in moved)
    assert (one.unit, two.unit) == (MIDDLE, OTHER)
    assert bottom(a_new) <= one.outline.y
    assert two.outline.x >= right(one.outline) + PROFILE.column_gap
    assert b_new.y >= bottom(one.outline)  # b is A's lower band, not B's upper one
    assert b_new.x < two.outline.x
    assert c_new.x >= right(one.outline)
    assert bottom(c_new) <= two.outline.y


def test_shape_boxes_lists_each_outline_then_its_title_then_its_boxes() -> None:
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    _, shapes = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    (shape,) = shapes
    assert isinstance(shape, GroupShape)
    assert shape_boxes(shapes) == (shape.outline, shape.title, *(one.box for one in shape.boxes))
    assert shape_boxes(()) == ()


def test_a_split_group_draws_on_each_page_only_the_interfaces_its_columns_reach() -> None:
    """HL21 ruling (a): the page holding only b draws J2's box; J1 and its plug go with a.

    UNDO: `_edges` keeps every line interface of the unit on every page.
    """
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    only_b = (placed(2, x=96, y=152, name="b"),)
    _, (shape,) = fold_page(only_b, page_plan(("b",)), index, PROFILE)
    assert [one.function for one in shape.boxes] == [J2]
    assert shape.lead == J2


def test_a_unit_draws_an_interface_in_no_hidden_set() -> None:
    """layout-0160: not in its own set, not in a set an outer unit's black box holds."""
    unit, outer = hid("unit", 1), hid("unit", 2)
    assert draws_in(unit, frozenset({outer}), None)
    assert not draws_in(unit, frozenset({outer}), outer)
    assert not draws_in(unit, frozenset(), unit)


def cut_index() -> dict:
    group = replace(fold_group(), cut=True)
    return {key("a"): (group,), key("b"): (group,)}


def test_a_cut_group_has_no_outline_on_the_page_of_its_upper_band() -> None:
    """TALL-PAGE T2: the page holding only column a (J1's band) folds nothing.

    UNDO: `_here` lists a cut group on every page that holds one of its columns.
    """
    only_a = (placed(1, x=96, y=96, name="a"),)
    moved, shapes = fold_page(only_a, page_plan(("a",)), cut_index(), PROFILE)
    assert shapes == ()
    assert moved == only_a


def test_a_cut_group_draws_every_line_interface_on_the_page_of_its_lower_band() -> None:
    """T3: J1 reaches only column a, on the page before, yet its box and plug stand here.

    UNDO: `_edges` filters a cut group's interfaces by the columns they reach.
    """
    only_b = (placed(2, x=96, y=152, name="b"),)
    _, (shape,) = fold_page(only_b, page_plan(("b",), number=2), cut_index(), PROFILE)
    assert sorted(one.function.value for one in shape.boxes) == sorted(
        one.value for one in (J1, J2, PLUG)
    )
    assert shape.page == 2


def test_the_folded_bottom_is_how_far_the_group_reaches() -> None:
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    moved, (shape,) = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    assert shape.bottom == bottom(placed_keepout(moved[1]))
    assert not shape.held


def test_a_cut_group_s_outline_stands_from_its_lower_columns_as_the_uncut_fold_has_it() -> None:
    """TALL-PAGE R2: the cut page repeats the uncut fold's frame offset, so no line crosses a box.

    UNDO: `_frame_left` centres a cut group on its own span and ignores `frame_dx`.
    """
    group = replace(fold_group(), upper=frozenset({key("a"), key("c")}))
    both = {key(name): (group,) for name in "abc"}
    moved, (shape,) = fold_page(three_columns(), page_plan(("a", "b", "c")), both, PROFILE)
    offset = shape.outline.x - placed_keepout(moved[1]).x
    cut = replace(group, cut=True, frame_dx=shape.frame_dx)
    only_b = (placed(2, x=96, y=152, name="b"),)
    moved_b, (side,) = fold_page(
        only_b, page_plan(("b",)), {key("a"): (cut,), key("b"): (cut,)}, PROFILE
    )
    assert offset > 0
    assert side.outline.x - placed_keepout(moved_b[0]).x == offset


@dataclass(frozen=True)
class FakeInputs:
    middle: dict


@dataclass(frozen=True)
class FakeRun:
    inputs: FakeInputs


def pages_of(*shapes: GroupShape) -> list:
    return [(None, SimpleNamespace(shapes=list(shapes)))]


def test_tall_groups_names_the_units_whose_one_shape_passes_the_page_unless_held() -> None:
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    _, (shape,) = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    low, high = shape.bottom - 1, shape.bottom
    assert tall_groups(pages_of(shape), low, index) == {
        shape.unit: Cut(shape.frame_dx, below=False)
    }
    assert tall_groups(pages_of(shape), high, index) == {}
    assert tall_groups(pages_of(replace(shape, held=True)), low, index) == {}
    assert tall_groups(pages_of(shape, shape), low, index) == {}  # T7: split over pages


def test_tall_groups_leaves_out_a_group_recut_would_hold() -> None:
    """A group with no lower band or a shared column is not tall: no extra planning pass.

    UNDO: `tall_groups` drops its `cuttable` test.
    """
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    _, (shape,) = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    low = shape.bottom - 1
    bare = replace(group, lower=frozenset())
    sharing = replace(group, unit=replace(group.unit, unit=OTHER), upper=frozenset({key("b")}))
    assert tall_groups(pages_of(shape), low, {key("a"): (bare,)}) == {}
    assert tall_groups(pages_of(shape), low, {key("a"): (group, sharing)}) == {}


def cut_of(*groups: MiddleGroup, tall: dict) -> list[bool]:
    index = {key("a"): groups}
    run: Any = FakeRun(FakeInputs(index))  # `recut` reads and replaces only `inputs.middle`
    return [one.cut for one in recut(run, tall).inputs.middle[key("a")]]


def test_recut_flags_the_tall_groups_only() -> None:
    group = fold_group()
    assert cut_of(group, tall={MIDDLE: Cut(0, below=False)}) == [True]
    assert cut_of(group, tall={}) == [False]


def test_fold_overfull_widens_places_finding_with_the_folded_cells_below_the_page() -> None:
    """TALL-PAGE T6: one PAGE_OVERFULL, naming place's cells and the fold's.

    UNDO: `fold_overfull` returns `found` unchanged.
    """
    group = fold_group()
    index = {key("a"): (group,), key("b"): (group,)}
    moved, (shape,) = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    floor = shape.bottom - 1
    earlier = Finding(
        code=PAGE_OVERFULL, severity=Severity.WARNING, subjects=(hid("function", 9),), message="m"
    )
    other = Finding(code="OTHER", severity=Severity.INFO, subjects=(), message="x")
    assert fold_overfull(moved, [shape], shape.bottom, (other,)) == (other,)
    found = fold_overfull(moved, [shape], floor, (earlier, other))
    assert [one.code for one in found] == ["OTHER", PAGE_OVERFULL]
    assert hid("function", 9) in found[1].subjects
    assert {hid("function", 2), shape.lead} <= set(found[1].subjects)


def replica_page(*, bottom: bool) -> tuple[GroupShape, GroupShape]:
    """The group's shape on a page with a top-edge replica in column a, and with `bottom` a
    bottom-edge replica in column b; and the shape of the same page with no replica."""
    base = fold_group()
    shown = interface(J3, views=[hid("function", 13)], line=False)
    low = interface(hid("function", 5), views=[hid("function", 14)], line=False)
    unit = replace(base.unit, interfaces=(*base.unit.interfaces, shown, low))
    group = replace(base, unit=unit, top=frozenset({J1, J3}))
    index = {key("a"): (group,), key("b"): (group,)}
    page = (*three_columns(), placed(13, x=96, y=56, name="a"))
    if bottom:
        page = (*page, placed(14, x=96, y=56, name="b"))
    _, (shape,) = fold_page(page, page_plan(("a", "b", "c")), index, PROFILE)
    _, (clear,) = fold_page(three_columns(), page_plan(("a", "b", "c")), index, PROFILE)
    return shape, clear


def test_a_group_with_replicas_in_its_upper_band_is_cut_below() -> None:
    """TALL-PAGE A1: the top cut is held for such a group; its shape asks for the bottom cut.

    UNDO: `measured` sets `below` False, and the group is not cut at its bottom edge.
    """
    shape, clear = replica_page(bottom=False)
    assert shape.below
    index = {key("a"): (fold_group(),), key("b"): (fold_group(),)}
    assert tall_groups(pages_of(shape), shape.bottom - 1, index) == {
        shape.unit: Cut(shape.frame_dx, below=True)
    }
    assert not shape.held
    assert not clear.below


def test_a_group_with_replicas_on_both_edges_is_held() -> None:
    """TALL-PAGE A1: no cut works when the bottom edge holds a replica too (layout-0167).

    UNDO: `measured` leaves `held` False, and the group is cut below with its bottom replica.
    """
    shape, _ = replica_page(bottom=True)
    assert shape.held
    assert not shape.below


def test_a_group_cut_below_has_its_outline_on_the_page_of_its_upper_band() -> None:
    """TALL-PAGE A1: the page of the upper band folds the group; the page of the lower band none.

    UNDO: `_here` lists a group cut below on the page of its lower band, as a top cut is.
    """
    group = replace(fold_group(), cut=True, below=True)
    index = {key("a"): (group,), key("b"): (group,)}
    only_a = (placed(1, x=96, y=96, name="a"),)
    only_b = (placed(2, x=96, y=152, name="b"),)
    _, (shape,) = fold_page(only_a, page_plan(("a",)), index, PROFILE)
    _, none = fold_page(only_b, page_plan(("b",), number=2), index, PROFILE)
    assert sorted(one.function.value for one in shape.boxes) == sorted(
        one.value for one in (J1, J2, PLUG)
    )
    assert none == ()
