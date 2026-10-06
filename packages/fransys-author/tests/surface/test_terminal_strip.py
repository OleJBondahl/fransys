"""EA9 core: `terminal_strip` and `X1[3]`, explicit numbers only."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import TerminalStrip, TypedDevice, design, unit

from fransys_model.vocab import Boundary, Placement, TerminalFacet, UnusedBoundary
from fransys_model.vocab import Item as ModelItem
lazy from fransys_model.kernel import Draft

from ..equivalence.series_parts import pair_library, series_library  # noqa: TID252 -- importlib mode puts tests/ on no path


@pytest.fixture(scope="module")
def lib() -> Draft:
    return series_library()


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def test_a_strip_is_an_item_with_its_description_and_terminals_by_number(parts: Draft) -> None:
    d = design(parts, place="C1")
    x1 = d.terminal_strip("X1", "TEST-TB", description="Field terminals")
    assert isinstance(x1, TerminalStrip)
    t3 = x1[3]
    assert x1[3] is t3
    strip = next(i for i in _records(d, ModelItem) if i.tag == "X1")
    assert strip.description == "Field terminals"
    (facet,) = _records(d, TerminalFacet)
    assert (facet.index, facet.group) == (3, "")


def test_count_makes_the_terminals_and_bounds_the_numbers(parts: Draft) -> None:
    d = design(parts)
    x1 = d.terminal_strip("X1", "TEST-TB", 4)
    assert sorted(f.index for f in _records(d, TerminalFacet)) == [1, 2, 3, 4]
    assert x1[4] is x1[4]
    with pytest.raises(AuthorError, match="X1 has 4 terminals; 5 is past the last"):
        x1[5]


@pytest.mark.parametrize("bad", [0, -1, "3", 2.0, True])
def test_a_terminal_number_is_an_integer_from_one(parts: Draft, bad: object) -> None:
    x1 = design(parts).terminal_strip("X1", "TEST-TB")
    with pytest.raises(AuthorError, match=r"a terminal number is an integer from 1"):
        x1[bad]  # ty: ignore[invalid-argument-type] -- the bad number is the test


def test_a_prefixed_tag_and_a_second_strip_with_one_tag_raise(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(AuthorError, match=r"write X1; terminal_strip\(\) adds the -"):
        d.terminal_strip("-X1", "TEST-TB")
    d.terminal_strip("X1", "TEST-TB")
    with d.function("P1", "a"), pytest.raises(AuthorError, match="tag 'X1' is already used;"):
        d.terminal_strip("X1", "TEST-TB")


def test_a_part_class_and_an_unknown_terminal_part(parts: Draft) -> None:
    class Tb(TypedDevice):
        mpn = "TEST-TB"

    d = design(parts)
    assert d.terminal_strip("X1", Tb)[1] is not None
    with pytest.raises(AuthorError, match="TEST-TB-X"):
        d.terminal_strip("X2", "TEST-TB-X")[1]


def test_place_defaults_and_none(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.terminal_strip("X1", "TEST-TB")
    d.terminal_strip("X2", "TEST-TB", place=None)
    items = {i.tag: i.id for i in _records(d, ModelItem)}
    placed = {p.item for p in _records(d, Placement)}
    assert items["X1"] in placed
    assert items["X2"] not in placed


def _groups_of(d, terminal) -> list:
    """The ids of the places and functions `terminal` is placed at."""
    return [p.node for p in _records(d, Placement) if p.item == terminal.id]


def test_a_terminal_joins_the_function_block_it_is_first_taken_in(parts: Draft) -> None:
    d = design(parts)
    x1 = d.terminal_strip("X1", "TEST-TB")
    with d.function("P1", "first") as p1:
        t1 = x1[1]
    with d.function("P2", "second") as p2:
        assert x1[1] is t1
        t2 = x1[2]
    assert _groups_of(d, t1) == [p1.id]
    assert _groups_of(d, t2) == [p2.id]


def test_a_counted_strips_terminal_joins_the_block_that_first_takes_it(parts: Draft) -> None:
    d = design(parts)
    x1 = d.terminal_strip("X1", "TEST-TB", 2)
    with d.function("P1", "first") as p1:
        t2 = x1[2]
    assert _groups_of(d, t2) == [p1.id]
    assert _groups_of(d, x1[1]) == []  # never taken in a block: the strip's group


def test_a_terminal_taken_outside_any_block_keeps_the_strips_group(parts: Draft) -> None:
    d = design(parts)
    x1 = d.terminal_strip("X1", "TEST-TB")
    t1 = x1[1]
    with d.function("P1", "first"):
        assert x1[1] is t1
    assert _groups_of(d, t1) == []


def test_a_series_takes_its_terminals_in_the_open_block(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM")
    with d.function("P1", "first") as p1:
        d.series(q1.main, x1, k1, wire=("BK", 2.5))
    assert _groups_of(d, x1[1]) == [p1.id]


def test_a_run_counts_in_its_block_too(parts: Draft) -> None:
    d = design(parts)
    with d.function("P1", "first") as p1:
        run = d.terminal_strip("X1", "TEST-TB").run("L", 2, bridged=True)
    assert _groups_of(d, run[1]) == [p1.id]


def test_a_terminal_has_no_group_keyword(parts: Draft) -> None:
    x1 = design(parts).terminal_strip("X1", "TEST-TB")
    with pytest.raises(TypeError, match="group"):
        x1._terminal(1, group="P1")  # ty: ignore[unknown-argument] -- the removed keyword is the test
    with pytest.raises(TypeError, match="group"):
        design(parts).terminal_strip("X2", "TEST-TB", group="P1")  # ty: ignore[unknown-argument] -- the removed keyword is the test


class _Strip(NamedTuple):
    X1: TerminalStrip


def _boundary_strip(**marks):
    @unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
    def board(d):
        return _Strip(d.terminal_strip("X1", "DEMO-TB-2.5", 2, **marks))

    d = design(pair_library(), place="C1")
    d.add(board, "IO")
    return d


def test_interface_marks_every_counted_terminal_a_boundary() -> None:
    d = _boundary_strip(interface=True)
    assert len(_records(d, Boundary)) == 2
    assert not _records(d, UnusedBoundary)


def test_unused_alone_makes_each_terminal_a_boundary_and_unused() -> None:
    d = _boundary_strip(unused=True)
    assert len(_records(d, Boundary)) == 2
    assert len(_records(d, UnusedBoundary)) == 2


def test_a_strip_with_no_mark_writes_no_boundary() -> None:
    d = _boundary_strip()
    assert not _records(d, Boundary)


def test_interface_outside_a_unit_raises_the_engines_error(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="needs a unit"):
        design(parts).terminal_strip("X1", "TEST-TB", 2, interface=True)
