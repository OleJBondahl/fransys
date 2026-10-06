"""The per-record and per-model checks `freeze()` and `evolve()` share (kernel-model.md 5.5, 5.7).

Each check returns `Problem`s instead of raising, so the caller can sort them by pipeline
stage, holder, path and message, and either raise them all (`freeze`) or the first (`evolve`).
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from .conform import _check_record
from .errors import ModelError, RefError, SchemaError, ValueTypeError
from .ids import Id
from .record import field_specs

if TYPE_CHECKING:
    from .conform import Reference
    from .record import Record
    from .schema import FieldInfo

# The pipeline position, which orders the errors in a `FreezeError`.
ALIAS, _SCHEMA, _VALUE, _REFERENCE, _CARDINALITY = range(5)

ALIAS_FIELD = "<alias>"


@dataclasses.dataclass(frozen=True, slots=True)
class Problem:
    """One thing wrong, with the position that orders it among the others."""

    stage: int
    holder: Id[Any]
    path: str
    error: ModelError

    def sort_key(self) -> tuple[int, Id[Any], str, str]:
        """Order by stage, holder, field path and message, never by discovery order."""
        return self.stage, self.holder, self.path, str(self.error)


def kind_of(record: Record) -> str:
    """The kind a record is filed under: the kind of its id."""
    return record.id.kind


def close_aliases(
    alias_map: frozendict[Id[Any], Id[Any]], ids: frozenset[Id[Any]]
) -> tuple[frozendict[Id[Any], Id[Any]], tuple[Problem, ...]]:
    """Follow every chain of aliases to its end; report the ones that cannot be followed."""
    closed = {}
    problems = []
    ends = finals(alias_map)
    for old, new in alias_map.items():
        final = ends[old]
        if old in ids:
            why = "a retired id must not still have a record of its own"
        elif final is None:
            why = "the aliases form a cycle"
        elif final not in ids:
            why = "the alias leads to an id that names no record"
        else:
            closed[old] = final
            continue
        error = RefError(why, record_id=old, field=ALIAS_FIELD, target=new)
        problems.append(Problem(ALIAS, old, ALIAS_FIELD, error))
    return frozendict(closed), tuple(problems)


def finals(
    alias_map: frozendict[Id[Any], Id[Any]],
) -> frozendict[Id[Any], Id[Any] | None]:
    """Return the id each retired id finally leads to, or `None` where its chain loops.

    Each chain is walked once and every link on it is recorded, so a long chain costs one
    pass, not one pass per link.
    """
    finals: dict[Id[Any], Id[Any] | None] = {}
    for start in alias_map:
        trail = []
        seen = set()
        current = start
        while current in alias_map and current not in finals and current not in seen:
            trail.append(current)
            seen.add(current)
            current = alias_map[current]
        end = finals.get(current, None if current in seen else current)
        for link in trail:
            finals[link] = end
    return frozendict(finals)


def type_problems(
    groups: tuple[tuple[str, tuple[Record, ...]], ...],
) -> tuple[frozenset[str], tuple[Problem, ...]]:
    """Resolve each kind's field specs once; a kind that cannot be is not checked further."""
    bad = set()
    problems = []
    for kind, group in groups:
        try:
            field_specs(type(group[0]))
        except SchemaError as exc:
            bad.add(kind)
            problems.append(Problem(_SCHEMA, group[0].id, "", exc))
    return frozenset(bad), tuple(problems)


def record_problems(
    records: tuple[Record, ...], bad_kinds: frozenset[str]
) -> tuple[tuple[Problem, ...], tuple[tuple[Id[Any], Reference], ...]]:
    """Check each record on its own; also return every reference found, with its holder.

    One `{class: FieldInfo}` memo, built empty and shared for the whole call, resolves each kind
    or nested `@value` type once, not once per occurrence.
    """
    problems = []
    references = []
    specs: dict[type, FieldInfo] = {}
    for record in records:
        if record.id.kind in bad_kinds:
            continue
        errors, found = _check_record(record, specs)
        for error in errors:
            stage = _SCHEMA if isinstance(error, SchemaError) else _VALUE
            path = ".".join(error.path) if isinstance(error, ValueTypeError) else ""
            problems.append(Problem(stage, record.id, path, error))
        references.extend((record.id, reference) for reference in found)
    return tuple(problems), tuple(references)


def reference_problems(
    references: tuple[tuple[Id[Any], Reference], ...], ids: frozenset[Id[Any]]
) -> tuple[Problem, ...]:
    """Report each reference whose target is not in `ids`, or is of another kind than declared."""
    problems = []
    for holder, reference in references:
        if reference.kind is not None and reference.target.kind != reference.kind:
            why = f"the field declares a {reference.kind} but the id is of another kind"
        elif reference.target not in ids:
            why = "the id names no record"
        else:
            continue
        error = RefError(why, record_id=holder, field=reference.path, target=reference.target)
        problems.append(Problem(_REFERENCE, holder, reference.path, error))
    return tuple(problems)


def cardinality_problems(
    groups: tuple[tuple[str, tuple[Record, ...]], ...],
) -> tuple[Problem, ...]:
    """Enforce `singleton` and `unique`: every record after the first is the offender."""
    offenders = []
    for kind, group in groups:
        cls = vars(type(group[0]))
        if cls.get("__singleton__"):
            why = "at most one record of this kind is allowed in a model"
            offenders.extend((kind, record, why) for record in group[1:])
        subject = cls.get("__subject__")
        if cls.get("__unique__") and subject is not None:
            why = "at most one record of this kind is allowed per subject"
            first = {}
            for record in group:
                owner = getattr(record, subject)
                if isinstance(owner, Id) and first.setdefault(owner, record) is not record:
                    offenders.append((kind, record, why))
    return tuple(
        Problem(_CARDINALITY, record.id, "", SchemaError(why, kind=kind, record_id=record.id))
        for kind, record, why in offenders
    )
