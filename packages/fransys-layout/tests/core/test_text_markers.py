"""Stage 8a: where each end of a planned reference stands, and what the marker names."""

from __future__ import annotations

import itertools
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options
from turn_fixtures import marker_views, turn_pin

from fransys_layout.core import AnnexBox, Facts, PinRef, PlacementProblem, Size, Unit
from fransys_layout.core.arrow_reserve import leg_feet, leg_lines
from fransys_layout.core.clearance import Keep, clear
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.geometry import inside, marker_box, marker_box_at, marker_drawn_box, overlaps
from fransys_layout.core.hangings import hung_keeps
from fransys_layout.core.outline import outline_keeps
from fransys_layout.core.outputs import Demand, Marker, Outline, Trunk, Wire
from fransys_layout.core.place import place_pages
from fransys_layout.core.route_env import Drawn
from fransys_layout.core.route_fixed import Fixed
from fransys_layout.core.text_cells import cell_of
from fransys_layout.core.text_ends import MarkEnv, Stand, _trunk_end_stand, bundle_nets, end_stand, hub_xy, mark_env, pin_keeps, pin_stand, wire_keeps
from fransys_layout.core.text_markers import _missed, _order, placed_marks, stagger, stand_ref
from fransys_layout.core.values import Box, Bundle, CutEnd, Finding, OutlineRoom, Pin, Ref, RefEnd, RefKind, StandClass

from . import pipeline_fixtures
from .conftest import MARKER
from .cut_fixtures import box_sym, net
from .text_fixtures import KIND_OF, PLANTS, marker_counts, plan_counts, star_two_tied

AREA = Size(1312, 854)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import Orientation, Placement, Side
    from fransys_layout.core.flow_values import CutResult

OPTIONS = core_options(
    marker=MARKER,
    marker_vertical=frozenset({"R90", "R270", "MR90", "MR270"}),
    marker_above="R270",
    marker_below="R90",
)  # el's facing views: the rows keep the flags' room, so no end stands past the page (R436)
PIN = PinRef("S", "p")
STUB = Ref("n", RefKind.STUB, (RefEnd(1, None, PIN),))


def _env(side: Side, orient: Orientation, trunks: tuple[Trunk, ...] = ()) -> MarkEnv:
    by_fan: dict[tuple[int, str], tuple[Trunk, ...]] = {}
    for t in trunks:
        by_fan[(t.page, t.fan)] = (*by_fan.get((t.page, t.fan), ()), t)
    return MarkEnv(
        OPTIONS,
        Size(1312, 854),
        {("S", "p"): (1, 100, 200, orient)},
        {("S", "p", orient): turn_pin(Pin("p", side, 0, 0, 0), orient).side},
        by_fan,
        {},
        ranks={"S": 0, "H": 1},
        columns={"c": (0,), "c1": (0,), "c2": (0,)},
    )


# the pin's own side, the orientation: the side the marker stands on
TURNS = [  # the symbol's tip, its origin, sits at the pin whichever way the marker turns
    ("E", "R0", (100, 200), "R0"),
    ("W", "R0", (100, 200), "R180"),
    ("N", "R0", (100, 200), "R270"),
    ("S", "R0", (100, 200), "R90"),
    ("E", "R180", (100, 200), "R180"),
    ("W", "R180", (100, 200), "R0"),
    ("N", "R180", (100, 200), "R90"),
    ("S", "R180", (100, 200), "R270"),
    ("E", "MR0", (100, 200), "R180"),
    ("E", "MR180", (100, 200), "R0"),
]


@pytest.mark.parametrize(("side", "orient", "xy", "turn"), TURNS)
def test_a_pin_marker_stands_its_origin_so_the_box_touches_the_pin(side, orient, xy, turn) -> None:
    stand = pin_stand(_env(side, orient), PIN, 1, STUB)
    assert (stand.x, stand.y) == xy
    assert (stand.end, stand.orient) == (PIN, turn)


@pytest.mark.parametrize(("side", "xy"), [("E", (96, 200)), ("W", (104, 200)), ("S", (100, 196)), ("N", (100, 204))])
def test_the_near_edge_of_the_marker_option_sits_at_the_pin(side, xy) -> None:
    """A box that starts 4 inside its origin: the origin backs off, the near edge meets the pin."""
    env = _env(side, "R0")
    got = pin_stand(
        replace(
            env,
            options=core_options(
                marker=marker_views(Box(4, -8, 44, 16)),
            ),
        ),
        PIN,
        1,
        STUB,
    )
    assert (got.x, got.y) == xy


@pytest.mark.parametrize(("side", "orient", "turn"), [("E", "R90", "R90"), ("E", "MR180", "R0")])
def test_a_quarter_turn_and_a_mirror_have_a_side_map(side, orient, turn) -> None:
    """Every orientation turns the pin side (layout-0306): E at R90 faces S, E at MR180 faces E."""
    assert pin_stand(_env(side, orient), PIN, 1, STUB).orient == turn


def test_a_pin_that_is_not_placed_raises_naming_the_net_and_kind() -> None:
    with pytest.raises(CoreError, match=r"net n \(stub\) has no placed pin S.q"):
        pin_stand(_env("E", "R0"), PinRef("S", "q"), 1, STUB)


def test_a_pin_on_another_page_raises_naming_the_net_and_page() -> None:
    with pytest.raises(CoreError, match=r"net n \(stub\) names S.p on page 2"):
        pin_stand(_env("E", "R0"), PIN, 2, STUB)


def test_a_stub_end_with_no_pin_raises() -> None:
    ref = Ref("n", RefKind.STUB, (RefEnd(1, None, None),))
    with pytest.raises(CoreError, match=r"net n \(stub\) page 1: the end names no pin"):
        end_stand(_env("E", "R0"), ref, ref.ends[0], 0)


def _fan_env() -> MarkEnv:
    """Fan f has a trunk in row 0 (x 40 to 500, y 100) and one in row 1 (x 60 to 400, y 300)."""
    trunks = (
        Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),)),
        Trunk("f", 1, 300, 60, 400, 1, 1, ((60, 400),)),
    )
    env = _env("E", "R0", trunks)
    fan = Fan("f", ("fa", "fb"), (), (), "H", 1, "S")
    return replace(env, fans={"f": fan})


