"""Ratchet E21: objects reachable under two surface doors, and one name bound to two objects.

A twin is one runtime object (by identity) in the `__all__` of two or more surface modules; a
small immutable scalar constant is skipped. A clash is one public name bound to two different
objects across surface modules. Both stocks only fall (`tests/ratchets.toml [twin_doors]`).
"""

import importlib
import importlib.util
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest
from gate_scan import ROOT, check_stock, stock

if TYPE_CHECKING:
    from collections.abc import Mapping

_spec = importlib.util.spec_from_file_location(
    "fransys_lean_surface_twins", ROOT / "scripts" / "lean_surface.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_surface.py"
    raise ImportError(msg)
lean_surface = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_surface
_spec.loader.exec_module(lean_surface)

# Designer ruling 2026-10-16: the facade is the consumer's one door (invariant 2), so its re-export
# of the same object is no twin. A facade name bound to a different object is still a clash.
FACADE = "fransys"
SCALARS = (str, bytes, int, float, bool, type(None))


def twin_objects(doors: Mapping[str, Mapping[str, object]]) -> list[tuple[str, ...]]:
    """The modules of each non-scalar object found in two or more doors, the facade not a door."""
    homes: dict[int, set[str]] = defaultdict(set)
    for module, names in doors.items():
        if module == FACADE:
            continue
        for obj in names.values():
            if not isinstance(obj, SCALARS):
                homes[id(obj)].add(module)
    return [tuple(sorted(found)) for found in homes.values() if len(found) > 1]


def clashing_names(doors: Mapping[str, Mapping[str, object]]) -> dict[str, tuple[str, ...]]:
    """Each name bound to two different objects, with the modules that bind it."""
    bound: dict[str, dict[int, str]] = defaultdict(dict)
    for module, names in doors.items():
        for name, obj in names.items():
            bound[name].setdefault(id(obj), module)
    return {name: tuple(sorted(by_id.values())) for name, by_id in bound.items() if len(by_id) > 1}


@pytest.fixture(scope="module")
def doors() -> dict[str, dict[str, object]]:
    """Module -> {name: object} over every surface module."""
    names = lean_surface.surface_names()
    return {
        module: {name: getattr(importlib.import_module(module), name) for name in found}
        for module, found in names.items()
    }


@pytest.mark.private_input  # a private-gate count (R462)
def test_twins_stock(doors):
    check_stock("twin_doors", len(twin_objects(doors)), stock("twin_doors", "twins"))


@pytest.mark.private_input  # a private-gate count (R462)
def test_clashes_stock(doors):
    check_stock("twin_doors", len(clashing_names(doors)), stock("twin_doors", "clashes"))


def test_twin_helper_counts_one_object_under_two_doors():
    shared = object()
    doors = {"a": {"x": shared, "y": object()}, "b": {"z": shared}}
    assert twin_objects(doors) == [("a", "b")]


def test_twin_helper_skips_scalars_and_distinct_objects():
    doors = {"a": {"x": 1, "y": object()}, "b": {"x": 1, "y": object()}}
    assert twin_objects(doors) == []


def test_clash_helper_counts_one_name_two_objects():
    doors = {"p.a": {"x": object()}, "q.b": {"x": object()}}
    assert clashing_names(doors) == {"x": ("p.a", "q.b")}


def test_clash_helper_ignores_same_object_and_different_names():
    shared = object()
    doors = {"a": {"x": shared, "y": object()}, "b": {"x": shared, "z": object()}}
    assert clashing_names(doors) == {}


def test_at_least_one_clash_is_cross_package(doors):
    clashes = clashing_names(doors)
    packages = [{m.split(".")[0] for m in mods} for mods in clashes.values()]
    assert any(len(p) > 1 for p in packages), clashes


def test_a_facade_re_export_of_one_object_is_no_twin():
    shared = object()
    doors = {"fransys": {"x": shared}, "fransys_model": {"x": shared}}
    assert twin_objects(doors) == []


def test_an_object_under_two_non_facade_doors_is_still_a_twin_beside_the_facade():
    shared = object()
    doors = {"fransys": {"x": shared}, "a": {"x": shared}, "b": {"x": shared}}
    assert twin_objects(doors) == [("a", "b")]


def test_a_facade_name_bound_to_a_different_object_is_a_clash():
    doors = {"fransys": {"x": object()}, "fransys_model": {"x": object()}}
    assert clashing_names(doors) == {"x": ("fransys", "fransys_model")}
