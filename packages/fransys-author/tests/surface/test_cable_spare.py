"""`W1.spare` and a one-ended `W1.core` write `OpenCoreFacet`s, and fail by name (CC2, CC4)."""

from typing import TYPE_CHECKING

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._cable import Cable
from fransys_author.surface.colours import BK, BN, BU, SH

from fransys_model.vocab import OpenCoreFacet

from ..equivalence.series_parts import series_library  # noqa: TID252 -- importlib mode puts tests/ on no path

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

FOUR, THREE = "TEST-CBL-4", "TEST-CBL-3"


@pytest.fixture(scope="module")
def lib() -> Draft:
    return series_library()


def _open(d: Design) -> dict[int, object]:
    return {r.index: r.at for r in d.draft().records() if isinstance(r, OpenCoreFacet)}


def _screened(d: Design) -> Cable:
    """A three-core cable whose third core is an `SH` screen (the stub parts hold none)."""
    engine = d._engine.cable(THREE, name="W9", tag="W9")
    engine._core_colours = (BN, BU, SH)
    return Cable("W9", engine)


def test_spare_by_colour_number_and_all_the_rest(lib: Draft) -> None:
    d = design(lib)
    m1 = d.device("M1", "TEST-MOTOR-3P")
    w1 = d.cable("W1", FOUR)
    w1.core(BN, m1.load["U"], m1.load["V"])
    w1.spare(BU, 3)
    w1.spare()
    assert _open(d) == {2: None, 3: None, 4: None}


def test_spare_at_parks_one_core_on_a_pin(lib: Draft) -> None:
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM")
    w1 = d.cable("W1", THREE)
    w1.spare(BK, at=x1[7])
    assert _open(d) == {3: x1[7].outer.id}


def test_spare_at_takes_exactly_one_core(lib: Draft) -> None:
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(AuthorError, match="takes exactly one core, got 2"):
        d.cable("W1", THREE).spare(BN, BU, at=x1[1])
    with pytest.raises(AuthorError, match="takes exactly one core, got 0"):
        d.cable("W2", THREE).spare(at=x1[1])


def test_core_with_one_end_is_for_a_screen_only(lib: Draft) -> None:
    # MUTATION: `_screen_end` skips the SH check
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(AuthorError, match=r"not SH: park a spare with spare\(\.\.\., at=\)"):
        d.cable("W1", THREE).core(BN, x1[1])
    w9 = _screened(d)
    w9.core(SH, x1[2])
    assert _open(d) == {3: x1[2].outer.id}


def test_spare_at_on_a_screen_names_core(lib: Draft) -> None:
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(AuthorError, match=r"is SH: earth it with core\(which, a\)"):
        _screened(d).spare(SH, at=x1[1])


def test_wired_then_spare_and_marked_twice_raise(lib: Draft) -> None:
    d = design(lib)
    m1 = d.device("M1", "TEST-MOTOR-3P")
    w1 = d.cable("W1", THREE)
    w1.core(BN, m1.load["U"], m1.load["V"])
    with pytest.raises(AuthorError, match="core 1 is already wired or marked spare"):
        w1.spare(BN)
    w1.spare(BU)
    with pytest.raises(AuthorError, match="core 2 is already wired or marked spare"):
        w1.spare(BU)


def test_series_marks_an_unlanded_gnye_core_spare(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, x1 = d.device("Q1", "TEST-MCB-3P"), d.terminal_strip("X1", "TEST-TERM")  # no PE anywhere
    d.series(q1.main, d.cable("W1", FOUR), x1, wire=("BK", 2.5))
    assert 4 in _open(d)
