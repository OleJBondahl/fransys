"""L6 gate: `SCHEMA_VERSION` becomes a contract (spec 2026-09-23-baseline.md, L6).

A fingerprint of the record registry -- every production `@record` kind, its fields and
their types, recursively through any `@value` type a field's annotation actually names --
is pinned together with `SCHEMA_VERSION`. A change to any record's shape without a bump
fails this test.

`kernel.registry`'s `_kinds` and `_value_classes` are global, module-level and never
cleared: a test elsewhere in the suite that defines a test-local `@record`/`@value` class
at module scope registers into these same dicts for the rest of the worker process, and
under `pytest-xdist` which test files a worker happens to have already imported is not
deterministic. The fingerprint below is scoped to keep this test's pinned value stable
regardless of that:

- only a registered kind whose class's `__module__` starts with `"fransys_model."` (the
  real package) is walked; a test module's classes live under a different `__module__`
  (`test_*`, `*_probes`, ...) and are excluded;
- `fransys_model.vocab` and `fransys_model.layout` are imported here so every real
  kind the package ships is registered before the walk runs, whatever else has or has not
  been imported by other tests in this worker;
- every kind, its fields and any nested `@value` type are walked in a fixed sort order, so
  the fingerprint's construction never depends on registration order or `dict` iteration
  order;
- an annotation is rendered by walking its own structure (`get_origin`/`get_args`, each
  leaf's `__name__`), never by a bare `repr()`, which can carry a module path or an
  address-flavoured string that is not guaranteed stable.

Only a `@value` type a `@record` field's annotation actually names is walked -- not the
whole of `_value_classes` -- so a report-row `@value` type (`TerminalRow` and friends, none
of which any `@record` field references) never moves this fingerprint.
"""

import hashlib
import json
import types
from annotationlib import ForwardRef
from types import NoneType
from typing import Any, TypeAliasType, get_args, get_origin

import fransys_model.layout  # noqa: F401 -- imported to register the layout vocabulary
import fransys_model.vocab  # noqa: F401 -- imported to register its kinds, not for its names
from fransys_model.kernel import SCHEMA_VERSION, registry, schema
from fransys_model.kernel.registry import is_value_class

_PRODUCTION_PREFIX = "fransys_model."


def _is_production(cls: type) -> bool:
    """Whether `cls` was declared inside the real package, not a test module."""
    return cls.__module__.startswith(_PRODUCTION_PREFIX)


def _render_annotation(annotation: object) -> str:
    """A stable string for `annotation`, built from its own structure, never a bare `repr()`."""
    origin = get_origin(annotation)
    if annotation is None:
        result = "None"
    elif origin is types.UnionType:
        member = next(arg for arg in get_args(annotation) if arg is not NoneType)
        result = f"{_render_annotation(member)} | None"
    elif origin is tuple:
        result = f"tuple[{_render_annotation(get_args(annotation)[0])}, ...]"
    elif origin is frozendict:
        result = f"frozendict[str, {_render_annotation(get_args(annotation)[1])}]"
    elif origin is schema.id_type():
        result = f"Id[{_render_id_target(get_args(annotation)[0])}]"
    elif isinstance(annotation, TypeAliasType | type):
        result = annotation.__name__
    else:
        result = repr(annotation)
    return result


def _render_id_target(target: object) -> str:
    """The name `Id[...]` carries: a forward name, `Any`, or a class's own `__name__`."""
    if isinstance(target, ForwardRef):
        return target.__forward_arg__
    if target is Any:
        return "Any"
    assert isinstance(target, TypeAliasType | type)
    return target.__name__


def _nested_values(annotation: object) -> tuple[type, ...]:
    """Every `@value` class `annotation` names: directly, or inside `tuple`/`frozendict`/`| None`.

    An `Id[K]` never names a `@value` (it references a record), so the walk stops there.
    """
    origin = get_origin(annotation)
    if origin is types.UnionType:
        member = next(arg for arg in get_args(annotation) if arg is not NoneType)
        return _nested_values(member)
    if origin is tuple:
        return _nested_values(get_args(annotation)[0])
    if origin is frozendict:
        return _nested_values(get_args(annotation)[1])
    if origin is schema.id_type():
        return ()
    if isinstance(annotation, type) and is_value_class(annotation):
        return (annotation,)
    return ()


def _field_entries(cls: type) -> list[dict[str, str]]:
    """`cls`'s fields, sorted by name, each as its name and its annotation's stable string."""
    annotations = schema.annotations_of(cls)
    return [
        {"name": field.name, "type": _render_annotation(annotations[field.name])}
        for field in sorted(schema.fields_of(cls), key=lambda field: field.name)
    ]


def _walk_value(cls: type, seen: set[type], values: dict[str, list[dict[str, str]]]) -> None:
    """Add `cls` and, recursively, every `@value` a field of it names, to `values`."""
    if cls in seen:
        return
    seen.add(cls)
    values[cls.__name__] = _field_entries(cls)
    annotations = schema.annotations_of(cls)
    for field in schema.fields_of(cls):
        for nested in _nested_values(annotations[field.name]):
            _walk_value(nested, seen, values)


def _fingerprint() -> str:
    """The SHA-256 of a canonical string over `SCHEMA_VERSION`, every production `@record`
    kind and its fields, and every `@value` type a field of one actually names.
    """
    kinds = {kind: cls for kind, cls in registry._kinds.items() if _is_production(cls)}
    values: dict[str, list[dict[str, str]]] = {}
    seen: set[type] = set()
    kind_entries = []
    for kind in sorted(kinds):
        cls = kinds[kind]
        kind_entries.append({"kind": kind, "class": cls.__name__, "fields": _field_entries(cls)})
        annotations = schema.annotations_of(cls)
        for field in schema.fields_of(cls):
            for nested in _nested_values(annotations[field.name]):
                _walk_value(nested, seen, values)
    structure = {
        "schema_version": SCHEMA_VERSION,
        "kinds": kind_entries,
        "values": [{"class": name, "fields": fields} for name, fields in sorted(values.items())],
    }
    text = json.dumps(structure, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_PINNED_FINGERPRINT = "210172cc4fc7abeb7c700fe30d9171197551104d9e7700b6acc49c0bd8d88733"


def test_schema_fingerprint_matches_the_pinned_value() -> None:
    """L6: a change to any record's shape with no matching `SCHEMA_VERSION` bump fails here."""
    assert _fingerprint() == _PINNED_FINGERPRINT
