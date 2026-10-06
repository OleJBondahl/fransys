"""Field case: a container wires a unit's interface strip with `d.series`.

The shape: a unit hands back an interface strip X1 of three terminals plus a PE run; the top
design wires a cable and a motor to it in one `d.series(s.x1, w1, m1.motor, ...)`.

The bug (v0.9.0): the series took the strip's next free terminals as a plain strip does, and a
container added new terminals to the unit (X1:4-6, or a refusal past the count) while the unit's
own X1:1-3 stayed BOUNDARY_UNCONNECTED. The owner ruled on 2026-09-23 that a nested unit is
boundary-only on its parent. Fixing decision: author-0023 (series and wire reach a unit's
boundary terminals; a container never adds a terminal to a unit).
"""

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


def _strip_unit(count: int, *, touch: bool = False):
    @fr.unit("demo-strip", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
    def unit(d: fr.Design) -> _Io:
        x1 = d.terminal_strip("X1", _TB, count, pe=_PE, interface=True)
        x1.run("PE", 1)
        if touch:
            x1[1]  # the unit names its own terminal 1, as a unit does when it wires it inside
        return _Io(x1)

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
    s = d.add(_strip_unit(3), "U1")
    for tag in ("M1", "M2", "M3"):
        d.wire(s.x1, d.device(tag, "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    result = fr.build(d)
    assert len(_terminals(result)) == 4
    assert {k[-1] for k in _landed(result)} == {"1", "2", "3"}
    with pytest.raises(AuthorError, match=r"(?s)X1.*U1"):
        d.wire(s.x1, d.device("M4", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))


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
    s = d.add(_strip_unit(3, touch=True), "U1")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    w1.core(1, s.x1, d.device("M1", "DEMO-MOTOR-4KW")["U"])
    result = fr.build(d)
    assert len(_terminals(result)) == 4
    assert _landed(result) == {("U1", "X1", "terminal", "1")}


def _free_after_wiring(pin_of: Callable[[fr.TerminalStrip], Any]) -> None:
    d = fr.design("demo_parts", place="C1")
    s = d.add(_strip_unit(4), "U1")
    d.wire(pin_of(s.x1), d.device("M0", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
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
    _free_after_wiring(lambda x1: x1[1])


def test_an_explicit_outer_side_is_the_same_outside_end() -> None:
    _free_after_wiring(lambda x1: x1[1].outer)
