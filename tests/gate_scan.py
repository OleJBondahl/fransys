"""The shared AST helper of the SURFACE-GATES test modules (spec SURFACE-COHERENCE, R1).

`imports_of` lists every import a module makes, in every form, as `Import` rows. `src_modules`
walks `packages/*/src`. A gate keeps its own rule; this file holds only the walk.
"""

import ast
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_ROOT = ROOT / "packages"


class Import(NamedTuple):
    """One import: `source` is the module imported from, `name` the name taken ("" if none)."""

    package: str
    module: str
    line: int
    source: str
    name: str


def src_modules() -> list[tuple[str, Path]]:
    """Every `packages/*/src` .py file with its dotted module name, sorted; an empty walk fails."""
    found = []
    for path in sorted(PACKAGES_ROOT.glob("*/src/**/*.py")):
        if "__pycache__" in path.parts:
            continue
        src = next(p for p in path.parents if p.name == "src")
        parts = path.relative_to(src).with_suffix("").parts
        found.append((".".join(parts[:-1] if parts[-1] == "__init__" else parts), path))
    assert found, "the source walk found no file"
    return found


def package_of(module: str) -> str:
    """The top-level package of a dotted module name."""
    return module.split(".", maxsplit=1)[0]


def _alias_map(tree: ast.AST) -> dict[str, str]:
    """Local name -> the dotted module or object it stands for, from level-0 imports."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.asname:
                    aliases[item.asname] = item.name
                else:
                    top = item.name.split(".", maxsplit=1)[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for item in node.names:
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    return aliases


def _chain(node: ast.Attribute) -> list[str] | None:
    """The dotted names of an attribute chain rooted in a plain name, else None."""
    names = [node.attr]
    inner = node.value
    while isinstance(inner, ast.Attribute):
        names.append(inner.attr)
        inner = inner.value
    if not isinstance(inner, ast.Name):
        return None
    return [inner.id, *reversed(names)]


def _attribute_uses(tree: ast.AST, aliases: dict[str, str]) -> list[tuple[str, str, int]]:
    """`(source, name, line)` for the outermost attribute chains rooted in an imported alias."""
    inner_ids = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    uses = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or id(node) in inner_ids:
            continue
        chain = _chain(node)
        if chain is None or chain[0] not in aliases:
            continue
        full = f"{aliases[chain[0]]}.{'.'.join(chain[1:])}"
        source, _, name = full.rpartition(".")
        uses.append((source, name, node.lineno))
    return uses


def imports_of(source: str, module: str) -> list[Import]:
    """Every level-0 import form in `source`, plus attribute reads on an imported module alias."""
    tree = ast.parse(source)
    package = package_of(module)
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            rows += [Import(package, module, node.lineno, item.name, "") for item in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            rows += [
                Import(package, module, node.lineno, node.module, item.name) for item in node.names
            ]
    for src, name, line in _attribute_uses(tree, _alias_map(tree)):
        rows.append(Import(package, module, line, src, name))
    return rows


def src_imports() -> list[Import]:
    """`imports_of` over every `packages/*/src` file."""
    rows = []
    for module, path in src_modules():
        rows += imports_of(path.read_text(encoding="utf-8"), module)
    return rows


def in_package(source: str, package: str) -> bool:
    """True when the dotted `source` is `package` or lies below it."""
    return source == package or source.startswith(f"{package}.")
