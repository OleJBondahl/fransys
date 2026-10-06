"""`freeze()`: `Draft` -> `Model` (design/kernel-model.md 5.5)."""

import dataclasses
from itertools import groupby
from typing import TYPE_CHECKING, Any, cast

from .checks import (
    ALIAS,
    ALIAS_FIELD,
    Problem,
    cardinality_problems,
    close_aliases,
    kind_of,
    record_problems,
    reference_problems,
    type_problems,
)
from .errors import FreezeError, ModelError, SchemaError, ValueTypeError
from .hashes import _record_hash, model_digest, namespace_digests
from .ids import Id
from .model import SCHEMA_VERSION, Model
from .registry import is_value_class
from .schema import fields_of
lazy from .draft import Draft

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from .record import Record
    from .schema import FieldInfo


def freeze(draft: Draft) -> Model:
    """Validate every record in `draft` and return the immutable `Model`.

    In order: rewrite references to retired ids, check every field against its annotation
    and every value against the closed set, resolve every reference, enforce `unique` and
    `singleton`, then hash: a hash per record, a digest per registered namespace, and the
    model digest.

    Raises:
        FreezeError: aggregates every problem found, sorted so that the list does not
            depend on the order records were added, so an author fixes a batch, not one
            error per run. A model nested too deeply to walk is one error, with no holder.
    """
    try:
        return _freeze(draft)
    except RecursionError as exc:
        msg = "a record is nested too deeply to check"
        raise FreezeError((ValueTypeError(msg, path=()),)) from exc


def _freeze(draft: Draft) -> Model:
    records = draft.records()
    ids = frozenset(record.id for record in records)
    aliases, alias_problems = close_aliases(draft.alias_map(), ids)
    records, rewrite_problems = _rewrite_records(records, aliases)
    groups = tuple((kind, tuple(group)) for kind, group in groupby(records, kind_of))
    bad_kinds, schema_found = type_problems(groups)
    record_found, references = record_problems(records, bad_kinds)
    problems = (
        *alias_problems,
        *rewrite_problems,
        *schema_found,
        *record_found,
        *reference_problems(references, ids),
        *cardinality_problems(groups),
    )
    if problems:
        raise FreezeError(tuple(p.error for p in sorted(problems, key=Problem.sort_key)))
    # One `{class: FieldInfo}` memo, shared for the whole hash pass (model-0102): a kind or a
    # nested `@value` type used by many records is resolved once, not once per record.
    specs: dict[type, FieldInfo] = {}
    hashes = frozendict({record.id: _record_hash(record, specs) for record in records})
    digests = namespace_digests(hashes, SCHEMA_VERSION)
    return Model(
        schema_version=SCHEMA_VERSION,
        tables=frozendict({kind: frozendict({r.id: r for r in group}) for kind, group in groups}),
        aliases=aliases,
        origins=draft.origins(),
        hashes=hashes,
        digests=digests,
        digest=model_digest(digests),
    )


def _rewrite_records(
    records: tuple[Record, ...], aliases: frozendict[Id[Any], Id[Any]]
) -> tuple[tuple[Record, ...], tuple[Problem, ...]]:
    """Rewrite retired ids in every record; one whose own rules then refuse is reported.

    A rebuild re-runs `__post_init__`, which may refuse the new values: report it, never raise.
    A retired id in an `init=False` field is not rewritten unless an `__init__` field derives it.
    """
    if not aliases:
        return records, ()
    rewritten = []
    problems = []
    for record in records:
        try:
            rewritten.append(cast("Record", _rewrite(record, aliases)))
        except ModelError as exc:
            rewritten.append(record)
            error = (
                SchemaError(str(exc), kind=exc.kind, record_id=record.id)
                if isinstance(exc, SchemaError)
                else exc
            )
            problems.append(Problem(ALIAS, record.id, ALIAS_FIELD, error))
    return tuple(rewritten), tuple(problems)


def _rewrite(value: object, aliases: frozendict[Id[Any], Id[Any]]) -> object:
    """Return `value` with every retired id replaced; the same object if none was found."""
    if type(value) is Id:
        return aliases.get(value, value)
    if type(value) is tuple:
        items = tuple(_rewrite(item, aliases) for item in value)
        return value if all(a is b for a, b in zip(items, value, strict=True)) else items
    if type(value) is frozendict:
        rewritten = frozendict({key: _rewrite(item, aliases) for key, item in value.items()})
        return value if all(rewritten[key] is item for key, item in value.items()) else rewritten
    cls = type(value)
    if is_value_class(cls) or "__kind__" in vars(cls):
        changes = {}
        for field in fields_of(cls):
            if not field.init:  # derived in `__post_init__` from the fields that are rewritten
                continue
            current = getattr(value, field.name)
            replaced = _rewrite(current, aliases)
            if replaced is not current:
                changes[field.name] = replaced
        return (
            dataclasses.replace(cast("DataclassInstance", value), **changes) if changes else value
        )
    return value
