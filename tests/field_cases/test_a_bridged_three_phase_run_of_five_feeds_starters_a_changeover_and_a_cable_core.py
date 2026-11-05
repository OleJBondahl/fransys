"""Field case: runs L1, L2, L3 of five bridged terminals; terminal 1 takes the supply, 2 to 5 feed three starters and a changeover with a cable core.
The cabinet is nested in a larger unit. The build leaves no marker unplaced and no connection undrawn at any salt (consumer N5a, KI-687)."""

from collections import Counter
from contextlib import nullcontext
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BK

from fransys_model.kernel import id_namespace

_WIRE = (BK, 2.5)
_PHASES = ("L1", "L2", "L3")


class _Open(NamedTuple):
    pass


class _Strip(NamedTuple):
    X9: Any


@fr.unit("demo-enclosure", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _enclosure(u: Any) -> _Strip:
    return _Strip(u.terminal_strip("X9", "DEMO-TB-2.5", 3, interface=(1, 2, 3)))


@fr.unit("demo-feeders", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cabinet(u: Any) -> _Open:
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5")
    runs = [x3.run(p, 5, bridged=True) for p in _PHASES]
    u.ac_supply("400V", 230, *(r[1].outer for r in runs))
    far = u.add(_enclosure, "E2")
    cable = u.cable("W1", "DEMO-CBL-3X0.34", length_m=5)
    for k in (1, 2, 3):
        with u.function(f"P{k}", f"Feeder {k}"):
            f = u.device(f"F{k}", "DEMO-MCB-3P")
            q = u.device(f"Q{k}", "DEMO-CTR-3P-24")
            o = u.device(f"O{k}", "DEMO-OVERLOAD-3P")
            xo = u.terminal_strip(f"XO{k}", "DEMO-TB-2.5", 3)
            u.series(tuple(r[k + 1].outer for r in runs), f.element, q.main, o.main, tuple(xo[j].outer for j in (1, 2, 3)), wire=_WIRE)
    with u.function("C1", "Changeover"):
        co = u.device("Q9", "DEMO-CO-4P-24")
        for i, r in enumerate(runs, start=1):
            u.series(r[5].outer, co.co[f"{i}1"], wire=_WIRE)
    for i in (1, 2, 3):
        cable.core(i, co.co[f"{i}1"], far.X9[i].outer)
    return _Open()


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cabinet, "U1")
    return fr.build(d, unit_document("demo-feeders"))


@pytest.mark.parametrize("salt", ["-", "a", "b", "c", "d", "e"])
def test_a_bridged_three_phase_run_of_five_leaves_no_marker_unplaced_and_no_connection_undrawn(salt: str) -> None:
    with id_namespace(salt) if salt != "-" else nullcontext():
        result = _built()
    found = Counter(f.code for f in result.findings)
    assert (found["MARKER_UNPLACED"], found["CONNECTION_NOT_DRAWN"], found["DANGLING_WIRE_END"]) == (0, 0, 0)
