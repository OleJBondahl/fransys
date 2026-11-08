"""`build`: the problem round-trips, is repeatable, and names only symbols it draws."""
# NET_POTENTIAL_CONFLICT 2 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 2 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# WIRE_ROW_UNRESOLVED 6 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

import dataclasses

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import ProblemError, build, placement_syms
from fransys_el.kit_keys import PickKey, function_of
from fransys_el.placement_annexes import label_annexes
from fransys_el.placement_env import make_env
from fransys_el.placement_ids import symbol_key
from fransys_el.placement_sets import drawing_scopes, restriction
from fransys_el.placement_syms import strip_tags, syms_of
from fransys_el.placement_where import where_room
from placement_fixtures import _feed, demo_model, kit_for, planted_model, sid
from symdef import from_divisions, text_footprint

from electrical_symbols import LIBRARY
from fransys_layout.core import PlacementProblem, Size, from_plain, to_plain
from fransys_model.derive import function_role, function_scopes, port_designation, run_point_text, tag_text
from fransys_model.derive.order import functions_in_order
from fransys_model.vocab import ports
lazy from fransys_model.kernel import Model


@pytest.fixture(scope="module")
def planted() -> tuple[Model, PlacementProblem]:
    """The all-features planted model and its problem, built once for the module."""
    model = planted_model()
    return model, build(model, kit_for(model), house(), LIBRARY)[0]


@pytest.fixture(scope="module")
def demo() -> PlacementProblem:
    """The demo model's problem, built once for the module."""
    model = demo_model()
    return build(model, kit_for(model), house(), LIBRARY)[0]


def _reversed_model() -> Model:
    """The all-features planted design with its functions and devices authored in reverse."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    io = d.add(_feed, "U1")
    with d.function("FIELD", "Unit feed"):
        d.series(dc.plus, io.X1[1], wire=(BU, 0.75))
        d.series(dc.minus, io.X1[2], wire=(BU, 0.75))
    a2 = d.device("A2", "DEMO-PLC-DI-2")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    with d.function("SENSE", "Two-wire sensor"):
        d.series(g1.output["+"], b1.sig["1"], wire=(BU, 0.75))
        d.series(b1.sig["2"], a2.di_1["1"], wire=(BU, 0.75))
    q2 = d.device("Q2", "DEMO-MCB-3P")
    q1 = d.device("Q1", "DEMO-MCB-3P")
    with d.function("BREAKERS", "Breaker pair"):
        d.series(q1.element, q2.element, wire=(BU, 2.5))
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
    assert build(model, kit_for(model), house(), LIBRARY)[0] == problem


def test_authoring_order_does_not_change_problem(planted: tuple[Model, PlacementProblem]) -> None:
    """The same design authored in reverse order gives an equal problem."""
    _, problem = planted
    model = _reversed_model()
    assert build(model, kit_for(model), house(), LIBRARY)[0] == problem


def test_every_net_pin_names_a_pin_of_a_symbol(planted: tuple[Model, PlacementProblem]) -> None:
    """Each pin of each net names a symbol of the problem and one of that symbol's pins."""
    _, problem = planted
    assert problem.nets
    pins_of = {s.id: {p.id for p in s.pins} for s in problem.symbols}
    for net in problem.nets:
        for ref in net.pins:
            assert ref.sym in pins_of
            assert ref.pin in pins_of[ref.sym]


def test_symbols_keep_the_kit_order(planted: tuple[Model, PlacementProblem]) -> None:
    """The symbols come in function order (model-0396); `syms_of` sorts nowhere (R349); loose ones drop."""
    model, problem = planted
    env = make_env(model, kit_for(model), house(), LIBRARY)
    ids = [s.id for s in problem.symbols]
    assert len(ids) > 1
    kept = set(ids)
    assert ids == [i for i in (env.ids[lead] for lead in functions_in_order(model, env.kit)) if i in kept]


def test_strip_terminals_carry_row_fields_and_two_pin_sensor_does_not(planted: tuple[Model, PlacementProblem]) -> None:
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
        build(model, partial, house(), LIBRARY)
    assert info.value.fix
    own = [p for p, r in ports(model).items() if r.function == lead]
    assert any(info.value.subject == f"port {port_designation(model, p)}" for p in own)


def test_a_terminals_where_room_is_its_own_and_one_digit_wider_per_page_digit(planted: tuple[Model, PlacementProblem]) -> None:
    """No document-wide line remains (R1883): the room is per terminal, one line per other scope, its page number `digits` long."""
    model, _ = planted
    env = make_env(model, kit_for(model), house(), LIBRARY)
    assert not hasattr(env, "where")
    pin = function_of(model, _pin_of(model))
    one, two = where_room(env, pin), where_room(env, pin, 2)
    assert one.count("\n") == len(function_scopes(model, pin)) - 1 >= 1
    assert two.count("\n") == one.count("\n")
    assert len(two.splitlines()[1]) == len(one.splitlines()[1]) + 1  # a digit more, no more
    assert (
        where_room(
            env, function_of(model, next(k for k in env.owner if k != _pin_of(model) and not function_role(model, function_of(model, k)).terminal))
        )
        == ""
    )


