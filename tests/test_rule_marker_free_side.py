"""MARKER-FREE-SIDE (M1): a pin whose net is drawn on its page to its far end carries no marker.

Checked on the six corpus builds, at each core solve the layout step makes. The wire is the
reference, so a stub stands only where no wire is drawn: a far end on another page, or one cut
"""

import dataclasses
import functools
import importlib
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import fransys as fr
import pytest
from _direct_case import built_with_unlaid, laid_again
from fransys_el import build, drawn_power, house_conventions, lay_out_core, symbol_kit
from fransys_el.drawn_power import inked_power
from fransys_el.placement_env import port_pins
from test_drawn_symbols_placed_by_core import R825_STUBS

from electrical_symbols import LIBRARY, power_symbol_key
from fransys_layout.core.cut_drawn import stand_pins
from fransys_layout.core.values import PinRef
from fransys_model.derive import far_pins

ROOT = Path(__file__).resolve().parent.parent
CND_ENDS = tomllib.loads((ROOT / "tests/ratchets.toml").read_text())["drawing_connection_not_drawn"]
CASES = ["distribution_board", "machine_panel", "mcc", "panel_di16p", "remote_io", "skid"]


def model_conductors(model: Any, pins: Any) -> tuple[tuple[Any, Any], ...]:
    """Each `(near, far)` pin pair of the model's conductors, from `derive.far_pins`, not the planner's facts.

    A far end with no pin (undrawn, spare) is a `PinRef` of no symbol: that conductor is undrawn on its near page.
    """
    unpinned: dict[Any, PinRef] = {}
    pairs = ((pins[a], pins[b] if b in pins else unpinned.setdefault(b, PinRef("", str(b)))) for a, b in far_pins(model, tuple(pins)))
    return tuple(dict.fromkeys(pairs))


@functools.cache
def _both(name: str) -> tuple[Any, Any]:
    """(the build result, the model its layout step gets) of corpus build `name`."""
    run = importlib.import_module("placement_corpus.run")  # internal/ is not exported
    every = [*run.circuits("standard"), ("skid", run.load(run.SKID, "demo_skid"), {}, {})]
    circuit = next(c for c in every if c[0] == name)
    return built_with_unlaid(lambda: run.build(name, circuit))


def _built(name: str) -> Any:
    return _both(name)[0]


@functools.cache
def _unlaid(name: str) -> tuple[Any, tuple[tuple[PinRef, PinRef], ...], Any]:
    """(the model the layout step gets, its conductors as pin pairs, its port pins) of corpus build `name`."""
    unlaid = _both(name)[1]
    pins = port_pins(unlaid, symbol_kit(unlaid, LIBRARY), house_conventions(fr.settings().layout, LIBRARY, text_height=8), LIBRARY)
    return unlaid, model_conductors(unlaid, pins), pins


@functools.cache
def _solved(name: str) -> list[tuple[Any, Any]]:
    """(problem, CoreLayout) of every core solve the build's layout step makes, the problem's `far_ends` the model's conductors (KI-600)."""
    unlaid, every_conductor, _ = _unlaid(name)
    solved = []
    real = lay_out_core.solve

    def spy(problem, options, *args, **kwargs):
        layout = real(problem, options, *args, **kwargs)
        held = {sym.id for sym in problem.symbols}  # a drawing set owes every conductor end it holds, its far end in the set or not (R1573)
        owed = tuple(c for c in every_conductor if c[0].sym in held)
        solved.append((dataclasses.replace(problem, facts=dataclasses.replace(problem.facts, far_ends=owed)), layout))
        return layout

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lay_out_core, "solve", spy)
        laid_again(unlaid)
    return solved


def strikes(problem, layout) -> list[tuple[str, str, str]]:
    """Each `(net, stub pin, far pin)` where a stub stands on a pin whose every conductor is drawn."""
    nets = {p: n.id for n in problem.nets for p in n.pins}
    stubbed = {e.pin for r in layout.references if r.kind.value == "stub" for e in r.ends if e.pin}
    undrawn = {near for near, far in problem.facts.far_ends if (near, far) not in layout.drawn}
    return [
        (nets.get(near, "?")[:8], f"{near.sym}.{near.pin}", f"{far.sym}.{far.pin}")
        for near, far in problem.facts.far_ends
        if near in stubbed and near not in undrawn and (near, far) in layout.drawn
    ]


@pytest.fixture(scope="module", params=[pytest.param(n, marks=pytest.mark.private_input) for n in CASES])
def solved(request: pytest.FixtureRequest):
    return request.param, _solved(request.param)


# whole-class test: every STUB of every corpus build; none stands on a pin drawn to its far end
@pytest.mark.rule("MARKER-FREE-SIDE")
def test_no_stub_stands_on_a_pin_whose_net_is_drawn_to_its_far_end(solved) -> None:
    name, runs = solved
    found = [s for problem, layout in runs for s in strikes(problem, layout)]
    assert found == [], f"{name}: {len(found)} stubs on a drawn wire, first {found[:5]}"


