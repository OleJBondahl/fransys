"""Stage 6 trunks: the line, drops, risers and the crossed drops of a reversing pair."""

from __future__ import annotations

from dataclasses import replace
from itertools import permutations

import pytest

from fransys_layout.core import Box, Options, PinRef
from fransys_layout.core.outputs import PinXY, Placed, Trunk, Wire
from fransys_layout.core.route_counts import collinear, counts
from fransys_layout.core.route_env import RouteEnv
from fransys_layout.core.route_trunk import drop_kind, trunk_wires
from fransys_layout.core.score_wiring import bundles
from fransys_layout.core.values import Attach, Fan

from .conftest import MARKER_BOX
from .cycle_fixtures import acyclic_problem
from .pipeline_fixtures import cut_of
from .place_fixtures import all_pins, bundle_fan
from .route_fixtures import envs_of, inherent, overlaps, own_crossings, reversing_pair, with_crossed

STEP = Options(marker=MARKER_BOX).wiring_grid
FULL = (2, 1, 0)


def trunk_of(env: RouteEnv, fan_id: str) -> Trunk:
    return next(t for t in env.trunks if t.fan == fan_id)


def drops_of(env: RouteEnv, fan_id: str) -> list[Wire]:
    return [w for w in trunk_wires(env, trunk_of(env, fan_id)).wires if w.kind != "trunk"]


def far_ends(env: RouteEnv, wires: list[Wire]) -> dict[tuple[str, str], int]:
    """For each pin a wire ends on, the y of the wire's other end."""
    at = {xy: key for key, xy in all_pins(placement_of(env)).items()}
    out = {}
    for w in wires:
        first, last = w.points[0], w.points[-1]
        pin_end, line_end = (first, last) if first in at else (last, first)
        out[at[pin_end]] = line_end[1]
    return out


def placement_of(env: RouteEnv):
    from fransys_layout.core import Placement
    from fransys_layout.core.outputs import PagePlacement

    page = PagePlacement(env.page, tuple(env.placed.values()), env.gaps, env.trunks, (), env.bands)
    return Placement((page,))


def test_the_bundle_drops_meet_the_line_of_their_own_pole() -> None:
    prob = bundle_fan()
    (env,) = envs_of(prob)
    trunk = trunk_of(env, "f:bd1")
    pole = {(r.sym, r.pin): n.bundle.pole for n in prob.nets if n.bundle for r in n.pins}
    reached = far_ends(env, drops_of(env, "f:bd1"))
    assert reached
    assert reached == {pin: trunk.y + STEP * pole[pin] for pin in reached}


def test_a_plain_fan_has_one_drop_per_attachment_and_none_for_one_on_the_line() -> None:
    (env,) = envs_of(acyclic_problem())
    (trunk,) = env.trunks
    fan = env.fans[trunk.fan]
    xy = all_pins(placement_of(env))
    pins = [(a.pin.sym, a.pin.pin) for a in (*fan.drivers, *fan.legs)]
    on_line = [p for p in pins if xy[p][1] == trunk.y]
    drops = drops_of(env, fan.id)
    assert len(drops) == len(pins) - len(on_line)
    assert {w.net for w in drops} == {fan.nets[0]}
    assert {w.kind for w in drops} <= {"drop", "riser"}


def test_an_attachment_off_the_trunks_row_belongs_to_another_trunk() -> None:
    (env,) = envs_of(acyclic_problem())
    (trunk,) = env.trunks
    squeezed = replace(env, bands=((trunk.y, trunk.y),))
    assert drops_of(squeezed, trunk.fan) == []


def test_a_riser_is_a_box_pin_that_is_not_a_leg() -> None:
    pin = PinRef("A1", "p1")
    box = Attach(None, 0, 0, pin)
    cell = Attach("c:x", 0, 0, PinRef("x", "n"))
    fan = Fan("f", ("n",), (box,), (cell,), None, 1, "below")
    assert drop_kind(fan, box) == "riser"
    assert drop_kind(fan, cell) == "drop"
    assert drop_kind(replace(fan, legs=(box,), drivers=()), box) == "drop"


