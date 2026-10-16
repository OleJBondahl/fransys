"""`unused=` subscripts mirror the field handle's own subscript (author-0062)."""

from typing import Any, NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, Device, design, unit

from fransys_model.checks import check_units
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.kernel import freeze, merge
from fransys_model.vocab import Placement, UnusedBoundary

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


class _Io(NamedTuple):
    X1: tuple[Device, ...]
    X3: Any


@unit("demo-strip-io", revision=1, interface_version=1, date="d", text="t", by="XX")
def _io(d: Design) -> _Io:
    pair = (
        d.device("X1", "DEMO-CONN-2P", interface=True),
        d.device("X2", "DEMO-CONN-2P", interface=True),
    )
    return _Io(pair, d.terminal_strip("X3", "DEMO-TB-2.5", 4, interface=True))


def _build(names: tuple[str, ...]) -> Design:
    d = design(pair_library(), place="C1")
    io = d.add(_io, "U1", unused=names)
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.detail.wire(io.X3[1], lamp.lamp["1"], wire=("BK", 1.5))
    d.detail.wire(io.X3[2], lamp.lamp["2"], wire=("BK", 1.5))
    return d


def _codes(d: Design) -> list[str]:
    model = freeze(merge(pair_library(), d.draft()))
    return [f.code for f in name_findings(model, check_units(model))]


def _unused(d: Design) -> int:
    return sum(isinstance(r, UnusedBoundary) for r in d.draft().records())


def test_a_slice_marks_the_terminals_it_spans() -> None:
    d = _build(("X3[3:5]",))
    assert _unused(d) == 2
    assert "UNUSED_CONTRADICTED" not in _codes(d)


def test_two_indexes_mark_terminals_three_and_four() -> None:
    d = _build(("X3[3]", "X3[4]"))
    assert _unused(d) == 2
    assert "UNUSED_CONTRADICTED" not in _codes(d)


def test_the_bare_strip_still_marks_all_four() -> None:
    d = _build(("X3",))
    assert _unused(d) == 4
    assert _codes(d).count("UNUSED_CONTRADICTED") == 2


def test_a_strip_index_is_from_one() -> None:
    assert "UNUSED_CONTRADICTED" in _codes(_build(("X3[1]",)))


def test_a_strip_index_past_the_count_raises_the_strips_message() -> None:
    with pytest.raises(AuthorError, match="has 4 terminals"):
        _build(("X3[5]",))


def test_a_slice_on_a_tuple_field_raises() -> None:
    with pytest.raises(
        AuthorError, match=r"'X1\[0:2\]'.*slice.*use one index per element, such as X1\[0\]"
    ):
        _build(("X1[0:2]",))


def test_a_suffix_on_a_strip_terminal_raises() -> None:
    with pytest.raises(AuthorError, match="a terminal has one function"):
        _build(("X3[3].f",))


def test_a_tuple_index_stays_zero_based() -> None:
    d = _build(("X1[0]",))
    assert _unused(d) == 1


def test_unused_marks_no_use_and_places_nothing_inside_an_open_block() -> None:
    """Naming terminals 3 and 4 in `unused=` is not wiring them: no used mark, no placement."""
    d = design(pair_library(), place="C1")
    with d.function("F1", "a function block"):
        io = d.add(_io, "U1", unused=("X3[3:5]",))
    strip = io.X3
    assert strip._used == set()
    assert strip._placed == set()
    held = {strip._made[3].id, strip._made[4].id}
    placed = [r for r in d.draft().records() if isinstance(r, Placement) and r.item in held]
    assert placed == []
    assert _unused(d) == 2
