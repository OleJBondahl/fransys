"""WP5 tests: `kernel.freeze` (ROADMAP WP5, design/kernel-model.md 5.5). Aliases are in
test_freeze_aliases."""

import types
from typing import Any

import pytest
from freeze_probes import (
    Holds,
    Single,
    draft_of,
    errors_of,
    holder_id,
    make_facet,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_model.kernel import (
    SCHEMA_VERSION,
    AuthoringKey,
    Draft,
    FreezeError,
    Id,
    Origin,
    RefError,
    SchemaError,
    Value,
    ValueTypeError,
    describe,
    freeze,
    make_id,
    record,
)
from fransys_model.kernel.hashes import model_digest, namespace_digests, record_hash


def test_freeze_reports_all_errors_in_one_freeze_error(thing_cls: type, origin: Origin) -> None:
    """Two independent problems in one draft surface as one `FreezeError`, both included."""
    draft = Draft()
    draft.add(thing_cls(id=Id(kind="thing", value="1" * 32), key=("a",), name=1), origin=origin)
    draft.add(thing_cls(id=Id(kind="thing", value="2" * 32), key=("b",), name=2), origin=origin)
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    assert len(excinfo.value.errors) == 2


def test_freeze_catches_dangling_ref(link_cls: type, origin: Origin) -> None:
    """A `Link` referencing a `Thing` id that was never added is a `FreezeError`."""
    draft = Draft()
    missing = Id(kind="thing", value="0" * 32)
    draft.add(
        link_cls(id=Id(kind="link", value="1" * 32), key=("l",), a=missing, b=missing),
        origin=origin,
    )
    with pytest.raises(FreezeError):
        freeze(draft)


def test_freeze_catches_wrong_kind_ref(link_cls: type, origin: Origin) -> None:
    """A reference field pointing at an id of the wrong registered kind is a `FreezeError`."""
    draft = Draft()
    wrong_kind_id = Id(kind="link", value="1" * 32)
    draft.add(
        link_cls(id=Id(kind="link", value="2" * 32), key=("l",), a=wrong_kind_id, b=wrong_kind_id),
        origin=origin,
    )
    with pytest.raises(FreezeError):
        freeze(draft)


def test_freeze_catches_alias_to_missing_id() -> None:
    """An alias whose `new` id was never added is a `FreezeError`."""
    draft = Draft()
    draft.alias(Id(kind="thing", value="1" * 32), Id(kind="thing", value="2" * 32))
    with pytest.raises(FreezeError):
        freeze(draft)


def test_freeze_same_draft_twice_gives_equal_models(thing_cls: type, origin: Origin) -> None:
    """Freezing the same draft twice is deterministic: equal models, equal digests."""
    draft = Draft()
    thing = thing_cls(id=Id(kind="thing", value="1" * 32), key=("a",), name="pump")
    draft.add(thing, origin=origin)
    first = freeze(draft)
    second = freeze(draft)
    assert first == second
    assert first.digest == second.digest


def test_freeze_builds_the_model_from_the_draft(origin: Origin) -> None:
    """Tables by kind, every origin, the schema version, and the hashes and digests.

    The hashes are checked against `hashes.py` called the way `evolve` must call it; that the
    bytes are right is pinned by literals in `test_hashes.py`.
    """
    owner, holder = make_owner("1"), make_holder("2")
    model = freeze(draft_of(origin, holder, owner))
    assert model.schema_version == SCHEMA_VERSION
    assert model.tables["freeze_owner_probe"][owner.id] is owner
    assert model.tables["freeze_holder_probe"][holder.id] is holder
    assert set(model.tables) == {"freeze_owner_probe", "freeze_holder_probe"}
    assert dict(model.origins) == {owner.id: origin, holder.id: origin}
    assert dict(model.aliases) == {}
    assert model.hashes == {owner.id: record_hash(owner), holder.id: record_hash(holder)}
    assert model.digests == namespace_digests(model.hashes, SCHEMA_VERSION)
    assert model.digest == model_digest(model.digests)


def test_an_empty_draft_freezes_to_an_empty_model() -> None:
    """Nothing to check is not an error."""
    model = freeze(Draft())
    assert (dict(model.tables), dict(model.origins), dict(model.aliases)) == ({}, {}, {})


def test_freeze_does_not_rederive_an_id_from_its_key(origin: Origin) -> None:
    """`make_id` ties an id to its key when authored; a hand-built id is not a freeze error."""
    hand_built = make_owner("1")
    assert hand_built.id != make_id(type(hand_built), hand_built.key)
    freeze(draft_of(origin, hand_built))


def test_a_dangling_reference_names_the_holder_the_field_and_the_target(origin: Origin) -> None:
    """The error carries what an author needs: which record, which field, which id."""
    holder = make_holder("2", owner=owner_id("9"))
    (error,) = errors_of(draft_of(origin, holder, make_owner("1")))
    assert isinstance(error, RefError)
    assert (error.record_id, error.field, error.target) == (holder.id, "owner", owner_id("9"))


def test_a_reference_of_the_wrong_kind_is_reported_once_as_such(origin: Origin) -> None:
    """A record that exists but of another kind is a wrong-kind error, not also a dangling one."""
    holder = make_holder("2", owner=holder_id("5"))
    (error,) = errors_of(draft_of(origin, holder, make_holder("5"), make_owner("1")))
    assert isinstance(error, RefError)
    assert "declares a freeze_owner_probe" in str(error)


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"nested": Holds(owner=owner_id("9"))}, "nested.owner"),
        ({"nested": Holds(owner=owner_id("1"), who=owner_id("9"))}, "nested.who"),
        ({"many": (owner_id("1"), owner_id("9"))}, "many.1"),
        ({"maybe": owner_id("9")}, "maybe"),
        ({"anything": (owner_id("1"), owner_id("9"))}, "anything.1"),
        ({"ext": frozendict({"x": owner_id("9")})}, "ext.x"),
        ({"ext": frozendict({"x": (owner_id("1"), owner_id("9"))})}, "ext.x.1"),
    ],
    ids=["nested-value", "id-any", "tuple-element", "optional", "value-field", "ext", "ext-tuple"],
)
def test_a_dangling_reference_is_found_wherever_it_sits(
    overrides: dict[str, Any], field: str, origin: Origin
) -> None:
    """Nested values, tuples, optionals, `Id[Any]`, `Value` fields and `ext` are all walked."""
    (error,) = errors_of(draft_of(origin, make_holder("2", **overrides), make_owner("1")))
    assert isinstance(error, RefError)
    assert error.field == field


