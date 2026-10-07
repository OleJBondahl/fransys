"""D14 (M2) and D17 (deep-dive spec, GOLDEN-FIX 2 part 3c): a marker box never shifts the page.

A marker box that would cross a side edge of the content box stands against that edge instead,
its stub still at its port and still over the box, and grows away from the edge (layout-0068).
A star reference at the first column has its box past the left edge (LD3 (c): the sheet's fixed
reference width); its list growing taller from two entries to three (a branch added on another
page) must not move the whole page (`shift_pages`, C22b).

The page test builds three lamps' star (`H1` is the reference on page 1, `H2`, `H3`, `H4` the
branches on pages 2 to 4) and adds the third branch. The unit tests state the rule at the left
and right edge, for the markers' call (`place_markers`, S20 M5) and for a run box (C21, M8), and
the cases where the box stays (a shared box, M3; a neighbour in the way).
"""

from dataclasses import replace
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
from samples import (
    PROFILE,
    SHEET,
    built,
    connection,
    drawn,
    hid,
    page_plan,
    placed,
    standing,
)

from fransys_layout.geometry import WIRING_GRID, Box, Point, overlaps
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.references.off_stubs import _off_markers
from fransys_layout.stages.references.types import MarkerScene, OffStubs
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers
from fransys_layout.stages.tidy import shift_pages
from fransys_layout.stages.types import StubText
from fransys_model.kernel import Id, Severity
from fransys_model.layout import LinkMarker as MarkerRecord
from fransys_model.layout import Page, StarKind, SymbolPlacement, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Marker edge",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_FILLERS = 8  # lamps per branch group: one group fills a page, so each group is a page of its own


def _star(*, third_branch: bool):
    """Reference `H1` (group G1, first column of page 1); branches `H2`, `H3`, and `H4` if asked."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    groups = [d.group(name, name) for name in ("G1", "G2", "G3", "G4")]
    wire = d.wiring(colour="BU", gauge="0.5")

    def lamp(tag: str, group: int):
        return d.item("DEMO-LAMP-24", tag=tag, at=cabinet, group=groups[group]).fn("lamp")["1"]

    hub, branches = lamp("H1", 0), [lamp("H2", 1), lamp("H3", 2), lamp("H4", 3)]
    for group in (1, 2, 3):
        for n in range(_FILLERS):
            lamp(f"Y{group}{n}", group)
    for branch in branches[: 3 if third_branch else 2]:
        wire(hub, branch)
    return fr.build(parts, d.draft(), layout_trigger_document())


def _page_one(result):
    """Page 1's placements as `{tag: (x, y)}` and its star reference marker record."""
    model = result.model
    (page,) = (p.id for p in layout_of(model, Page).values() if p.number == 1)
    placed = {
        r.key[3]: (r.x, r.y) for r in layout_of(model, SymbolPlacement).values() if r.page == page
    }
    (ref,) = (
        m
        for m in layout_of(model, MarkerRecord).values()
        if m.page == page and m.star is StarKind.REF
    )
    return placed, ref


def test_a_reference_list_that_grows_at_the_first_column_moves_nothing() -> None:
    """D17 with M1 and M3: page 1's placements are the same with two branches and with three.

    The reference at the first column is vertical (M1): the sheet's fixed reference width
    (LD3 (c)) is its length, 42 G, and the third branch adds one line side by side (M3), one
    `text_height` wider. Vertical, it no longer crosses the left edge (it stood at x=0 once the
    centred box did, D14 M2), so it stays centred on its stub inside the content box and the
    page does not shift for it.

    # UNDO: `stand.vertical` returns False (the box is horizontal: `ref.vertical` fails, and the
    # third line grows its height, not its width)
    """
    before, after = _star(third_branch=False), _star(third_branch=True)
    (placed_before, ref_before), (placed_after, ref) = _page_one(before), _page_one(after)
    assert ref.vertical
    # C2 (model-0139): the third branch makes four ends, so the box prints the first target and
    # a count, one line where two branches printed two: one `text_height` narrower, still no move
    assert ref_before.width - ref.width == PROFILE.text_height
    assert ref.height == ref_before.height  # LD3 (c): the fixed reference length
    assert ref.box_x is None  # centred on its stub ...
    assert ref.x - ref.width // 2 >= 0  # ... and inside the content box
    assert placed_after == placed_before  # D17: no placement of page 1 moved
    assert ref.x == ref_before.x  # the port did not move
    assert not [f for f in after.findings if f.severity is Severity.ERROR]
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in after.findings}


_SHEET = replace(SHEET, content_width=400, content_height=400)