def test_an_arrow_stands_at_the_right_end_of_the_first_row_and_the_left_end_of_the_next() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, 0), RefEnd(1, "c2", PIN, 1)))
    env = _fan_env()
    first, second = (end_stand(env, ref, e, i) for i, e in enumerate(ref.ends))
    assert (first.orient, second.orient) == ("R0", "R180")  # east of x1, west of x0
    one = marker_box_at(first.x, first.y, OPTIONS, first.orient)
    two = marker_box_at(second.x, second.y, OPTIONS, second.orient)
    assert (one.x, one.y + one.h // 2, first.end) == (500, 100, PIN)  # near edge at x1
    assert (two.x + two.w, two.y + two.h // 2, second.end) == (60, 300, PIN)  # near edge at x0


@pytest.mark.parametrize(
    ("end", "message"),
    [
        (RefEnd(1, "c3", PIN, 2), r"net f \(arrow\) page 1: no trunk in row 2"),
        (RefEnd(2, "c1", PIN, 0), r"net f \(arrow\) page 2: fan f has no trunk"),
        (RefEnd(1, "c1", PIN, None), r"net f \(arrow\) page 1: the end names no row"),
    ],
)
def test_an_arrow_end_with_no_trunk_or_no_row_raises_naming_the_net_and_page(end: RefEnd, message: str) -> None:
    ref = Ref("f", RefKind.ARROW, (end,))
    with pytest.raises(CoreError, match=message):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_a_copy_follows_the_pin_rule_like_a_tag() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(1, "c1", PIN),))
    stand = end_stand(_fan_env(), ref, ref.ends[0], 0)
    want = pin_stand(_fan_env(), PIN, 1, ref)
    assert (stand.x, stand.y, stand.end, stand.orient) == (want.x, want.y, PIN, want.orient)
    assert marker_box_at(stand.x, stand.y, OPTIONS, stand.orient).x == 100  # near edge at the pin


# the planted problems, through the stages


@pytest.fixture(scope="module")
def built() -> dict[str, tuple[CutResult, Placement, tuple[Marker, ...]]]:
    out = {}
    for name, plant in PLANTS.items():
        prob = plant()
        cut = pipeline_fixtures.cut_of(prob, OPTIONS)
        pl = place_pages(cut, prob, OPTIONS)
        out[name] = (cut, pl, placed_marks(cut, pl, prob, OPTIONS, {})[0])
    return out


@pytest.fixture(scope="module")
def missed(built) -> dict[str, tuple[Finding, ...]]:
    """MARKER_UNPLACED of each plant: these options keep no marker room, so a top end overhangs."""
    return {name: placed_marks(cut, pl, PLANTS[name](), OPTIONS, {})[1] for name, (cut, pl, _) in built.items()}


@pytest.mark.parametrize("name", PLANTS)
def test_each_plant_gets_one_marker_for_each_planned_end_of_each_kind(built, missed, name: str) -> None:
    """Each planned end is a marker inside the page, or a MARKER_UNPLACED finding (R436)."""
    cut, _, markers = built[name]
    assert plan_counts(cut)[KIND_OF[name]] > 0
    unplaced = Counter(RefKind(f.text.split()[0]) for f in missed[name])
    assert marker_counts(markers) + unplaced == plan_counts(cut)


@pytest.mark.parametrize("name", PLANTS)
def test_markers_come_in_the_plans_order_and_stand_on_their_ends_pages(built, name: str) -> None:
    """Each end's marker, placed or not (MARKER_UNPLACED drops it, R436), in the plan's order."""
    cut, pl, placed = built[name]
    env = mark_env(cut, pl, PLANTS[name](), OPTIONS)
    pairs = [p for ref in cut.spec.reference_plan for p in stand_ref(env, ref)]
    own = {r.net: bundle_nets(env, r.net) for r in cut.spec.reference_plan}
    assert [m for m in stagger(pairs, OPTIONS, AREA, pin_keeps(env), own) if isinstance(m, Marker)] == list(placed)
    markers = [m for m, _ in pairs]
    want = [(r.net, r.kind, sorted(e.page for e in r.ends)) for r in cut.spec.reference_plan]
    got, i = [], 0
    for _, _, pages in want:
        got.append([m.page for m in markers[i : i + len(pages)]])
        i += len(pages)
    assert got == [p for _, _, p in want]
    assert [(m.net, m.kind) for m in markers] == [(n, k) for n, k, pages in want for _ in pages]


def test_a_stub_stands_at_each_boundary_net_one_for_the_pins_that_reach_one_outside_pin(built, missed) -> None:
    """R1645 `_merged`, R1686: x.e and z.e both reach the outside pin out.x, so one bundled stub names it and stands for both pins."""
    _, _, markers = built["unit_boundary_stubs"]
    stubs = [m for m in markers if m.kind == "stub"]
    assert [(m.end, m.also, m.far) for m in stubs] == [(PinRef("x", "e"), (PinRef("z", "e"),), (PinRef("out", "x"),))]
    assert missed["unit_boundary_stubs"] == ()  # no pin of the net is left without a stub: no CONNECTION_NOT_DRAWN


def test_an_arrow_across_pages_names_the_far_ends_cell(built) -> None:
    _, _, markers = built["page_wrapped_fan"]
    first, second = markers
    assert (first.page, second.page) == (1, 2)
    area = Size(1312, 854)
    assert first.cell == cell_of(second.x, second.y, area, OPTIONS.cells)
    assert second.cell == cell_of(first.x, first.y, area, OPTIONS.cells)


def test_a_row_wrapped_fan_has_arrows_in_different_rows_of_one_page(built) -> None:
    cut, _, markers = built["row_wrapped_fan"]
    first, second = markers[0], markers[1]
    assert first.page == second.page
    assert first.y != second.y
    assert first.x > second.x  # the right end of the first row, the left end of the next
    assert len(cut.spec.pages[0].rows) > 1