def test_a_record_nested_too_deeply_reports_the_exact_message_and_path(origin: Origin) -> None:
    """The `RecursionError` fallback's message and path are pinned, not just its type."""
    nested: Any = 1
    for _ in range(5000):
        nested = frozendict({"k": nested})
    (error,) = errors_of(draft_of(origin, make_owner("1", ext=frozendict({"deep": nested}))))
    assert isinstance(error, ValueTypeError)
    assert str(error) == "a record is nested too deeply to check"
    assert error.path == ()


def test_an_id_where_no_kind_is_declared_needs_only_to_exist(origin: Origin) -> None:
    """Under `ext`, a `Value` field or `Id[Any]` any existing record satisfies it."""
    holder = make_holder(
        "2",
        nested=Holds(owner=owner_id("1"), who=holder_id("2")),
        anything=(holder_id("2"), owner_id("1")),
        ext=frozendict({"any": holder_id("2"), "owner": owner_id("1")}),
    )
    freeze(draft_of(origin, holder, make_owner("1")))


def test_an_absent_optional_reference_is_not_a_problem(origin: Origin) -> None:
    """`None` in an `Id[K] | None` field names nothing to resolve."""
    freeze(draft_of(origin, make_holder("2", maybe=None), make_owner("1")))


def test_a_schema_error_names_the_record_and_a_value_error_too(origin: Origin) -> None:
    """Shape problems and legality problems both carry the record that holds them."""
    bad_shape = make_holder("2", owner="not-an-id")
    bad_value = make_holder("3", ext=frozendict({"x": 1.5}))
    errors = errors_of(draft_of(origin, bad_shape, bad_value, make_owner("1")))
    kinds = {type(error): error.record_id for error in errors}
    assert kinds == {SchemaError: bad_shape.id, ValueTypeError: bad_value.id}


def test_an_id_holding_an_illegal_value_does_not_reach_the_model(origin: Origin) -> None:
    """A record's own id is checked too: `bytes` in `Id.value` is a `ValueTypeError`."""
    smuggled: Any = b"bytes"
    bad = make_owner("1")
    object.__setattr__(bad, "id", Id(kind="freeze_owner_probe", value=smuggled))
    (error,) = errors_of(draft_of(origin, bad))
    assert isinstance(error, ValueTypeError)
    assert error.path == ("id", "value")


def test_a_second_singleton_record_is_the_offender(origin: Origin) -> None:
    """The first by id is fine; every later one is reported, each with its own id."""
    first = Single(id=Id(kind="freeze_single_probe", value="1" * 32), key=("a",))
    second = Single(id=Id(kind="freeze_single_probe", value="2" * 32), key=("b",))
    freeze(draft_of(origin, first))
    (error,) = errors_of(draft_of(origin, second, first))
    assert isinstance(error, SchemaError)
    assert error.record_id == second.id


