"""`just api <package>` (MS9): prints one package's API surface, on demand, never stored.

Built directly from the installed code each time it runs, using `scripts/lean_surface.py`'s
`surface_modules`/`surface_names`/`resolve_surface_names` (the one home of "the surface") --
never a stored module list of its own, so it cannot drift from what `tests/test_boundaries.py`
and the docstring/type gates already enforce. For `fransys_model`, the package's surface is
the seven modules MS1 names; for every other package it is that package's own top-level module
(and, for `fransys`, `fransys.colours` too, MS8's "kept separately" module) -- one rule,
`_package_modules`, with no special case for the model. Byte-identical across two calls on the
same commit: no object address, no set-order iteration, no cwd- or clock-dependent text anywhere
in the output.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imports `scripts/lean_surface.py`
the same way (there is no scripts package to import from).
"""

from __future__ import annotations

import ast
import copy
import importlib
import importlib.util
import inspect
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, override

if TYPE_CHECKING:
    from collections.abc import Iterable

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LEAN_SURFACE_NAME = "fransys_lean_surface"


class _ResolvedName(Protocol):
    """The two `lean_surface.SurfaceName` fields `_entry_text` reads.

    Structural, not imported: `lean_surface` is loaded dynamically (module docstring), so `ty`
    never sees its real dataclass. A resolved `SurfaceName` instance satisfies this shape, and
    ty checks attribute access against it instead of against `Any` or the attribute-less `object`
    (where `is not None` narrowing still leaves no known attributes).
    """

    defining_file: Path
    qualname: str


def _load_lean_surface() -> types.ModuleType:
    """Load `scripts/lean_surface.py` the way its own tests do, reusing a prior load."""
    if _LEAN_SURFACE_NAME in sys.modules:
        return sys.modules[_LEAN_SURFACE_NAME]
    spec = importlib.util.spec_from_file_location(
        _LEAN_SURFACE_NAME, _SCRIPTS_DIR / "lean_surface.py"
    )
    if spec is None or spec.loader is None:
        msg = "could not load scripts/lean_surface.py"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_LEAN_SURFACE_NAME] = module
    spec.loader.exec_module(module)
    return module


lean_surface = _load_lean_surface()


class UnknownPackageError(Exception):
    """`api()` was asked for a package name that owns no surface module."""


def _package_modules(package: str, modules: Iterable[str] | None = None) -> tuple[str, ...]:
    """Every surface module dotted path that belongs to `package`.

    A module belongs to `package` when it IS `package`, or is one of its dotted submodules
    (`package.something`) -- the general rule that, applied to `fransys_model`, picks out its
    seven MS1 modules with no special case, since `surface_modules()` already spells each of
    them as `fransys_model.<name>`. Applied to `fransys`, it also picks up
    `fransys.colours` (MS8's module kept separately). `modules` defaults to
    `lean_surface.surface_modules()`; a test passes its own small list instead.
    """
    if modules is None:
        modules = lean_surface.surface_modules()
    return tuple(m for m in modules if m == package or m.startswith(f"{package}."))


class _SurfaceNames(ast.NodeTransformer):
    """Rewrites a private-module reference (`_args.Design`) to the surface name (`Design`).

    The one rule for both outputs: an attribute whose name is in the package's `__all__` prints
    as that bare name, so a signature never shows a `_`-prefixed module path.
    """

    def __init__(self, surface: frozenset[str]) -> None:
        self._surface = surface

    @override
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        if node.attr in self._surface:
            return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return self.generic_visit(node)


def _surface_of(module_path: str) -> frozenset[str]:
    """Every name in `module_path`'s own `__all__`."""
    return frozenset(lean_surface.surface_names((module_path,))[module_path])


def _signature_text(node: ast.AST | None, surface: frozenset[str] = frozenset()) -> str:
    """`(params) -> returns`, built from the AST node's own signature text; `""` for a class.

    Read from the source `ast`, never `inspect.signature` on the live object: Python 3.15's
    lazy-annotation evaluation (PEP 749) raises `NameError` on a forward-referenced type that is
    only imported under `TYPE_CHECKING` (real case: `fransys_pdf.check`'s `model: Model`
    parameter) the moment anything asks for its resolved annotations. `ast.unparse` prints the
    written text as-is and never resolves a name, so it cannot hit that trap.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    node = _SurfaceNames(surface).visit(copy.deepcopy(node))
    params = ast.unparse(node.args)
    if node.returns is None:
        return f"({params})"
    return f"({params}) -> {ast.unparse(node.returns)}"


def _docstring_block(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None) -> str:
    """`node`'s own literal AST docstring (never the runtime `__doc__`), indented; `""` if none."""
    if node is None:
        return ""
    docstring = lean_surface.literal_docstring(node)
    if docstring is None:
        return ""
    lines = docstring.value.strip("\n").splitlines()
    return "\n".join(f"    {line}" if line else "" for line in lines)


