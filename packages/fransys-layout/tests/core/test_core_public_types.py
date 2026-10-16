"""A public core name takes core types and builtins only: no Any, Callable or outside Protocol."""

import annotationlib
import collections.abc as cabc
import importlib
import inspect
import pkgutil
import types
import typing

import pytest

from fransys_layout import core
from fransys_layout.core.values import Cell

CORE = "fransys_layout.core"
# The two sort keys: a named key function is the one Callable parameter S2 allows.
# Neither is exported today (topology_cycles is internal); listed as the order names them.
SORT_KEY_EXEMPT = {
    ("topology_cycles", "rank"),
    ("topology_cycles", "key"),
}  # reason: a sort key, S2 of SURFACE-COHERENCE
GENERIC_HOMES = {"builtins", "typing", "collections.abc", "types"}


def _namespace() -> dict[str, object]:
    """Every name a core annotation may use: typing, collections.abc, and each core module's own."""
    ns: dict[str, object] = {**vars(typing), **vars(cabc)}
    for info in pkgutil.iter_modules(core.__path__):
        ns |= {
            k: v
            for k, v in vars(importlib.import_module(f"{CORE}.{info.name}")).items()
            if not k.startswith("_")
        }
    return ns


def _is_core(obj: object) -> bool:
    module = getattr(obj, "__module__", "") or ""
    return module == CORE or module.startswith(CORE + ".")


_NS = _namespace()


def _bad_generic(ann: object, origin: object) -> list[str]:
    if origin is cabc.Callable:
        return ["Callable"]
    home = getattr(origin, "__module__", "")
    ok = origin is types.UnionType or home in GENERIC_HOMES or _is_core(origin)
    out = [] if ok else [f"generic {origin}"]
    return out + [w for a in typing.get_args(ann) for w in _bad(a)]


def _bad(ann: object) -> list[str]:
    """Why `ann` is not a builtin, a typing generic over those, or a core type; empty when fine."""
    if isinstance(ann, str):
        ann = annotationlib.ForwardRef(ann)
    if isinstance(ann, annotationlib.ForwardRef):
        return _bad(ann.evaluate(globals=dict(_NS)))
    origin = typing.get_origin(ann)
    if ann is typing.Any:
        return ["Any"]
    if origin is not None and origin is not typing.Literal:
        return _bad_generic(ann, origin)
    if getattr(ann, "_is_protocol", False) and not _is_core(ann):
        return [f"Protocol {ann}"]
    plain = ann is None or ann is Ellipsis or origin is typing.Literal
    plain = plain or isinstance(ann, typing.TypeVar)
    home_ok = getattr(ann, "__module__", "") in GENERIC_HOMES or _is_core(ann)
    return [] if plain or home_ok else [f"outside type {ann}"]


def _hints(obj: object) -> dict[str, object]:
    return annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF)


def _signature_problems(name: str, func: object) -> list[str]:
    module = getattr(func, "__module__", "").rsplit(".", 1)[-1]
    found = []
    for param, ann in _hints(func).items():
        if (module, param) in SORT_KEY_EXEMPT:
            continue
        found += [f"{name}({param}): {w}" for w in _bad(ann)]
    return found


def _public_problems() -> list[str]:
    found = []
    for name in core.__all__:
        obj = getattr(core, name)
        if inspect.isfunction(obj):
            found += _signature_problems(name, obj)
        elif inspect.isclass(obj) and _is_core(obj):
            init = obj.__init__
            if inspect.isfunction(init):
                found += _signature_problems(name, init)
    return found


def test_the_public_core_types_are_core_types_and_builtins():
    assert _public_problems() == []


@pytest.mark.parametrize(
    ("ann", "word"),
    [
        (typing.Any, "Any"),
        (cabc.Callable[[str], int], "Callable"),
        (list[typing.Callable[[str], int]], "Callable"),
        (cabc.Mapping[str, typing.Any], "Any"),
        (inspect.Signature, "outside"),
    ],
)
def test_the_type_check_can_fail(ann: object, word: str):
    assert any(word in w for w in _bad(ann))


def test_a_core_type_and_a_builtin_generic_pass():
    assert _bad(core.Box) == _bad(dict[str, tuple[int, ...]]) == _bad(cabc.Mapping[str, Cell]) == []
