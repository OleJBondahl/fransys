"""Stage 8a: where each end of a planned reference stands, and what the marker names."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Fan, Options, PinRef, Ref, RefEnd, Size, Trunk, place_pages
from fransys_layout.core.text_cells import cell_of
from fransys_layout.core.text_ends import MarkEnv, end_stand, hub_xy, pin_stand
from fransys_layout.core.text_markers import mark_pages, mark_ref
from fransys_layout.core.values import Box, RefKind

from . import pipeline_fixtures
from .conftest import MARKER_BOX
from .text_fixtures import KIND_OF, PLANTS, marker_counts, plan_counts

if TYPE_CHECKING:
    from fransys_layout.core import CutResult, Marker, Orientation, Placement

OPTIONS = Options(marker=MARKER_BOX)
PIN = PinRef("S", "p")
STUB = Ref("n", RefKind.STUB, (RefEnd(1, None, PIN),))


def _env(side: str, orient: Orientation, trunks: tuple[Trunk, ...] = ()) -> MarkEnv:
    by_fan: dict[tuple[int, str], tuple[Trunk, ...]] = {}
    for t in trunks:
        by_fan[(t.page, t.fan)] = (*by_fan.get((t.page, t.fan), ()), t)
    return MarkEnv(
        OPTIONS,
        Size(1312, 854),
        {("S", "p"): (1, 100, 200, orient)},
        {("S", "p"): side},  # ty: ignore[invalid-argument-type] -- a Side literal
        by_fan,
        {},
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


@pytest.mark.parametrize(
    ("side", "xy"), [("E", (96, 200)), ("W", (104, 200)), ("S", (100, 196)), ("N", (100, 204))]
)
def test_the_near_edge_of_the_marker_option_sits_at_the_pin(side, xy) -> None:
    """A box that starts 4 inside its origin: the origin backs off, the near edge meets the pin."""
    env = _env(side, "R0")
    got = pin_stand(replace(env, options=Options(marker=Box(4, -8, 44, 16))), PIN, 1, STUB)
    assert (got.x, got.y) == xy


@pytest.mark.parametrize(("side", "orient", "turn"), [("E", "R90", "R90"), ("E", "MR180", "R0")])
def test_a_quarter_turn_and_a_mirror_have_a_side_map(side, orient, turn) -> None:
    """Every orientation turns the pin side (layout-0306): E at R90 faces S, E at MR180 faces E."""
    assert pin_stand(_env(side, orient), PIN, 1, STUB).orient == turn


def test_a_pin_that_is_not_placed_raises_naming_the_net_and_kind() -> None:
    with pytest.raises(ValueError, match=r"net n \(stub\) has no placed pin S.q"):
        pin_stand(_env("E", "R0"), PinRef("S", "q"), 1, STUB)


def test_a_pin_on_another_page_raises_naming_the_net_and_page() -> None:
    with pytest.raises(ValueError, match=r"net n \(stub\) names S.p on page 2"):
        pin_stand(_env("E", "R0"), PIN, 2, STUB)


def test_a_stub_end_with_no_pin_raises() -> None:
    ref = Ref("n", RefKind.STUB, (RefEnd(1, None, None),))
    with pytest.raises(ValueError, match=r"net n \(stub\) page 1: the end names no pin"):
        end_stand(_env("E", "R0"), ref, ref.ends[0], 0)


def _fan_env() -> MarkEnv:
    """Fan f has a trunk in row 0 (x 40 to 500, y 100) and one in row 1 (x 60 to 400, y 300)."""
    trunks = (Trunk("f", 1, 100, 40, 500, 1, 0), Trunk("f", 1, 300, 60, 400, 1, 1))
    env = _env("E", "R0", trunks)
    fan = Fan("f", ("fa", "fb"), (), (), "H", 1, "S")
    return replace(env, fans={"f": fan})


def test_an_arrow_stands_at_the_right_end_of_the_first_row_and_the_left_end_of_the_next() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, 0), RefEnd(1, "c2", PIN, 1)))
    env = _fan_env()
    first, second = (end_stand(env, ref, e, i) for i, e in enumerate(ref.ends))
    assert (first.x, first.y, first.end) == (500, 100, PIN)
    assert (second.x, second.y, second.end) == (60, 300, PIN)


def test_an_arrow_in_a_row_with_no_trunk_of_its_fan_raises() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c3", PIN, 2),))
    with pytest.raises(ValueError, match=r"net f \(arrow\) page 1: no trunk in row 2"):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_an_arrow_on_a_page_where_its_fan_has_no_trunk_raises() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(2, "c1", PIN, 0),))
    with pytest.raises(ValueError, match=r"net f \(arrow\) page 2: fan f has no trunk"):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_a_copy_stands_at_the_start_of_its_fans_first_trunk_on_its_page() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(1, "c1", PIN),))
    stand = end_stand(_fan_env(), ref, ref.ends[0], 0)
    assert (stand.x, stand.y, stand.end) == (40, 100, PIN)


def test_a_copy_of_a_net_in_no_fan_raises() -> None:
    ref = Ref("zz", RefKind.COPY, (RefEnd(1, "c1", PIN),))
    with pytest.raises(ValueError, match=r"net zz \(copy\) belongs to no fan"):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


# the planted problems, through the stages


@pytest.fixture(scope="module")
def built() -> dict[str, tuple[CutResult, Placement, tuple[Marker, ...]]]:
    out = {}
    for name, plant in PLANTS.items():
        prob = plant()
        cut = pipeline_fixtures.cut_of(prob, OPTIONS)
        pl = place_pages(cut, prob, OPTIONS)
        out[name] = (cut, pl, mark_pages(cut, pl, prob, OPTIONS))
    return out


@pytest.mark.parametrize("name", PLANTS)
def test_each_plant_gets_one_marker_for_each_planned_end_of_each_kind(built, name: str) -> None:
    cut, _, markers = built[name]
    assert plan_counts(cut)[KIND_OF[name]] > 0
    assert marker_counts(markers) == plan_counts(cut)


@pytest.mark.parametrize("name", PLANTS)
def test_markers_come_in_the_plans_order_and_stand_on_their_ends_pages(built, name: str) -> None:
    cut, _, markers = built[name]
    want = [(r.net, r.kind, sorted(e.page for e in r.ends)) for r in cut.spec.reference_plan]
    got, i = [], 0
    for _, _, pages in want:
        got.append([m.page for m in markers[i : i + len(pages)]])
        i += len(pages)
    assert got == [p for _, _, p in want]
    assert [(m.net, m.kind) for m in markers] == [(n, k) for n, k, pages in want for _ in pages]


def test_a_stub_stands_at_each_boundary_pin_of_the_net(built) -> None:
    _, pl, markers = built["unit_boundary_stubs"]
    xy = {(p.sym, q.pin): (q.x, q.y) for g in pl.pages for p in g.placed for q in p.pin_xy}
    stubs = [m for m in markers if m.kind == "stub"]
    assert [m.end for m in stubs] == [PinRef("x", "e"), PinRef("z", "e")]
    for m in stubs:
        px, py = xy[(m.end.sym, m.end.pin)]
        assert (m.x - px, m.y - py) == (
            -MARKER_BOX.x,
            0,
        )  # an east pin at R0: the near edge meets the pin


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
    with pytest.raises(
        ValueError, match=rf"net {net} \({kind.value}\) page 1: the end names no pin"
    ):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_every_marker_of_the_plants_names_a_pin(built) -> None:
    assert all(m.end is not None for _, _, markers in built.values() for m in markers)


def test_an_arrow_end_with_no_row_raises_naming_the_net_and_page() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, None),))
    with pytest.raises(ValueError, match=r"net f \(arrow\) page 1: the end names no row"):
        end_stand(_fan_env(), ref, ref.ends[0], 0)


def test_an_arrow_end_with_no_row_is_refused_by_mark_ref_with_the_fix() -> None:
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", PIN, None),))
    with pytest.raises(
        ValueError,
        match=r"net f \(arrow\) page 1: the end names no row; stage 4 fills RefEnd.row and pin",
    ):
        mark_ref(_fan_env(), ref)


def test_a_stub_end_with_no_pin_is_refused_by_mark_ref_with_the_fix() -> None:
    ref = Ref("n", RefKind.STUB, (RefEnd(1, None, None),))
    with pytest.raises(ValueError, match=r"names no pin; stage 4 fills RefEnd.row and pin"):
        mark_ref(_env("E", "R0"), ref)


def test_a_stub_end_with_no_row_but_a_pin_is_not_refused() -> None:
    markers = mark_ref(_env("E", "R0"), STUB)
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
        ValueError,
        match=r"net fb \(copy\) page 1: the hub H stands on the copy's.*"
        r"stage 4 copies\(\) plans a copy end only on a page other than the hub's",
    ):
        hub_xy(_hub_env(1), ref, ref.ends[0])


def test_a_copy_whose_hub_has_no_placed_pin_raises_naming_the_net() -> None:
    ref = Ref("fb", RefKind.COPY, (RefEnd(2, "c1", PIN),))
    with pytest.raises(
        ValueError,
        match=r"net fb \(copy\): the hub has no placed pin.*"
        r"the placement must place a pin of the fan's hub",
    ):
        hub_xy(replace(_hub_env(1), pins={}), ref, ref.ends[0])
