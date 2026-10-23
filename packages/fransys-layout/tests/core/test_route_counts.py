"""Stage 6 counts: one number with the scorer, collinear overlaps and gap demand."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core.outputs import Gap, SceneWire, Wire
from fransys_layout.core.route_counts import collinear, counts, demand
from fransys_layout.core.score_wiring import wiring


def wire(net: str, *points: tuple[int, int]) -> Wire:
    return Wire(net, 1, points, "routed")


H = wire("A", (0, 50), (100, 50))
V = wire("B", (50, 0), (50, 100))


def test_two_nets_crossing_count_one() -> None:
    assert counts((H, V)).crossings == 1


def test_the_same_two_nets_drawn_twice_count_one() -> None:
    """Crossings are counted once per point, so a doubled drawing adds none."""
    assert counts((H, V, H, V)).crossings == 1


def test_one_net_never_crosses_itself() -> None:
    assert counts((H, replace(V, net="A"))).crossings == 0


def test_a_t_junction_and_a_corner_count_zero() -> None:
    tee = wire("B", (50, 50), (50, 100))
    corner = wire("B", (100, 50), (100, 100))
    assert counts((H, tee)).crossings == 0
    assert counts((H, corner)).crossings == 0


def test_counts_equal_the_scorers_wiring_on_the_same_polylines() -> None:
    """The oracle: one number, whichever side counts."""
    z = wire("C", (10, 10), (10, 30), (90, 30), (90, 80))
    wires = (H, V, z)
    scene = tuple(SceneWire(w.net, w.page, w.points, w.kind) for w in wires)
    got, want = counts(wires), wiring(scene)
    assert (got.crossings, got.bends, got.excess, got.length, got.detour) == (
        want["crossings"],
        want["bends"],
        want["excess_bends"],
        want["length_g"],
        want["detour_g"],
    )
    assert got.crossings > 0
    assert got.bends == 2


def test_collinear_overlap_of_two_nets_counts_one_and_touching_ends_none() -> None:
    over = wire("B", (60, 50), (160, 50))
    touch = wire("B", (100, 50), (160, 50))
    assert collinear((H, over)) == 1
    assert collinear((H, touch)) == 0
    assert collinear((H, replace(over, net="A"))) == 0


GAP = Gap("g", 1, "c0", "c1", 40, 60, 0, 0, 100)


def test_two_nets_in_one_gap_give_demand_two() -> None:
    a, b = wire("A", (45, 0), (45, 90)), wire("B", (55, 10), (55, 80))
    assert demand((a, b), (GAP,))[0].tracks == 2


def test_two_vertical_runs_at_one_x_give_demand_one() -> None:
    a, b = wire("A", (45, 0), (45, 40)), wire("B", (45, 50), (45, 90))
    assert demand((a, b), (GAP,))[0].tracks == 1


def test_a_run_in_another_rows_band_gives_demand_zero() -> None:
    other = wire("A", (45, 200), (45, 290))
    assert demand((other,), (GAP,))[0].tracks == 0
    assert demand((wire("A", (30, 0), (30, 90)),), (GAP,))[0].tracks == 0
