"""Field case: `unused=` on a unit that hands a nested unit's interface up is checked at that unit.

The engineering shape: unit `inner` has an interface connector. Unit `middle` nests `inner`, wires
a conductor from that connector to a device of its own, and hands the connector up as its own
interface. The ship nests `middle`, wires nothing on it and declares it unused on the `middle`
instance. That is true at `middle`'s boundary.

The bug (v0.15.0): the declaration was also checked against `inner`, whose boundary the same
function is, and the conductor in `middle` crosses that one, so `UNUSED_CONTRADICTED` fired.
Fixing decision: model-0210 (the declaration is checked at the unit it is declared on).
"""

from typing import NamedTuple

import fransys as fr

_CONN = "DEMO-CONN-2P"


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _inner(d: fr.Design) -> _Io:
    return _Io(d.device("X1", _CONN, interface=True))


@fr.unit("demo-io-pair", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _middle(d: fr.Design) -> _Io:
    io = d.add(_inner, "I")
    d.detail.wire(io.X1["1"], d.device("K1", _CONN)["1"], wire=("WH", 0.5))  # ty: ignore[not-subscriptable] -- a bare Device has no typed pins
    return _Io(io.X1)


def _codes(d: fr.Design) -> list[str]:
    return [f.code for f in fr.build(d).findings]


def _ship(unused: tuple[str, ...] = ()) -> fr.Design:
    """The ship holds a device of its own, so `middle` is not standalone."""
    d = fr.design("demo_parts", place="C1")
    d.device("P1", _CONN)
    d.add(_middle, "M", unused=unused)
    return d


def test_undeclared_outer_boundary_is_unconnected() -> None:
    """A passed-up interface of a non-standalone unit is `middle`'s own open boundary."""
    assert "BOUNDARY_UNCONNECTED" in _codes(_ship())


def test_declared_on_the_outer_unit_is_not_contradicted() -> None:
    codes = _codes(_ship(unused=("X1",)))
    assert "UNUSED_CONTRADICTED" not in codes
    assert "BOUNDARY_UNCONNECTED" not in codes


def test_declared_on_the_unit_that_wires_it_is_still_contradicted() -> None:
    @fr.unit("demo-io-wrap", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def wrap(d: fr.Design) -> _Io:
        io = d.add(_inner, "I", unused=("X1",))
        d.detail.wire(io.X1["1"], d.device("K1", _CONN)["1"], wire=("WH", 0.5))  # ty: ignore[not-subscriptable] -- a bare Device has no typed pins
        return _Io(io.X1)

    d = fr.design("demo_parts", place="C1")
    d.add(wrap, "M")
    assert "UNUSED_CONTRADICTED" in _codes(d)