def _marker(at: Point, box: Box, *, shared: bool = False) -> LinkMarker:
    """A star reference marker above its port `at`, its box `box`."""
    return LinkMarker(
        connection=Id(kind="conductor", value="9" * 32),
        port=Id(kind="port", value=f"{at.x:032x}"),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=at,
        box=box,
        partner_page=2,
        shared_box=shared,
        star="ref",
    )


def _placed_alone(*markers: LinkMarker) -> tuple[tuple[LinkMarker, ...], tuple]:
    """`place_markers` over no function: the markers as placed in the unshifted content box."""
    return place_markers(
        markers,
        (),
        (),
        MarkerRoom(
            columns=(),
            connections=(),
            joins=(),
            wired=frozenset(),
            sheet=_SHEET,
            profile=PROFILE,
        ),
    )


def test_a_box_crossing_the_right_edge_stands_against_it_and_grows_left() -> None:
    """D14 M2 at the right edge: the box ends at `content_width`, its stub is still over it.

    The markers' call (`marker_row._tier`) offers the box against either content edge among its
    places, and `Space.holds` refuses the centred home that crosses it.

    # UNDO: `_tier` drops `room.width - box.width` from its steps (the nearest place is x=349)
    """
    at = Point(x=390, y=40)
    box = Box(x=at.x - 22, y=28, width=45, height=12)  # centred on the port: right edge at 413
    assert box.x + box.width > _SHEET.content_width  # the premise
    (moved,), findings = _placed_alone(_marker(at, box))
    assert moved.box.x + moved.box.width == _SHEET.content_width
    assert (moved.box.y, moved.box.width, moved.box.height) == (box.y, box.width, box.height)
    assert moved.box.x <= moved.at.x <= moved.box.x + moved.box.width
    assert moved.at == at  # the port and so the stub stay
    assert moved.shared_box
    assert moved.lead
    assert findings == ()


def test_a_box_inside_the_content_box_is_left_alone() -> None:
    """A box that crosses no edge and covers no lane is returned as it was.

    # UNDO: `_place` reads every home as on a lane (`fits=False`): the box is re-placed
    """
    marker = _marker(Point(x=100, y=40), Box(x=78, y=28, width=45, height=12))
    assert _placed_alone(marker) == ((marker,), ())


def test_a_box_flush_with_the_content_edge_stays_and_one_unit_past_it_moves() -> None:
    """The content box is closed (D2 P3): a box ending exactly at `content_width`, or starting at
    x=0, is inside it and stays; one unit past either edge is not, and moves.

    # UNDO: `Space.holds` tests `contains` with a strict comparison (the flush box moves)
    """
    right = _marker(Point(x=380, y=40), Box(x=355, y=28, width=45, height=12))
    left = _marker(Point(x=20, y=40), Box(x=0, y=28, width=45, height=12))
    assert _placed_alone(right) == ((right,), ())
    assert _placed_alone(left) == ((left,), ())
    past_right = replace(right, box=replace(right.box, x=356))
    past_left = replace(left, box=replace(left.box, x=-1))
    (moved_right,), _ = _placed_alone(past_right)
    (moved_left,), _ = _placed_alone(past_left)
    assert moved_right.box.x + moved_right.box.width <= _SHEET.content_width
    assert moved_left.box.x >= 0


