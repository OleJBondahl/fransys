"""The one home for "the API surface" (MS1, MS2, MS6, MS8): its module list and its names.

Four consumers over time: `scripts/lean_docstrings.py` (this order's own LEAN-GATES P3), a
later part's typed-surface check (MS7), a future SURFACE order's own hard import-boundary gate
in `tests/test_boundaries.py` plus `just api` (MS9, which prints a surface name's real
docstring, not a dataclass-generated one -- the AST helpers below exist for that too). Keep this
module's logic here; a consumer imports it rather than folding its own copy.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imported by its consumers the same
way.
"""

from __future__ import annotations

import ast
import dataclasses
import functools
import importlib
import inspect
import tomllib
import types
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[1]

#: `fransys_model`'s own nine surface modules (MS1, amended 2026-09-27 by the designer on
#: Part 0's draft to add `derive.numbering_pins`, and by model-0159 to add
#: `derive.cable_drawing`, model-0167 to add `derive.block_diagram`): not its top-level package,
#: which is excluded from the surface entirely -- only these nine dotted paths are read by
#: other packages.
_MODEL_MODULES: tuple[str, ...] = (
    "fransys_model.kernel",
    "fransys_model.vocab",
    "fransys_model.layout",
    "fransys_model.derive",
    "fransys_model.derive.drawing_text",
    "fransys_model.derive.baseline",
    "fransys_model.derive.numbering_pins",
    "fransys_model.derive.cable_drawing",
    "fransys_model.derive.block_diagram",
)

#: Kept separately from `_MODEL_MODULES` (MS8): `fransys.colours` is a submodule of
#: `fransys`; the engineer surface and its colours are the facade's one way into the author
#: package (decision 0103).
_EXTRA_MODULES: tuple[str, ...] = (
    "fransys.colours",
    "fransys_author.surface",
    "fransys_author.surface.colours",
)

_DEF_TYPES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _workspace_top_level_modules(root: Path) -> tuple[str, ...]:
    """Each `packages/*` workspace member's own import name, `fransys_model` excepted.

    Same filtering `scripts/cov_floors.py`'s `workspace_packages` uses (read root
    `pyproject.toml`'s `[tool.uv.workspace] members`, keep only members under `packages/`, read
    each kept member's own `pyproject.toml` for its `[project] name`, normalized to an import
    name) written fresh here since `fransys_model` is excluded and the return shape differs.
    """
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    members: list[str] = data["tool"]["uv"]["workspace"]["members"]
    names: list[str] = []
    for member in members:
        posix_member = member.replace("\\", "/")
        if not posix_member.startswith("packages/"):
            continue
        project = tomllib.loads((root / member / "pyproject.toml").read_text(encoding="utf-8"))
        import_name = project["project"]["name"].replace("-", "_")
        if import_name == "fransys_model":
            continue
        names.append(import_name)
    return tuple(names)


def surface_modules() -> tuple[str, ...]:
    """Every dotted module path that defines part of the workspace's API surface.

    MS1, MS2, MS6, MS8 combined: each `packages/*` workspace member's own top-level module
    (`fransys_model` excepted), `fransys_model`'s own nine named modules (MS1),
    `fransys.colours` and the author package's surface modules (MS8). Sorted, so stable.
    """
    top_level = _workspace_top_level_modules(ROOT)
    return tuple(sorted((*top_level, *_MODEL_MODULES, *_EXTRA_MODULES)))


def surface_names(modules: Iterable[str] | None = None) -> dict[str, tuple[str, ...]]:
    """Each surface module's own `__all__`, empty when absent.

    Every surface module has a real `__all__` today (`fransys_model.derive.drawing_text`/
    `.baseline`/`.numbering_pins` and `fransys_layout` were the last to gain one, in main's
    SURFACE Part 1) -- the empty-when-absent case now only ever fires for a module outside the
    surface entirely, such as `fransys_model` itself. `modules` defaults to
    `surface_modules()`; a test passes its own small list instead of importing the real
    workspace.
    """
    names: dict[str, tuple[str, ...]] = {}
    for dotted in modules if modules is not None else surface_modules():
        module = importlib.import_module(dotted)
        names[dotted] = tuple(getattr(module, "__all__", ()))
    return names


