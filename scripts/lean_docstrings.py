"""LEAN-GATES LC3/MS8's two docstring checks: API-surface presence and non-surface shape.

Check 1 (`check_surface_docstrings`): every name `scripts/lean_surface.py`'s
`resolve_surface_names` finds, plus each surface class's own public methods and properties,
must carry a literal AST docstring (`lean_surface.literal_docstring`, never `obj.__doc__` --
see that module's own docstring-trap note) within `[limits].surface_docstring_lines` (15)
lines. Presence is hard, zero-baseline (LC3's "Amended" bullet); the length half is NOT
zero-baseline on the real repo (see this order's own report) and is exposed separately by
`measure_surface_docstring_lines` for the lead to route, unwired here.

Check 2 (`measure_docstring_lines`, `banned_section_sites`): every OTHER docstring under
`packages/*/src` is optional, but when written is capped at `[limits].docstring_lines` (5)
lines (ceiling-bound, ready for `lean_ceilings.check`/`lower`/`first_run`) and may not carry a
Google-style `Args:`/`Returns:`/`Raises:`/`Yields:`/`Attributes:` section header (LC3's
original rule for everything off the surface).

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imports `lean_surface.py`/
`lean_ceilings.py` the same way (there is no scripts package to import from).
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import types
    from collections.abc import Iterable

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _load(module_name: str, filename: str) -> types.ModuleType:
    """Load `scripts/<filename>` the way its own tests do, reusing a prior load."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        msg = f"could not load scripts/{filename}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


lean_surface = _load("fransys_lean_surface", "lean_surface.py")
lean_ceilings = _load("fransys_lean_ceilings", "lean_ceilings.py")

DEFAULT_SURFACE_DOCSTRING_LINES_LIMIT = 15
DEFAULT_DOCSTRING_LINES_LIMIT = 5

_DEF_TYPES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_BANNED_SECTION_RE = re.compile(r"^(Args|Returns|Raises|Yields|Attributes):\s*$")


def _public_methods(class_node: ast.ClassDef) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    """`class_node`'s own public (non-`_`-prefixed) methods and properties, direct children only."""
    return tuple(
        child
        for child in class_node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not child.name.startswith("_")
    )


@dataclasses.dataclass(frozen=True)
class SurfaceDocstringViolation:
    """One API-surface name or method with no literal docstring, or one over the line cap."""

    site: str
    reason: str


def _surface_sites(
    entries: tuple[Any, ...] | None = None, root: Path | None = None
) -> tuple[tuple[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None], ...]:
    """Every `(site, node)` Check 1 examines, one entry per distinct `(file, qualname)`.

    Each resolved surface name, plus each surface class's own public methods and properties.
    `node` is `None` when no top-level or nested def matches (never expected in practice,
    reported as its own violation rather than silently dropped). The same underlying def
    reachable through two surface modules (`rail_pairs` via both `vocab` and `derive`) is
    de-duplicated to one entry, keyed by `(defining_file, qualname)`, before the site key is
    built -- `lean_surface.resolve_surface_names` itself yields one row per surface module, by
    design (its own docstring), so the dedup is this function's job, not its.

    `entries`/`root` default to the real workspace (`lean_surface.resolve_surface_names()`/
    `lean_surface.ROOT`); a test passes its own small tuple and tmp_path root instead.
    """
    if entries is None:
        entries = lean_surface.resolve_surface_names()
    if root is None:
        root = lean_surface.ROOT
    trees: dict[Path, ast.Module] = {}
    seen: set[tuple[Path, str]] = set()
    pairs: list[tuple[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None]] = []
    for entry in entries:
        key = (entry.defining_file, entry.qualname)
        if key in seen:
            continue
        seen.add(key)
        tree = trees.setdefault(entry.defining_file, lean_surface.module_tree(entry.defining_file))
        node = lean_surface.find_def(tree, entry.qualname)
        rel = entry.defining_file.relative_to(root).as_posix()
        pairs.append((f"{rel}::{entry.qualname}", node))
        if isinstance(node, ast.ClassDef):
            pairs.extend(
                (f"{rel}::{entry.qualname}.{method.name}", method)
                for method in _public_methods(node)
            )
    return tuple(pairs)


def surface_site_keys(
    entries: tuple[Any, ...] | None = None, root: Path | None = None
) -> frozenset[str]:
    r"""Every `f"{path}::{qualname}"` site Check 1 examines, pass or fail.

    `measure_docstring_lines`/`banned_section_sites` (Check 2) pass this in as `surface`, so a
    docstring Check 1 already ruled on is never counted twice.
    """
    return frozenset(site for site, _node in _surface_sites(entries, root))


def _docstring_violations(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, site: str, limit: int
) -> list[SurfaceDocstringViolation]:
    """`node`'s own presence/length violation, as a 0- or 1-element list."""
    docstring = lean_surface.literal_docstring(node)
    if docstring is None:
        return [SurfaceDocstringViolation(site, "missing")]
    lines = lean_surface.docstring_line_count(docstring)
    if lines > limit:
        return [SurfaceDocstringViolation(site, f"{lines} lines (max {limit})")]
    return []