def _pump_motor(*, wide: bool):
    """Motor `M1` at the first column (x=16 before any shift): ports U and W a lane apart (16 G)
    are the hubs of two stars, so their vertical reference boxes stand side by side (M1).

    U's list names one page ("/2.1", 17 G), or two when `wide` (a branch added in group G3, 31 G).
    W's list names three pages (45 G). Groups G2 to G4 are pages of their own (eight lamps each).
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    groups = [d.group(name, name) for name in ("G1", "G2", "G3", "G4")]
    wire = d.wiring(colour="BU", gauge="0.5")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=cabinet, group=groups[0]).fn("motor")

    def lamp(tag: str, group: int):
        return d.item("DEMO-LAMP-24", tag=tag, at=cabinet, group=groups[group]).fn("lamp")["1"]

    for group in (1, 2, 3):
        for n in range(_FILLERS):
            lamp(f"Y{group}{n}", group)
    for n, group in enumerate((1, 1, 2) if wide else (1, 1)):
        wire(motor["U"], lamp(f"A{n}", group))
    for group in (1, 2, 3):
        wire(motor["W"], lamp(f"B{group}", group))
    return fr.build(parts, d.draft(), layout_trigger_document())


def _x_span(ref) -> tuple[int, int]:
    """A vertical reference record's left and right edge: `box_x` when it stands off its stub,
    else centred on `x`."""
    left = ref.x - ref.width // 2 if ref.box_x is None else ref.box_x
    return left, left + ref.width


def test_a_reference_row_that_grows_wider_moves_no_placement_of_its_page() -> None:
    """D17 with M1 and C2: U's list growing by a branch never shifts the page.

    The reference boxes of the pins U and W (16 G apart) are vertical (M1) and as long as the
    sheet's fixed reference width (LD3 (c)). U's two-line box (two targets, printed in full)
    leaves W room beside it. With the added branch U has three targets and prints the first
    and a count (C2, model-0139): one line, narrower, so W still stands beside it. W's own
    three targets print one line. No box leaves the content box and none is left without a
    place. The tier (`stub_extra`) a wider box would force is tested in `test_marker_row`.

    # UNDO: `marker_lines` counts every target as a line (U's box grows and W moves a tier out)
    """
    before, after = _pump_motor(wide=False), _pump_motor(wide=True)
    (placed_before, refs_before), (placed_after, refs_after) = (
        _motor_page(before),
        _motor_page(after),
    )
    assert placed_after == placed_before  # D17: nothing on the page moved
    for refs in (refs_before, refs_after):
        assert set(refs) == {"U", "W"}
        assert all(
            m.vertical and m.height == refs["U"].height for m in refs.values()
        )  # M1, LD3 (c)
        assert min(_x_span(m)[0] for m in refs.values()) >= 0  # inside the content box
    assert (
        refs_before["U"].width - refs_after["U"].width == PROFILE.text_height
    )  # C2: two lines, one
    for refs in (refs_before, refs_after):
        assert refs["U"].stub_extra == refs["W"].stub_extra == 0
        assert _x_span(refs["U"])[1] <= _x_span(refs["W"])[0]  # side by side
    for result in (before, after):
        codes = {f.code for f in result.findings}
        assert "OUT_OF_CONTENT_BOX" not in codes
        assert "LABEL_UNPLACED" not in codes


def _motor_page(result):
    """Page 1's placements as `{tag: (x, y)}` and its star reference markers by port name."""
    model = result.model
    (page,) = (p.id for p in layout_of(model, Page).values() if p.number == 1)
    placed = {
        r.key[3]: (r.x, r.y) for r in layout_of(model, SymbolPlacement).values() if r.page == page
    }
    refs = {
        m.key[-2]: m
        for m in layout_of(model, MarkerRecord).values()
        if m.page == page and m.star is StarKind.REF
    }
    return placed, refs


def _star_marker(number: int, x: int, width: int) -> LinkMarker:
    """A star reference at port `number` of function `number` (x, 40), its box centred above."""
    return LinkMarker(
        connection=hid("conductor", number),
        port=hid("port", number * 10 + 2),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=x, y=40),
        box=Box(x=x - width // 2, y=28, width=width, height=12),
        partner_page=2,
        star="ref",
    )


def test_a_row_at_the_left_edge_stands_inside_the_content_box_each_over_its_own_stub() -> None:
    """D14 M2 for a row: stubs at 16 and 48, lists 45 G wide each. Centred, the first box would
    stand at x=-6 (past the edge) and the second at x=26 and they would meet once the first is
    against the edge (0..45). The greedy walk (S20) puts the first (the port nearer the edge) at
    the edge and the second, which has no place beside it, one tier out at its own centred x:
    both inside the content box, each over its own stub with half a grid of margin, no two
    boxes meeting, nothing reported.

    # UNDO: `place_texts` admits a place that overlaps a box already placed (the boxes meet)
    """
    row, findings = _placed_alone(_star_marker(1, 16, 45), _star_marker(2, 48, 45))
    assert findings == ()
    first, second = row
    assert first.box == Box(x=0, y=28, width=45, height=12)  # against the edge, grows right
    assert second.box == Box(x=26, y=16, width=45, height=12)  # one tier out, centred
    assert second.stub_extra == second.box.height
    assert not overlaps(first.box, second.box)
    for marker in row:
        assert marker.box.x >= 0
        assert marker.box.x + marker.box.width <= _SHEET.content_width
        assert marker.box.x + WIRING_GRID // 2 <= marker.at.x
        assert marker.at.x <= marker.box.x + marker.box.width - WIRING_GRID // 2


def test_a_marker_box_past_the_left_edge_moves_no_placement() -> None:
    """D14 M2 (C): `shift_pages` measures placements, keep-outs and labels only. A marker box
    at x=-25 and nothing else past the edge: the function at (64, 160) and the marker stay.
    """
    # UNDO: `shift_pages`: `boxes += [label.box for label in first]` -> `boxes += [label.box
    # for label in first] + [markers[i].box for i in mine]` (the page moves right 32 G).
    marker = _marker(Point(x=16, y=40), Box(x=-25, y=28, width=45, height=12))
    pages = [((placed(1, x=64, y=160),), ())]
    moved_pages, placed_all, markers = shift_pages((page_plan(("a",)),), pages, (marker,), SHEET)
    assert [(one.at.x, one.at.y) for one in placed_all] == [(64, 160)]
    assert moved_pages == pages
    assert markers == (marker,)


