"""Field case: a series of fixed terminals takes its width from its first fixed count.

The engineering shape: a field wire from terminal X1:4 to terminal X2:4, or the terminals 1 and 2
of one strip to the terminals 1 and 2 of another, with no device between them.

The bug: a series whose elements are all fixed terminals named no width ("name a supply, a rail or
a function with poles to set the width"), a single terminal and a two-terminal slice alike.

Decision author-0055 (API-FRICTION-2 C2): the width is the first fixed element's terminal count, as
SERIES-N rules; a single terminal is one pole and no keyword is added. A function with poles still
sets the width when the series holds one.
"""

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_author import AuthorError


def _ends(d: fr.Design) -> set[frozenset]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def _strips() -> tuple[fr.Design, fr.TerminalStrip, fr.TerminalStrip]:
    d = fr.design("demo_parts")
    return d, d.terminal_strip("X1", "DEMO-TB-2.5", 4), d.terminal_strip("X2", "DEMO-TB-2.5", 4)


def test_one_terminal_to_one_terminal_is_one_pole() -> None:
    d, x1, x2 = _strips()
    d.series(x1[4], x2[4], wire=(BU, 1.5))
    assert _ends(d) == {frozenset(("-X1:4", "-X2:4"))}


def test_a_slice_of_two_to_a_slice_of_two_is_two_poles() -> None:
    d, x1, x2 = _strips()
    d.series(x1[1:3], x2[1:3], wire=(BU, 1.5))
    assert _ends(d) == {frozenset(("-X1:1", "-X2:1")), frozenset(("-X1:2", "-X2:2"))}


def test_a_tuple_of_two_to_a_slice_of_two_is_two_poles() -> None:
    d, x1, x2 = _strips()
    d.series((x1[1], x1[3]), x2[1:3], wire=(BU, 1.5))
    assert _ends(d) == {frozenset(("-X1:1", "-X2:1")), frozenset(("-X1:3", "-X2:2"))}


def test_unequal_fixed_counts_still_name_both_ends() -> None:
    d, x1, x2 = _strips()
    with pytest.raises(AuthorError, match=r"2 poles.*1 pole"):
        d.series(x1[1:3], x2[4], wire=(BU, 1.5))


def test_a_series_with_nothing_fixed_still_names_the_fix() -> None:
    d = fr.design("demo_parts")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    with pytest.raises(AuthorError, match=r"name a supply, a rail or a function with poles"):
        d.series(w1, x1, wire=(BU, 1.5))
