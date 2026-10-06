"""S16: Room's N or S call on hand-made columns: a column-end text is margin, never a cell.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` at `in` on top of its
32 G keep-out, facing N; port `10n + 2` at `out` at its bottom, facing S. Column `a` holds
function 1 and column `b` function 2, whose keep-out a label box grows 24 G upward (C8(b)). So
`b`'s `in` stands 24 G deeper than `a`'s, and the run joining the two meets there: `a` is
lowered 24 G, and both columns then need 56 G of room (`join_y`). Every page keeps M4's band
above and below its columns, 48 G with `PROFILE`, and a column-end text that reaches past the
band adds the excess to the page's margin. The texts are built through `page_texts`, as the
engine builds them: each one line high (S16).
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import Box, Facing, Point, snap_up
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import _reference_band, page_stack
from fransys_layout.stages.references.marker_boxes import reference_size
from fransys_layout.stages.references.types import MarkerDecision
from fransys_layout.stages.stacking import JoinEnd, PageStack, join_y
from fransys_layout.stages.texts.stand import _text_box, page_texts
from fransys_layout.stages.types import MarkerSide, SheetFormat, StubText

_PLAN = page_plan(("a", "b"))
_COLUMNS = (column("a", (1,)), column("b", (2,)))
_FUNCTIONS = (drawn(1), drawn(2))
_LABELS = {hid("function", 2): [("marking.in", Box(x=16, y=-40, width=16, height=8))]}
_BAND = _reference_band(SHEET, PROFILE)  # M4: 48 G at the top and at the bottom of every page
_RUN = ((("invented", "a"), hid("port", 11)), (("invented", "b"), hid("port", 21)))


def _reference(port: int, *, lines: int, out: int) -> MarkerDecision:
    """A star reference of `lines` lines at port `port` (of function `port // 10`), `out` G out."""
    return MarkerDecision(
        connection=hid("conductor", port),
        function=hid("function", port // 10),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        star="ref",
        lines=lines,
        size=reference_size(SHEET, PROFILE, lines=lines),
        partner=hid("port", 91),
        partner_set=1,
        partner_page=2,
        out=out,
    )


def _stack(*texts: MarkerDecision, sheet: SheetFormat = SHEET) -> PageStack:
    """The page as `place` stacks it, with `texts` as Room reserves them (`page_texts`) or none."""
    reserved = page_texts(texts, frozenset(), sheet=sheet, profile=PROFILE)[1, 1] if texts else None
    stacking = PageStacking(profile=PROFILE, sheet=sheet, label_boxes=_LABELS, texts=reserved)
    return page_stack(_PLAN, _COLUMNS, _FUNCTIONS, stacking)


def _ends(stack: PageStack) -> tuple[JoinEnd, ...]:
    """The run's ends as `references` reads them off `stack` (`joins.port_spots`)."""
    return tuple(
        JoinEnd(
            port=port,
            row=stack.ports[key, port].row,
            offset=stack.ports[key, port].offset,
            height=stack.heights[key],
        )
        for key, port in _RUN
    )


def test_the_n_or_s_call_shrinks_the_room_and_changes_no_join_end() -> None:
    """A reference pushed 16 G out over `a`'s N port, and one under `b`'s S port: the room
    shrinks by both pushes, and every port's row and offset and every column's height stay as
    `references` read them before any text existed."""
    # UNDO: stages/place.py `_text_room`, first rows: `boxes += _owned(...)` -> grow the cell by
    #     them instead (`cell.geometry = grow_keepout(cell.geometry, owned)` when it owns any):
    #     `a`'s keep-out then grows 32 G up, so its ports stand 32 G deeper below the top
    texts = (_reference(11, lines=1, out=16), _reference(22, lines=1, out=16))
    decided, final = _stack(), _stack(*texts)
    assert final.room == decided.room - 32  # premise: both pushes are reserved, 16 G each
    assert final.ports == decided.ports
    assert final.heights == decided.heights
    assert final.last == decided.last
    assert _ends(final) == _ends(decided)


def test_a_merged_stubs_line_is_reserved_above_its_reference() -> None:
    """A reference at `a`'s N port stays inside M4's band and costs no room; the same reference
    with a stub merged into it (S5) is a longer turned box (M7) that reaches past the band, so
    the room shrinks by what passes the band, snapped to the grid."""
    # UNDO: stages/texts/stand.py `text_box`: `return box if one.merge is None else ...` ->
    #     `return box` (the merged stub's line is not reserved)
    stub = StubText(cable="-W1", far="+DB-X0", port=":1")
    plain = _reference(11, lines=1, out=0)
    merged = replace(plain, merge=stub)
    reach = -_text_box(merged, Point(x=0, y=0), Facing.N, PROFILE).y  # the port is at the origin
    assert reach > _BAND  # premise: the merged text outreaches the band
    assert _stack(plain).room == _stack().room
    assert _stack(merged).room == _stack().room - (snap_up(reach) - _BAND)


def test_a_run_at_the_room_limit_fits_the_final_room_beside_a_long_list() -> None:
    """The content box is cut to the 56 G the run needs, plus M4's bands above and below: a 3-line
    list at `a`'s N port, on the run's own port, takes no more room than one line (S16), which
    the band holds, so the run `references` joined still fits the room `place` places it in."""
    # UNDO: stages/place.py `_stack_page`: drop `lift, sink = max(lift, band), max(sink, band)`
    #     (no band: the room is 64 G longer than the run's, and the at-the-limit premise fails)
    sheet = replace(SHEET, content_height=_BAND + 56 + _BAND)
    decided = _stack(sheet=sheet)
    assert join_y(_ends(decided), decided.room) == 24  # `a` lowered to `b`'s offset
    assert join_y(_ends(decided), decided.room - 1) is None  # premise: the page is at the limit
    final = _stack(_reference(11, lines=3, out=0), sheet=sheet)
    assert join_y(_ends(final), final.room) == 24
