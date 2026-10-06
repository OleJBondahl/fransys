"""WP7 tests: `kernel.merge` (ROADMAP WP7, design/kernel-model.md 5.7)."""

import dataclasses
from itertools import permutations
from typing import Any

import pytest
from freeze_probes import make_facet, make_owner, owner_id

from fransys_model.kernel import (
    Draft,
    Id,
    MergeConflict,
    Model,
    Origin,
    SchemaError,
    freeze,
    merge,
)


def _thing_id(digit: str) -> Id[Any]:
    return Id(kind="thing", value=digit * 32)


def _draft(thing_cls: type, origin: Origin, **names: str) -> Draft:
    """A draft of things: keyword `t1="pump"` is the thing with id digit `1`."""
    draft = Draft()
    for label, name in names.items():
        digit = label.removeprefix("t")
        draft.add(thing_cls(id=_thing_id(digit), key=(digit,), name=name), origin=origin)
    return draft


def test_merge_dedups_identical_records(thing_cls: type, origin: Origin) -> None:
    """The same id with identical content in two drafts deduplicates into one record."""
    an_id = Id(kind="thing", value="1" * 32)
    first = Draft()
    first.add(thing_cls(id=an_id, key=("a",), name="pump"), origin=origin)
    second = Draft()
    second.add(thing_cls(id=an_id, key=("a",), name="pump"), origin=origin)
    merged = merge(first, second)
    assert isinstance(merged, Draft)
    assert [record.id for record in merged.records()] == [an_id]


def test_merge_raises_on_differing_records(thing_cls: type, origin: Origin) -> None:
    """The same id with different content in two drafts is a `MergeConflict`."""
    an_id = Id(kind="thing", value="1" * 32)
    first = Draft()
    first.add(thing_cls(id=an_id, key=("a",), name="pump"), origin=origin)
    second = Draft()
    second.add(thing_cls(id=an_id, key=("a",), name="valve"), origin=origin)
    with pytest.raises(MergeConflict):
        merge(first, second)


def test_merge_is_order_independent(thing_cls: type, origin: Origin) -> None:
    """`merge(a, b)` and `merge(b, a)`, once frozen, give the same digest."""
    thing_a = thing_cls(id=Id(kind="thing", value="a" * 32), key=("a",), name="pump-a")
    thing_b = thing_cls(id=Id(kind="thing", value="b" * 32), key=("b",), name="pump-b")
    first = Draft()
    first.add(thing_a, origin=origin)
    second = Draft()
    second.add(thing_b, origin=origin)
    assert freeze(merge(first, second)).digest == freeze(merge(second, first)).digest


def test_merge_of_any_number_of_parts_in_any_order_gives_one_model(
    thing_cls: type, origin: Origin
) -> None:
    """Every permutation of three overlapping parts freezes to the same model and dump."""
    parts = (
        _draft(thing_cls, origin, t1="a", t2="b"),
        _draft(thing_cls, origin, t2="b", t3="c"),
        _draft(thing_cls, origin, t3="c", t4="d"),
    )
    models = [freeze(merge(*ordering)) for ordering in permutations(parts)]
    assert len({model.digest for model in models}) == 1
    assert all(model == models[0] for model in models)
    assert len(models[0].hashes) == 4


def test_merge_names_both_origins_in_a_conflict(thing_cls: type) -> None:
    """The error says where each of the two clashing records was authored."""
    here, there = Origin(file="a.py", line=1, note=""), Origin(file="b.py", line=7, note="")
    with pytest.raises(MergeConflict) as excinfo:
        merge(_draft(thing_cls, here, t1="pump"), _draft(thing_cls, there, t1="valve"))
    assert excinfo.value.record_id == _thing_id("1")
    assert {excinfo.value.origin_a, excinfo.value.origin_b} == {here, there}


def test_merge_keeps_the_smaller_origin_of_an_identical_record_whatever_the_order(
    thing_cls: type,
) -> None:
    """Which part comes first must not decide where a shared record is said to come from."""
    early, late = Origin(file="a.py", line=1, note=""), Origin(file="b.py", line=9, note="")
    one, two = _draft(thing_cls, early, t1="pump"), _draft(thing_cls, late, t1="pump")
    for parts in ((one, two), (two, one)):
        assert merge(*parts).origin_of(_thing_id("1")) == early


def test_merge_takes_the_records_and_origins_of_a_model(thing_cls: type, origin: Origin) -> None:
    """A frozen `Model` is a part like a draft: its records, with the origins it holds."""
    there = Origin(file="model.py", line=3, note="")
    model = freeze(_draft(thing_cls, there, t1="pump"))
    merged = merge(model, _draft(thing_cls, origin, t2="valve"))
    assert [record.id for record in merged.records()] == [_thing_id("1"), _thing_id("2")]
    assert merged.origin_of(_thing_id("1")) == there
    assert merged.origin_of(_thing_id("2")) == origin


