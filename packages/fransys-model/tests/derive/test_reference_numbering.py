"""LD3/LD5's reference numbering (`derive.drawing_text`): `row_letter`, `frame_row`,
`position_text`'s new signature, `_reference_group`'s four shapes, and `reference_number`'s
per-drawing-set count (spec `docs/specs/2026-09-25-layout-redesign.md`, the D4 amendment
committed at main `4a280102`).

Hand-built records only, the same conventions as `test_drawing_text.py` (`_ids`, `_key`,
`_sheet`, `add_all`, `freeze`), kept in a file of its own so this work order never touches a
file another agent is concurrently editing.
"""

import itertools
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest import mock

from derive_helpers import add_all

from fransys_model.derive import drawing_text as dt
from fransys_model.derive.drawing_text import (
    _reference_group,
    frame_row,
    position_text,
    reference_number,
    row_letter,
)
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    PageRole,
    SheetFormat,
    Side,
    StarKind,
)
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortRole

if TYPE_CHECKING:
    from collections.abc import Callable

PRODUCED_BY = "test-engine 0.0.0"

# The same house-conventions sheet as `test_drawing_text.py`: content_width_mm=400,
# content_height_mm=257, module_mm=2.5 -> 1280 grid units wide (8 columns), 822 tall (6 rows).
CONTENT_WIDTH_GRID = 1280
FRAME_COLUMNS = 8
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
    new_id: Callable[[str], Id[Any]], *, number: int, location: Id[Any] | None = None
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


def _function(new_id: Callable[[str], Id[Any]], *, item: Id[Item]) -> Function:
    id_ = new_id("function")
    return Function(
        id=id_, key=_key(id_), item=item, template=None, name="fn", kind=FunctionKind.COIL
    )


def _port(new_id: Callable[[str], Id[Any]], *, function: Id[Function]) -> Port:
    id_ = new_id("port")
    return Port(
        id=id_, key=_key(id_), function=function, template=None, name="1", role=PortRole.GENERIC
    )


def _pair(
    new_id: Callable[[str], Id[Any]], *, item: Id[Item], page: Id[Page], x: int, y: int = 0
) -> tuple[Function, Function, Port, Port, LinkMarker, LinkMarker]:
    """A plain severed pair: two markers, both ends on `page` at `x`/`y`, with their own ports."""
    fn_a = _function(new_id, item=item)
    fn_b = _function(new_id, item=item)
    port_a = _port(new_id, function=fn_a.id)
    port_b = _port(new_id, function=fn_b.id)
    a_id = new_id("layout.link_marker")
    b_id = new_id("layout.link_marker")
    a = LinkMarker(
        id=a_id,
        key=_key(a_id),
        page=page,
        port=port_a.id,
        side=MarkerSide.OWNER,
        partner=b_id,
        x=x,
        y=y,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    b = LinkMarker(
        id=b_id,
        key=_key(b_id),
        page=page,
        port=port_b.id,
        side=MarkerSide.USER,
        partner=a_id,
        x=x,
        y=y,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    return (fn_a, fn_b, port_a, port_b, a, b)


# --------------------------------------------------------------------------------------
# row_letter
# --------------------------------------------------------------------------------------


def test_row_letter_of_zero_is_a() -> None:
    assert row_letter(0) == "A"


def test_row_letter_of_five_is_f() -> None:
    assert row_letter(5) == "F"


# --------------------------------------------------------------------------------------
# frame_row
# --------------------------------------------------------------------------------------


def test_frame_row_at_the_top_of_the_content_box_is_a() -> None:
    assert frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0) == "A"


def test_frame_row_at_the_bottom_of_the_content_box_is_the_last_letter() -> None:
    """Six rows: the bottom band is `row_letter(5)`, `"F"`."""
    assert frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, CONTENT_HEIGHT_GRID - 1) == "F"


def test_frame_row_of_two_different_bands_differ() -> None:
    """Can-fail shape: top and bottom must land in different bands, not just both be valid."""
    top = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, 0)
    bottom = frame_row(CONTENT_HEIGHT_GRID, FRAME_ROWS, CONTENT_HEIGHT_GRID - 1)
    assert top != bottom


# --------------------------------------------------------------------------------------
# position_text
# --------------------------------------------------------------------------------------


def test_position_text_same_set_form() -> None:
    assert position_text(2, 1, "A", ()) == "p2:1A"


def test_position_text_location_prefixed_form() -> None:
    assert position_text(2, 1, "A", ("C1",)) == "+C1p2:1A"


