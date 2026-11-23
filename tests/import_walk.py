"""The import walk the layering and boundary tests share: top-level names and resolved dotted names."""

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def top_level_imports(source: str) -> set[str]:
    """The top-level package of every absolute import in `source`."""
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def resolve_import(module_name: str, *, is_init: bool, node: ast.ImportFrom, submodules: bool = False) -> list[str]:
    """Every absolute dotted name `node` could refer to; `submodules` adds each imported name under its module."""
    if node.level == 0:
        base = node.module or ""
    else:
        parts = (module_name if is_init else module_name.rsplit(".", 1)[0]).split(".")
        up = node.level - 1
        if up:
            parts = parts[:-up] if up < len(parts) else []
        base = ".".join(parts)
        if node.module:
            base = f"{base}.{node.module}" if base else node.module
    if not base:
        return [alias.name for alias in node.names]
    return [base, *(f"{base}.{alias.name}" for alias in node.names)] if submodules else [base]


def imported_modules(module_name: str, source: str, *, is_init: bool, submodules: bool = False) -> set[str]:
    """Every module dotted name `source` imports, absolute or resolved-relative."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(resolve_import(module_name, is_init=is_init, node=node, submodules=submodules))
    return names


def module_name_of(path: Path, src_root: Path) -> tuple[str, bool]:
    """`path`'s dotted module name (relative to `src_root`'s parent) and whether it is a package `__init__`."""
    parts = list(path.relative_to(src_root.parent).with_suffix("").parts)
    is_init = parts[-1] == "__init__"
    if is_init:
        parts = parts[:-1]
    return ".".join(parts), is_init
