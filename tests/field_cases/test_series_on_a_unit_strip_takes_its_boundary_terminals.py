"""Field case: a container series over a nested unit's interface strip, which must reach its boundary terminals.
The bug: a container added new terminals to the unit, while the unit's own boundary terminals stayed BOUNDARY_UNCONNECTED.
Fixed by author-0023, series and wire reach a unit's boundary terminals, and a container never adds a terminal to a unit."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK
from fransys_author import AuthorError

if TYPE_CHECKING:
    from collections.abc import Callable

_TB, _PE = "DEMO-TB-2.5", "DEMO-TB-PE-2.5"


class _Io(NamedTuple):
    x1: fr.TerminalStrip
    pe: fr.Run | None = None


def _strip_unit(count: int, *, touch: bool = False, unused: tuple[int, ...] = (), pe_unused: bool = False):
    """A strip of `count` boundary terminals; `unused` numbers and the PE run (`pe_unused`) are declared unused on the strip itself."""

    @fr.unit("demo-strip", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def unit(d: fr.Design) -> _Io:
        x1 = d.terminal_strip("X1", _TB, count, pe=_PE, interface=tuple(range(1, count + 1)), unused=unused)
        pe = x1.run("PE", 1, interface=not pe_unused, unused=pe_unused)
        if touch:
            x1[1]  # the unit names its own terminal 1, as a unit does when it wires it inside
        return _Io(x1, pe)

    return unit


def _container(count: int) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(count), "U1")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(s.x1, w1, m1.motor, wire=(BK, 2.5))
    return fr.build(d)


def _landed(result: fr.BuildResult) -> set[tuple[str, ...]]:
    """The unit's terminals that carry a conductor, as their item keys."""
    model = result.model
    conductors: list[Any] = list(model.tables["conductor"].values())
    keys = (model.key_of(p) or () for c in conductors for p in (c.a, c.b))
    return {key[:-4] for key in keys if key[:1] == ("U1",) and "terminal" in key}


def _terminals(result: fr.BuildResult) -> set[tuple[str, ...]]:
    items: list[Any] = list(result.model.tables["item"].values())
    keys = (result.model.key_of(i.id) or () for i in items)
    return {k for k in keys if k[:3] == ("U1", "X1", "terminal")}


def test_series_lands_on_the_free_boundary_terminals() -> None:
    result = _container(3)
    assert len(_terminals(result)) == 4
    assert "BOUNDARY_UNCONNECTED" not in {f.code for f in result.findings}
    assert _landed(result) == {
        ("U1", "X1", "terminal", "1"),
        ("U1", "X1", "terminal", "2"),
        ("U1", "X1", "terminal", "3"),
        ("U1", "X1", "terminal", "PE", "1"),
    }


def test_a_conductor_past_the_free_terminals_names_the_strip_and_the_unit() -> None:
    with pytest.raises(AuthorError, match=r"(?s)X1.*U1|U1.*X1"):
        _container(2)


