"""Field case: part-less external boxes with named pins, cabled to a unit that exposes a strip, a PE terminal and three detectors, with earth bonds.
The build places every anchored earth symbol (consumer 0.22.3 item 3b, KI-694)."""

from contextlib import nullcontext
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import _COVER
from fransys.colours import GNYE

from fransys_model.kernel import id_namespace

_CABLE, _TB, _PE, _N = "DEMO-CBL-4G1.5", "DEMO-TB-2.5", "DEMO-TB-PE-2.5", 15


class _Io(NamedTuple):
    x7: Any
    pe: Any
    dets: tuple[Any, ...]


@fr.unit("demo-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _box(d: Any) -> _Io:
    dets = tuple(d.device(f"B{n}", "REPRO-DETECTOR", interface=True) for n in (1, 2, 3))
    return _Io(d.terminal_strip("X7", _TB, _N, interface=True), d.terminal_strip("PE", _PE, 1, interface=True), dets)


def _design() -> tuple[Any, Any]:
    d = fr.design("demo_parts", "intake_parts")
    room = d.location("ROOM", "Equipment room")
    d.location("CTRL", "Control room")
    u = d.add(_box, "U1", place="ROOM")
    with d.function("GAS", "Detection"):
        pins = (*(f"T-1:{n}" for n in "123"), *(f"T-3:{n}" for n in range(1, _N + 1)), *(f"T-5 {g}:{p}" for g in "ABC" for p in ("0", "+", "1")))
        a2 = d.device("A2", None, external=True, place="ROOM", pins=pins)
        sup = ("Supply L", "Supply N", "Supply PE", "Loop Out+", "Loop Out-", "Loop In+", "Loop In-", "R1 C", "R1 NO", "R2 C", "R2 NO")
        a3 = d.device("A3", None, external=True, place="ROOM", pins=sup)
        a6 = d.device("A6", None, external=True, place="ROOM", pins=("Q1:2", "Q1:4", "L", "N", "Q2:2", "Q2:4", "PE"))
        a1 = d.device("A1", None, external=True, place="CTRL", pins=("Ch6 +", "Ch6 -", "Ch7 +", "Ch7 -"))
        w1 = d.cable("W1", _CABLE, external=True)
        w1.core(GNYE, a2["T-1:3"], a6["PE"])
        d.series((a2["T-1:1"], a2["T-1:2"]), w1, (a6["L"], a6["N"]))
        d.earth(a2["T-1:3"], a6["PE"])
        w2 = d.cable("W2", _CABLE, external=True)
        d.series((a3["Supply L"], a3["Supply N"], a3["Supply PE"]), w2, (a6["Q2:2"], a6["Q2:4"], a6["PE"]))
        w5 = d.cable("W5", _CABLE, external=True)
        w5.core(GNYE, u.pe[1].outer, a6["PE"])
        w5.spare()
        d.earth(u.pe[1], a6["PE"])
        w27 = d.cable("W27", _CABLE, external=True)
        d.series((a3["R1 C"], a3["R1 NO"], a3["R2 C"]), w27, (a1["Ch6 +"], a1["Ch6 -"], a1["Ch7 +"]))
        w27.spare()
        w25 = d.cable("W25", _CABLE, external=True)
        d.series((u.dets[0].signal[3], u.dets[0].signal[4], u.dets[1].signal[3]), w25, (a3["Loop Out+"], a3["Loop Out-"], a3["Loop In+"]))
        for n, (s, g) in enumerate(zip(u.dets, "ABC", strict=True)):
            w = d.cable(f"W1{n}", _CABLE, external=True)
            d.series((s.supply[1], s.supply[2], s.signal[7]), w, (a2[f"T-5 {g}:0"], a2[f"T-5 {g}:+"], a2[f"T-5 {g}:1"]))
            w.spare()
        for k in range(0, _N, 3):
            w = d.cable(f"W2{k}", _CABLE, external=True)
            d.series(u.x7[k + 1 : k + 4], w, tuple(a2[f"T-3:{n}"] for n in range(k + 1, k + 4)))
    return d, room


def test_a_partless_external_box_with_named_pins_cabled_to_a_unit_finds_a_pose() -> None:
    d, room = _design()
    docs = (
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=_COVER),
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=_COVER),
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-box", cover=_COVER),
    )
    for salt in ("-", "a", "b", "c", "d", "e"):
        with id_namespace(salt) if salt != "-" else nullcontext():
            result = fr.build(d, *docs)
        assert [f.message for f in result.findings if f.code == "PLACEMENT_PROBLEM"] == [], salt