def _off_run(*xs: int) -> tuple[LinkMarker, ...]:
    """C21: off stubs of one cable to one far end, functions 1.. placed at `xs` on one row: a
    run that draws one shared box (`off_markers`), its stubs at the ports of the functions."""
    numbers = range(1, len(xs) + 1)
    scene = MarkerScene(
        tuple(placed(n, x=x, y=160) for n, x in zip(numbers, xs, strict=True)),
        tuple(drawn(n) for n in numbers),
        SHEET,
        PROFILE,
    )
    off = OffStubs(
        tuple(connection(n, n, 90 + n) for n in numbers),
        off_texts={
            hid("port", n * 10 + 2): [StubText(cable="-W1", far="+DB-X0", port=f":{n}")]
            for n in numbers
        },
    )
    return built(scene, _off_markers(scene, standing(scene, off)))


def _run_is_over_its_box(run: tuple[LinkMarker, ...]) -> None:
    """Every stub of the run is over the one shared box, half a grid in, and the box is one."""
    (box,) = {m.box for m in run}
    assert all(m.shared_box for m in run)
    assert [m.lead for m in run] == [True] + [False] * (len(run) - 1)
    for m in run:
        assert box.x + WIRING_GRID // 2 <= m.at.x <= box.x + box.width - WIRING_GRID // 2


def test_an_off_stub_run_at_the_left_edge_stands_against_it_and_grows_right() -> None:
    """D14 M2, C21, M8: the run's box spans half a pin pitch before the first stub to half a pitch
    after the last (two pins at least, 48 G), centred across them. With stubs at 8 and 32 that
    starts left of x=0. It stands at x=0, grows right, every stub of the run still over it; it
    did not change size.

    # UNDO: `stand.run_box`: `return stand_against_content_edge(...) or box` -> `return box`
    # (the box starts at a negative x)
    """
    run = _off_run(8, 32)
    first, last = run[0], run[-1]
    width = run[0].box.width
    assert (first.at.x + last.at.x) // 2 - width // 2 < 0  # premise: centred, it crosses the edge
    assert first.box.x == 0
    assert width == 6 * WIRING_GRID  # M8: two pin pitches of 3 G, unchanged by the move
    _run_is_over_its_box(run)


def test_an_off_stub_run_at_the_right_edge_stands_against_it_and_grows_left() -> None:
    """The mirror: the run's box ends at `content_width`, every stub still over it.

    # UNDO: as the left-edge test (the box stays 4 G past the right edge)
    """
    edge = SHEET.content_width
    run = _off_run(edge - 32, edge - 8)
    first, last = run[0], run[-1]
    width = first.box.width
    assert (first.at.x + last.at.x) // 2 - width // 2 + width > edge  # premise: centred, it crosses
    assert first.box.x + width == edge
    _run_is_over_its_box(run)


def test_an_off_stub_run_inside_the_content_box_stays_centred_across_its_stubs() -> None:
    """A run that crosses no edge keeps its centred place, half a pitch past the outer stubs
    (M8): the clamp moves nothing else.

    # UNDO: `stand.run_box`: the centred `left` -> `left = 0` (every run at the left edge)
    """
    run = _off_run(400, 424)
    first, last = run[0], run[-1]
    assert first.box.x == (first.at.x + last.at.x) // 2 - first.box.width // 2
    assert first.box.x == first.at.x - 3 * WIRING_GRID // 2
    _run_is_over_its_box(run)


def test_a_shared_box_stays_and_a_box_that_would_meet_it_goes_one_tier_out() -> None:
    """A C21 run's shared box has one place, where it stands, even past the edge (nothing moves
    it alone). A box whose edge place (x=0..45) would meet a neighbour's shared box at 40..70
    takes the next free place instead (S20): its stub's tier one box height out, at the edge.

    # UNDO: `_row` drops `marker.shared_box or` from its one-place test (the shared box moves)
    """
    shared = _marker(Point(x=16, y=40), Box(x=-6, y=28, width=45, height=12), shared=True)
    assert _placed_alone(shared)[0] == (shared,)
    right = _marker(Point(x=40, y=40), Box(x=40, y=28, width=30, height=12), shared=True)
    left = _marker(Point(x=16, y=40), Box(x=-6, y=28, width=45, height=12))
    found, findings = _placed_alone(left, right)
    assert found[1] == right
    assert not overlaps(found[0].box, right.box)
    assert found[0].box == Box(x=0, y=16, width=45, height=12)  # the edge place, a tier out
    assert found[0].stub_extra == left.stub_extra + left.box.height
    assert findings == ()
