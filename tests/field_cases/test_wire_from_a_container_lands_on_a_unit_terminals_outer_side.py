"""Field case: a container wires a nested unit's boundary terminal with d.wire, on the terminal's outer side.
The bug: d.wire took a terminal's inner side wherever it was called, so the series reused a boundary terminal that looked free.
Fixed by the amendment of author-0023: an explicit boundary terminal of a nested unit, seen from a container, is its outer side."""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

_TB, _PE = "DEMO-TB-2.5", "DEMO-TB-PE-2.5"


class _Io(NamedTuple):
    x1: fr.TerminalStrip
    pe: fr.Run


def _make_unit(*, wire_inside: bool = False, count: int = 3, unused: tuple[int, ...] = (), pe_unused: bool = False):
    """`unused` numbers and the PE run (`pe_unused`) are declared unused on the strip itself."""

    @fr.unit("demo-strip", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def unit(d: fr.Design) -> _Io:
        x1 = d.terminal_strip("X1", _TB, count, pe=_PE, interface=tuple(range(1, count + 1)), unused=unused)
        pe = x1.run("PE", 1, interface=not pe_unused, unused=pe_unused)
        if wire_inside:
            d.series(x1[1].inner, d.device("M9", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
        return _Io(x1, pe)

    return unit


def _sides(result: fr.BuildResult, terminal: str) -> list[str]:
    """The side ('internal' or 'external') of each conductor end on U1's terminal `terminal`."""
    model = result.model
    conductors: list[Any] = list(model.tables.get("conductor", {}).values())
    keys: list[tuple[str, ...]] = [model.key_of(p) or () for c in conductors for p in (c.a, c.b)]
    return sorted(k[-1] for k in keys if k[:4] == ("U1", "X1", "terminal", terminal))


def _unit_alone() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.add(_make_unit(), "U1")
    return fr.build(d)


def test_wire_from_a_container_lands_on_the_outer_side() -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_make_unit(unused=(2, 3), pe_unused=True), "U1")
    d.series(s.x1[1].outer, d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    result = fr.build(d)
    assert _sides(result, "1") == ["external"]
    assert _sides(_unit_alone(), "1") == []


def test_a_later_series_skips_the_terminal_wired_from_the_container() -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_make_unit(count=4), "U1")
    d.series(s.x1[1].outer, d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    d.series(
        s.x1,
        d.cable("W1", "DEMO-CBL-4G1.5"),
        d.device("M2", "DEMO-MOTOR-4KW").motor,
        wire=(BK, 2.5),
    )
    result = fr.build(d)
    assert _sides(result, "1") == ["external"]
    assert _sides(result, "2") == ["external"]
    assert _sides(result, "3") == ["external"]
    assert _sides(result, "4") == ["external"]


def test_inside_the_unit_body_an_explicit_terminal_lands_on_the_inner_side() -> None:
    d = fr.design("demo_parts", place="C1")
    d.add(_make_unit(wire_inside=True), "U1")
    assert _sides(fr.build(d), "1") == ["internal"]


def _net_sides(result: fr.BuildResult, name: str) -> list[str]:
    """The side of each U1 X1 terminal port that net `name` holds."""
    model = result.model
    every: list[Any] = list(model.tables["net"].values())
    nets = [n for n in every if n.name == name]
    keys: list[tuple[str, ...]] = [model.key_of(p) or () for n in nets for p in n.ports]
    return sorted(k[7] for k in keys if k[:3] == ("U1", "X1", "terminal"))


def test_supply_from_a_container_lands_on_the_outer_side() -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_make_unit(), "U1")
    d.ac_supply("S", 230, s.x1[1])
    assert _net_sides(fr.build(d), "L1") == ["external"]
