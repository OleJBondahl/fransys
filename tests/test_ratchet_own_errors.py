"""Ratchet E23: a surface module raises its package's own base error (SURFACE-COHERENCE R1).

`foreign_raises` lists the raises of one source whose class is not in `base_names`; with no base
(`None`) it lists only the builtin ValueError, KeyError, TypeError and OSError. The stock per
package is `[own_errors_<package>]` in `tests/ratchets.toml`; it only falls.
"""

import ast
import importlib
import importlib.util
import sys
import textwrap
from typing import TYPE_CHECKING

import pytest
from gate_scan import ROOT, check_stock, package_of, src_modules, stock

if TYPE_CHECKING:
    from pathlib import Path

BUILTINS = {"ValueError", "KeyError", "TypeError", "OSError"}
# package -> (module holding its base error, base error name); "none" packages are absent.
BASES = {
    "fransys_kernel": ("fransys_kernel", "ModelError"),
    "fransys_model": ("fransys_model.kernel", "ModelError"),
    "fransys_author": ("fransys_author", "AuthorError"),
    "fransys_parts": ("fransys_parts", "PartLibraryError"),
    "fransys_layout": ("fransys_layout.geometry.errors", "LayoutError"),
}


# layout-0313: the stdlib-only core has its own base, so its raises count as own.
EXTRA_BASES = {"fransys_layout": [("fransys_layout.core.errors", "CoreError")]}


def _load_lean_surface():
    spec = importlib.util.spec_from_file_location("lean_surface", ROOT / "scripts/lean_surface.py")
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["lean_surface"] = module
    spec.loader.exec_module(module)
    return module


def _raised_name(node: ast.Raise) -> str | None:
    """The class name a raise names (call or bare, attribute tail); None for a bare re-raise."""
    target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
    return name if name[:1].isupper() else None


def foreign_raises(source: str, base_names: set[str] | None) -> list[tuple[int, str]]:
    """`(line, name)` of each raise whose class is not in `base_names`; `None` = builtins only."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        name = _raised_name(node)
        if name is None:
            continue
        if (base_names is None and name in BUILTINS) or (
            base_names is not None and name not in base_names
        ):
            found.append((node.lineno, name))
    return found


def _subclass_names(package: str) -> set[str]:
    """The names of the package's base errors and of all their loaded subclasses."""
    for module, _ in src_modules():
        if package_of(module) == package:
            importlib.import_module(module)
    names, todo = (
        set(),
        [
            getattr(importlib.import_module(home), name)
            for home, name in (BASES[package], *EXTRA_BASES.get(package, ()))
        ],
    )
    while todo:
        cls = todo.pop()
        names.add(cls.__name__)
        todo += cls.__subclasses__()
    return names


def _surface_hits() -> list[tuple[str, Path]]:
    """`(package, file)` for each source file of a surface module."""
    surface = set(_load_lean_surface().surface_modules())
    return [
        (package_of(module), path)
        for module, path in src_modules()
        if any(module == name or module.startswith(f"{name}.") for name in surface)
    ]


def _surface_keys() -> list[str]:
    """The packages with a surface module; collection needs their names for parametrize."""
    return sorted({package for package, _ in _surface_hits()})


@pytest.fixture(scope="module")
def files() -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {}
    for package, path in _surface_hits():
        grouped.setdefault(package, []).append(path)
    return grouped


@pytest.mark.parametrize("package", _surface_keys())
@pytest.mark.private_input  # a private-gate count (R462)
def test_surface_modules_raise_own_errors(package, files):
    names = _subclass_names(package) if package in BASES else None
    found = sum(
        len(foreign_raises(path.read_text(encoding="utf-8"), names)) for path in files[package]
    )
    check_stock(f"own_errors_{package}", found, stock(f"own_errors_{package}"))


def test_every_package_has_a_row(files):
    import tomllib

    from gate_scan import RATCHETS

    with RATCHETS.open("rb") as handle:
        rows = tomllib.load(handle)
    for package in files:
        assert f"own_errors_{package}" in rows, f"no [own_errors_{package}] row"
        want = BASES[package][1] if package in BASES else "none"
        assert rows[f"own_errors_{package}"]["base"] == want


def test_foreign_raise_found():
    src = "def f():\n    raise ValueError('x')\n"
    assert foreign_raises(src, {"ModelError"}) == [(2, "ValueError")]


def test_base_raise_not_found():
    src = "def f():\n    raise ModelError('x')\n\ndef g():\n    try:\n        f()\n    except Exception:\n        raise\n"  # noqa: E501 -- one-line synthetic source
    assert foreign_raises(src, {"ModelError"}) == []


def test_subclass_name_not_found():
    src = textwrap.dedent("def f():\n    raise errors.SchemaError('x')\n")
    assert foreign_raises(src, {"ModelError", "SchemaError"}) == []
    assert foreign_raises(src, {"ModelError"}) == [(2, "SchemaError")]


def test_none_base_counts_builtins_only():
    src = "def f():\n    raise ProblemError('x')\n\ndef g():\n    raise KeyError('k')\n"
    assert foreign_raises(src, None) == [(5, "KeyError")]
