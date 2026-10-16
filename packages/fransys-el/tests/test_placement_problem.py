"""`build`: the problem round-trips, is repeatable, and names only symbols it draws."""

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import Conventions, ProblemError, build
from placement_fixtures import _feed, demo_model, kit_for, planted_model, sid

from fransys_layout.core import PlacementProblem, from_plain, natural_key, to_plain
from fransys_model.derive import port_designation
from fransys_model.vocab import ports
lazy from fransys_model.kernel import Model


@pytest.fixture(scope="module")
def planted() -> tuple[Model, PlacementProblem]:
    """The all-features planted model and its problem, built once for the module."""
    model = planted_model()
    return model, build(model, kit_for(model), Conventions())[0]


@pytest.fixture(scope="module")
def demo() -> PlacementProblem:
    """The demo model's problem, built once for the module."""
    model = demo_model()
    return build(model, kit_for(model), Conventions())[0]


def _reversed_model() -> Model:
    """The all-features planted design with its functions and devices authored in reverse."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    j2 = d.device("J2", "DEMO-CONN-2P")
    j1 = d.device("J1", "DEMO-CONN-2P")
    d.mate(j1.x1, j2.x1)
    io = d.add(_feed, "U1")
    with d.function("FIELD", "Unit feed"):
        d.series(dc.plus, io.X1[1], dc.minus, wire=(BU, 0.75))
    a2 = d.device("A2", "DEMO-PLC-DI-2")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    with d.function("SENSE", "Two-wire sensor"):
        d.detail.wire(g1.output["+"], b1.sig["1"], wire=(BU, 0.75))
        d.detail.wire(b1.sig["2"], a2.di_1["1"], wire=(BU, 0.75))
    q2 = d.device("Q2", "DEMO-MCB-3P")
    q1 = d.device("Q1", "DEMO-MCB-3P")
    with d.function("BREAKERS", "Breaker pair"):
        d.series(q1.element, q2.element, wire=2.5)
    s1 = d.device("S1", "DEMO-PB-NO")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("RELAY", "Relay"):
        d.series(dc.plus, k1.co_1.no, k1.co_2.no, dc.minus, wire=(BU, 0.75))
        d.series(dc.plus, s1.sw, k1.coil, dc.minus, wire=(BU, 0.75))
    with d.function("FEED", "Strip feed"):
        d.series(dc.plus, x1[1], dc.minus, wire=(BU, 0.75))
    return fr.build(d).model


def test_round_trip_demo(demo: PlacementProblem) -> None:
    """The demo problem survives `to_plain` and `from_plain` unchanged."""
    assert from_plain(PlacementProblem, to_plain(demo)) == demo


def test_round_trip_planted_all_features(planted: tuple[Model, PlacementProblem]) -> None:
    """The all-features planted problem survives `to_plain` and `from_plain` unchanged."""
    _, problem = planted
    assert from_plain(PlacementProblem, to_plain(problem)) == problem


def test_build_twice_gives_equal_problems(planted: tuple[Model, PlacementProblem]) -> None:
    """Building the same model twice gives equal problems."""
    model, problem = planted
    assert build(model, kit_for(model), Conventions())[0] == problem


def test_authoring_order_does_not_change_problem(planted: tuple[Model, PlacementProblem]) -> None:
    """The same design authored in reverse order gives an equal problem."""
    _, problem = planted
    model = _reversed_model()
    assert build(model, kit_for(model), Conventions())[0] == problem


def test_every_net_pin_names_a_pin_of_a_symbol(planted: tuple[Model, PlacementProblem]) -> None:
    """Each pin of each net names a symbol of the problem and one of that symbol's pins."""
    _, problem = planted
    assert problem.nets
    pins_of = {s.id: {p.id for p in s.pins} for s in problem.symbols}
    for net in problem.nets:
        for ref in net.pins:
            assert ref.sym in pins_of
            assert ref.pin in pins_of[ref.sym]


def test_symbols_are_in_natural_id_order(planted: tuple[Model, PlacementProblem]) -> None:
    """The symbols of the problem come in natural order of their ids."""
    _, problem = planted
    ids = [s.id for s in problem.symbols]
    assert len(ids) > 1
    assert ids == sorted(ids, key=natural_key)


def test_strip_terminals_carry_row_fields_and_two_pin_sensor_does_not(
    planted: tuple[Model, PlacementProblem],
) -> None:
    """Closest honest T4 check: row fields follow the strip, not the symbol kind.

    No fixture swaps a terminal's kind for a two-pin device with the same geometry, so this
    compares the row fields of a strip terminal with a two-pin generic box that is no strip.
    """
    model, problem = planted
    by_id = {s.id: s for s in problem.symbols}
    terminal = by_id[sid(model, "1.terminal")]
    sensor = by_id[sid(model, "B1.sig")]
    assert len(sensor.pins) == 2
    assert terminal.row_group is not None
    assert terminal.row_footprint is not None
    assert sensor.row_group is None
    assert sensor.row_footprint is None


def test_missing_pick_raises_problem_with_fix(planted: tuple[Model, PlacementProblem]) -> None:
    """A kit with one function's pick removed makes `build` raise `ProblemError`."""
    model, _ = planted
    kit = kit_for(model)
    lead = next(iter(kit))
    partial = frozendict({f: pick for f, pick in kit.items() if f != lead})
    with pytest.raises(ProblemError) as info:
        build(model, partial, Conventions())
    assert info.value.fix
    own = [p for p, r in ports(model).items() if r.function == lead]
    assert any(info.value.subject == f"port {port_designation(model, p)}" for p in own)
