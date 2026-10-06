"""`evolve()`: a pure `Model -> Model` edit for passes, not for authoring (kernel-model.md 5.7)."""

import dataclasses
from itertools import groupby
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Iterable

from .checks import (
    Problem,
    cardinality_problems,
    close_aliases,
    kind_of,
    record_problems,
    reference_problems,
    type_problems,
)
from .conform import check_record
from .errors import MergeConflict, SchemaError, ValueTypeError
from .hashes import model_digest, namespace_digests, record_hash
from .ids import Id
from .origin import Origin, require_origin
lazy from .model import Model
lazy from .record import Record

if TYPE_CHECKING:
    from .conform import Reference


def evolve(
    model: Model,
    *,
    put: Iterable[Record] = (),
    remove: Iterable[Id[Any]] = (),
    origin: Origin | None = None,
) -> Model:
    """Path-copy the tables `put` and `remove` touch, and check what they touch.

    For passes (`plc_allocation`, `numbering`) that persist a computed result; normal editing
    is a new `Draft` and `freeze()`. The result equals `freeze()`'s, except that a retired id
    used as a reference in a `put` record stays dangling. `remove` runs before `put`; a `put`
    over an id with identical content changes nothing, with different content it conflicts.
    `origin` attributes every `put` record and is required when `put` is not empty.

    Raises:
        SchemaError: bad `put`, `remove` or `origin`; a malformed record; a `remove` id no
            record holds; no origin for a conflicting record; `unique`/`singleton` broken.
        MergeConflict: a `put` record has the id of a record with different content.
        RefError: `remove` orphans a reference, a `put` record dangles, or an alias breaks.
        ValueTypeError: a `put` value is outside the closed set or nested too deeply.
    """
    try:
        return _evolve(model, _put_records(put), _remove_ids(remove), origin)
    except RecursionError as exc:
        msg = "a record is nested too deeply to check"
        raise ValueTypeError(msg, path=()) from exc


def _put_records(put: Iterable[Record]) -> tuple[Record, ...]:
    """Check each record is a table record of its own kind; repeats of one id collapse."""
    try:
        items = iter(put)
    except TypeError as exc:
        msg = f"put takes an iterable of records, not a {type(put).__name__}"
        raise SchemaError(msg, kind="evolve") from exc
    records = tuple(items)
    lying = sorted(type(record).__qualname__ for record in records if not _is_table_record(record))
    if lying:
        msg = f"{lying[0]} is not a @record instance with an id of its own kind"
        raise SchemaError(msg, kind=lying[0])
    unique: dict[Id[Any], Record] = {}
    for record in sorted(records, key=lambda record: record.id):
        if unique.setdefault(record.id, record) != record:
            msg = "the records put name one id twice, with different content"
            raise SchemaError(msg, kind=record.id.kind, record_id=record.id)
    return tuple(unique.values())


def _remove_ids(remove: Iterable[Id[Any]]) -> frozenset[Id[Any]]:
    """Check that `remove` is an iterable of `Id`s."""
    try:
        items = iter(remove)
    except TypeError as exc:
        msg = f"remove takes an iterable of ids, not a {type(remove).__name__}"
        raise SchemaError(msg, kind="evolve") from exc
    ids = tuple(items)
    lying = sorted(type(target).__qualname__ for target in ids if type(target) is not Id)
    if lying:
        msg = f"remove takes ids, not a {lying[0]}"
        raise SchemaError(msg, kind="evolve")
    return frozenset(ids)


def _is_table_record(record: Record) -> bool:
    kind = vars(type(record)).get("__kind__")
    return kind is not None and isinstance(record.id, Id) and record.id.kind == kind


