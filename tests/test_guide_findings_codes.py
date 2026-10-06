"""The consumer guide's `findings.md` lists exactly the finding codes the workspace emits (CG4).

`Finding(code=...)` is constructed three ways, all resolved here with `ast` (no import, no
execution): a literal kwarg (`Finding(code="COVER_OVERFLOW", ...)`); a module-level string
constant used as the kwarg's value, defined either in the same file or imported from another
one (e.g. `fransys_layout.lint.codes`); and a per-module helper (`_finding`, `_error`,
`_warn`, `fransys_parts._toml.finding`) that takes `code` as its own parameter and passes it
through, the literal then living at the helper's own call sites, positional or keyword.

This is BUILD-ONCE in spirit: the scan walks every `.py` file under `packages/*/src` once per
test module, in `scanned_finding_codes()`, called from the module-scoped `scanned_codes` fixture
rather than at collection (root CLAUDE.md's speed rule: computed once, not per test, and no
longer paid at collection time by every one of the gate's workers).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_ROOT = WORKSPACE_ROOT / "packages"

# A finding code is always upper-snake-case; this also rejects any resolution artifact that
# is not actually a code shape.
_CODE_SHAPE = re.compile(r"^[A-Z][A-Z0-9_]+$")


def _iter_package_files() -> list[Path]:
    return sorted(PACKAGES_ROOT.glob("*/src/**/*.py"))


def _module_and_package(path: Path) -> tuple[str, str]:
    """`path`'s dotted module name, and the dotted name of the package it lives in.

    The package name is what a relative import (`from .codes import X`, `from ._cuts import Y`)
    resolves against. An `__init__.py`'s own module name already *is* its package's name.
    """
    parts = path.relative_to(WORKSPACE_ROOT).parts
    rel = parts[parts.index("src") + 1 :]
    is_init = rel[-1] == "__init__.py"
    stem = rel[:-1] if is_init else (*rel[:-1], rel[-1][: -len(".py")])
    module = ".".join(stem)
    package = module if is_init else (module.rsplit(".", 1)[0] if "." in module else "")
    return module, package


@dataclass
class _FileInfo:
    path: Path
    tree: ast.Module
    module: str
    consts: dict[str, str] = field(default_factory=dict)
    imports: dict[str, tuple[str, str]] = field(default_factory=dict)  # alias -> (module, name)
    functions: dict[str, ast.FunctionDef] = field(default_factory=dict)
    parent: dict[ast.AST, ast.AST] = field(default_factory=dict)


def _literal_str(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _resolved_import_module(stmt: ast.ImportFrom, package: str) -> str:
    """The dotted module `stmt` imports from, resolving its relative level against `package`."""
    if not stmt.level:
        return stmt.module or ""
    strip = stmt.level - 1
    base_parts = package.split(".") if package else []
    if strip:
        base_parts = base_parts[:-strip] if strip <= len(base_parts) else []
    if stmt.module:
        base_parts = [*base_parts, stmt.module]
    return ".".join(base_parts)


def _record_assign(stmt: ast.Assign, consts: dict[str, str]) -> None:
    for target in stmt.targets:
        if isinstance(target, ast.Name):
            literal = _literal_str(stmt.value)
            if literal is not None:
                consts[target.id] = literal


def _record_ann_assign(stmt: ast.AnnAssign, consts: dict[str, str]) -> None:
    if isinstance(stmt.target, ast.Name):
        literal = _literal_str(stmt.value)
        if literal is not None:
            consts[stmt.target.id] = literal


def _record_import(stmt: ast.ImportFrom, package: str, imports: dict[str, tuple[str, str]]) -> None:
    resolved = _resolved_import_module(stmt, package)
    for alias in stmt.names:
        imports[alias.asname or alias.name] = (resolved, alias.name)


def _build_file_info(path: Path) -> _FileInfo:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module, package = _module_and_package(path)
    info = _FileInfo(path=path, tree=tree, module=module)
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            info.parent[child] = node
    # Module-level only (`tree.body`): a constant, import or helper def guarded by
    # `if TYPE_CHECKING:` or buried in a function body is not what "module-level" means, and
    # skipping those avoids ever mistaking a type-only import for a code source.
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            _record_assign(stmt, info.consts)
        elif isinstance(stmt, ast.AnnAssign):
            _record_ann_assign(stmt, info.consts)
        elif isinstance(stmt, ast.ImportFrom):
            _record_import(stmt, package, info.imports)
        elif isinstance(stmt, ast.FunctionDef):
            info.functions[stmt.name] = stmt
    return info


def _resolve_name(
    name: str,
    info: _FileInfo,
    files_by_module: dict[str, _FileInfo],
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> str | None:
    """The literal `name` names, as a local module constant or (recursively) an imported one."""
    if name in info.consts:
        return info.consts[name]
    if name in info.imports:
        target_module, orig_name = info.imports[name]
        key = (target_module, orig_name)
        if key in seen:
            return None
        target = files_by_module.get(target_module)
        if target is not None:
            return _resolve_name(orig_name, target, files_by_module, seen | {key})
    return None


def _is_finding_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Finding"
    )


def _code_arg(call: ast.Call) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == "code":
            return kw.value
    return call.args[0] if call.args else None


def _enclosing_function(node: ast.AST, parent: dict[ast.AST, ast.AST]) -> ast.FunctionDef | None:
    current = node
    while current in parent:
        current = parent[current]
        if isinstance(current, ast.FunctionDef):
            return current
    return None


@dataclass
class _Helper:
    """A module-level function that takes `code` as its own parameter and passes it to
    `Finding(code=...)` unchanged: the literal lives at its call sites, not at its definition."""

    param_index: int
    param_name: str


def _find_helpers(infos: list[_FileInfo]) -> dict[tuple[str, str], _Helper]:
    helpers: dict[tuple[str, str], _Helper] = {}
    for info in infos:
        for func_name, func in info.functions.items():
            param_names = [a.arg for a in func.args.args]
            for node in ast.walk(func):
                if not isinstance(node, ast.Call) or not _is_finding_call(node):
                    continue
                arg = _code_arg(node)
                if isinstance(arg, ast.Name) and arg.id in param_names:
                    helpers[(info.module, func_name)] = _Helper(
                        param_index=param_names.index(arg.id), param_name=arg.id
                    )
    return helpers


def _resolve_or_raise(
    value: ast.expr | None, info: _FileInfo, files_by_module: dict[str, _FileInfo], where: str
) -> str:
    """The literal `value` names -- itself, or (if a `Name`) a constant it resolves to.

    Raises `AssertionError` naming `where` instead of guessing, if it resolves to neither: a
    fourth code shape this scanner does not yet know, not something to skip quietly.
    """
    literal = _literal_str(value)
    if literal is not None:
        return literal
    if isinstance(value, ast.Name):
        resolved = _resolve_name(value.id, info, files_by_module)
        if resolved is not None:
            return resolved
    dumped = ast.dump(value) if value is not None else "no code argument"
    message = f"unresolved code argument at {where}: {dumped}"
    raise AssertionError(message)


def _direct_codes(
    infos: list[_FileInfo],
    files_by_module: dict[str, _FileInfo],
    helpers: dict[tuple[str, str], _Helper],
) -> set[str]:
    """Every `Finding(code=...)` call site's code, skipping calls that are a helper's own
    definition (pattern 3's def site: its argument is that helper's own parameter, resolved
    instead at its call sites by `_helper_call_codes`)."""
    codes: set[str] = set()
    for info in infos:
        for node in ast.walk(info.tree):
            if not isinstance(node, ast.Call) or not _is_finding_call(node):
                continue
            enclosing = _enclosing_function(node, info.parent)
            if enclosing is not None and (info.module, enclosing.name) in helpers:
                continue
            where = f"{info.path}:{node.lineno}"
            codes.add(_resolve_or_raise(_code_arg(node), info, files_by_module, where))
    return codes


def _helper_target(
    node: ast.Call, info: _FileInfo, helpers: dict[tuple[str, str], _Helper]
) -> tuple[str, str] | None:
    """Which known helper (if any) `node` calls: by name in `info`'s own module, or by an
    import `info` resolved that name to."""
    if not isinstance(node.func, ast.Name):
        return None
    name = node.func.id
    if (info.module, name) in helpers:
        return (info.module, name)
    if name in info.imports:
        target_module, orig_name = info.imports[name]
        if (target_module, orig_name) in helpers:
            return (target_module, orig_name)
    return None


def _helper_call_arg(node: ast.Call, helper: _Helper) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == helper.param_name:
            return kw.value
    if len(node.args) > helper.param_index:
        return node.args[helper.param_index]
    return None


def _helper_call_codes(
    infos: list[_FileInfo],
    files_by_module: dict[str, _FileInfo],
    helpers: dict[tuple[str, str], _Helper],
) -> set[str]:
    """Every call site of a known helper's code, wherever in the workspace it is called."""
    codes: set[str] = set()
    for info in infos:
        for node in ast.walk(info.tree):
            if not isinstance(node, ast.Call):
                continue
            target_key = _helper_target(node, info, helpers)
            if target_key is None:
                continue
            helper = helpers[target_key]
            where = f"{info.path}:{node.lineno}"
            codes.add(
                _resolve_or_raise(_helper_call_arg(node, helper), info, files_by_module, where)
            )
    return codes


