"""The shared AST helper of the SURFACE-GATES test modules (spec SURFACE-COHERENCE, R1).

`imports_of` lists every import a module makes, in every form, as `Import` rows. `src_modules`
walks `packages/*/src`. A gate keeps its own rule; this file holds only the walk.
"""

import ast
import importlib.util
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_ROOT = ROOT / "packages"


def load_script(module_name: str, filename: str):
    """Load `scripts/<filename>` as the module `module_name`; the scripts are not a package."""
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        msg = f"could not load scripts/{filename}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ci_gates = load_script("fransys_ci_gates", "ci_gates.py")


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
    for path in ci_gates.source_files(ROOT):
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


RATCHETS = ROOT / "tests" / "ratchets.toml"


def stock(check: str, key: str = "stock") -> int:
    """The stock of a ratchet: `[check] key` in `tests/ratchets.toml`; it only falls."""
    with RATCHETS.open("rb") as handle:
        return tomllib.load(handle)[check][key]


def check_stock(check: str, found: int, stock_: int) -> None:
    """Fail above the stock, and below it with the order to lower `tests/ratchets.toml`."""
    assert found <= stock_, f"{check}: {found} above its stock {stock_}"
    assert found >= stock_, f"{check}: {found} below its stock {stock_}: lower tests/ratchets.toml"


def _qualnames(tree: ast.AST, prefix: str = "") -> set[str]:
    """Every function and class name in `tree`, dotted by nesting (`Class.method`)."""
    found: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.add(prefix + node.name)
            found |= _qualnames(node, f"{prefix}{node.name}.")
        else:
            found |= _qualnames(node, prefix)
    return found


def stale_ceiling_keys(
    ceilings: dict, root: Path = ROOT, *, skip_missing: bool = False
) -> list[str]:
    """One message per `ceilings.toml` key (`path::name`, or a bare file path) naming nothing.

    `skip_missing` passes a key whose file is absent: the export lacks the private docs (R462).
    """
    cache: dict[str, set[str] | None] = {}
    problems = []
    for section, keys in ceilings.items():
        for key in keys if section != "limits" else ():
            path, _, name = key.partition("::")
            if not path.endswith((".py", ".md")):
                continue
            if path not in cache:
                file = root / path
                cache[path] = (
                    _qualnames(ast.parse(file.read_text()))
                    if file.suffix == ".py" and file.exists()
                    else None
                )
            if not (root / path).exists():
                if not skip_missing:
                    problems.append(
                        f"ceilings.toml [{section}] key {key}: {path} does not exist; "
                        "delete the key (the file was moved or removed)"
                    )
            elif name and name not in (cache[path] or set()):
                problems.append(
                    f"ceilings.toml [{section}] key {key}: {path} has no {name}; "
                    "delete the key (the function was renamed or removed)"
                )
    return problems