def test_a_unique_kind_allows_one_record_per_subject(origin: Origin) -> None:
    """Three records for one subject: two offenders; another subject's record is fine."""
    facets = [make_facet(d, s) for d, s in (("1", "1"), ("2", "1"), ("3", "1"), ("4", "2"))]
    errors = errors_of(draft_of(origin, *facets, make_owner("1"), make_owner("2")))
    assert [error.record_id for error in errors] == [facets[1].id, facets[2].id]


def test_a_class_level_problem_is_reported_once_however_many_records_it_touches(
    origin: Origin,
) -> None:
    """A kind whose forward name never resolves gives one error, not one per record."""

    def body(namespace: dict[str, Any]) -> None:
        generic: Any = Id
        namespace["__annotations__"] = {
            "id": generic["GhostKindProbe"],
            "key": AuthoringKey,
            "ext": frozendict[str, Value],
            "ghost": generic["NoSuchRecordAtAll"],
        }
        namespace["ext"] = frozendict()

    ghost = record(kind="ghost_kind_probe")(types.new_class("GhostKindProbe", (), exec_body=body))
    made = [
        ghost(id=Id(kind="ghost_kind_probe", value=d * 32), key=(d,), ghost=owner_id("1"))
        for d in "123"
    ]
    (error,) = errors_of(draft_of(origin, *made, make_owner("1")))
    assert isinstance(error, SchemaError)
    assert error.record_id is None
    assert "is not a registered record" in str(error)


def _messy_records() -> list[Any]:
    return [
        make_holder("2", owner=owner_id("9")),
        make_holder("3", owner="not-an-id"),
        make_holder("4", ext=frozendict({"x": 1.5})),
        make_holder("5", many=(owner_id("1"), owner_id("8"))),
        make_facet("1", "1"),
        make_facet("2", "1"),
        make_owner("1"),
    ]


def test_the_errors_come_out_in_the_same_order_whatever_the_insertion_order(
    origin: Origin,
) -> None:
    """Invariant 7: an author sees the same list however the front end happened to emit."""
    records = _messy_records()
    orders = (records, records[::-1], records[2:] + records[:2], records[5:] + records[:5])
    seen = set()
    for order in orders:
        errors = errors_of(draft_of(origin, *order))
        seen.add(tuple((type(error).__name__, str(error)) for error in errors))
    assert len(seen) == 1


def test_references_under_keys_that_differ_only_by_a_dot_have_distinct_paths(
    origin: Origin,
) -> None:
    """`{"a.b": X}` and `{"a": {"b": Y}}` are two places; equal records give equal errors.

    Were both paths `ext.a.b`, the two errors would tie in the sort and follow the order the
    frozendict was built in, though the two records compare equal.
    """
    dotted = frozendict({"a.b": owner_id("8"), "a": frozendict({"b": owner_id("9")})})
    reordered = frozendict({"a": frozendict({"b": owner_id("9")}), "a.b": owner_id("8")})
    assert dotted == reordered
    results = []
    for ext in (dotted, reordered):
        errors = errors_of(draft_of(origin, make_holder("2", ext=ext), make_owner("1")))
        results.append(tuple((error.field, error.target) for error in errors))
    assert results[0] == results[1]
    assert {field for field, _ in results[0]} == {"ext['a.b']", "ext.a.b"}


def test_the_errors_are_ordered_by_pipeline_stage(origin: Origin) -> None:
    """Alias problems, then shape, then value, then reference, then cardinality.

    The value error sits on a lower id than the shape error, so the stage, not the id,
    decides.
    """
    records = [
        make_holder("2", ext=frozendict({"x": 1.5})),
        make_holder("3", owner="not-an-id"),
        make_holder("4", owner=owner_id("9")),
        make_facet("1", "1"),
        make_facet("2", "1"),
        make_owner("1"),
    ]
    draft = draft_of(origin, *records)
    draft.alias(owner_id("7"), owner_id("9"))
    errors = errors_of(draft)
    assert [type(error).__name__ for error in errors] == [
        "RefError",
        "SchemaError",
        "ValueTypeError",
        "RefError",
        "SchemaError",
    ]
    assert errors[0].field == "<alias>"


def test_a_freeze_error_renders_through_the_draft_it_came_from(origin: Origin) -> None:
    """`describe` turns the collected ids into the origins the author wrote."""
    bad = Origin(file="pumps.py", line=12, note="pump1")
    draft = Draft()
    draft.add(make_holder("2", owner=owner_id("9")), origin=bad)
    draft.add(make_owner("1"), origin=origin)
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    text = describe(excinfo.value, draft)
    assert "record: pumps.py:12 (2)" in text
    assert "field: owner" in text