def test_a_copy_names_the_cell_of_its_hub(built) -> None:
    _, pl, markers = built["copied_hub"]
    hub = next(p for g in pl.pages for p in g.placed if p.sym == "t2")
    first = min(hub.pin_xy, key=lambda q: q.pin)
    want = cell_of(first.x, first.y, Size(1312, 854), OPTIONS.cells)
    assert {m.cell for m in markers} == {want}


def test_a_tag_stands_at_a_pin_of_its_net(built) -> None:
    _, _, markers = built["tag_chain"]
    assert [m.end for m in markers] == [PinRef("k01", "s"), PinRef("k02", "n")]


@pytest.mark.parametrize("kind", [RefKind.ARROW, RefKind.COPY, RefKind.TAG])
def test_an_arrow_copy_or_tag_end_with_no_pin_raises_naming_the_net_and_page(kind) -> None:
    net = "fb" if kind is RefKind.COPY else "f"
    ref = Ref(net, kind, (RefEnd(1, "c1", None, 0),))
    with pytest.raises(CoreError, match=rf"net {net} \({kind.value}\) page 1: the end names no pin"):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_every_marker_of_the_plants_names_a_pin(built) -> None:
    assert all(m.end is not None for _, _, markers in built.values() for m in markers)


def test_an_arrow_end_with_no_row_is_refused_by_stand_ref_with_the_fix() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, None),))
    with pytest.raises(
        CoreError,
        match=r"net f \(arrow\) page 1: the end names no row; stage 4 fills RefEnd.row and pin",
    ):
        stand_ref(_fan_env(), ref)


def test_a_stub_end_with_no_pin_is_refused_by_stand_ref_with_the_fix() -> None:
    ref = Ref("n", RefKind.STUB, (RefEnd(1, None, None),))
    with pytest.raises(CoreError, match=r"names no pin; stage 4 fills RefEnd.row and pin"):
        stand_ref(_env("E", "R0"), ref)


def test_a_stub_end_with_no_row_but_a_pin_is_not_refused() -> None:
    markers = stand_ref(_env("E", "R0"), STUB)
    assert len(markers) == 1


def _hub_env(page: int) -> MarkEnv:
    fan = Fan("f", ("fa", "fb"), (), (), "H", 1, "S")
    return replace(_env("E", "R0"), pins={("H", "p"): (page, 10, 20, "R0")}, fans={"f": fan})


def test_a_copys_hub_is_read_from_the_page_it_stands_on() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(2, "c1", PIN),))
    assert hub_xy(_hub_env(1), ref, ref.ends[0]) == (10, 20)


def test_a_copy_on_its_hubs_own_page_raises_naming_the_net_and_page() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(1, "c1", PIN),))
    with pytest.raises(
        CoreError,
        match=r"net fb \(copy\) page 1: the hub H stands on the copy's.*"
        r"stage 4 copies\(\) plans a copy end only on a page other than the hub's",
    ):
        hub_xy(_hub_env(1), ref, ref.ends[0])


def test_a_copy_whose_hub_has_no_placed_pin_raises_naming_the_net() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(2, "c1", PIN),))
    with pytest.raises(
        CoreError,
        match=r"net fb \(copy\): the hub has no placed pin.*"
        r"the placement must place a pin of the fan's hub",
    ):
        hub_xy(replace(_hub_env(1), pins={}), ref, ref.ends[0])


# the stagger (I8.7) and the cyclic far end (I8.4)


def _all(markers: Sequence[Marker | Demand]) -> list[Marker]:
    """The markers, each placed (none dropped for want of room)."""
    assert all(isinstance(m, Marker) for m in markers)
    return [m for m in markers if isinstance(m, Marker)]


def _box_of(m: Marker | Demand | None):
    assert isinstance(m, Marker)
    return marker_box(m, OPTIONS)


def test_two_spilled_pins_16_g_apart_stand_each_at_its_lead_end_and_do_not_overlap(built) -> None:
    """R1407: a cut pin's lead is a keep from the pin to its step-out, so a marker at that end is fed and stays level (R879)."""
    _, _, markers = built["spilled_pair"]
    pair = [m for m in markers if m.end.sym == "A1"]
    assert [m.end.pin for m in pair] == ["p18", "p19"]
    first, second = pair
    assert first.x + 16 == second.x
    assert second.y == first.y
    assert not overlaps(_box_of(first), _box_of(second))


@pytest.mark.parametrize("name", PLANTS)
def test_no_two_markers_of_a_page_overlap(built, name: str) -> None:
    markers = built[name][2]
    for i, a in enumerate(markers):
        for b in markers[i + 1 :]:
            assert a.page != b.page or not overlaps(_box_of(a), _box_of(b))


def test_the_spilled_pair_overlaps_without_the_levels() -> None:
    pairs = stand_ref(_pair_env(), _pair_ref())
    plain = [m for m, _ in pairs]
    assert overlaps(_box_of(plain[0]), _box_of(plain[1]))
    staggered = _all(stagger(pairs, OPTIONS, AREA, {}, {}))
    assert not overlaps(_box_of(staggered[0]), _box_of(staggered[1]))


def test_a_tag_whose_drawn_box_leaves_the_page_gives_the_room_demand() -> None:
    """OUT_OF_PAGE (bank:71): a tag is placed by its plain box and drawn stretched (R543); the page test is on the drawn box."""
    assert OPTIONS.marker is not None
    tall = replace(OPTIONS, link_fit={o: Box(b.x, b.y - 60, b.w, b.h + 60) for o, b in OPTIONS.marker.items()})
    pairs = stand_ref(_pair_env(), _pair_ref())
    assert isinstance(stagger(pairs, tall, AREA, {}, {})[0], Marker)
    top = min(marker_box(m, tall).y for m, _ in pairs)
    up = [(replace(m, y=m.y - top + 5), replace(st, y=st.y - top + 5)) for m, st in pairs]
    assert all(inside(marker_box(m, tall), AREA) and not inside(marker_drawn_box(m, tall), AREA) for m, _ in up)
    assert all(isinstance(k, Demand) for k in stagger(up, tall, AREA, {}, {}))