def synthetic(
    perm: tuple[int, ...], xs: list[int], *, above: bool, skip: int | None = None, grid: int = STEP
) -> tuple[RouteEnv, Trunk, int]:
    """One function K whose pole p sits at xs[p], feeding (or fed by) a trunk of len(perm) lanes."""
    n, ty = len(perm), 100
    pin_y = ty - 2 * grid * n if above else ty + 2 * grid * n
    pins = tuple(PinXY(f"n{p}", xs[p], pin_y) for p in range(n) if p != skip)
    box = Box(min(xs) - 4, pin_y - 4, max(xs) - min(xs) + 8, 8)
    placed = {"K": Placed("K", 1, min(xs), pin_y, "R0", box, box, pins)}
    atts = tuple(Attach("c:K", p, 0, PinRef("K", f"n{p}")) for p in range(n))
    fan = Fan(
        "f:b",
        tuple(f"L{k}" for k in range(n)),
        atts if above else (),
        () if above else atts,
        None,
        n,
        "below",
        (("K", perm),),
    )
    trunk = Trunk("f:b", 1, ty, min(xs), max(xs), n, 0)
    band = (ty - 2 * grid * n - grid, ty + 2 * grid * n + grid)
    env = RouteEnv(
        1,
        placed,
        (),
        {},
        {},
        {"f:b": fan},
        (),
        (trunk,),
        (band,),
        (),
        frozenset(),
        replace(Options(marker=MARKER_BOX), wiring_grid=grid),
    )
    return env, trunk, pin_y


def lanes_reached(wires: list[Wire], pin_y: int, xs: list[int]) -> dict[int, int]:
    """Pole -> y of the line its drop ends on."""
    out = {}
    for w in wires:
        ends = (w.points[0], w.points[-1])
        pin = next(e for e in ends if e[1] == pin_y and e[0] in xs)
        out[xs.index(pin[0])] = next(e for e in ends if e != pin)[1]
    return out


@pytest.mark.parametrize("n", [3, 4])
@pytest.mark.parametrize("above", [False, True], ids=["legs", "drivers"])
@pytest.mark.parametrize("mirrored", [False, True], ids=["poles-rightward", "poles-leftward"])
def test_every_permutation_draws_square_without_overlap_and_crosses_only_where_inverted(
    n: int, *, above: bool, mirrored: bool
) -> None:
    xs = [100 + 24 * (n - 1 - p if mirrored else p) for p in range(n)]
    for perm in permutations(range(n)):
        env, trunk, pin_y = synthetic(perm, xs, above=above)
        wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
        runs = [s for w in wires for s in zip(w.points, w.points[1:], strict=False)]
        assert all(a != b and (a[0] == b[0] or a[1] == b[1]) for a, b in runs), perm
        assert lanes_reached(wires, pin_y, xs) == {perm[j]: trunk.y + STEP * j for j in range(n)}
        assert own_crossings_of(wires) == inherent(xs, perm), perm
        assert not overlaps_of(wires), perm
        levels = [a[1] for a, b in runs if a[1] == b[1]]
        assert all(
            pin_y < y <= trunk.y - STEP if above else trunk.y + STEP * n <= y < pin_y
            for y in levels
        ), perm


def own_crossings_of(wires: list[Wire]) -> int:
    from fransys_layout.core.outputs import Counts, PageRoutes, Routes

    page = PageRoutes(1, tuple(wires), (), Counts(0, 0, 0, 0, 0))
    return own_crossings(Routes((page,)))


def overlaps_of(wires: list[Wire]) -> list:
    from fransys_layout.core.outputs import Counts, PageRoutes, Routes

    page = PageRoutes(1, tuple(wires), (), Counts(0, 0, 0, 0, 0))
    return overlaps(Routes((page,)))


def test_with_pole_0_off_the_row_each_pin_present_drops_straight_to_its_own_lane() -> None:
    xs = [100, 124, 148]
    env, trunk, pin_y = synthetic(FULL, xs, above=False, skip=0)
    wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
    assert sorted(w.points for w in wires) == [
        ((124, pin_y), (124, trunk.y + STEP)),
        ((148, pin_y), (148, trunk.y)),
    ]


