"""Field case: a three-pole starter, breaker, contactor, overload, then a strip whose runs are wired in a second series.
The bug (v0.23.8): the strip is drawn under the contactor outputs and tapped off their bus, joining two nets; KI-874 STARTER-SIDE-TAP.
Also KI-875 (the series through the overload draws it turned 180 degrees) and KI-876 (the guide starter in a cabinet: YCycleError)."""

import tempfile
from functools import cache
from itertools import pairwise
from pathlib import Path

import fransys as fr
from _drawn_facts import Placed, pin_turn, symbol_subjects, wire_nets
from _field_shared import Point, join
from fransys.colours import BK, BU


def _cover() -> Path:
    path = Path(tempfile.mkdtemp()) / "cover.md"
    path.write_text("# Fan\n", encoding="utf-8")
    return path


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5-TWIN")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    with d.function("FAN", "Fan"):
        q0 = d.device("Q0", "DEMO-MCB-3P")
        q1 = d.device("Q1", "DEMO-CTR-3P-24")
        f1 = d.device("F1", "DEMO-OVERLOAD-3P")
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
        d.device("M1", "DEMO-MOTOR-4KW")
        d.series(ac, q0.element, q1.main, f1.main, wire=(BK, 2.5))
        r1, r2, r3 = x1.run("L1", 1), x1.run("L2", 1), x1.run("L3", 1)
        d.series(f1.main, (r1[1], r2[1], r3[1]), wire=(BK, 2.5))
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=_cover()))


def _pole(key: str, tag: str) -> Placed:
    return next(p for p in symbol_subjects(_built().model) if p.symbol == key and p.tag == tag)


def _components() -> dict[Point, int]:
    """Each drawn wire point with the id of the drawn piece it is in: wires meet end to end or where an end lies on a run."""
    wires = [list(w.points) for _, w in wire_nets(_built().model)]
    dots = {p for w in wires for p in w}
    root = {p: p for p in dots}

    def find(p: Point) -> Point:
        while root[p] != p:
            p = root[p]
        return p

    for wire in wires:
        for a, b in pairwise(wire):
            for p in (q for q in dots if min(a, b) <= q <= max(a, b) and (q[0] == a[0] == b[0] or q[1] == a[1] == b[1])):
                root[find(p)] = find(a)
    return {p: hash(find(p)) for p in dots}


def _turned_pin(one: Placed, pin: str) -> Point:
    turn = pin_turn(one.symbol, pin, poles=one.poles, orient=one.orient)
    return int(one.x + turn.dx), int(one.y + turn.dy)


def test_each_overload_output_is_drawn_to_its_strip_terminal() -> None:
    """KI-874: F1 2, 4 and 6 are drawn joined to X1 L1:1, L2:1 and L3:1."""
    f1 = _pole("thermal-overload", "F1")
    for k in (1, 2, 3):
        join(_built(), _turned_pin(f1, f"{k}.out"), _turned_pin(_pole("terminal", f"L{k}:1"), "n"))


def test_no_drawn_piece_joins_two_model_nets() -> None:
    """KI-874: a phase's contactor output and overload input (one net) and its overload output and strip terminal (the next) are separate pieces."""
    f1, q1 = _pole("thermal-overload", "F1"), _pole("make-contact", "Q1")
    piece, groups = _components(), {}
    for k in (1, 2, 3):
        groups[f"Q1:{2 * k}=F1:{2 * k - 1}"] = [_turned_pin(q1, f"{k}.out"), _turned_pin(f1, f"{k}.in")]
        groups[f"F1:{2 * k}=X1 L{k}:1"] = [_turned_pin(f1, f"{k}.out"), _turned_pin(_pole("terminal", f"L{k}:1"), "n")]
    seen: dict[int, set[str]] = {}
    for name, pins in groups.items():
        for pin in pins:
            seen.setdefault(piece.get(pin, hash(pin)), set()).add(name)
    joined = sorted(sorted(names) for names in seen.values() if len(names) > 1)
    assert joined == [], f"one drawn piece joins model nets: {joined}"


def _cabinet(d: fr.Design) -> fr.BuildResult:
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, d.location("CAB", "Cabinet"), cover=_cover()))


def test_a_series_through_the_overload_draws_each_wire_to_the_pin_the_model_connects() -> None:
    """KI-875: supply, Q1, F1, a whole strip, motor: Q1 pole k out is drawn joined to F1 pole k in."""
    d = fr.design("demo_parts", place="CAB")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5-TWIN")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    q1, f1 = d.device("Q1", "DEMO-CTR-3P-24"), d.device("F1", "DEMO-OVERLOAD-3P")
    x1, m1 = d.terminal_strip("X1", "DEMO-TB-2.5"), d.device("M1", "DEMO-MOTOR-4KW")
    d.series(ac, q1.main, f1.main, x1, m1, wire=(BK, 2.5))
    result = _cabinet(d)
    drawn = symbol_subjects(result.model)
    q, f = (next(p for p in drawn if p.symbol == key and p.tag == tag) for key, tag in (("make-contact", "Q1"), ("thermal-overload", "F1")))
    for k in (1, 2, 3):
        join(result, _turned_pin(q, f"{k}.out"), _turned_pin(f, f"{k}.in"))


def test_the_guide_motor_starter_in_a_cabinet_builds_without_an_error() -> None:
    """KI-876: the guide's motor starter with place= and CABINET_SCHEMATIC has no ERROR finding (it gave PLACEMENT_PROBLEM: YCycleError)."""
    d = fr.design("demo_parts", place="CAB")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5-TWIN")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1)
    q0, q1, f1 = d.device("Q0", "DEMO-MCB-3P"), d.device("Q1", "DEMO-CTR-3P-24"), d.device("F1", "DEMO-OVERLOAD-3P")
    s1, s2 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
    w1, m1 = d.cable("W1", "DEMO-CBL-4G1.5"), d.device("M1", "DEMO-MOTOR-4KW")
    d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1, wire=(BK, 2.5))
    d.series(ac.L1, g1.input, ac.N, wire=(BK, 2.5))
    d.series(dc.plus, s1.nc, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
    errors = [f"{f.code}: {f.message[:160]}" for f in _cabinet(d).findings if f.severity.value == "error"]
    assert errors == [], f"the build shows ERROR findings: {errors}"
