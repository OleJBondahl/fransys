"""Field case: a bridged five-terminal PE strip in a nested unit, terminals 4 and 5 on its interface taken by cable cores to two motors.
The build places every terminal copy (consumer 0.22.3 item 3a, KI-691)."""

from contextlib import nullcontext
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import GNYE

from fransys_model.kernel import id_namespace

_PE, _TB, _MOTOR, _CABLE = "DEMO-TB-PE-2.5", "DEMO-TB-2.5", "DEMO-MOTOR-4KW", "DEMO-CBL-4G1.5"


class _Io(NamedTuple):
    pe: Any


@fr.unit("demo-pe-strip", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _strip_unit(d: Any) -> _Io:
    pe = d.terminal_strip("PE", _PE, 5, bridged=True, interface=(4, 5))
    runs = [d.terminal_strip(tag, _TB, 2, pe=_PE).run("PE", 1, interface=False) for tag in ("X1", "X2", "X4")]
    for i, run in enumerate(runs, start=1):
        d.series(run, pe[i].outer, wire=(GNYE, 2.5))
    d.earth(*(run[1] for run in runs))
    return _Io(pe)


@fr.unit("demo-pe-outer", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _outer(d: Any) -> _Io:
    cab = d.add(_strip_unit, "CAB")
    for n, term in ((1, 4), (2, 5)):
        with d.function(f"PM{n}", f"Pump {n}"):
            motor = d.device(f"M{n}", _MOTOR)
            d.cable(f"C{n}", _CABLE).core(GNYE, cab.pe[term].outer, motor.motor.PE)
    return _Io(cab.pe)


def test_a_bridged_pe_strip_whose_interface_terminals_take_cable_cores_finds_a_pose() -> None:
    d = fr.design("demo_parts")
    d.add(_outer, "U1")
    for salt in ("-", "a", "b", "c", "d", "e"):
        with id_namespace(salt) if salt != "-" else nullcontext():
            result = fr.build(d, unit_document("demo-pe-outer"))
        assert [f.message for f in result.findings if f.code == "PLACEMENT_PROBLEM"] == [], salt
