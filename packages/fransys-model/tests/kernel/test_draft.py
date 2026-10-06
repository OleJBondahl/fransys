"""WP5 tests: `kernel.draft` (ROADMAP WP5, design/kernel-model.md 5.5)."""

from itertools import permutations
from typing import Any

import pytest

from fransys_model.kernel import (
    Draft,
    Id,
    MergeConflict,
    Origin,
    RefError,
    SchemaError,
    describe,
)

_A = Id(kind="thing", value="a" * 32)
_B = Id(kind="thing", value="b" * 32)
_C = Id(kind="thing", value="c" * 32)


def test_add_duplicate_identical_is_noop(thing_cls: type, origin: Origin) -> None:
    """Adding the same id with identical content twice is a no-op, not a conflict."""
    draft = Draft()
    an_id = Id(kind="thing", value="0" * 32)
    thing = thing_cls(id=an_id, key=("a",), name="pump")
    draft.add(thing, origin=origin)
    draft.add(thing, origin=origin)
    assert draft.records() == (thing,)


def test_describe_renders_a_drafts_ids_through_origin_source(
    thing_cls: type, origin: Origin
) -> None:
    """A `Draft` answers `origin_of` and `key_of` like a `Model` (design/kernel-model.md 5.8)."""
    draft = Draft()
    an_id = Id(kind="thing", value="0" * 32)
    draft.add(thing_cls(id=an_id, key=("pumps", "pump1"), name="pump"), origin=origin)
    error = RefError("dangling reference", record_id=an_id, field="a", target=an_id)
    assert "conftest.py:1 (pumps/pump1)" in describe(error, draft)


def test_add_conflicting_raises_with_both_origins(thing_cls: type) -> None:
    """Adding the same id with different content raises `MergeConflict`, naming both origins."""
    draft = Draft()
    an_id = Id(kind="thing", value="0" * 32)
    first_origin = Origin(file="a.py", line=1, note="first")
    second_origin = Origin(file="b.py", line=2, note="second")
    draft.add(thing_cls(id=an_id, key=("a",), name="pump"), origin=first_origin)
    with pytest.raises(MergeConflict) as excinfo:
        draft.add(thing_cls(id=an_id, key=("a",), name="valve"), origin=second_origin)
    assert excinfo.value.origin_a == first_origin
    assert excinfo.value.origin_b == second_origin
    assert excinfo.value.record_id == an_id


def test_a_conflict_leaves_the_draft_as_it_was(thing_cls: Any, origin: Origin) -> None:
    """The conflicting record is not stored: the first one stays."""
    draft = Draft()
    first = thing_cls(id=_A, key=("a",), name="pump")
    draft.add(first, origin=origin)
    with pytest.raises(MergeConflict):
        draft.add(thing_cls(id=_A, key=("a",), name="valve"), origin=origin)
    assert draft.records() == (first,)


def test_an_identical_duplicate_keeps_the_smaller_origin_in_either_order(thing_cls: Any) -> None:
    """The origin kept does not depend on which call came first."""
    thing = thing_cls(id=_A, key=("a",), name="pump")
    early = Origin(file="a.py", line=1, note="x")
    late = Origin(file="b.py", line=9, note="x")
    for order in permutations((early, late)):
        draft = Draft()
        for origin in order:
            draft.add(thing, origin=origin)
        assert draft.origin_of(_A) == early


@pytest.mark.parametrize(
    "not_a_record",
    [object(), "thing", 42],
    ids=["object", "str", "int"],
)
def test_add_refuses_something_that_is_not_a_record(not_a_record: Any, origin: Origin) -> None:
    """Only an instance of a `@record` class can be collected."""
    with pytest.raises(SchemaError, match="is not a @record instance") as excinfo:
        Draft().add(not_a_record, origin=origin)
    assert excinfo.value.kind == type(not_a_record).__qualname__


def test_add_refuses_a_value_instance(label_cls: Any, origin: Origin) -> None:
    """A `@value` has no id, so it cannot be a table entry."""
    with pytest.raises(SchemaError, match="is not a @record instance") as excinfo:
        Draft().add(label_cls(text="x"), origin=origin)
    assert excinfo.value.kind == label_cls.__qualname__


def test_add_refuses_an_id_of_another_kind_than_the_class(thing_cls: Any, origin: Origin) -> None:
    """A `Thing` with a `link` id would land in the wrong table."""
    wrong = Id(kind="link", value="a" * 32)
    with pytest.raises(SchemaError, match="id of its own kind") as excinfo:
        Draft().add(thing_cls(id=wrong, key=("a",), name="pump"), origin=origin)
    assert excinfo.value.kind == thing_cls.__qualname__