def bare_conductors(problem, layout, *, one_sided: bool = False) -> list[tuple[str, str]]:
    """Each `(pin, far pin)` undrawn at a pin with a drawn conductor, where the pin has no reference and no power symbol pair.

    `one_sided` picks the pins with no free side to stand at (ONE-SIDED-PIN); the default picks the others.
    """
    stands = stand_pins(problem.facts.far_ends, (layout.drawn, (), ()), problem.symbols)
    referenced = {e.pin for r in layout.references for e in r.ends if e.pin}
    mixed = {near for near, _ in layout.drawn}
    powered = {a.pin for a in problem.anchors}  # a power symbol at a pin draws its connection: the pin is covered (CL1)
    return [
        (f"{near.sym}.{near.pin}", f"{far.sym}.{far.pin}")
        for near, far in problem.facts.far_ends
        if near in mixed
        and near in stands
        and (not any(stands[near].values())) is one_sided
        and (near, far) not in layout.drawn
        and near not in referenced
        and near not in powered
    ]


# R804: every undrawn conductor of a mixed pin has a reference at the pin
@pytest.mark.rule("MARKER-FREE-SIDE")
def test_every_undrawn_conductor_of_a_mixed_pin_has_a_reference_at_the_pin(solved) -> None:
    name, runs = solved
    found = [c for problem, layout in runs for c in bare_conductors(problem, layout)]
    assert found == [], f"{name}: {len(found)} conductors with no reference, first {found[:5]}"


# ONE-SIDED-PIN: a mixed pin with no free side has a reference for its undrawn conductors (a leg from the cut)
@pytest.mark.private_input
@pytest.mark.rule("MARKER-FREE-SIDE")
def test_every_undrawn_conductor_of_a_one_sided_mixed_pin_has_a_reference() -> None:
    found = {n: [c for problem, layout in _solved(n) for c in bare_conductors(problem, layout, one_sided=True)] for n in CASES}
    assert not any(found.values()), {n: len(c) for n, c in found.items() if c}


# R825: the r308 stock rises by exactly one per stub at a mixed pin
@pytest.mark.rule("MARKER-FREE-SIDE")
@pytest.mark.private_input
@pytest.mark.parametrize("name", CASES)
def test_the_r308_rise_is_one_per_mixed_pin_stub(name) -> None:
    count = 0
    for problem, layout in _solved(name):
        stands = stand_pins(problem.facts.far_ends, (layout.drawn, (), ()), problem.symbols)
        count += sum(1 for r in layout.references if r.kind.value == "stub" for e in r.ends if e.pin in stands and any(stands[e.pin].values()))
    assert count == R825_STUBS.get(name, 0)


# whole class: every conductor end of a corpus build is drawn or reported CONNECTION_NOT_DRAWN by the sweep (R553, R753, R1611)
@pytest.mark.rule("MARKER-FREE-SIDE")
@pytest.mark.rule("G01-CONNECTED")
def test_every_conductor_of_a_pin_is_a_drawn_wire_or_has_a_reference(solved) -> None:
    name, runs = solved
    ends = [f for f in _built(name).findings if f.code == "CONNECTION_NOT_DRAWN" and f.message.startswith("1 conductor end")]
    idle = [s for problem, layout in runs for s in strikes(problem, layout)]
    stock = CND_ENDS.get(name, 0)  # 0 on every corpus build (tests/ratchets.toml [drawing_connection_not_drawn])
    assert (len(ends), idle) == (stock, []), f"{name}: {len(ends)} conductor ends not drawn; stubs on drawn pins {idle[:3]}"


def leaves(wire_points: list[tuple[int, int]], at: tuple[int, int]) -> tuple[int, int] | None:
    """The unit step a wire takes away from the point `at` it starts or ends at, else None."""
    pts = list(wire_points)
    for here, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
        if here == at and nxt != at:
            return (nxt[0] > at[0]) - (nxt[0] < at[0]), (nxt[1] > at[1]) - (nxt[1] < at[1])
    return None


def side_strikes(marks, wires) -> list[object]:
    """Each key of `marks` `(key, pin xy, marker xy)` whose marker stands on a side one of `wires` leaves its pin by."""
    out = []
    for key, pin, mark in marks:
        dx, dy = mark[0] - pin[0], mark[1] - pin[1]
        side = ((dx > 0) - (dx < 0), 0) if abs(dx) > abs(dy) else (0, (dy > 0) - (dy < 0))
        if any(leaves(w, pin) == side for w in wires):
            out.append(key)
    return out


