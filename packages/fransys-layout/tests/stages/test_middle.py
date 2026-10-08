"""HL11 to HL13 and HL20: a middle unit's stripped columns, groups, bands and folded outline."""

from dataclasses import replace
from fractions import Fraction
from typing import TYPE_CHECKING

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
from fransys_layout.stages.middle_fold import GroupShape, fold_page, shape_boxes
from fransys_layout.stages.middle_reach import line_reach
from fransys_model.derive import natural_key
from fransys_model.kernel import Id

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
