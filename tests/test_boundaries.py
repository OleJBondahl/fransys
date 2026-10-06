"""First-party import boundaries of the workspace (spec section 5), checked with stdlib ast."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_ROOT = ROOT / "packages"

# `lean_surface` is the one home of "the surface" (MS1, MS2, MS6): loaded like `test_lean_
# surface.py` loads it (`importlib.util.spec_from_file_location`, not a package module).
_lean_surface_spec = importlib.util.spec_from_file_location(
    "fransys_lean_surface", ROOT / "scripts" / "lean_surface.py"
)
if _lean_surface_spec is None or _lean_surface_spec.loader is None:
    msg = "could not load scripts/lean_surface.py"
    raise ImportError(msg)
lean_surface = importlib.util.module_from_spec(_lean_surface_spec)
sys.modules[_lean_surface_spec.name] = lean_surface
_lean_surface_spec.loader.exec_module(lean_surface)

# import name -> first-party packages it may import (itself is always allowed)
ALLOWED: dict[str, frozenset[str]] = {
    "fransys_model": frozenset(),
    "electrical_symbols": frozenset(),
    "fransys_parts": frozenset({"fransys_model"}),
    "fransys_author": frozenset({"fransys_model"}),
    "fransys_layout": frozenset({"fransys_model", "electrical_symbols"}),
    "fransys_render": frozenset({"fransys_model", "electrical_symbols"}),
    "fransys_reports": frozenset({"fransys_model"}),
    "fransys_pdf": frozenset({"fransys_model"}),
    "fransys_kicad": frozenset({"fransys_model"}),
    "fransys_wago": frozenset({"fransys_model"}),
    "fransys_overview": frozenset({"fransys_model"}),
}
ALLOWED["fransys"] = frozenset(ALLOWED)

FIRST_PARTY = frozenset(ALLOWED) | {"fransys"}

# Every source package gets an entry: packages that import no third-party package, except the
# ones named here. This must cover every package (not just the ones with an exception) because
# `third_party_violations` is only checked for packages listed here -- a package left out of this
# table is never checked for a third-party import at all (decision 0015). Each entry must equal
# root DESIGN 4's third-party column for that package.
THIRD_PARTY: dict[str, frozenset[str]] = {
    "fransys_model": frozenset(),
    "electrical_symbols": frozenset({"graphical_symbols"}),
    "fransys_parts": frozenset(),
    "fransys_author": frozenset(),
    "fransys_layout": frozenset({"graphical_symbols"}),
    "fransys_render": frozenset({"graphical_symbols"}),
    "fransys_reports": frozenset(),
    "fransys_pdf": frozenset(),
    "fransys_kicad": frozenset(),
    "fransys_wago": frozenset(),
    "fransys_overview": frozenset(),
    "fransys": frozenset({"typst"}),
}

# A type-checker stub module: importable only under TYPE_CHECKING, absent at runtime, no dependency.
TYPE_CHECKER_ONLY = frozenset({"_typeshed"})


def _imported(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def violations(package: str, source: str) -> set[str]:
    """First-party top-level packages that `source` imports and `package` may not."""
    return (_imported(source) & FIRST_PARTY) - ALLOWED[package] - {package}


def third_party_violations(package: str, source: str) -> set[str]:
    """Third-party top-level packages that `source` imports and `package` may not."""
    outside = _imported(source) - FIRST_PARTY - sys.stdlib_module_names - TYPE_CHECKER_ONLY
    return outside - THIRD_PARTY[package]


def _source_packages() -> list[Path]:
    """Every `packages/*/src/<name>` directory that holds at least one real `*.py` file.

    A directory left holding only a stale `__pycache__` (git deletes a package's tracked
    files but not the interpreter's cache) is not a package: `__pycache__` is skipped, so a
    directory holding nothing else has no `*.py` under it. Unlike requiring `__init__.py`,
    this still counts a namespace-style package (real `.py` files, no `__init__.py`): that
    directory is a real source package too, and every source package must be checked.
    """
    return sorted(
        p
        for p in PACKAGES_ROOT.glob("*/src/*")
        if p.is_dir() and any("__pycache__" not in f.parts for f in p.rglob("*.py"))
    )


def test_every_source_package_is_in_the_table():
    packages = _source_packages()
    unknown = [p.name for p in packages if p.name not in ALLOWED]
    assert unknown == []
    # A named expectation, not just `unknown == []`: an emptied glob (e.g. a broken pattern)
    # would otherwise pass this test vacuously.
    assert len(packages) == len(ALLOWED)


@pytest.mark.parametrize("package_dir", _source_packages(), ids=lambda p: p.name)
def test_package_imports_only_what_the_table_allows(package_dir: Path):
    found = {
        f"{path.relative_to(PACKAGES_ROOT)}: {name}"
        for path in package_dir.rglob("*.py")
        for name in violations(package_dir.name, path.read_text(encoding="utf-8"))
    }
    assert found == set()


@pytest.mark.parametrize(
    "package_dir", [p for p in _source_packages() if p.name in THIRD_PARTY], ids=lambda p: p.name
)
def test_package_imports_no_third_party_beyond_its_exceptions(package_dir: Path):
    found = {
        f"{path.relative_to(PACKAGES_ROOT)}: {name}"
        for path in package_dir.rglob("*.py")
        for name in third_party_violations(package_dir.name, path.read_text(encoding="utf-8"))
    }
    assert found == set()


def test_the_check_can_fail():
    assert violations("fransys_reports", "import fransys_render") == {"fransys_render"}
    assert violations("fransys_author", "from fransys_parts.loader import load") == {
        "fransys_parts"
    }
    assert violations("fransys_render", "from fransys_model.kernel import Model") == set()
    assert violations("fransys_pdf", "from . import presets\nimport tomllib") == set()


def test_the_third_party_check_can_fail():
    assert third_party_violations("electrical_symbols", "import jsonschema") == {"jsonschema"}
    assert third_party_violations("fransys_model", "import deal") == {"deal"}
    assert third_party_violations("electrical_symbols", "import graphical_symbols") == set()
    assert third_party_violations("electrical_symbols", "from . import x\nimport typing") == set()
    assert (
        third_party_violations("fransys_model", "from _typeshed import DataclassInstance") == set()
    )
    assert third_party_violations("fransys_reports", "import graphical_symbols") == {
        "graphical_symbols"
    }


# --- The import surface (SURFACE spec, decision 0046, MS1/MS3/MS6): outside a package, source
# crosses into another workspace package only through that package's own top-level `__all__`
# (MS6), or, for the model, one of its seven named modules (MS1). `lean_surface` is the one home
# of "the surface"; this test keeps no module list of its own. `graphical_symbols` is outside:
# it is third-party, never a workspace package, so it never reaches `FIRST_PARTY` at all.

SURFACE_MODULES: frozenset[str] = frozenset(lean_surface.surface_modules())
SURFACE_NAMES: dict[str, tuple[str, ...]] = lean_surface.surface_names()

# Layout's own imports of `fransys_model` are still its pre-redesign deep paths (step 5 is
# mid-rewrite); this ONE dated line exempts that one pair until its follow-up rewrites them to
# the seven surface modules and removes it. Nothing else is exempt (2026-09-27, SURFACE MS3).
SURFACE_EXEMPT: frozenset[tuple[str, str]] = frozenset({("fransys_layout", "fransys_model")})


def _surface_import_targets(
    node: ast.Import | ast.ImportFrom, package: str
) -> list[tuple[str, str]]:
    """`(bound_name, full_dotted_target)` for every name `node` pulls from another first-party
    workspace package (never `package`'s own, never third-party or stdlib).
    """
    found: list[tuple[str, str]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in FIRST_PARTY and top != package:
                found.append((alias.asname or top, alias.name if alias.asname else top))
        return found
    if node.level or node.module is None:
        return found  # a relative import is always this same package
    top = node.module.split(".")[0]
    if top not in FIRST_PARTY or top == package:
        return found
    return [(alias.asname or alias.name, f"{node.module}.{alias.name}") for alias in node.names]


def surface_violations(package: str, source: str) -> set[str]:
    """Every crossing import or attribute read in `source` that MS1, MS3 or MS6 forbids.

    A name whose full dotted path is itself a surface module (`lean_surface.surface_modules()`)
    binds that module (MS3): the import itself passes, and every attribute the file later reads
    off its bound name must be in THAT module's own `__all__`, checked in a second pass over the
    whole file (an attribute read may be anywhere, not only beside the import). Any other
    crossing name must already be in its own module's `__all__`, that module must itself be a
    surface module, and a `_`-prefixed name always fails either way -- which also covers a
    submodule bound directly (`from fransys_model.vocab import tables`): a submodule's own
    name is never listed in its parent's `__all__`, so it fails the same ordinary check.
    """
    tree = ast.parse(source)
    module_aliases: dict[str, str] = {}
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        for bound, target in _surface_import_targets(node, package):
            if (package, target.split(".")[0]) in SURFACE_EXEMPT:
                continue
            if target in SURFACE_MODULES:
                module_aliases[bound] = target
                continue
            module_path, _, name = target.rpartition(".")
            if (
                module_path not in SURFACE_MODULES
                or name.startswith("_")
                or name not in SURFACE_NAMES.get(module_path, ())
            ):
                found.add(target)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in module_aliases
        ):
            target = module_aliases[node.value.id]
            if node.attr.startswith("_") or node.attr not in SURFACE_NAMES.get(target, ()):
                found.add(f"{target}.{node.attr}")
    return found


@pytest.mark.parametrize("package_dir", _source_packages(), ids=lambda p: p.name)
def test_package_crosses_into_another_package_only_through_its_surface(package_dir: Path):
    found = {
        f"{path.relative_to(PACKAGES_ROOT)}: {name}"
        for path in package_dir.rglob("*.py")
        for name in surface_violations(package_dir.name, path.read_text(encoding="utf-8"))
    }
    assert found == set()


def test_the_surface_check_can_fail():
    # Acceptance 1: a deep path, even of a name in its entry point's own `__all__`, fails; the
    # same name from the surface module itself passes.
    assert surface_violations("fransys_render", "from fransys_model.vocab.tables import items") == {
        "fransys_model.vocab.tables.items"
    }
    assert surface_violations("fransys_render", "from fransys_model.vocab import items") == set()
    # Acceptance 2: a name not in the module's `__all__` fails, and so does a `_` name.
    assert surface_violations(
        "fransys_render", "from fransys_model.vocab import not_a_real_name"
    ) == {"fransys_model.vocab.not_a_real_name"}
    assert surface_violations("fransys_render", "from fransys_model.vocab import _hidden") == {
        "fransys_model.vocab._hidden"
    }
    # Acceptance 3: a name in `derive.drawing_text`'s own `__all__` passes.
    assert (
        surface_violations(
            "fransys_render", "from fransys_model.derive.drawing_text import outline_title"
        )
        == set()
    )
    # Acceptance 5 (MS6): a facade import from layout's internals fails; the same name from
    # layout's own top level passes.
    assert surface_violations(
        "fransys", "from fransys_layout.engines.schematic import lay_out_schematic"
    ) == {"fransys_layout.engines.schematic.lay_out_schematic"}
    assert surface_violations("fransys", "from fransys_layout import lay_out_schematic") == set()
    # Acceptance 9 (MS3, module binding): `baseline.listing` passes; `baseline._common_location`
    # and a submodule bound directly (`designation`, not one of the seven) both fail.
    assert (
        surface_violations(
            "fransys",
            "from fransys_model.derive import baseline\nbaseline.listing(model, unit)\n",
        )
        == set()
    )
    assert surface_violations(
        "fransys",
        "from fransys_model.derive import baseline\nbaseline._common_location(model, unit)\n",
    ) == {"fransys_model.derive.baseline._common_location"}
    assert surface_violations("fransys", "from fransys_model.derive import designation") == {
        "fransys_model.derive.designation"
    }
    # Layout's own deep model imports are exempt (MS3), until step 5's follow-up.
    assert (
        surface_violations(
            "fransys_layout", "from fransys_model.derive.designation import bom_sort_key"
        )
        == set()
    )


def test_a_leading_underscore_fails_even_when_the_surface_itself_lists_it(monkeypatch):
    """MS1's `_`-prefix rule fires on its own, not only as a side effect of a name being absent
    from `__all__` -- every other `_` case above is also absent, so this proves the clause
    matters by making the checker's own copy of a real `__all__` list a `_` name, which no
    module's real `__all__` ever does.
    """
    monkeypatch.setitem(
        SURFACE_NAMES,
        "fransys_model.vocab",
        (*SURFACE_NAMES["fransys_model.vocab"], "_hidden"),
    )
    assert surface_violations("fransys_render", "from fransys_model.vocab import _hidden") == {
        "fransys_model.vocab._hidden"
    }


def test_a_leading_underscore_attribute_fails_even_when_listed(monkeypatch):
    """The same proof as above, for MS3's attribute-off-a-bound-module check."""
    monkeypatch.setitem(
        SURFACE_NAMES,
        "fransys_model.derive.baseline",
        (*SURFACE_NAMES["fransys_model.derive.baseline"], "_common_location"),
    )
    assert surface_violations(
        "fransys",
        "from fransys_model.derive import baseline\nbaseline._common_location(model, unit)\n",
    ) == {"fransys_model.derive.baseline._common_location"}


def test_a_deep_import_under_type_checking_still_fails():
    # The order's own wording ("including TYPE_CHECKING blocks"): `ast.walk` already reaches
    # this body (the same way `_imported`/`violations` do), so no `_runtime_imports`-style
    # skip is needed -- this guards against someone later switching to that style by mistake.
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from fransys_model.vocab.tables import items\n"
    )
    assert surface_violations("fransys_render", source) == {"fransys_model.vocab.tables.items"}


def test_a_plain_import_of_a_deep_path_fails():
    assert surface_violations("fransys_render", "import fransys_model.vocab.tables as t") == {
        "fransys_model.vocab.tables"
    }


def test_a_plain_top_level_import_still_checks_its_attribute_reads():
    source = "import fransys_pdf\nfransys_pdf._geometry.document_metadata\n"
    assert surface_violations("fransys", source) == {"fransys_pdf._geometry"}


# --- Output purity (design section 3, invariant 4): every package in PURITY_SCOPE is checked for
# a stdlib-name and call-name deny-list. Matching is deliberately crude, by name only, never by
# type or scope: a false positive is fixed by renaming a method, a false negative is the thing
# this guards against (designer's ruling; see decision 0012).

# Every first-party package except `fransys` (the facade may do all of it) and
# `fransys_parts` (reads part files by contract).
PURITY_SCOPE: frozenset[str] = frozenset(ALLOWED) - {"fransys", "fransys_parts"}

# Forbidden by top-level import name. NOT forbidden, and each for a stated reason: `datetime`
# (parsing an authored date is pure), `pathlib` (a path is a value; `font_dir()` returns one),
# `uuid`, `io` (reports writes CSV to a StringIO). `sys` is also not here: most of `sys` is a
# value or introspection (`_getframe`, `maxsize`, `stdlib_module_names`) and is pure -- `fransys
# _author`'s `caller_origin()` reads `sys._getframe(1)` to satisfy the Input contract's Origin
# (design section 3), not to touch the process environment. What the list was reaching for through
# `sys` is named directly below instead.
FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "time",
        "random",
        "secrets",
        "tempfile",
        "shutil",
        "subprocess",
        "os",
        "glob",
        "socket",
        "threading",
        "multiprocessing",
        "asyncio",
    }
)

