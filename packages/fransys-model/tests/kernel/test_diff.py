"""WP7 tests: `kernel.diff` (ROADMAP WP7, design/kernel-model.md 5.7)."""

from typing import Any

import pytest

from fransys_model.kernel import Draft, Id, ModelDiff, Origin, SchemaError, diff, freeze


def _thing_id(digit: str) -> Id[Any]:
    return Id(kind="thing", value=digit * 32)


def _model(thing_cls: type, origin: Origin, **names: str) -> Any:
    """A model of things: `name` keyword `t1="pump"` is the thing with id digit `1`."""
    draft = Draft()
    for label, name in names.items():
        digit = label.removeprefix("t")
        draft.add(thing_cls(id=_thing_id(digit), key=(digit,), name=name), origin=origin)
    return freeze(draft)


def test_diff_lists_exactly_the_changed_ids(thing_cls: type, origin: Origin) -> None:
    """`diff` lists exactly the ids added, removed and changed between two models."""
    kept_id = Id(kind="thing", value="1" * 32)
    removed_id = Id(kind="thing", value="2" * 32)
    added_id = Id(kind="thing", value="3" * 32)

    before_draft = Draft()
    before_draft.add(thing_cls(id=kept_id, key=("a",), name="pump"), origin=origin)
    before_draft.add(thing_cls(id=removed_id, key=("b",), name="valve"), origin=origin)
    before = freeze(before_draft)

    after_draft = Draft()
    after_draft.add(thing_cls(id=kept_id, key=("a",), name="pump"), origin=origin)
    after_draft.add(thing_cls(id=added_id, key=("c",), name="sensor"), origin=origin)
    after = freeze(after_draft)

    result = diff(before, after)
    assert result.added == (added_id,)
    assert result.removed == (removed_id,)
    assert result.changed == ()


def test_diff_reports_a_record_whose_content_changed(thing_cls: type, origin: Origin) -> None:
    """Same id, different hash: it is `changed`, and neither added nor removed."""
    before = _model(thing_cls, origin, t1="pump", t2="valve")
    after = _model(thing_cls, origin, t1="pump", t2="tank")
    assert diff(before, after) == ModelDiff(added=(), removed=(), changed=(_thing_id("2"),))


def test_diff_of_equal_models_built_separately_is_empty(thing_cls: type, origin: Origin) -> None:
    """The comparison is by content hash, not by object identity."""
    one = _model(thing_cls, origin, t1="pump", t2="valve")
    two = _model(thing_cls, origin, t1="pump", t2="valve")
    assert one is not two
    assert diff(one, two) == ModelDiff(added=(), removed=(), changed=())


def test_diff_ignores_where_a_record_was_authored(thing_cls: type, origin: Origin) -> None:
    """A moved line is not a change to the plant (design/kernel-records.md 5.4)."""
    elsewhere = Origin(file="other.py", line=99, note="moved")
    one = _model(thing_cls, origin, t1="pump")
    two = _model(thing_cls, elsewhere, t1="pump")
    assert diff(one, two) == ModelDiff(added=(), removed=(), changed=())


def test_diff_is_symmetric_with_added_and_removed_swapped(thing_cls: type, origin: Origin) -> None:
    """Reading it backwards turns additions into removals and leaves changes as they are."""
    before = _model(thing_cls, origin, t1="pump", t2="valve")
    after = _model(thing_cls, origin, t2="tank", t3="sensor")
    forward, backward = diff(before, after), diff(after, before)
    assert forward == ModelDiff(
        added=(_thing_id("3"),), removed=(_thing_id("1"),), changed=(_thing_id("2"),)
    )
    assert backward == ModelDiff(
        added=forward.removed, removed=forward.added, changed=forward.changed
    )


def test_diff_lists_ids_in_id_order_whatever_order_the_models_were_built_in(
    thing_cls: type, origin: Origin
) -> None:
    """Each tuple is sorted by `Id`, so a consumer never re-sorts and never sees insertion order."""
    empty = freeze(Draft())
    forward = _model(thing_cls, origin, t1="a", t5="e", t3="c")
    backward = _model(thing_cls, origin, t3="c", t5="e", t1="a")
    expected = (_thing_id("1"), _thing_id("3"), _thing_id("5"))
    assert diff(empty, forward).added == expected
    assert diff(empty, backward).added == expected
    assert diff(forward, empty).removed == expected


def test_diff_spans_kinds(thing_cls: type, link_cls: type, origin: Origin) -> None:
    """A record in another table is found the same way."""
    thing = thing_cls(id=_thing_id("1"), key=("a",), name="pump")
    link = link_cls(id=Id(kind="link", value="1" * 32), key=("l",), a=thing.id, b=thing.id)
    only_thing = Draft()
    only_thing.add(thing, origin=origin)
    both = Draft()
    both.add(thing, origin=origin)
    both.add(link, origin=origin)
    assert diff(freeze(only_thing), freeze(both)).added == (link.id,)


def test_diff_of_a_model_with_itself_is_three_empty_tuples(thing_cls: type, origin: Origin) -> None:
    """Nothing added, removed or changed."""
    model = _model(thing_cls, origin, t1="pump", t2="valve")
    assert diff(model, model) == ModelDiff(added=(), removed=(), changed=())


def test_diff_ignores_aliases(thing_cls: type, origin: Origin) -> None:
    """Aliases are not records: two models that differ only in them have no difference."""
    plain = _model(thing_cls, origin, t1="pump")
    draft = Draft()
    draft.add(thing_cls(id=_thing_id("1"), key=("1",), name="pump"), origin=origin)
    draft.alias(_thing_id("8"), _thing_id("1"))
    renamed = freeze(draft)
    assert renamed.aliases
    assert not plain.aliases
    assert diff(plain, renamed) == ModelDiff(added=(), removed=(), changed=())
    assert diff(renamed, plain) == ModelDiff(added=(), removed=(), changed=())


def test_diff_shows_an_id_retired_between_two_models_as_removed_and_added(
    thing_cls: type, origin: Origin
) -> None:
    """The record moved from one id to another, and the alias that says so is not compared."""
    before = _model(thing_cls, origin, t1="pump")
    draft = Draft()
    draft.add(thing_cls(id=_thing_id("2"), key=("2",), name="pump"), origin=origin)
    draft.alias(_thing_id("1"), _thing_id("2"))
    after = freeze(draft)
    assert diff(before, after) == ModelDiff(
        added=(_thing_id("2"),), removed=(_thing_id("1"),), changed=()
    )


@pytest.mark.parametrize("bad", [None, "model", 3])
def test_diff_refuses_something_that_is_not_a_model(
    bad: Any, thing_cls: type, origin: Origin
) -> None:
    """Either side: a `SchemaError`, not an `AttributeError`."""
    model = _model(thing_cls, origin, t1="pump")
    with pytest.raises(SchemaError, match="two Models") as excinfo:
        diff(bad, model)
    assert excinfo.value.kind == "diff"
    with pytest.raises(SchemaError, match="two Models") as excinfo:
        diff(model, bad)
    assert excinfo.value.kind == "diff"
