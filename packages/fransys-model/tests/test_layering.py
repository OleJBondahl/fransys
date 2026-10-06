"""Import-layer check via stdlib `ast`.

Replaces `import-linter`, which does not run on this Python (root decision 0010; the root
`tests/test_boundaries.py` does the same for the workspace). Enforces design/foundations.md 4: the
layers are `derive` → `layout` → `vocab` → `kernel`, and a layer imports only layers to its right.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "fransys_model"

# layer -> the layers it must not import
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "kernel": (
        "fransys_model.vocab",
        "fransys_model.layout",
        "fransys_model.derive",
    ),
    "vocab": ("fransys_model.layout", "fransys_model.derive"),
    "layout": ("fransys_model.derive",),
}


def _package_of(module_name: str, *, is_init: bool) -> str:
    """The dotted package a module belongs to, for resolving its relative imports."""
    return module_name if is_init else module_name.rsplit(".", 1)[0]


def _resolve_import(module_name: str, *, is_init: bool, node: ast.ImportFrom) -> list[str]:
    """Every absolute dotted name `node` could refer to, resolving relative imports."""
    if node.level == 0:
        base = node.module or ""
        return [base] if base else [alias.name for alias in node.names]
    package = _package_of(module_name, is_init=is_init)
    parts = package.split(".")
    up = node.level - 1
    if up:
        parts = parts[:-up] if up < len(parts) else []
    base = ".".join(parts)
    if node.module:
        base = f"{base}.{node.module}" if base else node.module
    return [base] if base else [f"{base}.{alias.name}" for alias in node.names]


def _imported_modules(module_name: str, source: str, *, is_init: bool) -> set[str]:
    """Every module dotted name `source` imports, absolute or resolved-relative."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(_resolve_import(module_name, is_init=is_init, node=node))
    return names


def _module_name(path: Path) -> tuple[str, bool]:
    """`path`'s dotted module name (relative to `src/`) and whether it is a package `__init__`."""
    rel = path.relative_to(SRC_ROOT.parent)
    parts = list(rel.with_suffix("").parts)
    is_init = parts[-1] == "__init__"
    if is_init:
        parts = parts[:-1]
    return ".".join(parts), is_init


def _violates(imported: set[str], forbidden: tuple[str, ...]) -> set[str]:
    """The subset of `imported` that names a forbidden module or one of its submodules."""
    return {
        module
        for module in imported
        for banned in forbidden
        if module == banned or module.startswith(banned + ".")
    }


def _layer_violations(root: Path, forbidden: dict[str, tuple[str, ...]]) -> list[str]:
    """One `"<file>: imports <module>"` entry per forbidden import found under `root`."""
    problems = []
    for layer, banned in forbidden.items():
        layer_dir = root / layer
        if not layer_dir.is_dir():
            continue
        for path in sorted(layer_dir.rglob("*.py")):
            module_name, is_init = _module_name(path)
            source = path.read_text(encoding="utf-8")
            imported = _imported_modules(module_name, source, is_init=is_init)
            problems.extend(f"{path}: imports {bad}" for bad in sorted(_violates(imported, banned)))
    return problems


def test_no_layer_imports_a_downstream_layer() -> None:
    """No layer imports a layer to its left in `derive` → `layout` → `vocab` → `kernel`."""
    assert _layer_violations(SRC_ROOT, FORBIDDEN) == []


def test_checker_fails_on_a_synthetic_violation() -> None:
    """The checker catches a `kernel` module importing `vocab`, fed as a source string."""
    source = "from fransys_model.vocab import core\n"
    imported = _imported_modules("fransys_model.kernel.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["kernel"]) == {"fransys_model.vocab"}


def test_checker_fails_when_vocab_imports_layout() -> None:
    """The checker catches a `vocab` module importing `layout` (decision 0009)."""
    source = "from fransys_model.layout import pages\n"
    imported = _imported_modules("fransys_model.vocab.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["vocab"]) == {"fransys_model.layout"}