def scanned_finding_codes() -> frozenset[str]:
    """Every finding code the workspace can actually emit, found by walking `Finding(...)`
    construction sites under `packages/*/src` (three shapes; see module docstring)."""
    infos = [_build_file_info(path) for path in _iter_package_files()]
    files_by_module = {info.module: info for info in infos}
    helpers = _find_helpers(infos)
    codes = _direct_codes(infos, files_by_module, helpers) | _helper_call_codes(
        infos, files_by_module, helpers
    )
    return frozenset(code for code in codes if _CODE_SHAPE.match(code))


@pytest.fixture(scope="module")
def scanned_codes() -> frozenset[str]:
    return scanned_finding_codes()


def _findings_table_rows(markdown: str) -> list[list[str]]:
    """`findings.md`'s one table's data rows, each as its `|`-delimited cells, stripped.

    The page is a header row, a `---` separator row, then data rows: this skips the first two
    `|`-led lines (header, separator) and returns the rest. Reusable by a later test in this
    module that checks the table's other columns, not just the code column.
    """
    table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in table_lines[2:]]


def findings_md_codes() -> frozenset[str]:
    """The set of finding codes with a row in `findings.md` (each data row's first cell)."""
    text = files("fransys").joinpath("guide", "findings.md").read_text(encoding="utf-8")
    return frozenset(row[0] for row in _findings_table_rows(text) if row and row[0])


def test_findings_codes_match_scanned_codes(scanned_codes: frozenset[str]) -> None:
    assert findings_md_codes() == scanned_codes


def test_no_todo_placeholder_remains() -> None:
    """No cell of `findings.md`'s table is still the literal placeholder string `TODO`."""
    text = files("fransys").joinpath("guide", "findings.md").read_text(encoding="utf-8")
    rows = _findings_table_rows(text)
    stale = [row[0] for row in rows if row and "TODO" in row]
    assert not stale, f"still has a TODO cell: {stale}"
