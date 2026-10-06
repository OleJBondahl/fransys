"""`unused=` on `d.add` leaves named boundaries of one placed unit instance open (author-0020)."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, Device, design, unit

from fransys_model.vocab import Boundary, UnusedBoundary

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


class _Io(NamedTuple):
    X1: Device
    X2: Device


@unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
def _board(d: Design) -> _Io:
    return _Io(d.device("X1", "DEMO-CONN-2P", interface=True), d.device("X2", "DEMO-CONN-2P"))


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def _two_instances(names):
    d = design(pair_library(), place="C1")
    return d, d.add(_board, "U1"), d.add(_board, "U2", unused=names)


def test_one_instance_gets_one_unused_boundary() -> None:
    d, io1, io2 = _two_instances(("X1",))
    (unused,) = _records(d, UnusedBoundary)
    assert unused.function == io2.X1._item.functions[0].id
    assert unused.function != io1.X1._item.functions[0].id
    assert len(_records(d, Boundary)) == 2


def test_a_function_name_takes_that_function() -> None:
    d, _, io2 = _two_instances(("X1.x1",))
    (unused,) = _records(d, UnusedBoundary)
    assert unused.function == io2.X1._item.functions[0].id


def test_no_unused_writes_none() -> None:
    d, _, _ = _two_instances(())
    assert not _records(d, UnusedBoundary)


def test_an_unknown_field_raises_listing_the_fields() -> None:
    with pytest.raises(AuthorError, match=r"'Y9'.*fields: X1, X2"):
        _two_instances(("Y9",))


def test_a_non_boundary_field_raises_listing_the_boundary_functions() -> None:
    with pytest.raises(AuthorError, match=r"no boundary function.*U\d?-?X1\.x1|X1\.x1"):
        _two_instances(("X2",))


def test_a_non_boundary_function_name_raises() -> None:
    with pytest.raises(AuthorError, match="no boundary function"):
        _two_instances(("X1.nope",))


def test_a_bare_string_raises() -> None:
    with pytest.raises(AuthorError, match="tuple of names"):
        _two_instances("X1")


class _Row(NamedTuple):
    X: tuple[Device, Device]


@unit("demo-row-board", revision=1, interface_version=1, date="d", text="t", by="XX")
def _row(d: Design) -> _Row:
    return _Row(tuple(d.device(f"X{n}", "DEMO-CONN-2P", interface=True) for n in (1, 2)))


def _row_unused(*names):
    d = design(pair_library(), place="C1")
    return d, d.add(_row, "U1", unused=names)


def test_an_index_leaves_only_that_element_open() -> None:
    d, io = _row_unused("X[1]")
    (unused,) = _records(d, UnusedBoundary)
    assert unused.function == io.X[1]._item.functions[0].id


def test_an_index_with_a_function_and_the_bare_tuple_field() -> None:
    d, io = _row_unused("X[0].x1")
    (unused,) = _records(d, UnusedBoundary)
    assert unused.function == io.X[0]._item.functions[0].id
    assert len(_records(_row_unused("X")[0], UnusedBoundary)) == 2


def test_an_index_past_the_end_raises_naming_the_length() -> None:
    with pytest.raises(AuthorError, match="2 elements"):
        _row_unused("X[2]")


def test_an_index_on_a_plain_device_field_raises() -> None:
    with pytest.raises(AuthorError, match="not a tuple"):
        _two_instances(("X1[0]",))