# Forbidden by attribute-call name, whatever the receiver (crude by design). `uuid.uuid5` is
# deliberately absent: it is deterministic (same namespace and name give the same id), which is
# why `uuid1` and `uuid4` are denied and `uuid5` is not -- and it is a real current use (netlist
# tstamps, model ids).
FORBIDDEN_CALLS: frozenset[str] = frozenset(
    {
        "now",
        "today",
        "utcnow",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "rename",
        "exists",
        "is_file",
        "iterdir",
        "glob",
        "uuid1",
        "uuid4",
        "getenv",
    }
)

# Forbidden `sys.<attr>` access, qualified to the Name `sys` (unlike the rest of this file's
# crude by-name matching): the process environment, not stack introspection.
FORBIDDEN_SYS_ATTRS: frozenset[str] = frozenset(
    {"argv", "stdin", "stdout", "stderr", "exit", "path", "modules"}
)

# Recorded exceptions, module by module, never package-wide, and ONLY while the gate would
# otherwise fail on the module: the can-fail tests prove the gate fires, this table lists what it
# fires on. This is not the workspace's full list of file I/O -- invariant 4 is. The
# `electrical_symbols` bundle read at import (invariant 4) is real, recorded there, and
# invisible to this ast scan of our own source: the read happens inside
# `graphical_symbols.load_bundle`, not a name on either deny-list. It needs no entry here, and
# adding one anyway would let a reader mistake this table for the exhaustive list. CT1 removed
# the workspace's other such exception, the wireviz `dot` spawn: no third-party package spawns a
# subprocess for this workspace any more.
PURITY_EXEMPT: frozenset[tuple[str, str]] = frozenset(
    {
        ("fransys_kicad", "__main__.py"),  # invariant 4: developer command (kicad-sym skeleton)
    }
)


