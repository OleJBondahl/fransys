"""Field case: `unused=` on a unit that wires a nested unit's boundary inside itself is clean.

The engineering shape: unit `inner` has a boundary connector. Unit `middle` nests `inner`, wires
that connector to a device of its own and hands it up as its own boundary field. The ship places
`middle` and declares the field unused on that instance. Wiring inside the instance never
contradicts the declaration, so no `UNUSED_CONTRADICTED` and no `BOUNDARY_UNCONNECTED` is raised.

The bug (reported on 0.15.0 and 0.15.1): the declaration was checked against `inner` as well,
whose boundary the conductor in `middle` crosses. Fixing decision: model-0210. A conductor the
container adds outside the instance still contradicts the declaration.
"""

from typing import NamedTuple

import fransys as fr

_CONN = "DEMO-CONN-2P"


class _Io(NamedTuple):
    FIELD: fr.Device


@fr.unit("demo-nest-inner", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _inner(d: fr.Design) -> _Io:
    return _Io(d.device("T", _CONN, interface=True))


@fr.unit("demo-nest-middle", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _middle(d: fr.Design) -> _Io:
    io = d.add(_inner, "I")
    d.detail.wire(io.FIELD["1"], d.device("K1", _CONN)["1"], wire=("WH", 0.5))
    return _Io(io.FIELD)


def _codes(d: fr.Design) -> list[str]:
    return [f.code for f in fr.build(d).findings]


def _ship() -> tuple[fr.Design, _Io]:
    d = fr.design("demo_parts", place="C1")
    return d, d.add(_middle, "M", unused=("FIELD",))


def test_wiring_inside_the_instance_does_not_contradict_unused() -> None:
    d, _ = _ship()
    codes = _codes(d)
    assert "UNUSED_CONTRADICTED" not in codes
    assert "BOUNDARY_UNCONNECTED" not in codes


def test_a_conductor_the_container_adds_outside_still_contradicts() -> None:
    d, io = _ship()
    d.detail.wire(io.FIELD["2"], d.device("P1", _CONN)["1"], wire=("WH", 0.5))
    assert "UNUSED_CONTRADICTED" in _codes(d)