def _entry_text(
    module_path: str,
    name: str,
    entry: _ResolvedName | None,
    trees: dict[Path, ast.Module],
) -> str:
    """One name's printed block: its header line, then an indented docstring if it has one.

    `entry` is the matching `lean_surface.SurfaceName` when `resolve_surface_names` placed this
    name at a real `def`/`class`; `None` for a submodule reference (`fransys.derive`, also
    listed in `fransys.__all__`) or a plain data value (`fransys_pdf.PRESET_PAGES`) -- both
    real surface names with no signature or docstring of their own, printed by name and kind
    only, so every name in `__all__` is still accounted for (acceptance 8).
    """
    header = f"{module_path}.{name}"
    if entry is None:
        module = importlib.import_module(module_path)
        obj = getattr(module, name)
        kind = "submodule" if isinstance(obj, types.ModuleType) else type(obj).__name__
        return f"{header} ({kind})"
    tree = trees.setdefault(entry.defining_file, lean_surface.module_tree(entry.defining_file))
    node = lean_surface.find_def(tree, entry.qualname)
    signature = _signature_text(node, _surface_of(module_path))
    block = f"{header}{signature}"
    docstring = _docstring_block(node)
    if docstring:
        block = f"{block}\n{docstring}"
    return block


def api(package: str) -> str:
    """Every surface name's signature and docstring for one package, in a stable order.

    `package`'s surface modules (`_package_modules`) in `surface_modules()`'s sorted order, each
    module's own `__all__` names in their declared order (never a set) -- deterministic and
    byte-identical across calls on the same commit, since it reads only the installed source and
    stores nothing of its own (MS9). Raises `UnknownPackageError` for a name that owns no
    surface module.
    """
    modules = _package_modules(package)
    if not modules:
        msg = f"unknown package: {package!r}"
        raise UnknownPackageError(msg)
    names_by_module = lean_surface.surface_names(modules)
    resolved = {
        (entry.module, entry.name): entry for entry in lean_surface.resolve_surface_names(modules)
    }
    trees: dict[Path, ast.Module] = {}
    blocks = [
        _entry_text(module_path, name, resolved.get((module_path, name)), trees)
        for module_path in modules
        for name in names_by_module.get(module_path, ())
    ]
    return "\n\n".join(blocks) + "\n"


def _entry_md(
    module_path: str,
    name: str,
    entry: _ResolvedName | None,
    trees: dict[Path, ast.Module],
) -> tuple[str, str]:
    """One name as `(group, markdown)`: a `###` heading, a signature code block, the docstring."""
    if entry is None:
        obj = getattr(importlib.import_module(module_path), name)
        kind = "submodule" if isinstance(obj, types.ModuleType) else type(obj).__name__
        code = f"{name}: {kind}"
        node = None
    else:
        tree = trees.setdefault(entry.defining_file, lean_surface.module_tree(entry.defining_file))
        node = lean_surface.find_def(tree, entry.qualname)
        signature = _signature_text(node, _surface_of(module_path))
        code = f"def {name}{signature}" if signature else f"class {name}"
    parts = [f"### {name}", f"```python\n{code}\n```"]
    docstring = None if node is None else lean_surface.literal_docstring(node)
    if docstring is not None:
        parts.append(inspect.cleandoc(docstring.value))
    return _md_group(node), "\n\n".join(parts)


def _md_group(node: ast.AST | None) -> str:
    """A name's page group: `def` is Functions, `class` Classes, anything else Constants."""
    if isinstance(node, ast.ClassDef):
        return "Classes"
    return "Functions" if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else "Constants"


def api_md(module_path: str) -> str:
    """One surface module's `__all__` as a markdown page: a title, then names under `## ` groups.

    `module_path` is a module with its own `__all__` (`fransys`, `fransys_model.derive`).
    The groups are Functions, Classes, Constants (an empty one is omitted), names sorted within
    each, so the page is byte-identical across calls (FS5).
    """
    names = lean_surface.surface_names((module_path,))[module_path]
    resolved = {
        (entry.module, entry.name): entry
        for entry in lean_surface.resolve_surface_names((module_path,))
    }
    trees: dict[Path, ast.Module] = {}
    groups: dict[str, list[tuple[str, str]]] = {"Functions": [], "Classes": [], "Constants": []}
    for name in names:
        group, block = _entry_md(module_path, name, resolved.get((module_path, name)), trees)
        groups[group].append((name, block))
    parts = [f"# `{module_path}`"]
    for group, entries in groups.items():
        if entries:
            parts += [f"## {group}", *(block for _, block in sorted(entries))]
    return "\n\n".join(parts) + "\n"


_ARGV_COUNT = 2  # scripts/lean_api.py, PACKAGE
_ARGV_COUNT_MD = 3  # scripts/lean_api.py, --md, MODULE


def main() -> None:
    """CLI entry point: `lean_api.py PACKAGE` (`just api PACKAGE`) or `lean_api.py --md MODULE`."""
    if len(sys.argv) == _ARGV_COUNT_MD and sys.argv[1] == "--md":
        sys.stdout.write(api_md(sys.argv[2]))
        return
    if len(sys.argv) != _ARGV_COUNT:
        sys.stderr.write("usage: lean_api.py PACKAGE | lean_api.py --md MODULE\n")
        sys.exit(2)
    try:
        sys.stdout.write(api(sys.argv[1]))
    except UnknownPackageError as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