def purity_violations(source: str) -> set[str]:
    """Deny-listed imports, calls, `os.environ` and `sys.<attr>` access (design section 3)."""
    found = _imported(source) & FORBIDDEN_IMPORTS
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                found.add("open")
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CALLS:
                found.add(func.attr)
        elif isinstance(node, ast.Attribute) and node.attr == "environ":
            found.add("environ")
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "sys"
            and node.attr in FORBIDDEN_SYS_ATTRS
        ):
            found.add(f"sys.{node.attr}")
    return found


def _purity_scope_packages() -> list[Path]:
    return [p for p in _source_packages() if p.name in PURITY_SCOPE]


@pytest.mark.parametrize("package_dir", _purity_scope_packages(), ids=lambda p: p.name)
def test_package_output_is_pure(package_dir: Path):
    found = {
        f"{path.relative_to(PACKAGES_ROOT)}: {name}"
        for path in package_dir.rglob("*.py")
        if (package_dir.name, path.relative_to(package_dir).as_posix()) not in PURITY_EXEMPT
        for name in purity_violations(path.read_text(encoding="utf-8"))
    }
    assert found == set()


def test_the_purity_check_can_fail():
    # `import random` in a fransys_reports source is a violation.
    assert purity_violations("import random") == {"random"}
    # `Path("x").read_text()` in a fransys_pdf source is a violation.
    assert purity_violations('from pathlib import Path\nPath("x").read_text()') == {"read_text"}
    # `sys.argv` in a fransys_reports source is a violation (the process environment).
    assert purity_violations("import sys\nsys.argv") == {"sys.argv"}


