"""REVIEW-M measure M4: every `Id` field of every registered kind, in one table that stays true.

`TABLE` (a Python constant in `id_field_rows.py`) has one row per `Id`-typed field of every kind
that `vocab` and `layout` register: the `id` primary key, `subject` fields, `Id[K] | None`,
`tuple[Id[K], ...]`, and every `Id` nested inside a `@value` class, keyed `(kind, "field.subfield")`
(a tuple in between is transparent: `partners.port`). No kind has an `Id` inside a `frozendict`,
so the walker does not enter one: a new such field would not be found (extend `_id_leaves`).

Columns of a row:

- `resolved`: `freeze()` checks that the id names a record of the declared kind (a `RefError`
  otherwise, for a missing record and for a record of another kind). False only for `id`: it is the
  primary key, it defines the set the others resolve to, so `check_record` collects no reference
  for it.
- `cardinality`: `one` (`Id[K]`: `None` is a `SchemaError`), `optional` (`Id[K] | None`: `None` is
  accepted) or `many` (a `tuple` on the path: each item is checked, neither order nor
  no-duplicates is a schema rule).
- `unique`: no two records of the kind may hold the same value in this field, and the code
  enforces it. Exactly three sources exist: the `id` primary key (`Draft.add` raises
  `MergeConflict` for two different records under one id), a `subject` field of a `unique=True`
  record (`cardinality_problems` in `kernel/checks.py`), and every field of a `singleton=True` kind
  (at most one record exists). Nothing else is unique: a tuple does not forbid a repeated id, an
  optional field does not forbid two records naming the same target.

The tests read the registry (`fransys_model.kernel.registry._kinds`, filtered to the classes
declared in `vocab` and `layout`, so kernel test kinds do not count) and fail in both directions
when the table and the code disagree. The dynamic tests build each record with `object.__new__`
plus `object.__setattr__`, so `__post_init__` refuses nothing: `freeze()` does not run it, and
the check under test is `freeze()`'s, not the record's own. Every field of a built record is a
valid value of its annotation; an `Id` is dangling unless the test places a real one. `many`
rows have no `None` probe: the cardinality of the tuple itself is not a per-item property.
"""

from decimal import Decimal
from enum import Enum
from types import NoneType, UnionType
from typing import Any, NamedTuple, get_args, get_origin

import pytest
from id_field_rows import TABLE

from fransys_model import layout, vocab
from fransys_model.kernel import (
    AuthoringKey,
    Draft,
    FreezeError,
    Id,
    MergeConflict,
    Origin,
    RefError,
    SchemaError,
    Value,
    freeze,
    lookup_kind,
)
from fransys_model.kernel.conform import check_record
from fransys_model.kernel.registry import _kinds, is_value_class
from fransys_model.kernel.schema import annotations_of, fields_of, resolve_target

_ORIGIN = Origin(file="test_id_field_table.py", line=1, note="fixture")
_FIXED = {
    str: "x",
    int: 0,
    bool: False,
    Decimal: Decimal(0),
    None: None,
    Value: None,
    AuthoringKey: ("k",),
}
_EMPTY = {tuple: (), frozendict: frozendict(), UnionType: None}


class Leaf(NamedTuple):
    """An `Id` field as the code declares it: its cardinality and the kind it names."""

    cardinality: str
    target: str


def _id_leaves(annotation, path, flags, seen):
    """Yield `(path, flags, target)` for every `Id` in `annotation`, entering `@value` classes."""
    origin = get_origin(annotation)
    if origin is Id:
        yield path, flags, get_args(annotation)[0]
    elif origin is UnionType:
        for arg in get_args(annotation):
            if arg is not NoneType:
                yield from _id_leaves(arg, path, flags | {"optional"}, seen)
    elif origin is tuple:
        yield from _id_leaves(get_args(annotation)[0], path, flags | {"many"}, seen)
    elif isinstance(annotation, type) and is_value_class(annotation) and annotation not in seen:
        for name, nested in annotations_of(annotation).items():
            yield from _id_leaves(nested, (*path, name), flags, seen | {annotation})


