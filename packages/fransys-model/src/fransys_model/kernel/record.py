"""`@record` and `@value`.

The two dataclass decorators every kernel and vocab type is declared with (design/kernel-records.md
5.3).

`@record` decorates table kinds: it builds the frozen slotted dataclass, checks its
annotations (`schema.py`) and its `id`, `key`, `ext` fields, and registers the kind
(`registry.py`). `@value` decorates nested value types: the same dataclass and annotation
check, without identity, `key` or `ext`, registered as a value class. `field_specs` is
the lazy half of the check: it resolves reference targets, which may be forward
references, and applies the namespace rule.
"""

import dataclasses
from annotationlib import ForwardRef
from typing import TYPE_CHECKING, Any, Protocol, dataclass_transform, get_args, get_origin
lazy from collections.abc import Callable

from .errors import SchemaError
from .registry import (
    is_value_class,
    namespace_of,
    namespace_rank,
    register_kind,
    register_value_class,
)
from .schema import (
    annotations_of,
    fields_of,
    id_type,
    key_and_value_aliases,
    resolve_target,
    schema_error,
    validate_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .ids import AuthoringKey, Id
    from .values import Value


class Record(Protocol):
    """Structural stand-in for any `@record`-decorated instance: it has `id`, `key`, `ext`.

    Members are read-only properties so a concrete `id: Id[Item]` matches covariantly;
    plain attribute members are invariant and reject every real record.
    """

    @property
    def id(self) -> Id[Any]:
        """The record's primary key."""
        ...

    @property
    def key(self) -> AuthoringKey:
        """The authoring key the id was derived from."""
        ...

    @property
    def ext(self) -> frozendict[str, Value]:
        """Typed-leaf escape hatch for facts not yet modelled."""
        ...


def key_text(record: Record) -> str:
    """Join a record's authoring key with `/`: the one text of a record's key in a message."""
    return "/".join(record.key)


@dataclass_transform(frozen_default=True, kw_only_default=True)
def value[V](cls: type[V]) -> type[V]:
    """Decorate a nested value type: frozen, slotted, keyword-only, no identity.

    Raises:
        SchemaError: a field is annotated with a type outside the closed set.
    """
    built = dataclasses.dataclass(frozen=True, slots=True, kw_only=True)(cls)
    validate_annotations(built)
    register_value_class(built)
    return built


@dataclass_transform(frozen_default=True, kw_only_default=True)
def record[R](
    *, kind: str, subject: str | None = None, unique: bool = False, singleton: bool = False
) -> Callable[[type[R]], type[R]]:
    """Decorate a table record type: frozen, slotted, keyword-only, registered under `kind`.

    `subject` names the field holding the id a facet describes, and `unique=True` means at
    most one record of this `kind` per value of that field. It is a schema rule, so
    `freeze()` enforces it and raises `FreezeError`; it is not a `Finding`. `singleton=True`
    is the same kind of rule for a whole table: at most one record of this `kind` per model
    (`Project`).

    Raises:
        SchemaError: `kind` is malformed or taken, an annotation is outside the closed set,
            `id`, `key` or `ext` is missing or mis-declared, or `subject`/`unique` do not
            fit the fields.
    """

    def decorator(cls: type[R]) -> type[R]:
        built = dataclasses.dataclass(frozen=True, slots=True, kw_only=True)(cls)
        built.__kind__ = kind
        built.__subject__ = subject
        built.__unique__ = unique
        built.__singleton__ = singleton
        validate_annotations(built)
        _check_required_fields(built)
        _check_cardinality(built, subject=subject, unique=unique)
        register_kind(kind, built)
        return built

    return decorator


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FieldSpec:
    """One declared field of a `@record`/`@value` class.

    `ref_kind` is the target kind name (e.g. `"port"`) when the field is an `Id[K]`
    reference, in any of its allowed shapes (`Id[K]`, `Id[K] | None`, `tuple[Id[K], ...]`);
    `None` for a field that is not a reference. An `Id` inside a nested `@value` is not
    this field's reference: `freeze()` walks nested values itself.
    """

    name: str
    ref_kind: str | None


def field_specs(cls: type) -> tuple[FieldSpec, ...]:
    """List `cls`'s declared fields, one `FieldSpec` per field, in declaration order.

    Runs the annotation check again, since a forward reference may now resolve. Resolves
    reference targets now, not at class definition: a target may be a forward reference or
    imported only for type checking, so it is looked up by class name among the registered
    records. A record's `id` is its primary key, so its `ref_kind` is `None`. For a record,
    also applies the namespace rule to every reference, including those in nested `@value`s.

    Raises:
        SchemaError: `cls` is not a `@record` or `@value` class; a field that has since
            resolved is outside the closed set; a reference target cannot be resolved, is
            not a record, or is ambiguous; a record's namespace is not registered; or a
            reference points to a later or unregistered namespace.
    """
    validate_annotations(cls)
    annotations = annotations_of(cls)
    is_record = "__kind__" in vars(cls)
    specs = tuple(
        FieldSpec(
            name=field.name,
            ref_kind=None
            if is_record and field.name == "id"
            else next(_targets(annotations[field.name], cls, field.name, None), None),
        )
        for field in fields_of(cls)
    )
    if is_record:
        _check_namespaces(cls, annotations)
    return specs


def _check_required_fields(cls: type) -> None:
    annotations = annotations_of(cls)
    fields = {field.name: field for field in fields_of(cls)}
    for required in ("id", "key", "ext"):
        if required not in fields:
            raise schema_error(cls, required, "a @record needs `id`, `key` and `ext`")
    authoring_key, value_alias = key_and_value_aliases()
    id_annotation = annotations["id"]
    id_target = get_args(id_annotation)[0] if get_origin(id_annotation) is id_type() else None
    # Matched by name: `slots=True` rebuilds the class, so the annotation cannot name the final one.
    id_target_name = id_target.__forward_arg__ if isinstance(id_target, ForwardRef) else None
    if cls.__name__ not in (id_target_name, getattr(id_target, "__name__", None)):
        raise schema_error(cls, "id", f"must be annotated Id[{cls.__name__}]")
    # These two are checked against the real aliases, so import them at runtime, not under
    # TYPE_CHECKING.
    if annotations["key"] is not authoring_key:
        raise schema_error(cls, "key", "must be annotated AuthoringKey, imported at runtime")
    if get_origin(annotations["ext"]) is not frozendict or get_args(annotations["ext"]) != (
        str,
        value_alias,
    ):
        why = "must be annotated frozendict[str, Value], imported at runtime"
        raise schema_error(cls, "ext", why)
    ext = fields["ext"]
    if ext.default is dataclasses.MISSING and ext.default_factory is dataclasses.MISSING:
        raise schema_error(cls, "ext", "needs a default, frozendict()")


def _check_cardinality(cls: type, *, subject: str | None, unique: bool) -> None:
    if unique and subject is None:
        raise schema_error(cls, "<unique>", "unique=True needs a `subject` field to group by")
    if subject is None:
        return
    if get_origin(annotations_of(cls).get(subject)) is not id_type():
        raise schema_error(cls, subject, "`subject` must name a plain Id[K] field")


def _targets(annotation: object, owner: type, label: str, seen: set[type] | None) -> Iterator[str]:
    """Yield the kind of every `Id[K]` in `annotation`.

    Descends through unions, tuples and mappings. Nested `@value` classes are entered
    only when `seen` is given, once each, so a value that holds itself terminates.
    """
    origin = get_origin(annotation)
    if origin is id_type():
        kind = resolve_target(get_args(annotation)[0], owner, label)
        if kind is not None:
            yield kind
    elif origin is not None:
        for arg in get_args(annotation):
            yield from _targets(arg, owner, label, seen)
    elif (
        seen is not None
        and isinstance(annotation, type)
        and is_value_class(annotation)
        and annotation not in seen
    ):
        seen.add(annotation)
        for name, nested in annotations_of(annotation).items():
            yield from _targets(nested, owner, f"{label}.{name}", seen)


def _check_namespaces(cls: type, annotations: dict[str, Any]) -> None:
    kind = vars(cls)["__kind__"]
    own_rank = namespace_rank(namespace_of(kind))
    if own_rank is None:
        msg = f"kind {kind!r} is in namespace {namespace_of(kind)!r}, which is not registered"
        raise SchemaError(msg, kind=kind)
    seen: set[type] = set()
    for name, annotation in annotations.items():
        for target in _targets(annotation, cls, name, seen):
            target_rank = namespace_rank(namespace_of(target))
            if target_rank is None or target_rank > own_rank:
                msg = (
                    f"{cls.__qualname__}.{name} references {target!r}, in a later or "
                    f"unregistered namespace than {kind!r} (design/kernel-records.md 5.3)"
                )
                raise SchemaError(msg, kind=kind)