def _evolve(
    model: Model, put: tuple[Record, ...], removed: frozenset[Id[Any]], origin: Origin | None
) -> Model:
    if put and not isinstance(origin, Origin):
        msg = "evolve needs an origin (an Origin) to attribute the records it puts to"
        raise SchemaError(msg, kind=put[0].id.kind)
    for target in sorted(removed):
        if target not in model.hashes:
            msg = "there is no record with this id to remove"
            raise SchemaError(msg, kind=target.kind, record_id=target)
    changes = _changes(model, put, removed, cast("Origin", origin)) if put else ()
    if not changes and not removed:
        return model
    final_ids = (frozenset(model.hashes) - removed) | {record.id for record in changes}
    touched = _final_tables(model, changes, removed)
    problems = _problems(model, changes, removed, final_ids, touched)
    if problems:
        raise min(problems, key=Problem.sort_key).error
    hashes = {target: found for target, found in model.hashes.items() if target not in removed}
    hashes.update((record.id, record_hash(record)) for record in changes)
    origins = {target: where for target, where in model.origins.items() if target not in removed}
    origins.update((record.id, cast("Origin", origin)) for record in changes)
    digests = namespace_digests(hashes, model.schema_version)
    tables = {kind: table for kind, table in model.tables.items() if kind not in touched}
    tables.update(
        (kind, frozendict({record.id: record for record in rows}))
        for kind, rows in touched.items()
        if rows
    )
    tables = {kind: tables[kind] for kind in sorted(tables)}  # as `freeze()` orders them
    return dataclasses.replace(
        model,
        tables=frozendict(tables),
        origins=frozendict(origins),
        hashes=frozendict(hashes),
        digests=digests,
        digest=model_digest(digests),
    )


def _changes(
    model: Model, put: tuple[Record, ...], removed: frozenset[Id[Any]], origin: Origin
) -> tuple[Record, ...]:
    """The put records that add or replace something, in `Id` order."""
    changes = []
    for record in put:
        present = model.tables.get(record.id.kind, {}).get(record.id)
        if present is None or record.id in removed:
            changes.append(record)
        elif present != record:
            msg = "two different records share one id"
            raise MergeConflict(
                msg,
                record_id=record.id,
                origin_a=require_origin(model.origins, record.id),
                origin_b=origin,
            )
    return tuple(changes)


def _final_tables(
    model: Model, changes: tuple[Record, ...], removed: frozenset[Id[Any]]
) -> dict[str, tuple[Record, ...]]:
    """The records of every table the call touches as they will be, in `Id` order."""
    kinds = {record.id.kind for record in changes} | {target.kind for target in removed}
    tables = {}
    for kind in sorted(kinds):
        rows = {
            target: record
            for target, record in model.tables.get(kind, {}).items()
            if target not in removed
        }
        rows.update((record.id, record) for record in changes if record.id.kind == kind)
        tables[kind] = tuple(rows[target] for target in sorted(rows))
    return tables


def _problems(
    model: Model,
    changes: tuple[Record, ...],
    removed: frozenset[Id[Any]],
    final_ids: frozenset[Id[Any]],
    touched: dict[str, tuple[Record, ...]],
) -> tuple[Problem, ...]:
    """Everything wrong with the result, for the records that changed and what points at them."""
    groups = tuple((kind, tuple(group)) for kind, group in groupby(changes, kind_of))
    bad_kinds, schema_found = type_problems(groups)
    record_found, references = record_problems(changes, bad_kinds)
    orphaned = removed - {record.id for record in changes}
    if orphaned:  # only a record that disappears can leave a reference behind
        references += _references_into(model, removed, orphaned)
    put_kinds = {kind for kind, _ in groups}
    return (
        *close_aliases(model.aliases, final_ids)[1],
        *schema_found,
        *record_found,
        *reference_problems(references, final_ids),
        *cardinality_problems(
            tuple((kind, rows) for kind, rows in touched.items() if kind in put_kinds)
        ),
    )


def _references_into(
    model: Model, removed: frozenset[Id[Any]], orphaned: frozenset[Id[Any]]
) -> tuple[tuple[Id[Any], Reference], ...]:
    """The references, in the records that stay, to an id that goes.

    Those records passed `freeze()` once, so only what they point at can be wrong now.
    """
    found = []
    for table in model.tables.values():
        for record in table.values():
            if record.id not in removed:
                _, references = check_record(record)
                found.extend((record.id, ref) for ref in references if ref.target in orphaned)
    return tuple(found)