def test_the_purity_check_does_not_fire_on_deterministic_or_allowed_code():
    # `uuid.uuid5(...)` in fransys_kicad is deterministic (netlist tstamps, model ids): not a
    # violation, unlike `uuid1`/`uuid4`.
    assert purity_violations("import uuid\nuuid.uuid5(namespace, name)") == set()
    # `from pathlib import Path` in fransys_pdf is not a violation.
    assert purity_violations("from pathlib import Path") == set()
    # `sys._getframe(1)` in fransys_author is stack introspection, not the process environment:
    # not a violation (this is what lets `caller_origin()`'s Input contract pass with no
    # exception).
    assert purity_violations("import sys\nsys._getframe(1)") == set()


# --- Import cycles: the module graph of the whole workspace has no strongly connected component
# of more than one module. Nodes are the modules under every `packages/*/src` (`__init__.py` is
# the module named by its package); an edge is an import of another workspace module.


def _module_names(src_root: Path) -> dict[str, Path]:
    """Dotted module name -> file, for every `*.py` under `src_root`; `pkg/__init__.py` is `pkg`."""
    names: dict[str, Path] = {}
    for path in sorted(src_root.rglob("*.py")):
        parts = list(path.relative_to(src_root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        if parts:
            names[".".join(parts)] = path
    return names


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _runtime_imports(node: ast.AST) -> list[ast.Import | ast.ImportFrom]:
    """Every import under `node`, at any depth (a function-level import counts), that can run.

    The body of `if TYPE_CHECKING:` (or `if typing.TYPE_CHECKING:`) never runs, so its imports are
    left out; the `else:` branch of such an `if` runs, so its imports stay.
    """
    found: list[ast.Import | ast.ImportFrom] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Import | ast.ImportFrom):
            found.append(child)
        elif isinstance(child, ast.If) and _is_type_checking(child.test):
            for branch_node in child.orelse:
                found.extend(_runtime_imports(ast.Module(body=[branch_node], type_ignores=[])))
        else:
            found.extend(_runtime_imports(child))
    return found


def _import_targets(
    node: ast.Import | ast.ImportFrom, package: str, modules: dict[str, Path]
) -> set[str]:
    """Workspace modules that one import statement in a module of `package` depends on.

    `import a.b.c` depends on `a.b.c` only (the parents' implicit import is not an edge).
    `from x import y` depends on `x.y` when that is a workspace module, else on `x`.
    """
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names if alias.name in modules}
    base: list[str] = []
    if node.level:
        parts = package.split(".")
        base = parts[: len(parts) - (node.level - 1)]
    if node.module:
        base += node.module.split(".")
    source = ".".join(base)
    targets = {f"{source}.{alias.name}" for alias in node.names} & modules.keys()
    if not targets and source in modules:
        targets.add(source)
    return targets


