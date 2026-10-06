"""Field case: a container places two instances of one unit whose boundary is terminals: a tuple
field of four terminals and a run. One instance leaves one terminal open, the other leaves the
whole tuple and the run open.

The bug (v0.8.0): `unused=` on `d.add` took only devices and functions, so a field of
`fr.Terminal`, `fr.Run` or `fr.TerminalStrip` raised "not a device or a function", though the unit
guide lets a unit return those. Fixing decision: author-0021 (amends author-0020).
"""

from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_author import AuthorError

from fransys_model.vocab.tables import functions, items, unused_boundaries

_TB = "DEMO-TB-2.5"
_WIRE = (BU, 0.5)


class _Io(NamedTuple):
    spare: tuple[fr.Terminal, ...]
    feed: fr.Run


class _Bare(NamedTuple):
    feed: fr.Run


@fr.unit("demo-term-board", revision=1, interface_version=1, date="2026-01-01", text="a", by="AB")
def _board(d: fr.Design) -> _Io:
    strip = d.terminal_strip("X1", _TB, interface=True)
    return _Io(tuple(strip[n] for n in range(1, 5)), strip.run("feed", 2))


@fr.unit("demo-quiet-board", revision=1, interface_version=1, date="2026-01-01", text="a", by="AB")
def _quiet(d: fr.Design) -> _Bare:
    return _Bare(d.terminal_strip("X1", _TB).run("feed", 1))


@pytest.fixture(scope="module")
def built() -> tuple[fr.BuildResult, set[tuple[str, ...]]]:
    d = fr.design("demo_parts", place="C1")
    one = d.add(_board, "U1", unused=("spare[1]",))
    d.add(_board, "U2", unused=("spare", "feed"))
    far = d.terminal_strip("X9", _TB, 5)
    for pick, n in ((0, 1), (2, 2), (3, 3)):
        d.wire(one.spare[pick].outer, far[n].inner, wire=_WIRE)
    d.wire(one.feed[1].outer, far[4].inner, wire=_WIRE)
    d.wire(one.feed[2].outer, far[5].inner, wire=_WIRE)
    result = fr.build(d)
    model = result.model
    by_id = {f.id: f for f in functions(model).values()}
    keys = {i.id: i.key for i in items(model).values()}
    named = {tuple(keys[by_id[u.function].item]) for u in unused_boundaries(model).values()}
    return result, named


def test_terminal_fields_build_clean(built: tuple[fr.BuildResult, set[tuple[str, ...]]]) -> None:
    result, _ = built
    assert not [f for f in result.findings if f.severity == fr.Severity.ERROR]


def test_exactly_the_named_terminals_are_unused(
    built: tuple[fr.BuildResult, set[tuple[str, ...]]],
) -> None:
    _, named = built
    two: set[tuple[str, ...]] = {
        ("U2", "X1", "terminal", *rest) for rest in (("1",), ("2",), ("3",), ("4",))
    }
    two |= {("U2", "X1", "terminal", "feed", "1"), ("U2", "X1", "terminal", "feed", "2")}
    assert named == {("U1", "X1", "terminal", "2"), *two}


def test_a_run_without_a_boundary_terminal_raises() -> None:
    d = fr.design("demo_parts", place="C1")
    with pytest.raises(AuthorError, match="no boundary function"):
        d.add(_quiet, "U1", unused=("feed",))


def test_a_function_suffix_on_a_terminal_raises() -> None:
    d = fr.design("demo_parts", place="C1")
    with pytest.raises(AuthorError, match="one function"):
        d.add(_board, "U1", unused=("spare[1].f",))


def test_an_index_on_a_run_says_not_a_tuple() -> None:
    d = fr.design("demo_parts", place="C1")
    with pytest.raises(AuthorError, match=r"not a tuple$"):
        d.add(_board, "U1", unused=("feed[1]",))
