"""Stage 6 trunks: the line, drops, risers and the crossed drops of a reversing pair."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import Box, PinRef
from fransys_layout.core.arrow_reserve import leg_lines
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.outputs import PinXY, Placed, Trunk, Wire
from fransys_layout.core.route import route_page
from fransys_layout.core.route_counts import collinear, counts
from fransys_layout.core.route_env import RouteEnv, body_hit
from fransys_layout.core.route_trunk import Line, TrunkError, _leg_wires, drop_kind, trunk_wires
from fransys_layout.core.score_wiring import bundles

from .conftest import MARKER
from .cycle_fixtures import acyclic_problem
from .place_fixtures import all_pins, bundle_fan
from .route_fixtures import envs_of, link_env, reversing_pair

STEP = core_options(
    marker=MARKER,
).wiring_grid
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
    box = Attach(None, 0, 0, pin, net="n")
    cell = Attach("c:x", 0, 0, PinRef("x", "n"), net="n")
    fan = Fan("f", ("n",), (box,), (cell,), None, 1, "below")
    assert drop_kind(fan, box) == "riser"
    assert drop_kind(fan, cell) == "drop"
    assert drop_kind(replace(fan, legs=(box,), drivers=()), box) == "drop"


def synthetic(  # noqa: PLR0913 - a fixture builder; each knob is keyword-only
    perm: tuple[int, ...],
    xs: list[int],
    *,
    above: bool,
    skip: int | None = None,
    grid: int = STEP,
    columns: tuple[int, ...] | None = None,
) -> tuple[RouteEnv, Trunk, int]:
    """One function K whose pole p sits at xs[p], feeding (or fed by) a trunk of len(perm) lanes.

    `columns[p]` is the column lane pole p stands in; by default the pole's own number.
    """
    n, ty = len(perm), 100
    pin_y = ty - 2 * grid * n if above else ty + 2 * grid * n
    pins = tuple(PinXY(f"n{p}", xs[p], pin_y) for p in range(n) if p != skip)
    box = Box(min(xs) - 4, pin_y - 8 if above else pin_y, max(xs) - min(xs) + 8, 8)  # behind the pins
    placed = {"K": Placed("K", 1, min(xs), pin_y, "R0", box, box, pins)}
    at = columns or tuple(range(n))
    atts = tuple(Attach("c:K", at[p], 0, PinRef("K", f"n{p}"), p, net="n") for p in range(n))
    fan = Fan(
        "f:b",
        tuple(f"L{k}" for k in range(n)),
        atts if above else (),
        () if above else atts,
        None,
        n,
        "below",
    )
    trunk = Trunk("f:b", 1, ty, min(xs), max(xs), n, 0, ((min(xs), max(xs)),) * n)
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
        replace(
            core_options(
                marker=MARKER,
            ),
            wiring_grid=grid,
        ),
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


def test_with_pole_0_off_the_row_each_pin_present_drops_straight_to_its_own_lane() -> None:
    xs = [100, 124, 148]
    env, trunk, pin_y = synthetic((0, 1, 2), xs, above=False, skip=0)
    wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
    assert sorted(w.points for w in wires) == [
        ((124, pin_y), (124, trunk.y + STEP)),
        ((148, pin_y), (148, trunk.y + 2 * STEP)),
    ]


def test_a_trunks_lines_stand_the_wiring_grid_apart() -> None:
    xs = [100, 124, 148]
    env, trunk, pin_y = synthetic((0, 1, 2), xs, above=False, grid=16)
    wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
    assert lanes_reached(wires, pin_y, xs) == {p: trunk.y + 16 * p for p in range(3)}


def reversing_env(*, lower: int) -> tuple[RouteEnv, Trunk]:
    """The reversing pair through the stages; K2 moved down by `lower`."""
    prob = reversing_pair(FULL)
    (env,) = envs_of(prob)
    k2 = env.placed["K2"]
    moved = replace(
        k2,
        pin_xy=tuple(replace(q, y=q.y + lower) for q in k2.pin_xy),
        body=replace(k2.body, y=k2.body.y + lower),
        footprint=replace(k2.footprint, y=k2.footprint.y + lower),
    )  # the body goes with its pins: a drop from a pin inside a body is a rise (R1290 ii)
    env = replace(env, placed={**env.placed, "K2": moved})
    return env, trunk_of(env, "f:bL")


def drawn_with_trunk(perm: tuple[int, ...], xs: list[int], *, above: bool) -> tuple[RouteEnv, list[Wire]]:
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


def test_a_drop_never_counts_against_its_own_trunk_but_counts_against_a_foreign_one() -> None:
    xs = [100, 124, 148]
    env, wires = drawn_with_trunk((0, 1, 2), xs, above=True)
    own = bundles(env.fans.values())
    assert counts(wires, own).crossings == 0
    assert counts(wires, None).crossings > 0
    foreign = Wire("G", 1, ((xs[0] - 8, 100), (xs[-1] + 8, 100)), "trunk")
    drops = [w for w in wires if w.kind != "trunk"]
    assert counts([*drops, foreign], own).crossings == len(xs) - 1


def test_a_gapped_bundle_draws_each_drop_on_its_poles_line() -> None:
    """Column lanes 1, 2, 3, 6 hold poles 0..3: the line is the pole's, never the column lane's."""
    xs = [100, 124, 148, 172]
    env, trunk, pin_y = synthetic((0, 1, 2, 3), xs, above=False, columns=(1, 2, 3, 6))
    wires = [w for w in trunk_wires(env, trunk).wires if w.kind != "trunk"]
    assert lanes_reached(wires, pin_y, xs) == {j: trunk.y + STEP * j for j in range(4)}
    assert {w.net for w in wires} == {f"L{k}" for k in range(4)}


def test_a_pole_beyond_the_bundles_nets_raises_naming_the_bundle() -> None:
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    short = replace(env, fans={"f:b": replace(env.fans["f:b"], nets=("L0", "L1"))})
    with pytest.raises(TrunkError, match=r"bundle f:b: K n2 is on pole 2, but the bundle has 3"):
        trunk_wires(short, trunk)


def test_a_trunk_with_no_fan_in_the_flow_raises_naming_the_fan_and_the_fix() -> None:
    env, trunk, _ = synthetic((0, 1, 2), [100, 124, 148], above=False)
    with pytest.raises(CoreError, match=r"trunk of fan f:b has no fan in the flow, so it is not drawn: report it"):
        trunk_wires(replace(env, fans={}), trunk)


def _runs_without_length(wires: list[Wire]) -> list[Wire]:
    return [w for w in wires if any(a == b for a, b in zip(w.points, w.points[1:], strict=False))]


@pytest.mark.rule("BUNDLE")
@pytest.mark.parametrize("perm", [(0,), (0, 1, 2)])
def test_a_trunk_with_one_x_draws_no_line_of_no_length_and_still_its_drops(perm) -> None:
    """Whole class: a trunk whose ends share one x draws no zero-length line (symdef refuses it)."""
    xs = [100 + 24 * p for p in range(len(perm))]
    env, trunk, _ = synthetic(perm, xs, above=False)
    point = replace(trunk, x1=trunk.x0)
    for t in (trunk, point):
        wires = list(trunk_wires(replace(env, trunks=(t,)), t).wires)
        assert [w for w in wires if w.kind != "trunk"]
        assert _runs_without_length(wires) == []


@pytest.mark.parametrize("lanes", [1, 3])
def test_a_rise_from_a_pin_off_the_wiring_grid_reaches_its_lane_line(lanes: int) -> None:
    """KI-199: the pin stands at x 42, a foreign body under it; the last lane's line takes the rise at that x."""
    env = link_env({"p": (42, 16, "S"), "f": (42, 40, "N")}, {})
    nets = ("a", "b", "c")[:lanes]
    fan = Fan("f1", nets, (Attach(None, 0, 0, PinRef("p", "p"), pole=lanes - 1, net="n"),), (), None, lanes, "S")
    trunk = Trunk("f1", 1, 72, 24, 80, lanes, 0, ((24, 80),) * lanes)
    env = replace(env, fans={"f1": fan}, trunks=(trunk,), bands=((0, 120),))
    page, _, _ = route_page(env)
    y = 72 + (lanes - 1) * STEP
    rise = next(w for w in page.wires if w.kind == "riser")
    assert rise.points[0] == (42, 16)
    assert rise.points[-1] == (42, y)


