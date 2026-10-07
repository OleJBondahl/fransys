"""Kernel origins: where a record was authored (kernel-records.md 5.4 and kernel-model.md 5.8)."""

from typing import Any, Protocol
lazy from collections.abc import Mapping

from .errors import (
    FreezeError,
    MergeConflict,
    RefError,
    SchemaError,
    SchemaVersionError,
    ValueTypeError,
)
from .findings import Finding
from .ids import render_id
from .record import value
lazy from .errors import ModelError
lazy from .ids import AuthoringKey, Id


@value
class Origin:
    """File, line and note of where a record was authored.

    Lives in `Model.origins`, outside the tables: excluded from hashes, the digest and
    default canonical output, because a moved line is not a change to the plant.
    """

    file: str
    line: int
    note: str


def require_origin[K](origins: Mapping[Id[K], Origin], target: Id[K]) -> Origin:
    """Return where `target` was authored.

    Raises:
        SchemaError: `origins` has none for `target`, or what it holds is not an `Origin`;
            nothing is invented in its place.
    """
    found = origins.get(target)
    if not isinstance(found, Origin):
        msg = f"no origin is known for {render_id(target)}"
        raise SchemaError(msg, kind=target.kind, record_id=target)
    return found


class OriginSource(Protocol):
    """Anything `describe` can ask where an id was authored: a `Model`, or a `Draft`."""

    def origin_of(self, target: Id[Any]) -> Origin | None:
        """Where the record `target` was authored, or `None` if nothing is known."""
        ...

    def key_of(self, target: Id[Any]) -> AuthoringKey | None:
        """The authoring key of the record `target`, or `None` if no record holds it."""
        ...


def describe(problem: ModelError | Finding, source: OriginSource) -> str:
    """Render `problem` as text with every id it carries shown as its origin (kernel-model.md 5.8).

    The only place ids are turned into text for humans. The message is printed verbatim,
    never inspected: one labelled line per id-bearing field follows it. Pure and total: an
    id with no origin or no record falls back to `unknown origin (...)`, and `Id.value` is
    never printed.
    """
    return "\n".join(_lines(problem, source))


def _lines(problem: ModelError | Finding, source: OriginSource) -> tuple[str, ...]:
    if isinstance(problem, Finding):
        subjects = (f"  subject: {_render(s, source)}" for s in problem.subjects)
        return (f"{problem.code} ({problem.severity.value}): {problem.message}", *subjects)
    lines = str(problem).splitlines() or [""]
    lines += _extra_lines(problem, source)
    return tuple(lines)


def _freeze_lines(problem: FreezeError, source: OriginSource) -> list[str]:
    lines: list[str] = []
    for number, error in enumerate(problem.errors, start=1):
        prefix = f"  {number}. "
        first, *rest = _lines(error, source)
        lines += [prefix + first, *(" " * len(prefix) + line for line in rest)]
    return lines


def _extra_lines(problem: ModelError, source: OriginSource) -> list[str]:
    # A new error that carries ids gets a case here, above any base class it inherits from.
    extra: list[str] = []
    match problem:
        case FreezeError():
            extra = _freeze_lines(problem, source)
        case RefError():
            extra = [
                f"  record: {_render(problem.record_id, source)}",
                f"  field: {problem.field}",
                f"  target: {_render(problem.target, source)}",
            ]
        case MergeConflict():
            extra = [
                f"  record: {_render(problem.record_id, source)}",
                f"  first: {problem.origin_a.file}:{problem.origin_a.line}",
                f"  second: {problem.origin_b.file}:{problem.origin_b.line}",
            ]
        case SchemaError():
            extra = [*_holder(problem.record_id, source), f"  kind: {problem.kind}"]
        case ValueTypeError():
            path = ".".join(problem.path) or "<top level>"
            extra = [*_holder(problem.record_id, source), f"  path: {path}"]
        case SchemaVersionError():
            extra = [f"  expected: {problem.expected}", f"  actual: {problem.actual}"]
    return extra


def _holder(record_id: Id[Any] | None, source: OriginSource) -> tuple[str, ...]:
    return () if record_id is None else (f"  record: {_render(record_id, source)}",)


def _render(target: Id[Any], source: OriginSource) -> str:
    origin = source.origin_of(target)
    key = source.key_of(target)
    where = None if origin is None else f"{origin.file}:{origin.line}"
    named = None if key is None else "/".join(key)
    if where is not None and named is not None:
        return f"{where} ({named})"
    if where is not None:
        return where
    if named is not None:
        return f"unknown origin ({named})"
    return f"unknown origin (kind {target.kind})"
