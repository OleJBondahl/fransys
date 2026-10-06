"""M3 of the model review: nothing reachable from a build's result is mutable.

The gate walks every object reachable from `build_scale(N)` (`scale_units_fixture.py`), starting
at the whole `BuildResult`: its `model` (tables, records, values, aliases, origins, hashes,
digests) and its `findings`. It fails, with the attribute path, on any `list`, `dict`, `set`,
`bytearray` (and any other `MutableSequence`, `MutableMapping` or `MutableSet`), on any dataclass
instance whose `__dataclass_params__.frozen` is False, and on any other instance carrying a
`__dict__`. The `BuildResult` holds only the `Model` and the findings tuple, so there is no Draft
or other mutable member to walk apart.

What is followed: dataclass fields (`dataclasses.fields`), `__slots__` and `__dict__` of any other
object, tuple and list members, set and frozenset members, and `frozendict` keys and values.
Enums, `Decimal`, `str`, `bytes`, numbers, `UUID`, dates and classes are leaves. Objects are
visited once by identity (cycles and shared objects), with an explicit stack, so depth never
reaches the recursion limit.

N = 1 is the smallest that works: the fixture builds 21 record kinds at N = 0 and 41 at N = 1, 2
and 3 (`test_n_is_the_smallest_build_that_reaches_every_kind` below re-proves it; the demo parts'
rating tables added `facet.rating`, `facet.part_rating` and `facet.operating`, model-0079; the
project's `Revision` entry added `revision`, schema SC4; the numbering pass's
`facet.assigned_designation` added one, the SC3 split; a unit's release record added
`unit_release`, SC2; FUSE-LINK's PCB fuse holder added `facet.footprint`, the demo
library's first), and
immutability is a property of a type, not of how many instances a build has. Two of the two
kind-counting tests below build through `_build_scale_with_document`, not `build_scale`
directly: decision 0037 (PS1) gates layout on the model holding a `Document`, and `build_scale`
itself must stay document-free (acceptance 6 of MODEL-BUILD -- the examples' largest build with
its documents left out), so this file's own document-bearing variant is what reaches the
`layout.*` kinds and adds `document` itself (one more kind than the pre-0037 39, since no build
here ever held a document before). Thirteen of the 54 registered kinds are still not built by
this fixture, so this walk does not reach them: `supply_system`, `facet.boundary_values`,
`facet.plc_binding`, `facet.plc_request`, `facet.scaling`, and the `layout.*`
hints `break_before`, `chain`, `group_hint`, `keep_together`, `link_marker`, `order_hint`,
`profile`, `sheet_format`.
"""

import dataclasses
import sys
from collections import Counter
from collections.abc import Iterator, MutableMapping, MutableSequence, MutableSet
from datetime import date, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import NamedTuple
from uuid import UUID

import fransys as fr
import fransys_parts

from fransys_model.kernel import Id

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from _model_build_cover import system_document  # noqa: E402
from scale_units_fixture import (  # noqa: E402
    build_scale,
    scale_design,
)

N = 1
REQUIRED_KINDS = {"item", "function", "port", "conductor", "unit", "boundary"}
MIN_OBJECTS = 1500  # the walk of the N = 1 build visits 1914; an empty walk cannot pass


def _build_scale_with_document(n: int):
    """`build_scale(n)`'s own design, with a `system_document()` merged in.

    `build_scale` itself must stay document-free (`tests/test_scale_units_fixture.py`,
    acceptance 6 of MODEL-BUILD: it is the "examples' largest build with its documents left
    out" measurement). Decision 0037 (PS1) gates layout on a document, so without one this
    walk's own build reaches none of the `layout.*` kinds -- this helper is this file's own
    document-bearing build, reached from `scale_design` directly, never from `build_scale`.
    """
    parts = fransys_parts.load("demo_parts")
    return fr.build(parts, scale_design(parts, n).draft(), system_document())


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
        frozen = type(obj).__dataclass_params__.frozen  # ty: ignore[unresolved-attribute]
        return None if frozen else f"dataclass {type(obj).__name__} is not frozen"
    return f"{type(obj).__name__} instance with a mutable __dict__" if vars_of(obj) else None


def vars_of(obj: object) -> dict[str, object]:
    """The instance `__dict__` of `obj`, empty when it has none."""
    return getattr(obj, "__dict__", {})


def _slot_names(obj: object) -> Iterator[str]:
    for cls in type(obj).__mro__:
        slots = vars(cls).get("__slots__", ())
        yield from (slots,) if isinstance(slots, str) else slots


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
    assert len(kinds_at_n) == 41


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
    assert found.violations == (
        ("root[1]", "mutable list"),
    )  # the stack pops the last member first


def test_a_very_deep_graph_does_not_hit_the_recursion_limit():
    deep: object = [0]
    for _ in range(sys.getrecursionlimit() * 3):
        deep = (deep,)
    assert len(walk(deep, "root").violations) == 1