def test_wire_on_a_unit_strip_takes_its_boundary_terminals() -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(3, pe_unused=True), "U1")
    for tag in ("M1", "M2", "M3"):
        d.series(s.x1, d.device(tag, "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    result = fr.build(d)
    assert len(_terminals(result)) == 4
    assert {k[-1] for k in _landed(result)} == {"1", "2", "3"}
    with pytest.raises(AuthorError, match=r"(?s)X1.*U1"):
        d.series(s.x1, d.device("M4", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))


def test_a_pe_conductor_on_a_unit_without_a_pe_run_raises() -> None:
    @fr.unit("demo-bare", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def bare(d: fr.Design) -> _Io:
        return _Io(d.terminal_strip("X1", _TB, 3, pe=_PE, interface=True))

    d = fr.design("demo_parts", place="C1")
    s = d.add(bare, "U1")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    with pytest.raises(AuthorError, match=r"(?s)X1 of unit U1 has no PE run"):
        d.series(s.x1, w1, m1.motor, wire=(BK, 2.5))


def test_core_on_a_unit_strip_takes_its_boundary_terminal() -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(3, touch=True, unused=(2, 3), pe_unused=True), "U1")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    w1.core(1, s.x1, d.device("M1", "DEMO-MOTOR-4KW")["U"])
    result = fr.build(d)
    assert len(_terminals(result)) == 4
    assert _landed(result) == {("U1", "X1", "terminal", "1")}


def _free_after_wiring(pin_of: Callable[[fr.TerminalStrip], Any]) -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(4), "U1")
    d.series(pin_of(s.x1), d.device("M0", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    d.series(
        s.x1,
        d.cable("W1", "DEMO-CBL-4G1.5"),
        d.device("M1", "DEMO-MOTOR-4KW").motor,
        wire=(BK, 2.5),
    )
    result = fr.build(d)
    assert len(_terminals(result)) == 5
    assert {k[-1] for k in _landed(result)} == {"1", "2", "3", "4"}
    assert ("U1", "X1", "terminal", "PE", "1") in _landed(result)


def test_free_means_the_outside_end_has_no_conductor() -> None:
    _free_after_wiring(lambda x1: x1[1].outer)


def test_an_explicit_outer_side_is_the_same_outside_end() -> None:
    _free_after_wiring(lambda x1: x1[1].outer)


def test_a_fixed_terminal_and_the_whole_strip_in_one_series_do_not_double_take() -> None:
    """The fixed x1[1] is taken: the whole strip behind it lands on 2, never on 1 again."""
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(3, unused=(3,), pe_unused=True), "U1")
    h1, h2, h3 = (d.device(tag, "DEMO-LAMP-24") for tag in ("H1", "H2", "H3"))
    d.series(h1.lamp, s.x1[1], h2.lamp, s.x1, h3.lamp, wire=(BK, 2.5))
    d.series(h1.lamp["1"], h3.lamp["2"], wire=(BK, 2.5))
    assert {k[-1] for k in _landed(fr.build(d))} == {"1", "2"}


def test_a_unit_that_names_its_own_terminal_in_a_series_still_offers_it_to_the_container() -> None:
    """Only a container's fixed terminal is taken; the unit's own x1[1] stays a boundary one."""

    @fr.unit("demo-fixed", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def unit(d: fr.Design) -> _Io:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 3, interface=True)  # the container lands beside the unit's own wire (R1266)
        h0, h9 = (d.device(tag, "DEMO-LAMP-24") for tag in ("H0", "H9"))
        d.series(h0.lamp, x1[1], h9.lamp, wire=(BK, 2.5))
        d.series(h0.lamp["1"], h9.lamp["2"], wire=(BK, 2.5))
        return _Io(x1)

    d = fr.design("demo_parts", place="C1")
    s = d.add(unit, "U1")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(s.x1, d.cable("W1", "DEMO-CBL-4G1.5"), m1.motor, wire=(BK, 2.5))
    assert {k[-1] for k in _landed(fr.build(d))} == {"1", "2", "3"}


def _sides(result: fr.BuildResult) -> set[str]:
    """The side ('internal' or 'external') each terminal port of a conductor stands on."""
    model = result.model
    conductors: list[Any] = list(model.tables["conductor"].values())
    keys: list[tuple[str, ...]] = [model.key_of(p) or () for c in conductors for p in (c.a, c.b)]
    return {key[-1] for key in keys if "terminal" in key}


def test_a_hop_lands_on_the_strip_side_that_faces_the_unit_of_the_other_end() -> None:
    """R1507: a pin outside the unit lands outer; the same series written inside the unit lands inner."""
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(1, pe_unused=True), "U1")
    d.series(s.x1, d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    assert _sides(fr.build(d)) == {"external"}

    @fr.unit("demo-inside", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def inside(u: fr.Design) -> _Io:
        x1 = u.terminal_strip("X1", _TB, 1, interface=True)
        u.series(x1, u.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
        return _Io(x1)

    e = fr.design("demo_parts", place="C1")
    e.add(inside, "U1")
    assert _sides(fr.build(e)) == {"internal"}


def test_a_lone_terminal_hop_lands_on_the_side_that_faces_the_unit_of_the_other_end() -> None:
    """R1507 for a Terminal element (x1[1]): outer from the container, inner from inside the unit."""
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(1, pe_unused=True), "U1")
    d.series(s.x1[1], d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    assert _sides(fr.build(d)) == {"external"}

    @fr.unit("demo-lone", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def lone(u: fr.Design) -> _Io:
        x1 = u.terminal_strip("X1", _TB, 1, interface=True)
        u.series(x1[1], u.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
        return _Io(x1)

    e = fr.design("demo_parts", place="C1")
    e.add(lone, "U1")
    assert _sides(fr.build(e)) == {"internal"}
