"""Field case: a series with a pin in the middle, and a series between pins of two child units.
The bug: a pin stood only at the ends of a series and the width of bare pins was refused, so each such wire needed a `d.detail.wire`.
Fixed by API-WIRE (API-022 W2), a pin stands anywhere in a series; a hop across units is an ordinary series (R1498)."""

from typing import Any, NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK
from fransys_reports import wires_csv

from fransys_model.vocab.tables import conductors


class _Io(NamedTuple):
    strip: Any


@fr.unit("demo-sub", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _sub(u: fr.Design) -> _Io:
    strip = u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.series(strip[1].inner, lamp["1"], wire=(BK, 0.75))
    u.series(lamp["2"], strip[2].inner, wire=(BK, 0.75))
    return _Io(strip)


def _ends(result: fr.BuildResult) -> set[frozenset[tuple[str, ...]]]:
    model = result.model
    return {frozenset(tuple(model.key_of(p) or ()) for p in (c.a, c.b)) for c in conductors(model).values()}


def test_a_pin_in_the_middle_builds_with_every_connection_drawn() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    f1, h1 = d.device("F1", "DEMO-MCB-C6"), d.device("H1", "DEMO-LAMP-24")
    d.series(x1[1].outer, f1.element["1"], h1["1"], wire=(BK, 1.5))
    d.series(f1.element["2"], h1["2"], wire=(BK, 1.5))
    d.series(x1[2].outer, h1["2"], wire=(BK, 1.5))
    result = fr.build(d)
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in result.findings}
    assert len(_ends(result)) == 4


def test_a_series_across_two_child_units_builds_with_every_connection_drawn() -> None:
    d = fr.design("demo_parts")
    a, b = d.add(_sub, "U1"), d.add(_sub, "U2")
    d.series(a.strip[1].outer, b.strip[1].outer, wire=(BK, 0.75))
    d.series(a.strip[2].outer, b.strip[2].outer, wire=(BK, 0.75))
    result = fr.build(d)
    expect_codes(result, "ITEM_WITHOUT_PART")
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in result.findings}
    outer = {(unit, n) for e in _ends(result) for k in e for unit, n in [(k[0], k[3])] if k[-1] == "external"}
    assert outer == {("U1", "1"), ("U2", "1"), ("U1", "2"), ("U2", "2")}
    assert len([e for e in _ends(result) if all(k[-1] == "external" for k in e)]) == 2
    listed = wires_csv(result.model).splitlines()
    assert [row.rsplit(",", 1)[0] for row in listed if "-U1-X1:" in row and "-U2-X1:" in row] == [
        "-U1-X1:1,-U2-X1:1,BK,0.75",
        "-U1-X1:2,-U2-X1:2,BK,0.75",
    ]
    own = [len(wires_csv(result.model, unit=unit).splitlines()) for unit in result.model.tables["unit"]]
    assert own == [3, 3]  # the header and the unit's own lamp wires: the cross-unit wire is the root's
    for unit in result.model.tables["unit"]:
        assert not [row for row in wires_csv(result.model, unit=unit).splitlines() if "-U1-X1:" in row and "-U2-X1:" in row]