def test_a_terminal_with_a_where_room_holds_its_label_again_per_extra_page_digit(planted: tuple[Model, PlacementProblem]) -> None:
    """`Sym.wider` is the label at 2, 3, ... digits, growing; a symbol with no room holds none (R1883)."""
    model, _ = planted
    env = make_env(model, kit_for(model), house(), LIBRARY)
    found = {s.id: s for s in syms_of(env)}
    pin = found[symbol_key(model, _pin_of(model))]
    widths = [pin.labels[""].w, *(w[""].w for w in pin.wider)]
    assert len(pin.wider) == house().options.where_digit_rounds
    assert widths == sorted(set(widths))
    assert all(not s.wider for s in found.values() if s.row_group is None)


def _pin_of(model: Model, text: str = "-U1-X1:2") -> PickKey:
    """The kit key of the terminal whose full designation is `text` (a drawing prints its point only, STRIP-TAG-ONCE)."""
    return next(f for f in kit_for(model) if tag_text(model, function_of(model, f)) == text)


def _label_of_pin(model: Model) -> tuple[Size, float, str]:
    """The label size of the pin `-U1-X1:2` over `model`, the cap height in mm, and its where room."""
    env = make_env(model, kit_for(model), house(), LIBRARY)
    pin = _pin_of(model)
    label = next(s.labels[""] for s in syms_of(env) if s.id == symbol_key(model, pin))
    cap = from_divisions(LIBRARY.grid, house().text_height) * LIBRARY.font.cap_height / LIBRARY.font.units_per_em * LIBRARY.grid.module_mm
    return label, cap, where_room(env, function_of(model, pin))


def test_a_tag_with_where_lines_is_measured_as_the_block_of_its_lines(planted: tuple[Model, PlacementProblem]) -> None:
    """The tag and its where line are one block: the widest line wide, two lines tall, not the sum of both widths by one line."""
    label, cap, room = _label_of_pin(planted[0])
    assert room
    point = run_point_text(planted[0], function_of(planted[0], _pin_of(planted[0])))
    assert label == Size(*text_footprint(LIBRARY.font, point + room, cap, LIBRARY.grid))  # the point, the strip tag is the run's (STRIP-TAG-ONCE)
    assert label.h > text_footprint(LIBRARY.font, point, cap, LIBRARY.grid)[1]


def test_a_tag_in_a_unit_scoped_set_is_measured_as_that_set_prints_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-734 (GAP-FLIP-734 in tests/gap_flip_other.toml): `-U1-X1` prints `-X1` in its unit's set: its run tag there has that width."""
    monkeypatch.setattr(placement_syms, "where_room", lambda *_: "")
    model = planted_model()
    kit = kit_for(model)
    problem = build(model, kit, house(), LIBRARY)[0]
    tags = strip_tags(make_env(model, kit, house(), LIBRARY))
    scopes = drawing_scopes(model, kit)
    pin = _pin_of(model)
    scope = next(s for s in scopes if s.of_unit is not None and symbol_key(model, pin) in s.symbols)
    strip = next(sym.row_group for sym in problem.symbols if sym.id == symbol_key(model, pin))
    label = next(a.size for a in restriction(problem, scope, scopes=scopes, options=house().options, tags=tags).problem.annexes if a.owner == strip)
    cap = from_divisions(LIBRARY.grid, house().text_height) * LIBRARY.font.cap_height / LIBRARY.font.units_per_em * LIBRARY.grid.module_mm
    assert label.w == text_footprint(LIBRARY.font, "-X1", cap, LIBRARY.grid)[0]


def test_a_symbol_with_no_tag_slot_has_a_zero_label_in_every_set_that_draws_it(planted: tuple[Model, PlacementProblem]) -> None:
    """`Sym.labels` holds every scope key the sets use, so `label_annexes` of a unit's set never misses a zero-label symbol."""
    env = make_env(planted[0], kit_for(planted[0]), house(), LIBRARY)
    got = placement_syms._labels(env, None, None, Size(0, 0), {"U1": "-X1:2"})  # ty: ignore[invalid-argument-type] a zero label reads neither
    assert got == {"": Size(0, 0), "U1": Size(0, 0)}


def test_a_strip_named_like_a_symbol_is_refused_naming_the_strip(planted: tuple[Model, PlacementProblem]) -> None:
    """The strip owns its template annex and a symbol its own: one id space, so a clash raises."""
    sym = planted[1].symbols[0]
    with pytest.raises(ProblemError, match=sym.id):
        label_annexes((dataclasses.replace(sym, row_group=sym.id),), house().options, "", {sym.id: {"": Size(8, 8)}})