def test_a_drop_of_a_bundle_through_a_foreign_body_is_a_rise_for_the_router() -> None:
    """R1290 (ii), KI-394: a drop asks the keepout test; a body in the way sends the drop to A*."""
    env, trunk = reversing_env(lower=3 * STEP)
    assert not trunk_wires(env, trunk).rises, "control: nothing stands in the way"
    wall = replace(env.placed["K1"], sym="Z", body=Box(0, 90, 2000, 8), footprint=Box(0, 90, 2000, 8), pin_xy=())
    drawn = trunk_wires(replace(env, placed={**env.placed, "Z": wall}), trunk)
    assert drawn.rises


def test_a_one_sided_pins_leg_stands_clear_of_every_body_because_leg_lines_places_it_around_them() -> None:
    """R1632, KI-626: leg_lines places each leg once around the page footprints, so _leg_wires needs no body test of its own."""
    env, trunk = reversing_env(lower=3 * STEP)
    fan, wall = env.fans[trunk.fan], Box(820, 70, 30, 10)
    pin = fan.drivers[0].pin
    placed = {
        **env.placed,
        "Z": replace(env.placed["K1"], sym="Z", body=wall, footprint=Box(wall.x - 4, wall.y - 4, wall.w + 8, wall.h + 8), pin_xy=()),
    }

    def hits(feet: list[Box]) -> list[bool]:
        lines = leg_lines([trunk], {fan.id: fan}, {pin: trunk.row}, env.options, (feet, {}, None))
        e = replace(env, placed=placed, legs={pin: trunk.row}, leg_lines=lines)
        return [body_hit(e, w.net, w.points) is not None for w in _leg_wires(e, Line(fan, trunk, fan.id, STEP), set())]

    assert hits([p.footprint for p in env.placed.values()]) == [True], "control: a leg placed blind to the wall runs through it"
    assert hits([p.footprint for p in placed.values()]) == [False]


