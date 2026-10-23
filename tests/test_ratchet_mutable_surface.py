"""E20: the mutable names of the API surface, a ratchet whose stock only falls.

A surface name is a hit when it is a dict, list or set, or a class that is not a frozen dataclass,
an Enum, an exception, a Protocol, a NamedTuple or a TypedDict. Each object counts once, so a
re-export of one class is one hit. The named builders are exempt: kernel `Draft` and consumer
`Design` (designer ruling 2026-10-16, SURFACE-COHERENCE S1: "the builder is named").
"""

import dataclasses
import enum
import importlib
import importlib.util
import typing
from pathlib import Path

import gate_scan
import pytest

BUILDERS = frozenset({"Draft", "Design"})
_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_surface", _ROOT / "scripts" / "lean_surface.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_surface.py"
    raise ImportError(msg)
lean_surface = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lean_surface)


def _is_mutable(name: str, obj: object) -> bool:
    if isinstance(obj, dict | list | set):
        return True
    if not isinstance(obj, type) or name in BUILDERS:
        return False
    params = getattr(obj, "__dataclass_params__", None)
    immutable = (
        (params is not None and params.frozen)
        or issubclass(obj, enum.Enum | BaseException)
        or getattr(obj, "_is_protocol", False)
        or (issubclass(obj, tuple) and hasattr(obj, "_fields"))
        or typing.is_typeddict(obj)
    )
    return not immutable


def mutable_hits(names: dict[str, dict[str, object]]) -> list[str]:
    """`module.name` of the first surface name of each mutable object, in module then name order."""
    first: dict[int, str] = {}
    for module, objects in names.items():
        for name, obj in objects.items():
            if _is_mutable(name, obj):
                first.setdefault(id(obj), f"{module}.{name}")
    return list(first.values())


@pytest.fixture(scope="module")
def real_names() -> dict[str, dict[str, object]]:
    return {
        module: {name: getattr(importlib.import_module(module), name) for name in surface}
        for module, surface in lean_surface.surface_names().items()
    }


@pytest.mark.private_input  # a private-gate count (R462)
def test_the_real_surface_has_the_stock_of_mutable_names(real_names):
    hits = mutable_hits(real_names)
    gate_scan.check_stock("mutable_surface", len(hits), gate_scan.stock("mutable_surface"))


def test_unionfind_is_a_real_mutable_hit(real_names):
    assert "UnionFind" in {hit.rsplit(".", 1)[1] for hit in mutable_hits(real_names)}


def test_a_dict_constant_is_a_hit():
    assert mutable_hits({"m": {"X": {}}}) == ["m.X"]


def test_a_list_constant_is_a_hit():
    assert mutable_hits({"m": {"X": []}}) == ["m.X"]


def test_an_unfrozen_dataclass_is_a_hit():
    @dataclasses.dataclass
    class Loose:
        x: int = 0

    assert mutable_hits({"m": {"Loose": Loose}}) == ["m.Loose"]


def test_a_plain_class_is_a_hit():
    class Plain:
        pass

    assert mutable_hits({"m": {"Plain": Plain}}) == ["m.Plain"]


def test_frozen_or_immutable_kinds_are_not_hits():
    @dataclasses.dataclass(frozen=True)
    class Frozen:
        x: int = 0

    class Colour(enum.Enum):
        RED = 1

    class OopsError(Exception):
        pass

    class Shape(typing.Protocol):
        def area(self) -> float: ...

    class Pair(typing.NamedTuple):
        a: int
        b: int

    class Movie(typing.TypedDict):
        title: str

    objects: dict[str, object] = {
        "Frozen": Frozen,
        "Colour": Colour,
        "OopsError": OopsError,
        "Shape": Shape,
        "Pair": Pair,
        "Movie": Movie,
        "PAIR_CONST": (1, 2),
    }
    assert mutable_hits({"m": objects}) == []


def test_a_class_named_draft_is_exempt():
    class Draft:
        pass

    assert mutable_hits({"m": {"Draft": Draft}}) == []


def test_a_class_named_design_is_exempt():
    class Design:
        pass

    assert mutable_hits({"m": {"Design": Design}}) == []


def test_one_object_under_two_doors_counts_once():
    class Plain:
        pass

    assert mutable_hits({"a": {"Plain": Plain}, "b": {"Plain": Plain}}) == ["a.Plain"]