def test_a_trunks_lines_stand_the_wiring_grid_apart() -> None:
    xs = [100, 124, 148]
    env, trunk, pin_y = synthetic((0, 1, 2), xs, above=False, grid=16)
    wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
    assert lanes_reached(wires, pin_y, xs) == {p: trunk.y + 16 * p for p in range(3)}


def crossed_env(*, lower: int) -> tuple[RouteEnv, Trunk]:
    """The reversing pair through the stages with Fan.crossed set; K2 moved down by `lower`."""
    prob = reversing_pair(FULL)
    cut = with_crossed(cut_of(prob), "f:bL", (("K2", FULL),))
    (env,) = envs_of(prob, cut=cut)
    k2 = env.placed["K2"]
    moved = replace(k2, pin_xy=tuple(replace(q, y=q.y + lower) for q in k2.pin_xy))
    env = replace(env, placed={**env.placed, "K2": moved})
    return env, trunk_of(env, "f:bL")


def test_a_reversing_pair_through_the_stages_draws_its_inherent_crossings() -> None:
    env, trunk = crossed_env(lower=3 * STEP)
    drawn = trunk_wires(env, trunk)
    drops = [w for w in drawn.wires if w.kind != "trunk"]
    assert drawn.findings == ()
    assert own_crossings_of(drops) == 3
    assert not overlaps_of(drops)


def test_a_crossed_trunk_with_no_room_for_its_levels_is_a_finding_and_draws_nothing() -> None:
    """Stage 5 now leaves grid * (3 + 2); K2 raised by two steps leaves the lanes' share only."""
    env, trunk = crossed_env(lower=-2 * STEP)
    drawn = trunk_wires(env, trunk)
    (finding,) = drawn.findings
    assert (finding.code, finding.subject) == ("ROUTE_FAILED", "K2")
    assert "crossed" in finding.text
    assert "stage 5" in finding.text
    assert not [w for w in drawn.wires if w.points[0] in k2_pins(env)]


def k2_pins(env: RouteEnv) -> set[tuple[int, int]]:
    return {(q.x, q.y) for q in env.placed["K2"].pin_xy}


def drawn_with_trunk(
    perm: tuple[int, ...], xs: list[int], *, above: bool
) -> tuple[RouteEnv, list[Wire]]:
    """The whole bundle of `synthetic` (trunk line and drops) and the env it came from."""
    env, trunk, _ = synthetic(perm, xs, above=above)
    return env, list(trunk_wires(env, trunk).wires)


def test_a_bundle_trunk_of_k_lanes_with_k_drops_counts_no_crossing_and_no_collinear_run() -> None:
    for k in (2, 3, 4):
        xs = [100 + 24 * p for p in range(k)]
        for above in (False, True):
            env, wires = drawn_with_trunk(tuple(range(k)), xs, above=above)
            member_drops = [w for w in wires if w.kind != "trunk"]
            assert {w.net for w in member_drops} <= {f"L{p}" for p in range(k)}
            assert counts(wires, bundles(env.fans.values())).crossings == 0, (k, above)
            assert collinear(wires) == 0, (k, above)


def test_two_drops_of_one_bundle_that_cross_count_one_crossing() -> None:
    xs = [100, 124]
    env, wires = drawn_with_trunk((1, 0), xs, above=False)
    drops = [w for w in wires if w.kind != "trunk"]
    assert {w.net for w in drops} == {"L0", "L1"}
    assert counts(drops, bundles(env.fans.values())).crossings == 1


def test_a_drop_never_counts_against_its_own_trunk_but_counts_against_a_foreign_one() -> None:
    xs = [100, 124, 148]
    env, wires = drawn_with_trunk((0, 1, 2), xs, above=True)
    own = bundles(env.fans.values())
    assert counts(wires, own).crossings == 0
    assert counts(wires, None).crossings > 0
    foreign = Wire("G", 1, ((xs[0] - 8, 100), (xs[-1] + 8, 100)), "trunk")
    drops = [w for w in wires if w.kind != "trunk"]
    assert counts([*drops, foreign], own).crossings == len(xs) - 1
