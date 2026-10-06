"""EA11 and EA13: every public name of the author engine has a row in the coverage table.

The engine's public names are found by walking the union of the MROs of Scope, Design,
LinkScope, Fn, Item, Strip, Terminal, Cable and Wiring. A class counts when its module is in
`fransys_author`. Its names come from its own `vars`: a public function or property, plus
`__call__` and `__getitem__`. A name is keyed "Class.name" by the class that defines it. Data
fields (ids, keys, colour, gauge) are not rows.
"""

import importlib
import inspect
import re

import pytest
from fransys_author import design as engine_design
from fransys_author import handles, wiring
from fransys_author.surface import Design, Device, Fn, TerminalStrip

from .coverage_table import ROWS

_ENGINE = (
    engine_design.Scope,
    engine_design.Design,
    wiring.LinkScope,
    handles.Fn,
    handles.Item,
    handles.Strip,
    handles.Terminal,
    handles.Cable,
    wiring.Wiring,
)
_LAYOUT = getattr(importlib.import_module("fransys_author.surface._layout"), "Layout", None)
_CABLE = getattr(importlib.import_module("fransys_author.surface._cable"), "Cable", None)
_SURFACE = {
    "Design": Design,
    "Device": Device,
    "Fn": Fn,
    "TerminalStrip": TerminalStrip,
    "Terminal": handles.Terminal,
    "Layout": _LAYOUT,
    "Cable": _CABLE,
}
_SPELLING = re.compile(r"(\w+)\.(\w+)(?:\((\w+)=\))?")
_ABSENT_FROM_DESIGN = ("item", "strip", "wiring", "link", "supply", "scope", "group")


def engine_names() -> set[str]:
    """The "Class.name" of every public function or property of the engine classes."""
    names: set[str] = set()
    for root in _ENGINE:
        for cls in root.__mro__[:-1]:
            if not cls.__module__.startswith("fransys_author"):
                continue
            for name, value in vars(cls).items():
                func = value.fget if isinstance(value, property) else value
                public = not name.startswith("_") or name in ("__call__", "__getitem__")
                if public and callable(func):
                    names.add(f"{cls.__name__}.{name}")
    return names


def name_differences(found: set[str], keys: set[str]) -> str:
    """The names with no row and the rows with no name, empty when the sets are equal."""
    missing, extra = sorted(found - keys), sorted(keys - found)
    if not (missing or extra):
        return ""
    return f"engine names with no row: {missing}; rows with no engine name: {extra}"


def resolves(spelling: str) -> bool:
    """True when `Class.attr` is on a surface class and `(kw=)`, if any, is a parameter."""
    match = _SPELLING.fullmatch(spelling)
    assert match, f"{spelling!r} is not Class.attr or Class.attr(kw=)"
    cls_name, attr, keyword = match.groups()
    cls = _SURFACE.get(cls_name)
    if cls is None or not hasattr(cls, attr):
        return False
    if keyword is None:
        return True
    code = getattr(inspect.unwrap(getattr(cls, attr)), "__code__", None)
    return (
        code is not None
        and keyword in code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
    )


def _entries(kind: str) -> list[tuple[str, tuple[str, ...]]]:
    return [(key, e) for key, row in ROWS.items() for e in row if e[0] == kind]


def test_every_engine_public_name_has_a_row() -> None:
    assert not name_differences(engine_names(), set(ROWS))


def test_a_missing_row_is_reported() -> None:
    mutated = {k: v for k, v in ROWS.items() if k != "Scope.item"}
    assert "Scope.item" in name_differences(engine_names(), set(mutated))
    assert "Scope.zzz" in name_differences(engine_names() | {"Scope.zzz"}, set(ROWS))


@pytest.mark.parametrize(("key", "entry"), _entries("surface"), ids=str)
def test_every_surface_spelling_resolves(key: str, entry: tuple[str, ...]) -> None:
    assert resolves(entry[1]), f"{key}: {entry[1]} is not on the surface yet"


def test_a_pending_spelling_is_not_resolved_and_names_its_order() -> None:
    """Loops over the pending rows, so it passes with none left (parametrize would skip)."""
    for key, entry in _entries("pending"):
        assert entry[1] in ("EA-SERIES", "EA-UNITS-RUNS"), f"{key}: unknown order {entry[1]}"
        assert not resolves(entry[2]), f"{key}: {entry[2]} landed, so flip the row to surface"


@pytest.mark.parametrize(("key", "entry"), _entries("dropped"), ids=str)
def test_a_dropped_row_has_a_reason(key: str, entry: tuple[str, ...]) -> None:
    assert len(entry) == 2
    assert entry[1].strip(), f"{key}: a dropped row needs a reason"


def test_every_row_has_entries_of_a_known_kind() -> None:
    kinds = {"surface": 2, "pending": 3, "dropped": 2}
    for key, row in ROWS.items():
        assert row, key
        for entry in row:
            assert len(entry) == kinds[entry[0]], f"{key}: {entry}"


@pytest.mark.parametrize("name", _ABSENT_FROM_DESIGN)
def test_engine_names_spelled_differently_are_not_design_attributes(name: str) -> None:
    assert not hasattr(Design, name), f"Design.{name} is a second spelling"
