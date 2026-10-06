"""Field case: a container places two instances of one unit; on one a boundary connector is
mated, on the other it is open on purpose.

The bug (v0.7.0): `unused=` on `d.device` sits inside the unit body and marks every instance, so
the mated instance gave UNUSED_CONTRADICTED; without it the open instance gave
BOUNDARY_UNCONNECTED (ERROR) and nothing was written. The engine could mark one instance but the
engineer API had no call. Fixing decision: author-0020 (`unused=` on `d.add`).
"""

from typing import NamedTuple

import fransys as fr

_CONN = "DEMO-CONN-2P"


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: fr.Design) -> _Io:
    return _Io(d.device("X1", _CONN, interface=True))


def test_one_instance_left_open_builds_clean() -> None:
    d = fr.design("demo_parts", place="C1")
    io1 = d.add(_board, "U1")
    d.add(_board, "U2", unused=("X1",))
    d.mate(d.device("B1", _CONN), io1.X1)
    findings = fr.build(d).findings
    codes = {f.code for f in findings}
    assert "BOUNDARY_UNCONNECTED" not in codes
    assert "UNUSED_CONTRADICTED" not in codes
    assert not [f for f in findings if f.severity == fr.Severity.ERROR]
