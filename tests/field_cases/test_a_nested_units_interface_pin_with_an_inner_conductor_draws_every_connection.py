"""Field cases: an interface pin with an inner conductor leaves no connection undrawn and no wire end dangling at any salt.
1(d), KI-692: a detector's supply 2 joins its signal 6 inside the unit while the carrier cables supply 1, 2 and signal 7.
1(c), KI-693: a transformer secondary is cabled to the line pins of a nested unit's breaker that another breaker also takes."""

from collections import Counter
from contextlib import nullcontext
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import _COVER, unit_document
from fransys.colours import BK

from fransys_model.kernel import id_namespace

_TB = "DEMO-TB-2.5"


class _Io(NamedTuple):
    b: Any


class _Open(NamedTuple):
    pass


class _CabIo(NamedTuple):
    F1: Any
    X1: Any


@fr.unit("demo-detector", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _detector(d: Any) -> _Io:
    with d.function("DET", "Detector"):
        b = d.device("B1", "DEMO-GAS-DETECTOR", interface=True)
        d.series(b.supply[2], b.signal[6], wire=(BK, 0.75))
    return _Io(b)


@fr.unit("demo-trafo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cabinet(d: Any) -> _CabIo:
    with d.function("CAB", "Cabinet"):
        x1 = d.terminal_strip("X1", _TB, 4, description="Mains", interface=(1, 2))
        x2 = d.terminal_strip("X2", _TB, 4, description="Load")
        f1 = d.device("F1", "DEMO-MCB-2P-C2", interface=("main",))
        d.series(f1.main, (x2[1].inner, x2[2].inner), wire=(BK, 1.5))
        f2 = d.device("F2", "DEMO-MCB-2P-C2")
        d.series((f1.main[1], f1.main[3]), f2.main, wire=(BK, 1.5))
        x3 = d.terminal_strip("X3", _TB, 4, description="Load 2")
        d.series(f2.main, (x3[1].inner, x3[2].inner), wire=(BK, 1.5))
    return _CabIo(f1, x1)


@fr.unit("demo-trafo-carrier", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _carrier(d: Any) -> _Open:
    cab = d.add(_cabinet, "CAB")
    with d.function("TR", "Transformer T1"):
        t1 = d.device("T1", "DEMO-TRAFO-400-230")
        w1 = d.cable("W1", "DEMO-CBL-4G1.5")
        w1.core(1, cab.X1[1].inner, t1.primary["1U"])
        w1.core(2, cab.X1[2].inner, t1.primary["1V"])
        w2 = d.cable("W2", "DEMO-CBL-4G1.5")
        w2.core(1, cab.F1.main[1], t1.secondary["2U"])
        w2.core(2, cab.F1.main[3], t1.secondary["2V"])
    return _Open()


def _detector_build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("ROOM", "Equipment room")
    u = d.add(_detector, "U1")
    with d.function("FEED", "Detector feed"):
        a = d.device("A1", None, external=True, place="ROOM", pins=("0", "+", "1"))
        w = d.cable("W1", "DEMO-CBL-4G1.5", external=True)
        d.series((u.b.supply[1], u.b.supply[2], u.b.signal[7]), w, (a["0"], a["+"], a["1"]))
        w.spare()
    docs = (
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=_COVER),
        unit_document("demo-detector"),
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=_COVER),
    )
    return fr.build(d, *docs)


def _transformer_build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_carrier, "U1")
    return fr.build(d, unit_document("demo-trafo-carrier"))


_BUILDS = {"detector": _detector_build, "transformer": _transformer_build}


@pytest.mark.parametrize("salt", ["-", "a", "b", "c", "d", "e"])
@pytest.mark.parametrize("case", ["detector", "transformer"])
def test_an_interface_pin_with_an_inner_conductor_leaves_no_connection_undrawn(case: str, salt: str) -> None:
    with id_namespace(salt) if salt != "-" else nullcontext():
        result = _BUILDS[case]()
    found = Counter(f.code for f in result.findings)
    assert (found["CONNECTION_NOT_DRAWN"], found["DANGLING_WIRE_END"]) == (0, 0)
