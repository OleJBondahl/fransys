"""LEAN-GATES LC2's two size checks: no function inside a function, and a module's code lines.

Both scoped to `packages/*/src` only (LC2's own scoping for these two checks): tests and scripts
are never walked. Not a package module (loaded by file path, never imported): lives under root
`scripts/`, loaded by its own tests via `importlib.util.spec_from_file_location`, and pairs with
`lean_ceilings.py`'s `check`/`lower`/`first_run` for the ceilings-file plumbing.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from pathlib import Path

_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)

DEFAULT_MODULE_CODE_LINES_LIMIT = 300


def package_src_files(root: Path) -> list[Path]:
    """Every `.py` file under every `packages/*/src`, sorted, `__pycache__` excluded."""
    files: list[Path] = []
    for src_dir in sorted(root.glob("packages/*/src")):
        files.extend(sorted(p for p in src_dir.rglob("*.py") if "__pycache__" not in p.parts))
    return files


class _ScopeWalker(ast.NodeVisitor):
    """Walks one module's AST, tracking a dotted class/function scope chain.

    `counts` maps each function's own dotted qualname to the number of `FunctionDef`/
    `AsyncFunctionDef` nodes found among its immediate `.body` children (direct children only,
    so a def nested two levels deep is charged to its own immediate parent, never to an outer
    ancestor). `Lambda` nodes are never counted.
    """

    def __init__(self) -> None:
        self._scope: list[str] = []
        self.counts: dict[str, int] = {}

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        nested = sum(1 for child in node.body if isinstance(child, _DEF_TYPES))
        if nested:
            self.counts[".".join(self._scope)] = nested
        self.generic_visit(node)
        self._scope.pop()

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a `def`, tracking it as a scope and counting its direct nested defs."""
        self._visit_function(node)

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an `async def`, tracking it as a scope and counting its direct nested defs."""
        self._visit_function(node)

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a `class`, tracking it as a scope so its methods qualify as `Class.method`."""
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


def measure_nested_defs(root: Path) -> dict[str, int]:
    """Every `packages/*/src` function with a nested `def`, keyed `path::qualname`.

    LC2's "no function inside a function": the implicit limit is 0, so every entry here is
    already a violation (a lambda is never a nested def). `root` is the repo root; keys are
    root-relative posix paths.
    """
    measured: dict[str, int] = {}
    for path in package_src_files(root):
        walker = _ScopeWalker()
        walker.visit(ast.parse(path.read_text(encoding="utf-8")))
        rel = path.relative_to(root).as_posix()
        for qualname, count in walker.counts.items():
            measured[f"{rel}::{qualname}"] = count
    return measured


def _docstring_line_numbers(tree: ast.Module) -> set[int]:
    """1-based line numbers covered by a module, class or function docstring literal."""
    covered: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, *_DEF_TYPES)):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            covered.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return covered


def count_code_lines(source: str) -> int:
    """Lines of `source` that are code: not blank, not comment-only, not inside a docstring.

    LC3 gates docstrings separately, so counting them here would charge them twice (designer
    ruling 2026-10-01, decision 0044 amendment).
    """
    docstring_lines = _docstring_line_numbers(ast.parse(source))
    return sum(
        1
        for number, line in enumerate(source.splitlines(), start=1)
        if line.strip() and not line.strip().startswith("#") and number not in docstring_lines
    )


def _is_all_assignment(node: ast.stmt) -> bool:
    """Whether `node` assigns `__all__` (plain, annotated or augmented)."""
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return False
    return all(isinstance(t, ast.Name) and t.id == "__all__" for t in targets)


def is_pure_reexport(source: str) -> bool:
    """Whether every statement of `source` is an import, its `__all__` or its module docstring.

    LC2's 2026-10-02 amendment: such a module holds no logic, so it is exempt from the size check.
    """
    tree = ast.parse(source)
    docstring = tree.body[0] if tree.body else None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) or _is_all_assignment(node):
            continue
        is_docstring = node is docstring and isinstance(node, ast.Expr)
        if not (is_docstring and isinstance(node.value, ast.Constant)):
            return False
    return True


def measure_module_code_lines(
    root: Path, limit: int = DEFAULT_MODULE_CODE_LINES_LIMIT
) -> dict[str, int]:
    """Every `packages/*/src` module over `limit` code lines, keyed by its root-relative path.

    A code line is non-blank, not comment-only and not part of a module, class or function
    docstring. A pure re-export module (`is_pure_reexport`) is exempt. `limit` defaults to LC2's
    own 300; the real ceiling comes from `ceilings.toml`'s `[limits].module_code_lines`.
    """
    measured: dict[str, int] = {}
    for path in package_src_files(root):
        source = path.read_text(encoding="utf-8")
        code_lines = count_code_lines(source)
        if code_lines > limit and not is_pure_reexport(source):
            measured[path.relative_to(root).as_posix()] = code_lines
    return measured