@pytest.mark.parametrize(("kind", "drop"), [(RefKind.TAG, "the whole pair is dropped"), (RefKind.STUB, "this end is dropped")])
def test_a_marker_with_no_slot_gives_the_room_demand_of_its_owner_and_its_finding_says_so(kind: RefKind, drop: str) -> None:
    """Layout-0559 (R436): a box off the page is no slot; the marker gives the room above its owner, never None. KI-912: its finding names
    the conductor, the unmet demand and what the drop costs."""
    ref = replace(_pair_ref(), kind=kind)
    pairs = stand_ref(_pair_env(), ref)
    lifted = stagger(pairs, OPTIONS, AREA, {}, {})[1]
    assert isinstance(lifted, Marker)
    dy = _box_of(lifted).y + 1
    up = [(replace(m, y=m.y - dy, far=(PinRef("T", "1"),)), replace(st, y=st.y - dy)) for m, st in pairs]
    got = stagger(up, OPTIONS, AREA, {}, {})
    ask = got[1]
    assert isinstance(got[0], Marker)
    assert isinstance(ask, Demand)
    assert (ask.gap, ask.owner, ask.side) == ("", "S", pairs[0][1].side)
    assert ask.room > OPTIONS.label_gap
    (found,) = _missed(ref, up, got)
    assert found.code == "MARKER_UNPLACED"
    assert "of net n for the conductor to T/1" in found.text
    assert f"room demand of {ask.room} G on side {ask.side} of S stays unmet, {drop}" in found.text


def test_a_marker_lifted_past_its_rows_band_fits_nowhere() -> None:
    """R1333: the row band is a hard limit of the fit test; the pair's second level, one G over the band top, is None."""
    pairs = stand_ref(_pair_env(), _pair_ref())
    lifted = stagger(pairs, OPTIONS, AREA, {}, {})[1]
    assert isinstance(lifted, Marker)
    top = _box_of(lifted).y + 1
    banded = [(m, replace(st, band=(top, m.y))) for m, st in pairs]
    got = stagger(banded, OPTIONS, AREA, {}, {})
    assert isinstance(got[0], Marker)
    assert isinstance(got[1], Demand)


def _pair_env() -> MarkEnv:
    pins = {("S", "p"): (1, 100, 200, "R0"), ("S", "q"): (1, 108, 200, "R0")}
    sides = {("S", "p", "R0"): "N", ("S", "q", "R0"): "N"}
    return replace(_env("N", "R0"), pins=pins, sides=sides)


def _pair_ref() -> Ref:
    return Ref("n", RefKind.TAG, (RefEnd(1, "c", PinRef("S", "p")), RefEnd(1, "c", PinRef("S", "q"))))


def test_a_three_end_star_names_the_next_end_cyclically() -> None:
    area = Size(1312, 854)
    pins = {("S", f"p{k}"): (1, x, 200, "R0") for k, x in enumerate((100, 600, 1200), 1)}
    env = replace(_env("E", "R0"), pins=pins, sides={(s, p, "R0"): "E" for s, p in pins})
    star = Ref("m", RefKind.STAR, tuple(RefEnd(1, "c", PinRef("S", p), 0) for _, p in pins))
    pairs = stand_ref(env, star)
    assert len(pairs) == 3
    assert len({m.cell for m, _ in pairs}) == 3  # three cells, so a wrong end shows
    for i, (m, _) in enumerate(pairs):
        nxt = pairs[(i + 1) % 3][1]
        assert m.cell == cell_of(nxt.x, nxt.y, area, OPTIONS.cells)  # the cell of the next end's stand, from the same Stand that sets x,y


def test_a_one_end_reference_names_its_own_cell() -> None:
    ((m, _),) = stand_ref(_env("E", "R0"), STUB)
    assert m.cell == cell_of(m.x, m.y, Size(1312, 854), OPTIONS.cells)


def test_an_arrow_and_a_copy_of_two_sides_that_meet_stay_at_their_anchors() -> None:
    arrow = Marker("f", RefKind.ARROW, 1, "1A", 120, 500, PIN, "R180")  # box west of x 120
    copy = Marker("f", RefKind.COPY, 1, "1A", 96, 500, PIN)  # box east of x 96
    pairs = [(arrow, Stand(120, 500, PIN, "R180", "W")), (copy, Stand(96, 500, PIN, "R0", "E"))]
    assert overlaps(_box_of(arrow), _box_of(copy))
    got = _all(stagger(pairs, OPTIONS, AREA, {}, {}))
    assert got == [arrow, copy]  # the overlap is counted, a step would leave the wire (R453)


def test_a_crowded_wall_leaves_every_marker_at_its_anchor_inside_the_page() -> None:
    """Six west boxes and a late east box overlap: none steps off its wire end (R453)."""
    wall = [Marker(f"w{k}", RefKind.ARROW, 3, "1A", 200 + 56 * k, 500, PIN, "R180") for k in range(6)]
    late = Marker("late", RefKind.COPY, 3, "1A", 120, 500, PIN)
    pairs = [(m, Stand(m.x, m.y, PIN, "R180", "W")) for m in wall] + [(late, Stand(120, 500, PIN, "R0", "E"))]
    assert not any(overlaps(_box_of(a), _box_of(b)) for a, b in itertools.pairwise(wall))
    got = _all(stagger(pairs, OPTIONS, AREA, {}, {}))
    assert [(m.x, m.y) for m in got] == [(m.x, m.y) for m, _ in pairs]  # each at its anchor
    assert all(inside(_box_of(m), AREA) for m in got)
    assert any(overlaps(_box_of(a), _box_of(b)) for a, b in itertools.combinations(got, 2))


def test_a_two_end_star_tied_in_page_row_and_column_is_ordered_by_the_pin_id() -> None:
    pins = {("S", "p2"): (1, 100, 200, "R0"), ("S", "p10"): (1, 300, 200, "R0")}
    env = replace(_env("E", "R0"), pins=pins, sides={("S", "p2", "R0"): "E", ("S", "p10", "R0"): "E"})
    pairs = stand_ref(env, star_two_tied())
    assert [m.end.pin for m, _ in pairs] == ["p2", "p10"]  # natural order, not input or text order
    first, second = (m for m, _ in pairs)
    assert first.cell == cell_of(second.x, second.y, Size(1312, 854), OPTIONS.cells)
    assert second.cell == cell_of(first.x, first.y, Size(1312, 854), OPTIONS.cells)


