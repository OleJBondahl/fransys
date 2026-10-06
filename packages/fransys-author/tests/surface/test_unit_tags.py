"""UT1, UT3, UT5: `d.add` takes a bare tag or `None` with `name=`; `class_code` is kept."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, Device, design, unit

from fransys_model.vocab import Unit, UnitRelease

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


class _One(NamedTuple):
    X1: Device


def _board(class_code: str | None = None):
    @unit(
        "demo-tag-board",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AA",
        class_code=class_code,
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


def test_a_floating_instance_has_no_tag_and_a_key_from_name() -> None:
    d = design(pair_library())
    d.add(_board("U"), None, name="io1")
    (record,) = _records(d, Unit)
    assert record.tag is None
    assert record.key == ("io1", "unit")


def test_class_code_reaches_the_release() -> None:
    d = design(pair_library())
    d.add(_board("U"), None, name="io1")
    (release,) = _records(d, UnitRelease)
    assert release.class_code == "U"


def test_no_class_code_leaves_the_release_blank() -> None:
    d = design(pair_library())
    d.add(_board(), "U1")
    (release,) = _records(d, UnitRelease)
    assert release.class_code == ""


@pytest.mark.parametrize("code", ["u", "UUUU", "U1", "-"])
def test_a_class_code_not_one_to_three_capitals_raises(code: str) -> None:
    with pytest.raises(AuthorError, match="class_code"):
        _board(code)


@pytest.mark.parametrize("tag", ["io1", "cab", "a2"])
def test_a_lowercase_tag_raises_with_both_forms(tag: str) -> None:
    with pytest.raises(AuthorError, match="lowercase") as raised:
        design(pair_library()).add(_board("U"), tag)
    assert f"d.add(defn, {tag.upper()!r})" in str(raised.value)
    assert f"d.add(defn, None, name={tag!r})" in str(raised.value)


def test_a_floating_instance_without_a_name_raises() -> None:
    with pytest.raises(AuthorError, match=r"name="):
        design(pair_library()).add(_board("U"), None)


def test_a_floating_instance_of_a_release_without_a_class_code_names_both_fixes() -> None:
    with pytest.raises(AuthorError, match=r"(?s)class_code=.*write the tag"):
        design(pair_library()).add(_board(), None, name="io1")


def test_a_tag_twice_in_one_function_raises_but_in_two_functions_is_kept() -> None:
    d = design(pair_library())
    with d.function("F1", "First"):
        d.add(_board(), "U1")
        with pytest.raises(AuthorError, match="already used"):
            d.add(_board(), "U1")
    with d.function("F2", "Second"):
        d.add(_board(), "U1")
    assert [r.tag for r in _records(d, Unit)] == ["U1", "U1"]
