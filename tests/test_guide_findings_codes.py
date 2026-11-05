"""Every emitted finding code has one `CodeInfo` (A1), and the guide lists it.

`Finding(code=...)` is constructed three ways, all resolved here with `ast` (no import, no
execution): a literal kwarg (`Finding(code="COVER_OVERFLOW", ...)`); a module-level string
"""

from __future__ import annotations

import ast
import importlib.util
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import fransys_el
import fransys_kicad
import fransys_parts
import fransys_pdf
import fransys_render
import pytest
from fransys import _codes as fransys_codes

import fransys_layout
from fransys_model import vocab

if TYPE_CHECKING:
    from fransys_model.kernel import CodeInfo

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


def _finding_code_node(call: ast.Call) -> ast.expr | None:
    """The code expression of a call that builds a finding, else None.

    The shapes: `Finding(code=...)`; `X[code].finding(...)` (a registry lookup); and
    `_INFO.finding(...)` (a module's one `CodeInfo`, returned as the `_INFO` `Name` itself).
    """
    func = call.func
    if isinstance(func, ast.Name) and func.id == "Finding":
        for kw in call.keywords:
            if kw.arg == "code":
                return kw.value
        return call.args[0] if call.args else None
    if isinstance(func, ast.Attribute) and func.attr == "finding":
        if isinstance(func.value, ast.Subscript):
            return func.value.slice
        if isinstance(func.value, ast.Name) and func.value.id == "_INFO":
            return func.value
    return None


def _is_finding_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _finding_code_node(node) is not None


def _code_arg(call: ast.Call) -> ast.expr | None:
    return _finding_code_node(call)


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


def _passed_param(arg: ast.expr | None, func: ast.FunctionDef) -> _Helper | None:
    """`arg` as a `_Helper` when it is one of `func`'s own parameters, else None."""
    names = [a.arg for a in func.args.args]
    if isinstance(arg, ast.Name) and arg.id in names:
        return _Helper(param_index=names.index(arg.id), param_name=arg.id)
    return None


def _find_helpers(infos: list[_FileInfo]) -> dict[tuple[str, str], _Helper]:
    """Functions that pass their `code` parameter to a finding call or to another helper."""
    helpers: dict[tuple[str, str], _Helper] = {}
    grew = True
    while grew:
        grew = False
        for info in infos:
            for func_name, func in info.functions.items():
                for node in ast.walk(func):
                    if not isinstance(node, ast.Call):
                        continue
                    target = _helper_target(node, info, helpers)
                    if target is not None:
                        arg = _helper_call_arg(node, helpers[target])
                    elif _is_finding_call(node):
                        arg = _code_arg(node)
                    else:
                        continue
                    found = _passed_param(arg, func)
                    if found is not None and helpers.get((info.module, func_name)) != found:
                        helpers[(info.module, func_name)] = found
                        grew = True
    return helpers


def _local_values(name: str, scope: ast.FunctionDef | None) -> list[ast.expr]:
    """Every value assigned to the local `name` in `scope`."""
    if scope is None:
        return []
    return [n.value for n in ast.walk(scope) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]


def _resolve_or_raise(
    value: ast.expr | None,
    info: _FileInfo,
    files_by_module: dict[str, _FileInfo],
    where: str,
    scope: ast.FunctionDef | None = None,
) -> set[str]:
    """The literals `value` names: itself, a constant, an assigned local, or both arms of an `if`.

    Raises `AssertionError` naming `where` instead of guessing, if it resolves to none: a
    fourth code shape this scanner does not yet know, not something to skip quietly.
    """
    if isinstance(value, ast.IfExp):
        arms = (value.body, value.orelse)
        return set[str]().union(*(_resolve_or_raise(a, info, files_by_module, where, scope) for a in arms))
    literal = _literal_str(value)
    if literal is not None:
        return {literal}
    if isinstance(value, ast.Name):
        resolved = _resolve_name(value.id, info, files_by_module)
        if resolved is not None:
            return {resolved}
        local = _local_values(value.id, scope)
        if local:
            return set[str]().union(*(_resolve_or_raise(v, info, files_by_module, where, scope) for v in local))
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
            arg = _code_arg(node)
            if isinstance(arg, ast.Attribute):
                continue  # `CodeInfo.finding` builds from its own `self.code`
            if isinstance(arg, ast.Name) and arg.id == "_INFO":
                codes |= _single_info_codes(info)
                continue
            where = f"{info.path}:{node.lineno}"
            codes |= _resolve_or_raise(arg, info, files_by_module, where, enclosing)
    return codes