def test_add_refuses_an_id_that_is_not_an_id(thing_cls: Any, origin: Origin) -> None:
    """A stray `str` id must not leak an `AttributeError`."""
    with pytest.raises(SchemaError, match="id of its own kind") as excinfo:
        Draft().add(thing_cls(id="not-an-id", key=("a",), name="pump"), origin=origin)
    assert excinfo.value.kind == thing_cls.__qualname__


def test_extend_is_a_loop_over_add_and_is_not_atomic(thing_cls: Any, origin: Origin) -> None:
    """A conflict part-way leaves the records before it in place; a raised draft is discarded."""
    draft = Draft()
    good = thing_cls(id=_A, key=("a",), name="pump")
    draft.add(thing_cls(id=_B, key=("b",), name="one"), origin=origin)
    with pytest.raises(MergeConflict):
        draft.extend([good, thing_cls(id=_B, key=("b",), name="two")], origin=origin)
    assert good in draft.records()


def test_records_are_sorted_by_id_whatever_the_insertion_order(
    thing_cls: Any, origin: Origin
) -> None:
    """Nothing depends on the order records were added in."""
    things = [thing_cls(id=i, key=("k",), name=str(n)) for n, i in enumerate((_C, _A, _B))]
    for order in permutations(things):
        draft = Draft()
        draft.extend(order, origin=origin)
        assert [record.id for record in draft.records()] == [_A, _B, _C]


def test_the_origin_source_lookups_know_only_what_was_added(thing_cls: Any, origin: Origin) -> None:
    """`origin_of` and `key_of` answer for records, and `None` for any other id."""
    draft = Draft()
    draft.add(thing_cls(id=_A, key=("pumps", "p1"), name="pump"), origin=origin)
    assert draft.origin_of(_A) == origin
    assert draft.key_of(_A) == ("pumps", "p1")
    assert draft.origin_of(_B) is None
    assert draft.key_of(_B) is None
    assert dict(draft.origins()) == {_A: origin}


def test_record_of_answers_for_a_present_id_and_none_for_an_absent_one(
    thing_cls: Any, origin: Origin
) -> None:
    """`record_of` (model-0093) returns the stored record, or `None`, like `key_of`."""
    draft = Draft()
    thing = thing_cls(id=_A, key=("pumps", "p1"), name="pump")
    draft.add(thing, origin=origin)
    assert draft.record_of(_A) == thing
    assert draft.record_of(_B) is None


def test_record_of_agrees_with_key_of_for_every_id_of_a_draft(
    thing_cls: Any, origin: Origin
) -> None:
    """For every id a draft holds, `record_of(x).key == key_of(x)` (order acceptance 3)."""
    draft = Draft()
    things = [thing_cls(id=i, key=(f"k{n}",), name=str(n)) for n, i in enumerate((_A, _B, _C))]
    draft.extend(things, origin=origin)
    for record in things:
        found = draft.record_of(record.id)
        assert found is not None
        assert found.key == draft.key_of(record.id)


def test_record_of_does_not_resolve_an_alias(thing_cls: Any, origin: Origin) -> None:
    """R1: no alias resolution, like `key_of` — asking for the retired id still answers
    `None`, even though the record now lives under the id that replaced it."""
    draft = Draft()
    draft.alias(_A, _B)
    draft.add(thing_cls(id=_B, key=("k",), name="new"), origin=origin)
    assert draft.record_of(_A) is None
    assert draft.record_of(_B) is not None


def test_alias_records_the_retirement() -> None:
    """The authored map is exposed as it was given."""
    draft = Draft()
    draft.alias(_A, _B)
    draft.alias(_A, _B)
    draft.alias(_B, _C)
    assert dict(draft.alias_map()) == {_A: _B, _B: _C}


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (_A, _A),
        (_A, Id(kind="link", value="a" * 32)),
    ],
    ids=["same-id", "different-kind"],
)
def test_alias_refuses_a_retirement_that_makes_no_sense(old: Id[Any], new: Id[Any]) -> None:
    """An id retires in favour of a different id of its own kind."""
    with pytest.raises(SchemaError, match="different id of the same kind") as excinfo:
        Draft().alias(old, new)
    assert excinfo.value.kind == old.kind


def test_alias_refuses_two_replacements_for_one_id() -> None:
    """One retired id cannot lead to two different current ids."""
    draft = Draft()
    draft.alias(_A, _B)
    with pytest.raises(SchemaError, match="two different ids"):
        draft.alias(_A, _C)
    assert dict(draft.alias_map()) == {_A: _B}