def test_a_bundle_arrow_stands_at_the_hull_end_on_its_own_poles_lane() -> None:
    """The arrow of a pin stands at the end of the lane of its `Attach.pole`, on its y: three poles, the net order not the pole order (R1338 G12)."""
    trunk = Trunk("f", 1, 100, 40, 500, 3, 0, ((40, 508), (80, 308), (120, 408)))
    pins = [PinRef("a", "1"), PinRef("b", "1"), PinRef("c", "1")]
    legs = tuple(Attach(None, 0, 0, p, pole, net=n) for p, pole, n in zip(pins, (2, 0, 1), ("fa", "fb", "fc"), strict=True))
    fan = Fan("f", ("fb", "fc", "fa"), (), legs, "H", 3, "S")
    env = replace(_env("E", "R0", (trunk,)), fans={"f": fan})
    ends = [RefEnd(1, "c1", p, 0) for p in pins]
    stands = [end_stand(env, Ref("f", RefKind.ARROW, (e,)), e, 0) for e in ends]
    boxes = [marker_box_at(s.x, s.y, OPTIONS, s.orient) for s in stands]
    step = OPTIONS.wiring_grid
    assert [(b.x, b.y + b.h // 2) for b in boxes] == [(408, 100 + 2 * step), (508, 100), (308, 100 + step)]


def test_a_copy_of_a_bundle_stands_on_its_own_poles_lane_not_the_first() -> None:
    """R2071: the copy of a pin on lane 1 of a two-lane bundle stands on that lane's y, where its drop ends, not on the trunk's first line."""
    trunk = Trunk("f", 1, 100, 40, 500, 2, 0, ((40, 508), (80, 508)))
    pin = PinRef("a", "1")
    fan = Fan("f", ("fa",), (), (Attach(None, 0, 0, pin, 1, net="fa"),), "H", 2, "S")
    env = replace(_env("E", "R0", (trunk,)), fans={"f": fan})
    end = RefEnd(1, "c1", pin, 0, StandClass.TRUNK_END)
    stand = end_stand(env, Ref("fa", RefKind.COPY, (end,)), end, 0)
    box = marker_box_at(stand.x, stand.y, OPTIONS, stand.orient)
    assert box.y + box.h // 2 == 100 + OPTIONS.wiring_grid


def test_a_marker_names_the_cut_of_its_reference() -> None:
    """R550: Marker.ref is the Ref's cut, so a fan's two Refs are told apart downstream."""
    ((m, _),) = stand_ref(_env("E", "R0"), replace(STUB, cut=4))
    assert m.ref == 4


def _bundle_of_cut_pins(count: int = 8, pole: int | None = None) -> PlacementProblem:
    """A box on one unit whose `count` south pins are lone nets cut at the pin, all lanes of one bundle fan."""
    box = replace(box_sym(count), unit="U1")
    pins = tuple(PinRef("A1", f"p{i}") for i in range(1, count + 1))
    nets = tuple(
        replace(net(f"n{i}", f"A1.p{i}", crosses_unit=True), bundle=Bundle("b", i if pole is None else pole), cut=(CutEnd(pins[i - 1]),))
        for i in range(1, count + 1)
    )
    return PlacementProblem(AREA, (box,), nets, Facts(units=(Unit("U1", None, pins),)))


def test_one_stub_per_bundle_per_page() -> None:
    """R499: the eight lanes of one bundle fan end in one stub on the page, not one for each conductor."""
    prob = _bundle_of_cut_pins()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    markers = placed_marks(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS, {})[0]
    assert [m.kind for m in markers] == [RefKind.STUB]


def _pin_at(box: Box, dx: int = 0) -> Keep:
    """A point Keep inside the box: another net's pin."""
    return Keep("", Box(box.x + 1 + dx, box.y + 1, 0, 0), "pin", "other")


def test_no_stub_marker_on_another_nets_pin_or_lead_end() -> None:
    """R845: a slot whose box covers another net's pin is refused; the marker takes the next one."""
    pairs = stand_ref(_pair_env(), _pair_ref())
    first, second = stagger(pairs, OPTIONS, AREA, {}, {})
    assert isinstance(first, Marker)
    assert isinstance(second, Marker)
    keeps = {1: [_pin_at(_box_of(second))]}
    got = stagger(pairs, OPTIONS, AREA, keeps, {})
    assert got[0] == first
    assert isinstance(got[1], Marker)
    assert got[1] != second
    assert clear(marker_box(got[1], OPTIONS), keeps[1], {}) == ()


def test_a_marker_with_every_slot_refused_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """R845: pins of another net all along its side leave no slot: None, which placed_marks reports as MARKER_UNPLACED."""
    pairs = stand_ref(_pair_env(), _pair_ref())
    lifted = stagger(pairs, OPTIONS, AREA, {}, {})[1]
    assert isinstance(lifted, Marker)
    box = _box_of(lifted)
    keeps = {1: [_pin_at(replace(box, y=y - 1)) for y in range(0, AREA.h, 8)]}
    assert isinstance(stagger(pairs, OPTIONS, AREA, keeps, {})[1], Demand)
    assert isinstance(stagger(pairs, OPTIONS, AREA, keeps, {"n": frozenset({"other"})})[1], Marker)
    prob = _bundle_of_cut_pins(8, pole=0)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    assert placed_marks(cut, pl, prob, OPTIONS, {})[1] == ()
    wall = [Keep("", Box(x, y, 0, 0), "pin", "other") for x in range(0, AREA.w, 8) for y in range(0, AREA.h, 8)]
    monkeypatch.setattr("fransys_layout.core.text_markers.pin_keeps", lambda _env: {1: wall})
    marks, findings, _ = placed_marks(cut, pl, prob, OPTIONS, {})
    assert marks == ()
    assert [f.code for f in findings] == ["MARKER_UNPLACED"]


def test_the_anchor_outlines_are_keeps_the_markers_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """R1786: the anchors stand before the markers, so an anchor box over every slot leaves the marker no place."""
    prob = _bundle_of_cut_pins()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    assert placed_marks(cut, pl, prob, OPTIONS, {})[1] == ()
    wall = Keep("", Box(0, 0, AREA.w, AREA.h), "anchor", "K1")
    monkeypatch.setattr("fransys_layout.core.text_markers.anchor_keeps", lambda *_: {1: [wall]})
    marks, findings, _ = placed_marks(cut, pl, prob, OPTIONS, {})
    assert marks == ()
    assert [f.code for f in findings] == ["MARKER_UNPLACED"]


def test_a_marker_fed_by_a_fixed_wire_stands_unmoved_at_its_stand_and_only_a_stand_off_the_page_is_refused() -> None:
    """R2210: a fixed wire ends at the stub's stand; another net's wire through its box leaves no slot: it stands there, unmoved."""
    pairs = [(m, st) for m, st in stand_ref(_pair_env(), _pair_ref())][:1]
    marker, stand = pairs[0]
    box = marker_box(marker, OPTIONS)
    through = Keep("", Box(box.x, box.y, box.w, 1), "wire", "", "other", None, ((box.x, box.y), (box.x + box.w, box.y)))
    own = Keep("", Box(marker.x, marker.y, 1, 1), "wire", "", "n", None, ((marker.x, marker.y), (marker.x - 40, marker.y)))
    fed = replace(marker, kind=RefKind.STUB)
    assert stagger([(fed, stand)], OPTIONS, AREA, {1: [through, own]}, {"n": frozenset({"n"})})[0] == fed
    assert stagger([(fed, stand)], OPTIONS, AREA, {1: [through]}, {"n": frozenset({"n"})})[0] != fed
    assert isinstance(stagger([(fed, stand)], OPTIONS, Size(1, 1), {1: [through, own]}, {"n": frozenset({"n"})})[0], Demand)


def test_a_boundary_stub_steps_straight_out_until_its_box_is_clear_of_a_foreign_wire() -> None:
    """R920: no fixed wire ends at the stand, so the stub lengthens along its pin's side (same row) and never bends; nothing is refused."""
    prob = _bundle_of_cut_pins(8, pole=0)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    free = placed_marks(cut, pl, prob, OPTIONS, {})[0][0]
    box = marker_box(free, OPTIONS)
    across = Wire("foreign", free.page, ((box.x + box.w // 2, box.y - 8), (box.x + box.w // 2, box.y + box.h + 8)), "trunk")
    foreign = {free.page: Fixed(Drawn(wires=(across,)))}
    marks, findings, _ = placed_marks(cut, pl, prob, OPTIONS, foreign)
    assert findings == ()
    assert [(m.kind, m.y, m.end) for m in marks] == [(RefKind.STUB, free.y, free.end)]
    assert marks[0].x != free.x  # R1007: the foreign wire blocks the first end, the stub takes the other


def test_a_wire_of_the_arrows_own_fan_does_not_block_it() -> None:
    """R1331: an arrow stands where its lane end was walked clear; the marker stage tests it no more."""
    arrow = Marker("f", RefKind.ARROW, 1, "1A", 120, 500, PIN, "R180")
    stand = Stand(120, 500, PIN, "R180", "W", walked=True)

    def keeps(net: str) -> dict[int, list[Keep]]:
        wire = Wire(net, 1, ((90, 400), (90, 600)), "trunk")
        return wire_keeps({1: Fixed(Drawn(wires=(wire,)))})

    own = {"f": frozenset({"f", "g"})}
    assert stagger([(arrow, stand)], OPTIONS, AREA, keeps("g"), own) == [arrow]
    assert stagger([(arrow, stand)], OPTIONS, AREA, keeps("x"), own) == [arrow]  # the placement walked its lane end clear: the one fit test (R1331)


def test_a_leg_end_with_no_leg_line_stands_at_the_trunk_end_not_at_its_pin() -> None:
    """ONE-SIDED-PIN: a one-sided pin never stands at its own side; a LEG end the legs omitted stands where `_trunk_end_stand` puts it."""
    trunk = Trunk("n", 1, 200, 200, 500, 1, 0, ((200, 500),))
    fan = Fan("n", ("n",), (Attach(None, 0, 0, PinRef("S", "p"), net="n"),), (), None, 1, "S")
    env = replace(_env("E", "R0"), pin_net={("S", "p"): "n"}, fans={"n": fan}, trunks={(1, "n"): (trunk,)})
    ref = Ref("n", RefKind.STUB, (RefEnd(1, "c", PinRef("S", "p"), 0, StandClass.LEG),))
    assert end_stand(env, ref, ref.ends[0], 0) == _trunk_end_stand(env, trunk, (PinRef("S", "p"), "stub"))


@pytest.mark.parametrize("case", ["hanging", "fed-foreign-wire", "unfed-foreign-wire"])
def test_a_leg_stub_touches_a_hanging_box_and_a_fed_stub_stands_over_a_foreign_wire(case: str) -> None:
    """LEG-WALKED (layout-0591, R2222): a leg stub stands beside a hanging; fed it stands over a foreign wire (WOM counts it), unfed it is refused."""
    pin = PinRef("a", "in")
    fans = {"f0": Fan("f0", ("n0",), (Attach("c", 0, 0, pin, 0, net="n0"),), (), "H", 1, "S")}
    trunks = [Trunk("f0", 1, 100, 40, 480, 1, 0, ((40, 480),))]
    free = leg_lines(trunks, fans, {pin: 0}, OPTIONS, ((), {}, None))["f0", 0, pin]
    hung = {"card": (Box(free[1][0] - 6, 100 + OPTIONS.wiring_grid, 12, 40),)}  # a planned tag at a card pin, over the free leg's drop
    lines = leg_lines(trunks, fans, {pin: 0}, OPTIONS, (leg_feet((), hung), {}, None))
    pins: dict[tuple[str, str], tuple[int, int, int, Orientation]] = {("a", "in"): (1, 40, 60, "R0")}
    sides: dict[tuple[str, str, Orientation], Side] = {("a", "in", "R0"): "S"}
    env = MarkEnv(
        OPTIONS, AREA, pins, sides, {(1, "f0"): tuple(trunks)}, fans, legs={1: {pin: 0}}, leg_lines={1: lines}, ranks={"a": 0}, columns={"c": (0,)}
    )
    ((stub, stand),) = stand_ref(env, Ref("n0", RefKind.STUB, (RefEnd(1, "c", pin, 0, StandClass.LEG),)))
    leg, edge = lines["f0", 0, pin], marker_box(stub, OPTIONS)
    fixed = [
        Keep("", Box(min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])), "wire", "n0", None, None, (a, b))
        for a, b in itertools.pairwise(leg)
    ]
    foreign = [Keep("", Box(edge.x - 20, y := edge.y + edge.h // 2, 20, 0), "wire", "n1", None, None, ((edge.x - 20, y), (edge.x, y)))]
    unfed, wires = case[0] == "u", hung_keeps(hung) if case == "hanging" else foreign  # unfed: the stub may move, and with no room it is the Demand
    got = stagger([(stub, stand)], OPTIONS, Size(1, 1) if unfed else AREA, {1: [*wires, *([] if unfed else fixed)]}, {})
    assert isinstance(got[0], Demand) if unfed else got[0] == stub  # fed: the Marker stands at `first`


def test_a_marker_stands_beside_the_lanes_of_every_fan_that_meets_its_symbol() -> None:
    """R1007: the ring's arrows stand 48 apart beside each other's single-lane fans at one module; a fan at no shared symbol is another's."""

    def fan(net_: str, sym: str) -> Fan:
        return Fan(net_, (net_,), (Attach(None, 0, 0, PinRef(sym, "p"), net=net_),), (), None, 1, "S")

    env = replace(_env("E", "R0"), fans={n: fan(n, s) for n, s in (("a", "G1"), ("b", "G1"), ("c", "G2"))})
    assert bundle_nets(env, "a") == {"a", "b"}
    assert bundle_nets(env, "c") == {"c"}


def test_a_stub_stands_beside_a_sibling_fans_wire_never_on_it() -> None:
    """R1063: the bundle exemption is for the clearance margin; a sibling fan's wire through a stub's box refuses it."""
    marker, stand = stand_ref(_pair_env(), _pair_ref())[0]
    stub = replace(marker, kind=RefKind.STUB)
    box = marker_box(stub, OPTIONS)
    own = {"n": frozenset({"n", "other"})}

    def wire(x: int, y: int, w: int, h: int) -> Keep:
        return Keep("", Box(x, y, w, h), "wire", "other", None, None, ((x, y), (x + w, y + h)))

    # R1522: a keep 0..2 thick through the box refuses the stub; beside it or on its edge shares no interior
    through = (wire(box.x - 4, box.y + box.h // 2, box.w + 8, 0), wire(box.x + 3, box.y - 4, 2, box.h + 8))
    off = (wire(box.x - 4, box.y - 2, box.w + 8, 0), wire(box.x, box.y - 4, 0, box.h + 8))
    assert all(stagger([(stub, stand)], OPTIONS, AREA, {1: [w]}, own)[0] != stub for w in through)
    assert all(stagger([(stub, stand)], OPTIONS, AREA, {1: [w]}, own) == [stub] for w in off)


@pytest.mark.rule("MARKER-FREE-SIDE")
def test_a_stub_slot_whose_lead_runs_through_a_body_is_refused() -> None:
    """R2281, KI-952: a foreign wire refuses the stand, a body the next slot, and the slot past it has a lead through that body."""
    marker, stand = stand_ref(_pair_env(), _pair_ref())[0]
    stub = replace(marker, kind=RefKind.STUB)
    box = marker_box(stub, OPTIONS)
    wire = Keep(
        "",
        Box(box.x - 4, box.y + box.h // 2, box.w + 8, 0),
        "wire",
        "other",
        None,
        None,
        ((box.x - 4, box.y + box.h // 2), (box.x + box.w + 4, box.y + box.h // 2)),
    )
    wall = Keep("", Box(box.x - 4, box.y - box.h + 2, box.w + 8, box.h - 4), "body", "H")  # the slot above the stand, never the one past it
    assert isinstance(stagger([(stub, stand)], OPTIONS, AREA, {1: [wire, wall]}, {})[0], Demand)


@pytest.mark.rule("MARKER-STAGGER")
def test_markers_on_neighbouring_rows_whose_boxes_overlap_stand_one_box_apart() -> None:
    """KI-360: two markers whose across coordinate differs (200, 208) but whose boxes overlap are one group."""
    a, b = (Marker(n, RefKind.TAG, 3, "1A", x, y, PIN, "R0") for n, x, y in (("a", 200, 500), ("b", 208, 508)))
    pairs = [(a, Stand(200, 500, PIN, "R0", "E")), (b, Stand(208, 508, PIN, "R0", "E"))]
    assert overlaps(_box_of(a), _box_of(b))
    got = _all(stagger(pairs, OPTIONS, AREA, {}, {}))
    assert not overlaps(_box_of(got[0]), _box_of(got[1]))
    assert got[1].x - b.x == _box_of(a).w  # one box further out


def _across(box: Box) -> Keep:
    """A frame line (R900) running across `box`."""
    return Keep("", Box(box.x - 4, box.y + 1, box.w + 8, 2), "outline", "U")


@pytest.mark.rule("UNIT-OUTLINE")
def test_a_foreign_marker_is_refused_inside_a_frame_and_a_members_stub_stands_across_its_line() -> None:
    """R1104 (1): a member of the frame's unit may stand on its line; a foreign stub is moved."""
    stub = Ref("n", RefKind.STUB, (RefEnd(1, "c", PinRef("S", "p")),))
    free = stagger(stand_ref(_pair_env(), stub), OPTIONS, AREA, {}, {})[0]
    assert free is not None
    keeps = {1: [_across(_box_of(free))]}
    member = {"S": frozenset({"U"})}
    assert stagger(stand_ref(_pair_env(), stub), OPTIONS, AREA, keeps, member)[0] == free
    assert stagger(stand_ref(_pair_env(), stub), OPTIONS, AREA, keeps, {})[0] != free


@pytest.mark.rule("UNIT-OUTLINE")
def test_a_tag_of_a_member_of_the_frames_unit_stands_across_its_line() -> None:
    """R1104 (1): a marker of any kind on a member of the frame's unit stands on its line, unmoved."""
    tag = Ref("n", RefKind.TAG, (RefEnd(1, "c", PinRef("S", "p")),))
    free = stagger(stand_ref(_pair_env(), tag), OPTIONS, AREA, {}, {})[0]
    assert free is not None
    keeps = {1: [_across(_box_of(free))]}
    assert stagger(stand_ref(_pair_env(), tag), OPTIONS, AREA, keeps, {"S": frozenset({"U"})}) == [free]


@pytest.mark.rule("UNIT-OUTLINE")
def test_a_marker_keeps_clear_of_the_frame_lines_the_placement_holds() -> None:
    """R900 UO6: the placement's frames are keeps for the markers; the marker stands off the line and its label box."""
    prob = _bundle_of_cut_pins(8, pole=0)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    room = OutlineRoom(4, Box(2, 2, 48, 8), Size(64, 48))
    options = replace(OPTIONS, outline=room)
    pl = place_pages(cut, prob, options)
    free = placed_marks(cut, pl, prob, options, {})[0][0]
    box = marker_box(free, options)
    frame = Outline("u", 1, Box(box.x - 20, box.y + box.h // 2, box.w + 40, 40), 0)
    marks = placed_marks(cut, replace(pl, outlines=(frame,)), prob, options, {})[0]
    assert marks != ()
    assert marks[0] != free
    assert clear(marker_box(marks[0], options), outline_keeps([frame], room, 1), {}) == ()


def test_an_arrow_whose_lane_end_found_no_stand_is_refused_so_its_marker_is_unplaced() -> None:
    """layout-0507: `Trunk.stood` False at the end reaches `_slot`, which gives the arrow no slot."""
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, 0), RefEnd(1, "c2", PIN, 1)))
    first, second = _fan_env().trunks[(1, "f")]
    trunks = (replace(first, stood=((True, False),)), second)
    env = replace(_fan_env(), trunks={(1, "f"): trunks})
    marker, stand = stand_ref(env, ref)[0]
    assert stand.stood is False
    assert isinstance(stagger([(marker, stand)], OPTIONS, AREA, {}, {})[0], Demand)
    other = stand_ref(_fan_env(), ref)[0]
    assert stagger([other], OPTIONS, AREA, {}, {}) == [other[0]]


@pytest.mark.rule("SYMBOL-TIE")
@pytest.mark.parametrize("names", [("A", "B"), ("Y", "Z"), ("B", "A")])
def test_the_order_of_ends_follows_the_rank_never_the_symbol_id_text(names) -> None:
    """Whatever the ids spell (a salt renames them), the end of the lower-ranked symbol stands first."""
    first, second = names
    env = replace(_env("E", "R0"), ranks={second: 0, first: 1}, columns={})
    ref = Ref("n", RefKind.STUB, (RefEnd(1, None, PinRef(first, "p")), RefEnd(1, None, PinRef(second, "p"))))
    assert sorted(ref.ends, key=lambda e: _order(env, ref, e)) == [ref.ends[1], ref.ends[0]]


@pytest.mark.rule("TAG-CORNERS")
def test_a_marker_keeps_clear_of_a_label_the_round_before_stood() -> None:
    """A3: the labels of the round before are keeps of the marker stage, so a marker that would stand on one steps off it."""
    prob = _bundle_of_cut_pins(8, pole=0)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    free = placed_marks(cut, pl, prob, OPTIONS, {})[0][0]
    label = AnnexBox("S", free.page, marker_drawn_box(free, OPTIONS), "TL")
    marks, findings, _ = placed_marks(cut, pl, prob, OPTIONS, {free.page: Fixed(Drawn(), (label,))})
    assert findings == ()
    assert marks
    assert not any(overlaps(marker_drawn_box(m, OPTIONS), label.box) for m in marks)


@pytest.mark.parametrize("kind", [RefKind.TAG, RefKind.STAR])
def test_a_pair_marker_with_an_end_that_found_no_slot_stands_whole_or_not_at_all(kind: RefKind, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1566: a tag or star keeps all its ends or none, so the writer never meets a half pair; one MARKER_UNPLACED is raised."""
    prob = _bundle_of_cut_pins()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pair = Ref("n1", kind, tuple(RefEnd(1, None, PinRef("A1", f"p{i}")) for i in (1, 2)))
    cut = replace(cut, spec=replace(cut.spec, reference_plan=(pair,)))
    real = stagger
    monkeypatch.setattr("fransys_layout.core.text_markers.stagger", lambda *a: [*real(*a)[:1], Demand("", 0, 16, "A1")])
    marks, findings, _ = placed_marks(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS, {})
    assert len(marks) in {0, 2}
    assert [f.code for f in findings] == ["MARKER_UNPLACED"]


@pytest.mark.rule("ROUTING")
def test_a_marker_never_stands_on_a_pins_hanging_the_placement_holds() -> None:
    """layout-0547: the hangings of `PagePlacement` are keeps of the marker stage, so a marker that would stand on one steps off it."""
    prob = _bundle_of_cut_pins(8, pole=0)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    free = placed_marks(cut, pl, prob, OPTIONS, {})[0][0]
    box = marker_box(free, OPTIONS)
    page = replace(pl.pages[0], hangings={"HOLDER": (box,)})
    marks = placed_marks(cut, replace(pl, pages=(page, *pl.pages[1:])), prob, OPTIONS, {})[0]
    assert marks
    assert not any(overlaps(marker_box(m, OPTIONS), box) for m in marks if m.page == page.page and m.end.sym != "HOLDER")