def test_merge_of_a_model_and_a_draft_conflicts_like_two_drafts(
    thing_cls: type, origin: Origin
) -> None:
    """Freezing one side first changes nothing about what counts as a clash."""
    model = freeze(_draft(thing_cls, origin, t1="pump"))
    with pytest.raises(MergeConflict):
        merge(model, _draft(thing_cls, origin, t1="valve"))
    with pytest.raises(MergeConflict):
        merge(_draft(thing_cls, origin, t1="valve"), model)


def test_merge_of_models_freezes_to_the_models_together(thing_cls: type, origin: Origin) -> None:
    """Merging what was frozen and freezing again loses and invents nothing."""
    whole = freeze(_draft(thing_cls, origin, t1="a", t2="b", t3="c"))
    left = freeze(_draft(thing_cls, origin, t1="a", t2="b"))
    right = freeze(_draft(thing_cls, origin, t2="b", t3="c"))
    assert freeze(merge(left, right)) == whole


def test_merge_leaves_its_parts_alone(thing_cls: type, origin: Origin) -> None:
    """The result is a new draft: adding to it does not reach a part."""
    part = _draft(thing_cls, origin, t1="pump")
    merged = merge(part)
    merged.add(thing_cls(id=_thing_id("2"), key=("2",), name="valve"), origin=origin)
    assert [record.id for record in part.records()] == [_thing_id("1")]


def test_merge_of_nothing_is_an_empty_draft() -> None:
    """No parts, no records, no aliases."""
    merged = merge()
    assert merged.records() == ()
    assert merged.alias_map() == {}


def test_merge_unions_the_aliases_of_its_parts(thing_cls: type, origin: Origin) -> None:
    """A rename authored in one part reaches the merged draft, from a draft or a model."""
    old, new, other_old = _thing_id("8"), _thing_id("1"), _thing_id("9")
    first = _draft(thing_cls, origin, t1="pump")
    first.alias(old, new)
    second = _draft(thing_cls, origin, t1="pump")
    second.alias(other_old, new)
    model = freeze(first)
    merged = merge(model, second)
    assert merged.alias_map() == {old: new, other_old: new}
    assert freeze(merged).aliases == {old: new, other_old: new}


def test_merge_refuses_one_retired_id_with_two_replacements(
    thing_cls: type, origin: Origin
) -> None:
    """Nothing wins silently for a rename either: an id cannot be retired in favour of two."""
    old = _thing_id("8")
    first = _draft(thing_cls, origin, t1="a", t2="b")
    first.alias(old, _thing_id("1"))
    second = _draft(thing_cls, origin, t1="a", t2="b")
    second.alias(old, _thing_id("2"))
    with pytest.raises(SchemaError, match="two different ids"):
        merge(first, second)


@pytest.mark.parametrize("part", [None, "a draft", 3, [], (), object()])
def test_merge_refuses_a_part_that_is_neither_a_draft_nor_a_model(part: Any) -> None:
    """A `SchemaError` for the caller's mistake, not an `AttributeError` from deep inside."""
    with pytest.raises(SchemaError, match="Draft or a Model") as excinfo:
        merge(part)
    assert excinfo.value.kind == "merge"


def test_merge_refuses_a_model_that_holds_a_record_without_an_origin(
    thing_cls: type, origin: Origin
) -> None:
    """A part that cannot say where a record came from cannot be merged: nothing is invented."""
    model = freeze(_draft(thing_cls, origin, t1="pump"))
    gap = dataclasses.replace(model, origins=frozendict())
    with pytest.raises(SchemaError, match="no origin") as excinfo:
        merge(gap)
    assert excinfo.value.record_id == _thing_id("1")


def test_merge_of_a_models_closed_alias_with_a_drafts_chain_is_refused(
    thing_cls: type, origin: Origin
) -> None:
    """The documented limit: `x -> y` closed against `x -> w` with `w -> y` clashes on `x`."""
    x, w, y = _thing_id("7"), _thing_id("8"), _thing_id("1")
    chained = _draft(thing_cls, origin, t1="pump")
    chained.alias(x, w)
    chained.alias(w, y)
    closed = freeze(chained)
    assert closed.aliases[x] == y
    with pytest.raises(SchemaError, match="two different ids"):
        merge(closed, chained)


def _origin(file: str, line: int) -> Origin:
    return Origin(file=file, line=line, note="")