def _derive() -> dict[tuple[str, str], Leaf]:
    prefixes = (f"{vocab.__name__}.", f"{layout.__name__}.")
    found = {}
    for kind, cls in _kinds.items():
        if not cls.__module__.startswith(prefixes):
            continue
        for name, annotation in annotations_of(cls).items():
            for path, flags, target in _id_leaves(annotation, (name,), frozenset(), frozenset()):
                dotted = ".".join(path)
                cardinality = next((c for c in ("many", "optional") if c in flags), "one")
                named = resolve_target(target, cls, dotted)
                assert named is not None, f"{kind}.{dotted}: a record field is never Id[Any]"
                found[kind, dotted] = Leaf(cardinality, named)
    return found


DERIVED = _derive()
FIELD_ROWS = sorted((key, row) for key, row in TABLE.items() if key in DERIVED)
RESOLVED_KEYS = [key for key, row in FIELD_ROWS if row.resolved]
NONE_ROWS = [
    (key, row)
    for key, row in FIELD_ROWS
    if row.cardinality in ("one", "optional") and key[1] != "id"
]
_ALL_IDS = [f"{key[0]}.{key[1]}" for key, _ in FIELD_ROWS]
_RESOLVED_IDS = [f"{key[0]}.{key[1]}" for key in RESOLVED_KEYS]
_NONE_IDS = [f"{key[0]}.{key[1]}" for key, _ in NONE_ROWS]


def _default(annotation, owner):
    """A valid value of `annotation`; an `Id` in it dangles."""
    origin = get_origin(annotation)
    if origin is Id:
        return Id(kind=resolve_target(get_args(annotation)[0], owner, ""), value="d" * 32)
    if origin in _EMPTY:
        return _EMPTY[origin]
    if annotation in _FIXED:
        return _FIXED[annotation]
    if issubclass(annotation, Enum):
        return next(iter(annotation))
    return _build(annotation, (), None, None)


def _place(annotation, rest, ident):
    """A valid value of `annotation` holding `ident` at `rest` (field names only)."""
    origin = get_origin(annotation)
    if origin is Id:
        return ident
    if origin is UnionType:
        return _place(next(a for a in get_args(annotation) if a is not NoneType), rest, ident)
    if origin is tuple:
        return (_place(get_args(annotation)[0], rest, ident),)
    return _build(annotation, rest, ident, None)


def _build(cls, path, ident, record_id):
    """An instance of `cls` without running `__post_init__`; `ident` sits at `path` if given."""
    built = object.__new__(cls)
    annotations = annotations_of(cls)
    for field in fields_of(cls):
        annotation = annotations[field.name]
        if record_id is not None and field.name == "id":
            value = record_id
        elif path and field.name == path[0]:
            value = _place(annotation, path[1:], ident)
        else:
            value = _default(annotation, cls)
        object.__setattr__(built, field.name, value)
    return built


def _split(key):
    return lookup_kind(key[0]), tuple(key[1].split("."))


def _errors(*records: Any) -> tuple[Any, ...]:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    try:
        freeze(draft)
    except FreezeError as exc:
        return exc.errors
    return ()


def _refs(errors, holder):
    """The `RefError`s naming `holder`, by field with the tuple indexes removed."""
    return {
        ".".join(p for p in error.field.split(".") if not p.isdigit()): error
        for error in errors
        if isinstance(error, RefError) and error.record_id == holder
    }


def _card_offenders(errors):
    return {
        error.record_id
        for error in errors
        if isinstance(error, SchemaError) and "at most one record" in str(error)
    }


def _hold(key, held_kind):
    """A holder of `key` naming a real record of `held_kind`: `(records, holder_id, held_id)`."""
    cls, path = _split(key)
    holder_id = Id(kind=key[0], value="a" * 32)
    held = _build(lookup_kind(held_kind), (), None, Id(kind=held_kind, value="e" * 32))
    return (_build(cls, path, held.id, holder_id), held), holder_id, held.id


def test_table_and_registry_name_the_same_id_fields():
    missing = sorted(set(DERIVED) - set(TABLE))
    stale = sorted(set(TABLE) - set(DERIVED))
    assert not missing, f"Id fields in the code but not in the table: {missing}"
    assert not stale, f"table rows for Id fields the code no longer has: {stale}"
    assert TABLE
    assert {kind for kind, _ in DERIVED} == {kind for kind, _ in TABLE}


def test_cardinality_column_matches_the_annotations():
    wrong = {
        key: (row.cardinality, DERIVED[key].cardinality)
        for key, row in FIELD_ROWS
        if row.cardinality != DERIVED[key].cardinality
    }
    assert not wrong, f"(table, code) cardinality differs: {wrong}"
    assert {row.cardinality for _, row in FIELD_ROWS} == {"one", "optional", "many"}


