"""M3 of the model review: nothing reachable from a build's result is mutable.

The gate walks every object reachable from `build_scale(N)` (`scale_units_fixture.py`), starting
at the whole `BuildResult`: its `model` (tables, records, values, aliases, origins, hashes,
"""
# CONNECTION_NOT_DRAWN 8 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

import dataclasses
import sys
from collections import Counter
from collections.abc import Iterator, MutableMapping, MutableSequence, MutableSet
from datetime import date, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, NamedTuple, cast
from uuid import UUID

import fransys as fr
import fransys_parts
from _model_build_cover import printed
from scale_units_fixture import (
    build_scale,
    scale_design,
)

from fransys_model.kernel import Id

N = 1
REQUIRED_KINDS = {"item", "function", "port", "conductor", "unit", "boundary"}
MIN_OBJECTS = 1500  # the walk of the N = 1 build visits 1914; an empty walk cannot pass


def _build_scale_with_document(n: int):
    """`build_scale(n)`'s own design, with a document for each location merged in.

    `build_scale` itself must stay document-free (`tests/test_scale_units_fixture.py`:
    it is the "examples' largest build with its documents left
    """
    parts = fransys_parts.load("demo_parts")
    return fr.build(parts, *printed(scale_design(parts, n).draft()))


_MUTABLE = (MutableSequence, MutableMapping, MutableSet, bytearray)
_LEAVES = (str, bytes, int, float, complex, type(None), Decimal, Enum, type, UUID)
_LEAVES += (date, time, timedelta)
_IMMUTABLE_CONTAINERS = (tuple, frozenset, frozendict)


class Walk(NamedTuple):
    """What one walk saw: the type of every visited object, and every mutability finding."""

    types: Counter[type]
    kinds: frozenset[str]
    violations: tuple[tuple[str, str], ...]  # (path, what is mutable there)


def _label(key: object) -> str:
    if isinstance(key, Id):
        return f"<{key.kind}:{key.value[:8]}>"
    text = repr(key)
    return text if len(text) <= 40 else text[:37] + "..."


def _problem(obj: object) -> str | None:
    if isinstance(obj, _MUTABLE):
        return f"mutable {type(obj).__name__}"
    if isinstance(obj, (*_LEAVES, *_IMMUTABLE_CONTAINERS)):
        return None
    if dataclasses.is_dataclass(obj):
        frozen = cast("Any", type(obj)).__dataclass_params__.frozen
        return None if frozen else f"dataclass {type(obj).__name__} is not frozen"
    return f"{type(obj).__name__} instance with a mutable __dict__" if vars_of(obj) else None


def vars_of(obj: object) -> dict[str, object]:
    """The instance `__dict__` of `obj`, empty when it has none."""
    attrs: dict[str, object] = dict(getattr(obj, "__dict__", {}))
    return attrs


def _slot_names(obj: object) -> Iterator[str]:
    for cls in type(obj).__mro__:
        slots = vars(cls).get("__slots__", ())
        yield from (slots,) if isinstance(slots, str) else cast("tuple[str, ...]", slots)


def _children(obj: object, path: str) -> Iterator[tuple[str, object]]:
    if isinstance(obj, _LEAVES):
        return
    if isinstance(obj, (MutableMapping, frozendict)):
        for key, item in obj.items():
            yield f"{path}.<key {_label(key)}>", key
            yield f"{path}[{_label(key)}]", item
    elif isinstance(obj, (tuple, list)):
        yield from ((f"{path}[{i}]", item) for i, item in enumerate(obj))
    elif isinstance(obj, (frozenset, MutableSet)):
        yield from ((f"{path}{{{_label(item)}}}", item) for item in obj)
    elif dataclasses.is_dataclass(obj):
        for field in dataclasses.fields(obj):
            yield f"{path}.{field.name}", getattr(obj, field.name)
    else:
        for name in _slot_names(obj):
            if name not in ("__dict__", "__weakref__") and hasattr(obj, name):
                yield f"{path}.{name}", getattr(obj, name)
        yield from ((f"{path}.{name}", item) for name, item in vars_of(obj).items())


def walk(root: object, name: str) -> Walk:
    """Visit every object reachable from `root` once, iteratively, and collect what is mutable."""
    types: Counter[type] = Counter()
    kinds: set[str] = set()
    violations: list[tuple[str, str]] = []
    seen: set[int] = set()
    stack: list[tuple[str, object]] = [(name, root)]
    while stack:
        path, obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        types[type(obj)] += 1
        kind = vars(type(obj)).get("__kind__")
        if isinstance(kind, str):
            kinds.add(kind)
        if (what := _problem(obj)) is not None:
            violations.append((path, what))
        stack.extend(_children(obj, path))
    return Walk(types, frozenset(kinds), tuple(violations))


