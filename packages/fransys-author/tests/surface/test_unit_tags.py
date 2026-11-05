"""`d.add` takes a bare tag; `name=` sets the key the instance is held to."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, Device, design, unit
from series_parts import pair_library

from fransys_model.vocab import Unit


class _One(NamedTuple):
    X1: Device


def _board():
    @unit(
        "demo-tag-board",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AA",
    )
    def board(d: Design) -> _One:
        return _One(d.device("X1", "DEMO-CONN-2P", interface=True))

    return board


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def test_a_given_tag_is_the_unit_tag_and_the_key() -> None:
    d = design(pair_library())
    d.add(_board(), "U3")
    (record,) = _records(d, Unit)
    assert record.tag == "U3"
    assert record.key == ("U3", "unit")


def test_name_keys_a_tagged_instance() -> None:
    d = design(pair_library())
    d.add(_board(), "U1", name="io1")
    (record,) = _records(d, Unit)
    assert record.tag == "U1"
    assert record.key == ("io1", "unit")


@pytest.mark.parametrize("tag", ["io1", "cab", "a2"])
def test_a_lowercase_tag_raises_and_names_the_tag_fix(tag: str) -> None:
    with pytest.raises(AuthorError, match="lowercase") as raised:
        design(pair_library()).add(_board(), tag)
    assert f"d.add(defn, {tag.upper()!r})" in str(raised.value)


def test_a_tag_twice_in_one_function_raises_but_in_two_functions_is_kept() -> None:
    d = design(pair_library())
    with d.function("F1", "First"):
        d.add(_board(), "U1")
        with pytest.raises(AuthorError, match="already used"):
            d.add(_board(), "U1")
    with d.function("F2", "Second"):
        d.add(_board(), "U1")
    assert [r.tag for r in _records(d, Unit)] == ["U1", "U1"]