def test_side_strikes_finds_a_wire_on_the_markers_side_and_none_otherwise() -> None:
    wires = [[(0, 0), (0, 10), (5, 10)]]
    assert side_strikes([("m", (0, 0), (0, 4))], wires) == ["m"]
    assert side_strikes([("m", (0, 0), (0, -4))], wires) == []
    assert side_strikes([("m", (0, 0), (4, 0))], wires) == []


def near(m, xy) -> PinRef:
    """The pin of the marker's symbol nearest the marker: where a fan-wired pin's stub stands, which `stands` does not see."""
    return min((PinRef(s, p) for s, p in xy if s == m.end.sym), key=lambda k: abs(xy[k.sym, k.pin][0] - m.x) + abs(xy[k.sym, k.pin][1] - m.y))


def page_side_strikes(problem, layout) -> list[object]:
    """Each marker standing on a side a drawn wire of its page leaves its (stand) pin by."""
    stands = stand_pins(problem.facts.far_ends, (layout.drawn, (), ()), problem.symbols)
    xy = {(p.sym, q.pin): (q.x, q.y) for page in layout.placement.pages for p in page.placed for q in p.pin_xy}
    turned = {p.sym: p.orient for page in layout.placement.pages for p in page.placed}
    wires = {pr.page: [w.points for w in pr.wires] for pr in layout.routes.pages}
    return [
        (m.page, m.end.sym, m.end.pin)
        for m in layout.annotations.markers
        if m.kind.value != "arrow"
        and (pin := stands.get(m.end, {}).get(turned.get(m.end.sym), near(m, xy))) is not None  # a leg's marker stands off its pin
        and (pin.sym, pin.pin) in xy
        and side_strikes(
            [(0, xy[pin.sym, pin.pin], (m.x, m.y))], [list(w) for w in wires.get(m.page, ()) if (m.x, m.y) not in (w[0], w[-1])]
        )  # the marker's own lead ends at it
    ]


#: R1193 (KI-454, STACKED-LEG-ARROWS): the three Q32 leg stubs of mcc page 8 stand stacked on the leg's side; a looks count, it only falls.
STACKED_LEG_ARROWS = {"mcc": 3}


# A2: every marker of every build stands on a side no drawn wire of its page leaves its pin by
@pytest.mark.rule("MARKER-FREE-SIDE")
def test_every_marker_stands_on_a_side_no_drawn_wire_leaves_by(solved) -> None:
    name, runs = solved
    found = [s for problem, layout in runs for s in page_side_strikes(problem, layout)]
    assert len(found) <= STACKED_LEG_ARROWS.get(name, 0), f"{name}: {len(found)} markers on a wire's side {found[:3]}"


# STUB-SLOT (R962): a fan-wired pin's stub stands on the symbol's free pin or on a leg; none is left unplaced
@pytest.mark.rule("MARKER-FREE-SIDE")
def test_no_stub_of_a_fan_wired_pin_is_left_unplaced(solved) -> None:
    name, runs = solved
    unplaced = [f.subject for problem, layout in runs for f in layout.findings if f.code == "MARKER_UNPLACED"]
    assert unplaced == [], f"{name}: {len(unplaced)} markers unplaced {unplaced[:3]}"


@pytest.mark.private_input
def test_port_pins_hold_every_pin_the_planner_has_a_conductor_at() -> None:
    """The checker's pin map is the planner's: a pin of `build`'s own `far_ends` is a value of `port_pins`."""
    unlaid, _, _ = _unlaid("mcc")
    conventions = house_conventions(fr.settings().layout, LIBRARY, text_height=8)
    kit = symbol_kit(unlaid, LIBRARY)
    problem, _ = build(unlaid, kit, conventions, LIBRARY)
    planned = {p for pair in problem.facts.far_ends for p in pair}
    assert planned
    assert planned <= set(port_pins(unlaid, kit, conventions, LIBRARY).values())


@pytest.mark.private_input
@pytest.mark.rule("G01-CONNECTED")
@pytest.mark.parametrize(("key", "text"), [("ground", None), ("pe", None), ("supply", "24V"), ("supply", None)])
def test_a_port_drawn_as_an_inked_power_symbol_that_names_its_potential_is_a_carried_end(monkeypatch: pytest.MonkeyPatch, key: str, text: str | None):
    """R1631, R4: ground, PE and a texted supply with ink to their pin carry its end; a supply with no printed text names no potential."""
    symbols = [SimpleNamespace(key=power_symbol_key(key), ports=("a",))]
    part = SimpleNamespace(drawing=SimpleNamespace(symbols=symbols), ports={"a": (0, 0)}, nodes={(0, 0)}, powers={})
    net: Any = SimpleNamespace(pages={"p": part}, ids={"a": "a-id"}, linked={})
    monkeypatch.setattr(drawn_power, "port_power_text", lambda *_: text)
    assert (inked_power(net, None) == {"a"}) is (key != "supply" or text is not None)  # ty: ignore[invalid-argument-type] the read is monkeypatched