@pytest.mark.rule("BUNDLE-LANE-END")
def test_a_lone_tap_on_a_lane_of_no_length_draws_no_drop_while_another_lane_is_drawn() -> None:
    """R1904: the tap joins nothing on that row (its pin stands a reference end, CL1); a sole zero-length lane still draws its drop."""
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    flat = replace(trunk, lane_ends=((100, 148), (124, 124), (100, 148)))
    got = {w.points[0][0] for w in trunk_wires(replace(env, trunks=(flat,)), flat).wires if w.kind != "trunk"}
    assert got == {100, 148}
    alone = replace(trunk, lane_ends=((100, 100), (124, 124), (148, 148)))
    kept = {w.points[0][0] for w in trunk_wires(replace(env, trunks=(alone,)), alone).wires if w.kind != "trunk"}
    assert kept == {100, 124, 148}


@pytest.mark.rule("BUNDLE-LANE-END")
def test_a_lone_tap_that_stands_a_leg_keeps_its_drop() -> None:
    """R2211: the leg leaves the lane, so the lane draws its drop (KI-949) until the end stands at its pin."""
    env, trunk, _ = synthetic((0, 1, 2), [100, 124, 148], above=False)
    flat = replace(trunk, lane_ends=((100, 148), (124, 124), (100, 148)))
    env = replace(env, trunks=(flat,))

    def drops(e: RouteEnv) -> set[int]:
        return {w.points[0][0] for w in trunk_wires(e, flat).wires if w.kind != "trunk"}

    assert drops(env) == {100, 148}, "control: no leg, no drop"
    legged = replace(env, leg_lines={("f:b", 0, PinRef("K", "n1")): ((124, 100), (124, 108), (124, 116))})
    assert 124 in drops(legged)