@dataclasses.dataclass(frozen=True)
class SurfaceName:
    """One surface name: where it is declared (`module`) and where it is actually defined."""

    module: str
    name: str
    defining_file: Path
    qualname: str


def resolve_surface_names(modules: Iterable[str] | None = None) -> tuple[SurfaceName, ...]:
    """For every `(module, name)` pair from `surface_names(modules)`, find where it is defined.

    `getattr`s the real object, unwraps a `functools.wraps`-style wrapper (`inspect.unwrap`, so
    a decorated surface function is still placed at its own `def`, not skipped as unplaceable),
    then uses `inspect.getsourcefile` (never the surface module's own file, since many names are
    re-exported from elsewhere in their package). Two kinds of name are skipped, neither an
    error: a submodule reference (`fransys.__all__` lists `"author"`, `"derive"` -- module
    objects, not something with its own docstring to check this way), and a plain data value (a
    module-level constant such as `derive.TOP_LEVEL`, which `inspect.getsourcefile` cannot
    place, having no `def`/`class` node of its own). The same underlying object reachable
    through two surface modules (`rail_pairs` via both `vocab` and `derive`) yields one entry
    per module it is listed under -- callers that want one entry per site dedupe by
    `(defining_file, qualname)` themselves.
    """
    resolved: list[SurfaceName] = []
    for module_path, names in surface_names(modules).items():
        module = importlib.import_module(module_path)
        for name in names:
            obj = getattr(module, name)
            if isinstance(obj, types.ModuleType):
                continue
            unwrapped = inspect.unwrap(obj)
            try:
                source_file = inspect.getsourcefile(unwrapped)
            except TypeError:
                continue
            if source_file is None:
                continue
            qualname = getattr(unwrapped, "__qualname__", name)
            resolved.append(
                SurfaceName(
                    module=module_path,
                    name=name,
                    defining_file=Path(source_file),
                    qualname=qualname,
                )
            )
    return tuple(resolved)


def module_tree(path: Path) -> ast.Module:
    """Parse `path`, cached on the file text (0122); the tree is shared, so never edit it."""
    return _parse_source(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=512)
def _parse_source(text: str) -> ast.Module:
    return ast.parse(text)


def find_def(
    tree: ast.Module, name: str
) -> ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None:
    """The `ClassDef`/`FunctionDef`/`AsyncFunctionDef` named `name` in `tree`.

    Top-level first (`resolve_surface_names` only ever points at a module-level definition, so
    this is enough in every real case), falling back to a full walk only if the top-level
    search misses, rather than assume the surface can never point elsewhere.
    """
    for node in tree.body:
        if isinstance(node, _DEF_TYPES) and node.name == name:
            return node
    for node in ast.walk(tree):
        if isinstance(node, _DEF_TYPES) and node.name == name:
            return node
    return None


def literal_docstring(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Constant | None:
    """`node`'s own literal docstring `ast.Constant`, or `None` -- never the runtime `__doc__`.

    Only a `body[0]` that is an `ast.Expr` wrapping a `str` `ast.Constant` counts: a plain
    `dataclasses.dataclass` class with no written docstring still has a non-`None` runtime
    `__doc__` (`"ClassName(field: type)"`, auto-generated), which this deliberately ignores.
    `just api` (MS9) uses this too, so it never prints that generated signature as a docstring.
    """
    if not node.body:
        return None
    first = node.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def docstring_line_count(constant: ast.Constant) -> int:
    """Lines from the docstring's opening triple-quote line to its closing one, inclusive."""
    end = constant.end_lineno
    return 1 if end is None else end - constant.lineno + 1
