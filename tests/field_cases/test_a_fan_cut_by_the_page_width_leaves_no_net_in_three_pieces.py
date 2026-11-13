"""Field case: a supply cabled from outside to a cabinet whose three phases fan from one breaker to five starters.
The bug (KI-412): the page cut falls inside the fan, one phase gets a lone copy marker, and its net draws as 3 pieces (CONNECTION_NOT_DRAWN).
Closed (KI-412, KI-537): the repro is valid (X1 marks the supply only, the pumps' PE points sit on X5); no 3-piece net at six salts."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from fransys.colours import BK, BN, GNYE, GY

if TYPE_CHECKING:
    from pathlib import Path

_PH = (BN, BK, GY)
_PUMPS = 5


class _Io(NamedTuple):
    L1: fr.Run
    L2: fr.Run
    L3: fr.Run
    PE: fr.Run
    U: fr.Run
    V: fr.Run
    W: fr.Run
    PE_LOAD: fr.Run


def _fan(u: Any, *, motors_inside: bool) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        l1, l2, l3 = (x1.run(k, 1) for k in ("L1", "L2", "L3"))
        pe_in = x1.run("PE", 1)
        pe = u.terminal_strip("X5", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", _PUMPS, bridged=True)  # one point a pump (R1266)
        u.ac_supply("mains", 230, l1[1], l2[1], l3[1])
        q1 = u.device("Q1", "DEMO-MCB-3P")
        for run, pin, colour in ((l1, "1", BN), (l2, "3", BK), (l3, "5", GY)):
            u.series(run[1].inner, q1.element[pin], wire=(colour, 2.5))
        x4 = u.terminal_strip("X4", "DEMO-TB-2.5-TWIN")
        rails = [x4.run(k, _PUMPS, bridged=True) for k in ("L1", "L2", "L3")]
        for rail, pin, colour in zip(rails, ("2", "4", "6"), _PH, strict=True):
            u.series(q1.element[pin], rail[1].inner, wire=(colour, 2.5))
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=not motors_inside)
    mu, mv, mw, mpe = (x3.run(k, _PUMPS) for k in ("U", "V", "W", "PE"))
    for n in range(1, _PUMPS + 1):
        with u.function(f"P{n}", f"Pump {n}"):
            ct, ov = u.device(f"Q{n}1", "DEMO-CTR-3P-24"), u.device(f"B{n}2", "DEMO-OVERLOAD-3P")
            for i in range(3):
                u.series(rails[i][n].inner, ct.main[str(2 * i + 1)], wire=(_PH[i], 1.5))
                u.series(ct.main[str(2 * i + 2)], ov.main[str(2 * i + 1)], wire=(_PH[i], 1.5))
                u.series(ov.main[str(2 * i + 2)], (mu, mv, mw)[i][n].inner, wire=(_PH[i], 1.5))
            u.series(pe[n].inner, mpe[n].inner, wire=(GNYE, 1.5))
    u.earth(pe_in[1], pe[1], *(mpe[n] for n in range(1, _PUMPS + 1)))
    if motors_inside:
        _motors(u, (mu, mv, mw, mpe))
    return _Io(l1, l2, l3, pe_in, mu, mv, mw, mpe)


def _motors(u: Any, runs: tuple[fr.Run, ...]) -> None:
    """The five motors and their cables, authored inside the unit."""
    for n in range(1, _PUMPS + 1):
        with u.function(f"P{n}", f"Pump {n}"):
            m, cable = u.device(f"M{n}", "DEMO-MOTOR-4KW"), u.cable(f"W{n}1", "DEMO-CBL-4G1.5", length_m=15)
            for core, (run, pin) in enumerate(zip(runs, ("U", "V", "W", "PE"), strict=True), start=1):
                cable.core(core, run[n], m.motor[pin])


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet")
def _cabinet(u: Any) -> _Io:
    return _fan(u, motors_inside=False)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet")
def _cabinet_in(u: Any) -> _Io:
    return _fan(u, motors_inside=True)


def _built(tmp_path: Path, *, motors_inside: bool = False) -> Any:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cabinet_in if motors_inside else _cabinet, "U1", place=None)
    with d.function("SUP", "Supply"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
        for core, (outside, inside) in enumerate(zip((x0.run(k, 1) for k in ("L1", "L2", "L3", "PE")), cab[:4], strict=True), start=1):
            w1.core(core, outside[1], inside[1])
    for n in range(1, _PUMPS + 1) if not motors_inside else ():
        with d.function(f"P{n}", f"Pump {n}"):
            m, cable = d.device(f"M{n}", "DEMO-MOTOR-4KW"), d.cable(f"W{n}1", "DEMO-CBL-4G1.5", length_m=15)
            for core, (run, pin) in enumerate(zip(cab[4:], ("U", "V", "W", "PE"), strict=True), start=1):
                cable.core(core, run[n], m.motor[pin])
    cover = tmp_path / "cover.md"
    cover.write_text("# Fan\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_no_net_of_a_cut_fan_draws_as_three_pieces(tmp_path: Path) -> None:
    """KI-412: the fan's phases each stay one net on the drawing, whatever page the cut falls on."""
    findings = _built(tmp_path).findings
    assert not [f.message for f in findings if f.severity.name == "ERROR"], "the drawing must be made for the check to mean anything"
    assert not [f.message for f in findings if f.code in ("CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END")]


def test_motors_inside_the_unit_draw_without_an_error(tmp_path: Path) -> None:
    """KI-918, KI-919: the same fan with the motors authored inside the unit draws with no SHORT, no wire-meets-net, no JUNCTION ERROR."""
    errors = [f"{f.code}: {f.message}" for f in _built(tmp_path, motors_inside=True).findings if f.severity.name == "ERROR"]
    assert not errors