def _single_info_codes(info: _FileInfo) -> set[str]:
    """The code literals in a module's `_INFO = next(i for i in ... if i.code == "X")`."""
    return {
        node.value
        for stmt in info.tree.body
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_INFO" for t in stmt.targets)
        for node in ast.walk(stmt.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _helper_target(node: ast.Call, info: _FileInfo, helpers: dict[tuple[str, str], _Helper]) -> tuple[str, str] | None:
    """Which known helper (if any) `node` calls: by name in `info`'s own module, by an
    import `info` resolved that name to, or as an attribute of an imported module
    (`_toml.finding(...)` after `from . import _toml`)."""
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        imported = info.imports.get(node.func.value.id)
        if imported is None:
            return None
        key = (f"{imported[0]}.{imported[1]}", node.func.attr)
        return key if key in helpers else None
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
            arg = _helper_call_arg(node, helper)
            enclosing = _enclosing_function(node, info.parent)
            if enclosing is not None and (info.module, enclosing.name) in helpers and _passed_param(arg, enclosing) is not None:
                continue  # a helper handing its own `code` on: resolved at its call sites
            if isinstance(arg, ast.Subscript):
                codes.update(_tuple_head_codes(info))
                continue
            codes |= _resolve_or_raise(arg, info, files_by_module, where, enclosing)
    return codes


def _tuple_head_codes(info: _FileInfo) -> set[str]:
    """Codes a file builds as `(CODE, text)` pairs and passes on as `pair[0]` (`_joins.py`)."""
    return {
        head
        for node in ast.walk(info.tree)
        if isinstance(node, ast.Tuple) and node.elts and (head := _literal_str(node.elts[0])) is not None and _CODE_SHAPE.match(head)
    }


def scanned_finding_codes() -> frozenset[str]:
    """Every finding code the workspace can actually emit, found by walking `Finding(...)`
    construction sites under `packages/*/src` (three shapes; see module docstring)."""
    infos = [_build_file_info(path) for path in _iter_package_files()]
    files_by_module = {info.module: info for info in infos}
    helpers = _find_helpers(infos)
    codes = _direct_codes(infos, files_by_module, helpers) | _helper_call_codes(infos, files_by_module, helpers)
    return frozenset(code for code in codes if _CODE_SHAPE.match(code))


@pytest.fixture(scope="module")
def scanned_codes() -> frozenset[str]:
    return scanned_finding_codes()


def _findings_table_rows(markdown: str) -> list[list[str]]:
    """`findings.md`'s one table's data rows, each as its `|`-delimited cells, stripped.

    The page is a header row, a `---` separator row, then data rows: this skips the first two
    `|`-led lines (header, separator) and returns the rest. Reusable by a later test in this
    """
    table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in table_lines[2:]]


FINDINGS_PAGES = (
    "findings-validators",
    "findings-release",
    "findings-render",
    "findings-pdf",
    "findings-kicad",
    "findings-parts",
)


def _all_rows() -> list[list[str]]:
    """The data rows of every findings page."""
    return [
        row for page in FINDINGS_PAGES for row in _findings_table_rows(files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8"))
    ]


def findings_md_codes() -> frozenset[str]:
    """The set of finding codes with a row in a findings page (each data row's first cell)."""
    return frozenset(row[0] for row in _all_rows() if row and row[0])


def _registry() -> tuple[CodeInfo, ...]:
    """Every package's `CodeInfo` values, as the facade merges them (duplicates kept)."""
    return (
        *fransys_codes._OWN,
        *vocab.FINDING_CODES,
        *fransys_el.FINDING_CODES,
        *fransys_layout.FINDING_CODES,
        *fransys_render.FINDING_CODES,
        *fransys_pdf.FINDING_CODES,
        *fransys_kicad.FINDING_CODES,
        *fransys_parts.FINDING_CODES,
    )


def a1_violations(scanned: frozenset[str], registry: tuple[CodeInfo, ...]) -> dict[str, list[str]]:
    """Emitted codes with no `CodeInfo`, `CodeInfo`s nothing emits, and codes listed twice."""
    listed = [info.code for info in registry]
    return {
        "unlisted": sorted(scanned - set(listed)),
        "never emitted": sorted(set(listed) - scanned),
        "listed twice": sorted({code for code in listed if listed.count(code) > 1}),
    }


def test_every_emitted_code_has_one_code_info(scanned_codes: frozenset[str]) -> None:
    """A1 (BUILD-MESSAGES M1): one `CodeInfo` per emitted code, in the facade's merge too."""
    assert a1_violations(scanned_codes, _registry()) == {
        "unlisted": [],
        "never emitted": [],
        "listed twice": [],
    }
    assert set(fransys_codes.BY_CODE) == scanned_codes


def test_a1_fails_on_a_deleted_entry(scanned_codes: frozenset[str]) -> None:
    """Probe P1 in-process: the registry without one entry leaves that code unlisted."""
    registry = _registry()
    assert a1_violations(scanned_codes, registry[1:])["unlisted"] == [registry[0].code]
    assert a1_violations(scanned_codes, (*registry, registry[0]))["listed twice"] == [registry[0].code]


def test_findings_codes_match_the_registry() -> None:
    """Every registry code has its row on a findings page, and no page lists another code."""
    assert findings_md_codes() == {info.code for info in fransys_codes.BY_CODE.values()}


def test_no_todo_placeholder_remains() -> None:
    """No cell of a findings page's table is still the literal placeholder string `TODO`."""
    rows = _all_rows()
    stale = [row[0] for row in rows if row and "TODO" in row]
    assert not stale, f"still has a TODO cell: {stale}"


def test_no_generated_findings_page_shows_doubled_braces() -> None:
    """A template's `{{ }}` reads as `{ }` on a page, the way a finding's printed fix does."""
    path = WORKSPACE_ROOT / "scripts" / "findings_guide.py"
    spec = importlib.util.spec_from_file_location("findings_guide_braces", path)
    assert spec is not None
    assert spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    guide_dir = Path(str(files("fransys").joinpath("guide")))
    doubled = [p.name for p, text in generator.expected_pages(guide_dir).items() if "{{" in text or "}}" in text]
    assert doubled == []