def _report(found: Walk) -> str:
    return "\n".join(f"{path}: {what}" for path, what in found.violations)


# The gate itself ------------------------------------------------------------------------------


def test_nothing_reachable_from_the_build_result_is_mutable():
    result = _build_scale_with_document(N)
    found = walk(result, "result")
    assert found.violations == (), _report(found)
    assert sum(found.types.values()) >= MIN_OBJECTS
    assert found.kinds == {k for k, table in result.model.tables.items() if len(table)}
    assert found.kinds >= REQUIRED_KINDS, sorted(REQUIRED_KINDS - found.kinds)
    assert {tuple, frozendict} <= set(found.types)


def _built_kinds(n: int) -> set[str]:
    return {k for k, table in _build_scale_with_document(n).model.tables.items() if len(table)}


def test_n_is_the_smallest_build_that_reaches_every_kind():
    """N - 1 builds strictly fewer kinds and N + 1 adds none: N is neither short nor wasteful."""
    kinds_at_n = _built_kinds(N)
    assert _built_kinds(N - 1) < kinds_at_n
    assert _built_kinds(N + 1) == kinds_at_n
    assert kinds_at_n >= REQUIRED_KINDS


def test_a_mutable_value_smuggled_into_a_real_record_is_found_by_its_path():
    """Can-fail on the real model: `ext` swapped past `freeze()`, first for a dict, then a list."""
    result = build_scale(N)
    record = next(iter(result.model.tables["item"].values()))
    where = f"result.model.tables['item'][{_label(record.id)}].ext"
    object.__setattr__(record, "ext", {"k": 1})
    assert (where, "mutable dict") in walk(result, "result").violations
    object.__setattr__(record, "ext", frozendict({"k": [1]}))
    assert (f"{where}['k']", "mutable list") in walk(result, "result").violations


# The walker can fail --------------------------------------------------------------------------


@dataclasses.dataclass
class _Loose:
    a: int


@dataclasses.dataclass(frozen=True)
class _Tight:
    held: object


@dataclasses.dataclass(slots=True, kw_only=True)
class _LooseSlotted:
    a: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _TightSlotted:
    a: int


class _Plain:
    def __init__(self):
        self.x = 1


def _paths(root: object) -> dict[str, str]:
    return dict(walk(root, "root").violations)


def test_a_dataclass_that_is_not_frozen_is_reported():
    assert _paths(_Tight(held=_Loose(a=1))) == {"root.held": "dataclass _Loose is not frozen"}
    assert _paths(_Loose(a=1)) == {"root": "dataclass _Loose is not frozen"}
    assert _paths((_LooseSlotted(a=1),)) == {"root[0]": "dataclass _LooseSlotted is not frozen"}
    assert _paths((_TightSlotted(a=1),)) == {}


def test_a_list_inside_a_tuple_is_reported():
    assert _paths((1, ("x", [2]))) == {"root[1][1]": "mutable list"}


def test_a_dict_inside_a_frozendict_is_reported_with_its_own_content():
    found = _paths(frozendict({"k": {"inner": [3]}}))
    assert found == {"root['k']": "mutable dict", "root['k']['inner']": "mutable list"}


def test_a_set_and_a_bytearray_are_reported():
    found = _paths(_Tight(held=(set(), bytearray(b"x"))))
    assert found == {"root.held[0]": "mutable set", "root.held[1]": "mutable bytearray"}


def test_a_plain_object_with_a_dict_is_reported():
    assert _paths((_Plain(),)) == {"root[0]": "_Plain instance with a mutable __dict__"}


def test_a_graph_of_immutable_kinds_reports_nothing():
    graph = _Tight(held=(frozenset({1, 2}), frozendict({"a": (Decimal(1), b"x", None)}), "s"))
    found = walk(graph, "root")
    assert found.violations == ()
    assert found.types[frozenset] == found.types[frozendict] == 1


def test_a_cycle_and_a_shared_list_are_reported_once():
    loop: list[object] = []
    loop.append(loop)
    found = walk((loop, loop), "root")
    assert found.violations == (("root[1]", "mutable list"),)  # the stack pops the last member first


def test_a_very_deep_graph_does_not_hit_the_recursion_limit():
    deep: object = [0]
    for _ in range(sys.getrecursionlimit() * 3):
        deep = (deep,)
    assert len(walk(deep, "root").violations) == 1