def check_surface_docstrings(
    limit: int = DEFAULT_SURFACE_DOCSTRING_LINES_LIMIT,
    entries: tuple[Any, ...] | None = None,
    root: Path | None = None,
) -> tuple[SurfaceDocstringViolation, ...]:
    """Every API-surface name (MS8) with no literal docstring, or one over `limit` lines.

    Walks `_surface_sites`; for each entry that is a class, its own public methods and
    properties were already added there (same two rules apply to them). No ceiling, no exempt
    table -- the presence half is zero-baseline from this check's own landing commit (LC3's
    "Amended" bullet), so a caller uses this return value directly rather than routing it
    through `lean_ceilings.check`. The length half is NOT zero-baseline on the real repo today
    (see this order's report); `measure_surface_docstring_lines` exposes those sites separately
    for the lead to route through `lean_ceilings` if wiring this hard needs a ceiling first.
    """
    violations: list[SurfaceDocstringViolation] = []
    for site, node in _surface_sites(entries, root):
        if node is None:
            violations.append(SurfaceDocstringViolation(site, "no def node found"))
            continue
        violations.extend(_docstring_violations(node, site, limit))
    return tuple(sorted(violations, key=lambda violation: violation.site))


def measure_surface_docstring_lines(
    limit: int = DEFAULT_SURFACE_DOCSTRING_LINES_LIMIT,
    entries: tuple[Any, ...] | None = None,
    root: Path | None = None,
) -> dict[str, int]:
    """Every API-surface site already over `limit` lines, keyed like `lean_ceilings` expects.

    Unwired report-only output: `check_surface_docstrings` above still enforces the length cap
    directly, with no ceiling, per this order's own instruction -- this function exists so the
    lead can instead route the length half through `lean_ceilings.first_run`/`check`/`lower` if
    the real non-zero count (see the report) rules that presence and length need different
    enforcement timelines. `measured` holds only over-limit sites, `lean_ceilings`'s own
    contract.
    """
    measured: dict[str, int] = {}
    for site, node in _surface_sites(entries, root):
        if node is None:
            continue
        docstring = lean_surface.literal_docstring(node)
        if docstring is None:
            continue
        lines = lean_surface.docstring_line_count(docstring)
        if lines > limit:
            measured[site] = lines
    return measured


def _package_src_files(root: Path) -> list[Path]:
    """Every `.py` file under every `packages/*/src`, sorted, `__pycache__` excluded."""
    files: list[Path] = []
    for src_dir in sorted(root.glob("packages/*/src")):
        files.extend(sorted(p for p in src_dir.rglob("*.py") if "__pycache__" not in p.parts))
    return files


def _iter_docstring_nodes(
    tree: ast.Module,
) -> Iterable[tuple[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, ast.Constant]]:
    """Every `(dotted qualname, node, docstring)` in `tree` that has a literal docstring."""

    def visit(
        node: ast.AST, scope: tuple[str, ...]
    ) -> Iterable[tuple[str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, ast.Constant]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _DEF_TYPES):
                qualname = ".".join([*scope, child.name])
                docstring = lean_surface.literal_docstring(child)
                if docstring is not None:
                    yield qualname, child, docstring
                yield from visit(child, (*scope, child.name))
            else:
                yield from visit(child, scope)

    yield from visit(tree, ())


def measure_docstring_lines(root: Path, surface: frozenset[str]) -> dict[str, int]:
    """Every non-surface docstring under `packages/*/src` over `DEFAULT_DOCSTRING_LINES_LIMIT`.

    Keyed `f"{path}::{qualname}"`, matching `lean_ceilings`'s per-function site shape. `surface`
    holds the same `f"{path}::{qualname}"` keys `check_surface_docstrings` already checked (its
    own violations, plus every clean surface name and method); any site in `surface` is skipped
    here, so the two checks never double-count one docstring. `measured` holds only over-limit
    sites, `lean_ceilings.check`'s own contract.
    """
    measured: dict[str, int] = {}
    for path in _package_src_files(root):
        tree = lean_surface.module_tree(path)
        rel = path.relative_to(root).as_posix()
        for qualname, _node, docstring in _iter_docstring_nodes(tree):
            site = f"{rel}::{qualname}"
            if site in surface:
                continue
            lines = lean_surface.docstring_line_count(docstring)
            if lines > DEFAULT_DOCSTRING_LINES_LIMIT:
                measured[site] = lines
    return measured


def banned_section_sites(root: Path, surface: frozenset[str]) -> tuple[str, ...]:
    """Every non-surface docstring at or under the length cap that still has a banned section.

    Report-only input (LC3's own text flags this as needing confirmation before it is wired as
    a gate): a docstring already over `DEFAULT_DOCSTRING_LINES_LIMIT` and carrying a banned
    section is covered by `measure_docstring_lines`'s own ceiling already, so this returns only
    the genuinely new case -- short (`<= DEFAULT_DOCSTRING_LINES_LIMIT` lines) and still banned.
    """
    sites: list[str] = []
    for path in _package_src_files(root):
        tree = lean_surface.module_tree(path)
        rel = path.relative_to(root).as_posix()
        for qualname, _node, docstring in _iter_docstring_nodes(tree):
            site = f"{rel}::{qualname}"
            if site in surface:
                continue
            lines = lean_surface.docstring_line_count(docstring)
            if lines > DEFAULT_DOCSTRING_LINES_LIMIT:
                continue
            text_lines = cast("str", docstring.value).splitlines()
            if any(_BANNED_SECTION_RE.match(line.strip()) for line in text_lines):
                sites.append(site)
    return tuple(sorted(sites))