def _strongly_connected(graph: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan's algorithm: the components of `graph` with more than one node, each sorted."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(name: str) -> None:
        index[name] = low[name] = len(index)
        stack.append(name)
        on_stack.add(name)
        for target in sorted(graph[name]):
            if target not in index:
                visit(target)
                low[name] = min(low[name], low[target])
            elif target in on_stack:
                low[name] = min(low[name], index[target])
        if low[name] == index[name]:
            component = stack[stack.index(name) :]
            del stack[stack.index(name) :]
            on_stack.difference_update(component)
            if len(component) > 1:
                components.append(sorted(component))

    for name in sorted(graph):
        if name not in index:
            visit(name)
    return sorted(components)


def import_cycles(*src_roots: Path) -> list[list[str]]:
    """Import cycles among the modules under `src_roots`, each a sorted list of module names."""
    modules: dict[str, Path] = {}
    for src_root in src_roots:
        modules.update(_module_names(src_root))
    graph: dict[str, set[str]] = {}
    for name, path in modules.items():
        package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        targets: set[str] = set()
        for node in _runtime_imports(tree):
            targets |= _import_targets(node, package, modules)
        graph[name] = targets - {name}
    return _strongly_connected(graph)


def test_the_workspace_has_no_import_cycle():
    cycles = import_cycles(*sorted(PACKAGES_ROOT.glob("*/src")))
    assert cycles == [], "import cycles:\n" + "\n".join(f"  {', '.join(c)}" for c in cycles)


def _write_tree(root: Path, files: dict[str, str]) -> Path:
    for relative, source in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def test_the_cycle_check_catches_two_modules_importing_each_other(tmp_path: Path):
    _write_tree(tmp_path, {"a.py": "import b\n", "b.py": "from a import x\n"})
    assert import_cycles(tmp_path) == [["a", "b"]]


def test_the_cycle_check_catches_a_cycle_closed_by_a_function_level_import(tmp_path: Path):
    _write_tree(tmp_path, {"a.py": "import b\n", "b.py": "def f():\n    import a\n"})
    assert import_cycles(tmp_path) == [["a", "b"]]


def test_the_cycle_check_ignores_an_import_under_type_checking(tmp_path: Path):
    _write_tree(
        tmp_path,
        {
            "a.py": "import b\n",
            "b.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import a\n",
            "c.py": "import d\n",
            "d.py": "import typing\nif typing.TYPE_CHECKING:\n    import c\n",
        },
    )
    assert import_cycles(tmp_path) == []
    # The `else:` branch of such an `if` runs, so a cycle closed there is real.
    _write_tree(
        tmp_path,
        {"b.py": "if TYPE_CHECKING:\n    pass\nelse:\n    import a\n"},
    )
    assert import_cycles(tmp_path) == [["a", "b"]]


def test_the_cycle_check_leaves_an_acyclic_pair_alone(tmp_path: Path):
    _write_tree(tmp_path, {"a.py": "import b\nimport os\nimport missing\n", "b.py": "x = 1\n"})
    assert import_cycles(tmp_path) == []


def test_the_cycle_check_catches_a_cycle_through_a_package_init(tmp_path: Path):
    _write_tree(
        tmp_path,
        {
            "pkg/__init__.py": "from . import m\n",
            "pkg/m.py": "from pkg import x\n",
            "pkg/sub/__init__.py": "",
            "pkg/sub/n.py": "from .. import m\n",
        },
    )
    assert import_cycles(tmp_path) == [["pkg", "pkg.m"]]
    # A relative import resolves against the importing module's package (`..` from `pkg.sub`).
    _write_tree(tmp_path, {"pkg/m.py": "from .sub import n\n"})
    assert import_cycles(tmp_path) == [["pkg.m", "pkg.sub.n"]]