def test_merge_reports_the_same_conflict_whatever_order_the_parts_come_in(
    thing_cls: type,
) -> None:
    """A record conflict outranks an alias one and names the same two origins, in any order."""
    first = _draft(thing_cls, _origin("a.py", 1), t1="pump")
    second = _draft(thing_cls, _origin("b.py", 2), t2="valve")
    second.alias(_thing_id("8"), _thing_id("2"))
    third = _draft(thing_cls, _origin("c.py", 3), t1="other")
    third.add(thing_cls(id=_thing_id("3"), key=("3",), name="z"), origin=_origin("c.py", 3))
    third.alias(_thing_id("8"), _thing_id("3"))
    seen = set()
    for parts in permutations((first, second, third)):
        with pytest.raises(MergeConflict) as excinfo:
            merge(*parts)
        error = excinfo.value
        seen.add((error.record_id, frozenset((error.origin_a, error.origin_b))))
    assert seen == {(_thing_id("1"), frozenset((_origin("a.py", 1), _origin("c.py", 3))))}


def test_merge_reports_the_same_alias_clash_whatever_order_the_parts_come_in() -> None:
    """Two clashes of different kinds: the smallest retired id is the one named, every time."""
    thing_old, link_old = _thing_id("8"), Id(kind="link", value="8" * 32)
    parts = []
    for target in (_thing_id("1"), _thing_id("2")):
        part = Draft()
        part.alias(thing_old, target)
        parts.append(part)
    for number in ("1", "2"):
        part = Draft()
        part.alias(link_old, Id(kind="link", value=number * 32))
        parts.append(part)
    kinds = set()
    for ordering in permutations(parts):
        with pytest.raises(SchemaError, match="two different ids") as excinfo:
            merge(*ordering)
        kinds.add(excinfo.value.kind)
    assert kinds == {"link"}


def test_merge_does_not_depend_on_the_order_of_a_models_tables() -> None:
    """A model whose tables are stored in another order clashes on the same record."""
    here = _origin("here.py", 1)
    ours = freeze_probes_model(
        here, make_owner("1", ext=frozendict({"a": 1})), make_owner("2"), make_facet("7", "2")
    )
    theirs = freeze_probes_model(here, make_owner("1"), make_owner("2"), make_facet("7", "1"))
    reversed_tables = dataclasses.replace(
        ours, tables=frozendict(dict(reversed(list(ours.tables.items()))))
    )
    assert list(reversed_tables.tables) != list(ours.tables)
    seen = set()
    for parts in ((reversed_tables, theirs), (theirs, reversed_tables), (ours, theirs)):
        with pytest.raises(MergeConflict) as excinfo:
            merge(*parts)
        seen.add(excinfo.value.record_id)
    assert seen == {owner_id("1")}


def freeze_probes_model(origin: Origin, *records: Any) -> Model:
    """Freeze `records` of the freeze probes into a model."""
    draft = Draft()
    draft.extend(records, origin=origin)
    return freeze(draft)


@pytest.mark.parametrize(
    "origins",
    [
        [("a.py", 5, ""), ("b.py", 1, ""), ("c.py", 9, "")],
        [("x.py", 1, ""), ("x.py", 2, ""), ("x.py", 3, "")],
        [("x.py", 1, "a"), ("x.py", 1, "b"), ("x.py", 1, "c")],
    ],
    ids=["file", "line", "note"],
)
def test_merge_names_the_two_smallest_origins_of_three_clashing_records(
    thing_cls: type, origins: list[tuple[str, int, str]]
) -> None:
    """Three different records under one id: the conflict is between the first two by origin."""
    where = [Origin(file=file, line=line, note=note) for file, line, note in origins]
    parts = [
        _draft(thing_cls, place, t1=name)
        for place, name in zip(where, ("one", "two", "three"), strict=True)
    ]
    seen = set()
    for ordering in permutations(parts):
        with pytest.raises(MergeConflict) as excinfo:
            merge(*ordering)
        seen.add((excinfo.value.origin_a, excinfo.value.origin_b))
    assert seen == {(where[0], where[1])}


def test_merge_refuses_a_model_whose_origin_is_not_an_origin(
    thing_cls: type, origin: Origin
) -> None:
    """Something else stored as an origin is as good as none, and no `AttributeError` follows."""
    model = freeze(_draft(thing_cls, origin, t1="pump"))
    stray = dataclasses.replace(model, origins=frozendict({_thing_id("1"): "nowhere"}))
    with pytest.raises(SchemaError, match="no origin") as excinfo:
        merge(stray)
    assert excinfo.value.record_id == _thing_id("1")
