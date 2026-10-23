"""Import-layer check via stdlib `ast`.

Replaces `import-linter`, which does not run on this Python (root decision 0010; the root
`tests/test_boundaries.py` does the same for the workspace). Enforces the layer rule: the
layers are `derive` → `layout` → `vocab` → `kernel`, and a layer imports only layers to its right.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "fransys_model"
KERNEL_SRC = Path(__file__).resolve().parents[2] / "fransys-kernel" / "src" / "fransys_kernel"

# layer directory (under src/fransys_model) -> the modules it must not import (design 1.2).
# A row whose directory is absent is skipped (none is absent since EL-3).
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "kernel": (
        "fransys_model.vocab",
        "fransys_model.layout",
        "fransys_model.derive",
    ),
    "vocab": ("fransys_model.layout", "fransys_model.derive", "fransys_model.checks"),
    "layout": ("fransys_model.derive", "fransys_model.checks"),
    "derive/facts": (
        "fransys_model.checks",
        "fransys_model.derive.passes",
        "fransys_model.derive.texts",
        "fransys_model.derive.rows",
    ),
    "checks": (
        "fransys_model.derive.passes",
        "fransys_model.derive.texts",
        "fransys_model.derive.rows",
    ),
    "derive/passes": (
        "fransys_model.checks",
        "fransys_model.derive.texts",
        "fransys_model.derive.rows",
    ),
    "derive/texts": (
        "fransys_model.checks",
        "fransys_model.derive.passes",
        "fransys_model.derive.rows",
    ),
    "derive/rows": ("fransys_model.checks", "fransys_model.derive.passes"),
}


def _package_of(module_name: str, *, is_init: bool) -> str:
    """The dotted package a module belongs to, for resolving its relative imports."""
    return module_name if is_init else module_name.rsplit(".", 1)[0]


def _resolve_import(module_name: str, *, is_init: bool, node: ast.ImportFrom) -> list[str]:
    """Every absolute dotted name `node` could refer to: its module and each name as a submodule."""
    if node.level == 0:
        base = node.module or ""
    else:
        package = _package_of(module_name, is_init=is_init)
        parts = package.split(".")
        up = node.level - 1
        if up:
            parts = parts[:-up] if up < len(parts) else []
        base = ".".join(parts)
        if node.module:
            base = f"{base}.{node.module}" if base else node.module
    if not base:
        return [alias.name for alias in node.names]
    return [base, *(f"{base}.{alias.name}" for alias in node.names)]


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
    """No layer row imports a row to its left (design 1.2)."""
    assert _layer_violations(SRC_ROOT, FORBIDDEN) == []


def test_row_table_has_the_design_rows() -> None:
    """The table holds kernel plus the seven rows of design 1.2, each a directory or absent."""
    assert set(FORBIDDEN) == {
        "kernel",
        "vocab",
        "layout",
        "derive/facts",
        "checks",
        "derive/passes",
        "derive/texts",
        "derive/rows",
    }


def test_checker_fails_on_a_synthetic_violation() -> None:
    """The checker catches a `kernel` module importing `vocab`, fed as a source string."""
    source = "from fransys_model.vocab import core\n"
    imported = _imported_modules("fransys_model.kernel.bad", source, is_init=False)
    assert "fransys_model.vocab" in _violates(imported, FORBIDDEN["kernel"])


def test_checker_fails_when_vocab_imports_layout() -> None:
    """The checker catches a `vocab` module importing `layout` (decision 0009)."""
    source = "from fransys_model.layout import pages\n"
    imported = _imported_modules("fransys_model.vocab.bad", source, is_init=False)
    assert "fransys_model.layout" in _violates(imported, FORBIDDEN["vocab"])


def test_checker_fails_when_passes_imports_rows() -> None:
    """A `derive/passes` source importing `derive.rows`, by name from the package, is flagged."""
    source = "from fransys_model.derive import rows\n"
    imported = _imported_modules("fransys_model.derive.passes.bad", source, is_init=False)
    assert "fransys_model.derive.rows" in _violates(imported, FORBIDDEN["derive/passes"])


def _kernel_model_imports(root: Path) -> list[str]:
    """One entry per `fransys_model` import found in a `fransys_kernel` source file."""
    problems = []
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        is_init = parts[-1] == "__init__"
        module_name = ".".join(parts[:-1] if is_init else parts)
        source = path.read_text(encoding="utf-8")
        imported = _imported_modules(module_name, source, is_init=is_init)
        problems.extend(
            f"{path}: imports {bad}" for bad in sorted(_violates(imported, ("fransys_model",)))
        )
    return problems


def test_the_kernel_package_imports_no_fransys_model() -> None:
    """`fransys_kernel` sits under `fransys_model`: it never imports it (decision 0208)."""
    assert len(list(KERNEL_SRC.rglob("*.py"))) == 29
    assert _kernel_model_imports(KERNEL_SRC) == []


def test_the_kernel_check_fails_on_a_synthetic_import(tmp_path: Path) -> None:
    """The same scan catches a kernel module that imports `fransys_model`."""
    root = tmp_path / "fransys_kernel"
    root.mkdir()
    (root / "bad.py").write_text("from fransys_model.vocab import core\n", encoding="utf-8")
    assert _kernel_model_imports(root) == [
        f"{root / 'bad.py'}: imports fransys_model.vocab",
        f"{root / 'bad.py'}: imports fransys_model.vocab.core",
    ]


def _role_import_problems(module_name: str, source: str) -> list[str]:
    """The `fransys_model` imports of a role module that are outside `vocab` and the kernel."""
    imported = _imported_modules(module_name, source, is_init=False)
    bad = _violates(imported, ("fransys_model",)) - {"fransys_model"}
    return sorted(bad - _violates(bad, ("fransys_model.vocab", "fransys_model.kernel")))


def test_vocab_roles_imports_only_vocab_and_kernel() -> None:
    """The role tables are data: `vocab/roles*.py` imports `vocab` and the kernel only (EL-2a)."""
    paths = sorted((SRC_ROOT / "vocab").glob("roles*.py"))
    assert len(paths) >= 2
    for path in paths:
        name, _ = _module_name(path)
        assert _role_import_problems(name, path.read_text(encoding="utf-8")) == []


def test_the_role_module_check_fails_on_a_derive_import() -> None:
    """The same scan flags a role module that imports a `derive` fact."""
    source = "from fransys_model.derive.facts import children\n"
    assert _role_import_problems("fransys_model.vocab.roles_bad", source) == [
        "fransys_model.derive.facts",
        "fransys_model.derive.facts.children",
    ]


def _derive_imports_outside_facts(root: Path) -> list[str]:
    """Each `checks` import of a `derive` module that is not `derive.facts` (model-0320)."""
    problems = []
    for path in sorted((root / "checks").rglob("*.py")):
        parts = path.relative_to(root.parent).with_suffix("").parts
        imported = _imported_modules(
            ".".join(parts), path.read_text(encoding="utf-8"), is_init=parts[-1] == "__init__"
        )
        problems.extend(
            f"{path}: imports {bad}"
            for bad in sorted(imported)
            if bad.startswith("fransys_model.derive")
            and bad != "fransys_model.derive"
            and not bad.startswith("fransys_model.derive.facts")
        )
    return problems


def test_checks_read_derive_through_facts_only() -> None:
    """A check imports `derive.facts` and `vocab`; no other `derive` module (model-0320)."""
    assert _derive_imports_outside_facts(SRC_ROOT) == []


def test_checks_facts_only_rule_fails_on_a_synthetic_violation(tmp_path: Path) -> None:
    """The facts-only rule catches a check importing `derive.bom`."""
    root = tmp_path / "fransys_model"
    (root / "checks").mkdir(parents=True)
    (root / "checks" / "bad.py").write_text("from fransys_model.derive.bom import x\n")
    problems = _derive_imports_outside_facts(root)
    assert problems
    assert "fransys_model.derive.bom" in problems[0]