def test_position_text_cross_set_form() -> None:
    """C18: an empty prefix into another set names the set instead, `p<set>.<page>:<col><row>`."""
    assert position_text(2, 1, "A", (), set_number=3) == "p3.2:1A"


# --------------------------------------------------------------------------------------
# _reference_group: the four persisted shapes, plus the pure-stub exclusion (D4)
# --------------------------------------------------------------------------------------


def test_reference_group_of_a_plain_pair_is_the_pair() -> None:
    new_id = _ids()
    page = new_id("layout.page")
    a_id = new_id("layout.link_marker")
    b_id = new_id("layout.link_marker")
    a = LinkMarker(
        id=a_id,
        key=_key(a_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.OWNER,
        partner=b_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    b = LinkMarker(
        id=b_id,
        key=_key(b_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.USER,
        partner=a_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
    )
    markers = {a.id: a, b.id: b}
    assert _reference_group(a, markers, {}) == (a, b)


def test_reference_group_of_a_star_reference_is_the_ref_and_its_branches() -> None:
    new_id = _ids()
    page = new_id("layout.page")
    ref_id = new_id("layout.link_marker")
    branch1_id = new_id("layout.link_marker")
    branch2_id = new_id("layout.link_marker")
    ref = LinkMarker(
        id=ref_id,
        key=_key(ref_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.OWNER,
        partner=branch1_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.REF,
    )
    branch1 = LinkMarker(
        id=branch1_id,
        key=_key(branch1_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.USER,
        partner=ref_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.BRANCH,
    )
    branch2 = LinkMarker(
        id=branch2_id,
        key=_key(branch2_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.USER,
        partner=ref_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.BRANCH,
    )
    markers = {m.id: m for m in (ref, branch1, branch2)}
    branches_of = {ref.id: (branch1, branch2)}
    group = _reference_group(ref, markers, branches_of)
    assert group is not None
    assert {m.id for m in group} == {ref.id, branch1.id, branch2.id}


def test_reference_group_of_a_c17_split_is_the_two_mutual_branches() -> None:
    """Two mutual `BRANCH` markers, neither a `REF`: the split stands alone, no hub."""
    new_id = _ids()
    page = new_id("layout.page")
    a_id = new_id("layout.link_marker")
    b_id = new_id("layout.link_marker")
    a = LinkMarker(
        id=a_id,
        key=_key(a_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.OWNER,
        partner=b_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.BRANCH,
    )
    b = LinkMarker(
        id=b_id,
        key=_key(b_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.USER,
        partner=a_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.BRANCH,
    )
    markers = {a.id: a, b.id: b}
    group = _reference_group(a, markers, {})
    assert group is not None
    assert {m.id for m in group} == {a.id, b.id}


def test_reference_group_of_a_merged_off_stub_is_the_stub_and_its_branches() -> None:
    """`star is OFF`, named by a `BRANCH` via `branches_of`: a reference merged with a stub."""
    new_id = _ids()
    page = new_id("layout.page")
    off_id = new_id("layout.link_marker")
    branch_id = new_id("layout.link_marker")
    off = LinkMarker(
        id=off_id,
        key=_key(off_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.OWNER,
        partner=off_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.OFF,
        far=new_id("port"),
        facing=Side.S,
    )
    branch = LinkMarker(
        id=branch_id,
        key=_key(branch_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.USER,
        partner=off_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.BRANCH,
    )
    markers = {off.id: off, branch.id: branch}
    branches_of = {off.id: (branch,)}
    group = _reference_group(off, markers, branches_of)
    assert group is not None
    assert {m.id for m in group} == {off.id, branch.id}


def test_reference_group_of_a_pure_off_stub_is_none() -> None:
    """`star is OFF` with no branch naming it (D4): excluded, not a reference at all."""
    new_id = _ids()
    page = new_id("layout.page")
    off_id = new_id("layout.link_marker")
    off = LinkMarker(
        id=off_id,
        key=_key(off_id),
        page=page,
        port=new_id("port"),
        side=MarkerSide.OWNER,
        partner=off_id,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.OFF,
        far=new_id("port"),
        facing=Side.S,
    )
    markers = {off.id: off}
    assert _reference_group(off, markers, {}) is None


# --------------------------------------------------------------------------------------
# reference_number: reading order and the LD6 per-drawing-set restart
# --------------------------------------------------------------------------------------


def test_reference_number_orders_groups_by_reading_position_not_insertion_order(
    origin: Origin,
) -> None:
    """The earlier reading position is `#1`, regardless of which pair the draft added first."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    add_all(draft, sheet, ds, page, item, origin=origin)
    late = _pair(new_id, item=item.id, page=page.id, x=1200)  # added to the draft first
    add_all(draft, *late, origin=origin)
    early = _pair(new_id, item=item.id, page=page.id, x=0)  # added second
    add_all(draft, *early, origin=origin)
    model = freeze(draft)
    assert reference_number(model, early[-2]) == 1
    assert reference_number(model, late[-2]) == 2


def test_reference_number_restarts_at_one_in_a_second_drawing_set(origin: Origin) -> None:
    """LD6: the count runs through one drawing; a second set's own group starts back at #1."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds1 = _drawing_set(new_id, number=1)
    page1 = _page(new_id, drawing_set=ds1.id, number=1, sheet_format=sheet.id)
    ds2 = _drawing_set(new_id, number=2)
    page2 = _page(new_id, drawing_set=ds2.id, number=1, sheet_format=sheet.id)
    item = _item(new_id, designation="K1")
    add_all(draft, sheet, ds1, page1, ds2, page2, item, origin=origin)
    first_set_pair = _pair(new_id, item=item.id, page=page1.id, x=0)
    second_set_pair = _pair(new_id, item=item.id, page=page2.id, x=0)
    add_all(draft, *first_set_pair, origin=origin)
    add_all(draft, *second_set_pair, origin=origin)
    model = freeze(draft)
    assert reference_number(model, first_set_pair[-2]) == 1
    assert reference_number(model, second_set_pair[-2]) == 1


def _star(
    new_id: Callable[[str], Id[Any]], *, item: Id[Item], page: Id[Page], branches: int
) -> tuple[Function | Port | LinkMarker, ...]:
    """A star reference (`branches + 1` ends total): one `REF` and `branches` mutual `BRANCH`es.

    One `Function`/`Port` per end (`freeze` checks a marker's `port` reference), no real
    designation needed: `marker_text` for a `REF`/`BRANCH` marker never reads either (only a
    pure off stub's own text and Option B's `_partner_row` do, neither exercised here).
    """
    ref_id = new_id("layout.link_marker")
    branch_ids = [new_id("layout.link_marker") for _ in range(branches)]
    ref_fn = _function(new_id, item=item)
    ref_port = _port(new_id, function=ref_fn.id)
    ref = LinkMarker(
        id=ref_id,
        key=_key(ref_id),
        page=page,
        port=ref_port.id,
        side=MarkerSide.OWNER,
        partner=branch_ids[0],
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        star=StarKind.REF,
    )
    made: list[Function | Port | LinkMarker] = [ref_fn, ref_port, ref]
    for index, branch_id in enumerate(branch_ids):
        branch_fn = _function(new_id, item=item)
        branch_port = _port(new_id, function=branch_fn.id)
        branch = LinkMarker(
            id=branch_id,
            key=_key(branch_id),
            page=page,
            port=branch_port.id,
            side=MarkerSide.USER,
            partner=ref_id,
            x=(index + 1) * 160,  # each branch a full column (1280 / 8) apart, distinct letters
            y=0,
            width=13,
            height=8,
            produced_by=PRODUCED_BY,
            star=StarKind.BRANCH,
        )
        made.extend((branch_fn, branch_port, branch))
    return tuple(made)


def test_marker_text_gives_one_two_and_four_lines_for_two_three_and_five_ends(
    origin: Origin,
) -> None:
    """Acceptance 3 (LD3): a reference with 2, 3 and 5 ends prints 1, 2 and 4 lines, exact texts.

    Each group is its own drawing set, so its own `#1` and no cross-group interference. A
    2-end net is a plain severed pair (`_pair`); 3- and 5-end nets are star references
    (`_star`, `branches=2`/`4`).
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    sets = [_drawing_set(new_id, number=n) for n in (1, 2, 3)]
    pages = [_page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id) for ds in sets]
    item = _item(new_id, designation="K1")
    add_all(draft, sheet, *sets, *pages, item, origin=origin)

    pair = _pair(new_id, item=item.id, page=pages[0].id, x=0)
    add_all(draft, *pair, origin=origin)
    three = _star(new_id, item=item.id, page=pages[1].id, branches=2)
    add_all(draft, *three, origin=origin)
    five = _star(new_id, item=item.id, page=pages[2].id, branches=4)
    add_all(draft, *five, origin=origin)
    model = freeze(draft)

    def _ref(made: tuple) -> LinkMarker:
        return next(m for m in made if isinstance(m, LinkMarker) and m.star is StarKind.REF)

    pair_marker = pair[-2]  # a LinkMarker, the tuple's own trailing pair (see _pair)
    three_ref, five_ref = _ref(three), _ref(five)
    assert dt.marker_text(model, pair_marker).count("\n") + 1 == 1
    assert dt.marker_text(model, three_ref).count("\n") + 1 == 2  # the reference (3 ends)
    assert dt.marker_text(model, five_ref).count("\n") + 1 == 1  # C2: 4 targets, first and count
    # exact texts, not just counts: each line is #<n>-<the other end's position>, sorted
    # the ends stand on the reference's own page, so the cell alone
    assert dt.marker_text(model, three_ref) == "#1-2A\n#1-3A"
    assert (
        dt.marker_text(model, five_ref) == "#1-2A +3"
    )  # C2: three or more print the first + count


def _star_over_pages(origin: Origin, numbers: tuple[int, ...]):
    """A star whose reference stands on page 1 and whose branches stand on pages `numbers`."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    drawing_set = _drawing_set(new_id, number=1)
    pages = {
        n: _page(new_id, drawing_set=drawing_set.id, number=n, sheet_format=sheet.id)
        for n in (1, *numbers)
    }
    item = _item(new_id, designation="K1")
    made = _star(new_id, item=item.id, page=pages[1].id, branches=len(numbers))
    branches = iter(numbers)
    moved = tuple(
        replace(m, page=pages[next(branches)].id)
        if isinstance(m, LinkMarker) and m.star is StarKind.BRANCH
        else m
        for m in made
    )
    add_all(draft, sheet, drawing_set, *pages.values(), item, *moved, origin=origin)
    ref = next(m for m in moved if isinstance(m, LinkMarker) and m.star is StarKind.REF)
    return freeze(draft), ref


def test_the_first_target_is_by_page_number_not_by_text(origin: Origin) -> None:
    """C2 (model-0139): targets on p2 and p10 print p2 first, numbers compared by value.

    # UNDO: `_own_text` sorts the printed positions as strings ("p10:" sorts before "p2:")
    """
    model, ref = _star_over_pages(origin, (10, 2))
    assert dt.marker_text(model, ref).split("\n") == ["#1-p2:3A", "#1-p10:2A"]
    model, ref = _star_over_pages(origin, (10, 2, 3))
    assert dt.marker_text(model, ref) == "#1-p2:3A +2"


def test_two_ends_in_one_cell_print_one_line() -> None:
    """C2 (model-0139): the full branch drops a repeated position, as the count branch does."""
    assert dt.target_lines(1, ["1A", "1A"]) == ["#1-1A"]
    assert dt.target_lines(1, ["1A", "1A", "1A"]) == ["#1-1A"]
    assert dt.target_lines(1, ["1A", "2A", "2A"]) == ["#1-1A +1"]


def test_rank_drawing_set_runs_once_per_drawing_set_not_per_marker_read(origin: Origin) -> None:
    """The count test (D4 amendment, main `4a280102`): grouping runs once per drawing set, never
    once per marker read. Two drawing sets, three severed pairs each (12 markers total), 12
    calls to `reference_number` -- `_rank_drawing_set` must run exactly ONCE PER SET, twice
    total, not twelve times (a second set proves it truly counts sets, not just "once").
    """
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    item = _item(new_id, designation="K1")
    add_all(draft, sheet, item, origin=origin)
    all_pairs = []
    for set_number in (1, 2):
        ds = _drawing_set(new_id, number=set_number)
        page = _page(new_id, drawing_set=ds.id, number=1, sheet_format=sheet.id)
        add_all(draft, ds, page, origin=origin)
        pairs = [_pair(new_id, item=item.id, page=page.id, x=200 * i) for i in range(3)]
        for records in pairs:
            add_all(draft, *records, origin=origin)
        all_pairs.extend(pairs)
    model = freeze(draft)
    markers = [marker for records in all_pairs for marker in records[-2:]]
    assert len(markers) == 12

    dt._reference_numbers.cache_clear()
    real_rank_drawing_set = dt._rank_drawing_set
    with mock.patch.object(dt, "_rank_drawing_set", wraps=real_rank_drawing_set) as patched:
        for marker in markers:
            reference_number(model, marker)
        assert patched.call_count == 2  # once per drawing set, not once per marker read
    assert dt._reference_numbers.builds == 1