@pytest.mark.parametrize(("key", "row"), FIELD_ROWS, ids=_ALL_IDS)
def test_unique_column_matches_the_class_flags(key, row):
    cls, path = _split(key)
    by_class = (
        path == ("id",)
        or bool(cls.__singleton__)
        or (bool(cls.__unique__) and cls.__subject__ == key[1])
    )
    assert row.unique == by_class, f"{key}: table {row.unique}, class flags say {by_class}"


@pytest.mark.parametrize(("key", "row"), FIELD_ROWS, ids=_ALL_IDS)
def test_freeze_resolves_exactly_the_rows_that_say_so(key, row):
    cls, path = _split(key)
    if path == ("id",):  # a primary key of another kind, so no record could ever resolve it
        errors, references = check_record(_build(cls, (), None, Id(kind="other", value="d" * 32)))
        assert not errors, "the record itself is valid, so its references were collected"
        assert ("id" in {ref.path for ref in references}) == row.resolved, f"{key}: {row}"
        return
    holder_id = Id(kind=key[0], value="a" * 32)
    dangling = Id(kind=DERIVED[key].target, value="d" * 32)
    refs = _refs(_errors(_build(cls, path, dangling, holder_id)), holder_id)
    assert (key[1] in refs) == row.resolved, f"{key}: table resolved={row.resolved}"
    if row.resolved:
        assert refs[key[1]].target == dangling


@pytest.mark.parametrize("key", RESOLVED_KEYS, ids=_RESOLVED_IDS)
def test_freeze_checks_the_kind_of_a_real_target(key):
    target = DERIVED[key].target
    records, holder_id, _ = _hold(key, target)
    assert key[1] not in _refs(_errors(*records), holder_id), "a record of the declared kind"
    wrong_kind = "port" if target == "item" else "item"
    records, holder_id, wrong_id = _hold(key, wrong_kind)
    refs = _refs(_errors(*records), holder_id)
    assert refs[key[1]].target == wrong_id, "a real record of another kind is refused"
    assert "another kind" in str(refs[key[1]])


@pytest.mark.parametrize(("key", "row"), NONE_ROWS, ids=_NONE_IDS)
def test_none_is_refused_where_the_row_is_one_and_accepted_where_optional(key, row):
    cls, path = _split(key)
    holder_id = Id(kind=key[0], value="a" * 32)
    errors = _errors(_build(cls, path, None, holder_id))
    refused = [
        e
        for e in errors
        if isinstance(e, SchemaError) and e.record_id == holder_id and f".{key[1]}:" in str(e)
    ]
    assert bool(refused) == (row.cardinality == "one"), f"{key}: {refused}"
    assert key[1] not in _refs(errors, holder_id), "None is not a reference"


@pytest.mark.parametrize(("key", "row"), FIELD_ROWS, ids=_ALL_IDS)
def test_unique_rows_are_enforced_and_the_rest_are_not(key, row):
    cls, path = _split(key)
    first_id, second_id = (Id(kind=key[0], value=digit * 32) for digit in "ab")
    if path == ("id",):  # the primary key: a second, different record under one id is refused
        other = _build(cls, (), None, first_id)
        object.__setattr__(other, "ext", frozendict({"x": "y"}))
        draft = Draft()
        draft.add(_build(cls, (), None, first_id), origin=_ORIGIN)
        draft.add(_build(cls, (), None, first_id), origin=_ORIGIN)  # an identical add is fine
        with pytest.raises(MergeConflict):
            draft.add(other, origin=_ORIGIN)
        return
    a, b = (Id(kind=DERIVED[key].target, value=digit * 32) for digit in "12")

    def pair(first_value, second_value):
        first = _build(cls, path, first_value, first_id)
        second = _build(cls, path, second_value, second_id)
        subject = cls.__subject__
        if subject is not None and key[1] != subject:  # keep the subjects apart: only `path` varies
            elsewhere = Id(kind=getattr(first, subject).kind, value="s" * 32)
            object.__setattr__(second, subject, elsewhere)
        return _errors(first, second)

    same, different = pair(a, a), pair(a, b)
    assert bool(_card_offenders(same)) == row.unique, f"{key}: same value"
    if row.unique:
        assert _card_offenders(same) == {second_id}, "the later record is the offender"
    assert bool(_card_offenders(different)) == bool(cls.__singleton__), f"{key}: different values"
