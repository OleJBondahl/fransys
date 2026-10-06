"""Import-layer check via stdlib `ast`, as in fransys-model.

Enforces package-layout.md 4. The layers are `engines` → `lint` → `stages` → `conventions` →
`geometry` (decision layout-0111), and a layer imports only layers to its right. Every layer may
import
`fransys_model.kernel`; only `engines` may import anything else of `fransys_model`,
with one recorded exception (decision layout-0037, extended by units spec U7 and step4's
layout-0089): any module may import `fransys_model.derive.drawing_text` for its pure
formatters (`frame_column`, `frame_row`, `row_letter`, `position_text`, `location_prefix`,
`off_stub_line`); the readers it also holds (`marker_text`
and the rest, which take a model) stay engine-only, like every other `derive` name. Only
`geometry/symbols.py` may import the symbol libraries. Inside `engines`, only the `read/`
package may import `fransys_model.derive` or `vocab` (spec D6, `drawing_text` formatters
excepted), and only the `read/` and `write/` packages may import `fransys_model.layout`
(FC4's three enums `Orientation`, `MarkerSide` and `LabelKind` excepted); the modules that
still do are listed in `ENGINE_ALLOWED_OFFENDERS`, which is empty and stays as the refusal.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "fransys_layout"

# layer -> the layers it must not import
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "geometry": (
        "fransys_layout.conventions",
        "fransys_layout.stages",
        "fransys_layout.lint",
        "fransys_layout.engines",
    ),
    "conventions": (
        "fransys_layout.stages",
        "fransys_layout.lint",
        "fransys_layout.engines",
    ),
    "stages": ("fransys_layout.lint", "fransys_layout.engines"),
    "lint": ("fransys_layout.engines",),
}

# layers that may import `fransys_model.kernel` and nothing else of the model
KERNEL_ONLY_LAYERS = ("geometry", "conventions", "stages", "lint")
MODEL = "fransys_model"
MODEL_KERNEL = "fransys_model.kernel"

# decision layout-0037 (extended by units spec U7 and step4's layout-0089): any layer may
# import this module, but only for its pure formatters; its readers (which take a model) are
# as off-limits outside `engines` as any other `fransys_model.derive` name.
DRAWING_TEXT_MODULE = "fransys_model.derive.drawing_text"
DRAWING_TEXT_FORMATTERS = frozenset(
    {
        "frame_column",
        "frame_row",
        "row_letter",
        "position_text",
        "location_prefix",
        "off_stub_line",
        "marker_lines",
        "partner_position_text",
    }
)

SYMBOL_LIBRARIES = ("graphical_symbols", "electrical_symbols")
SYMBOL_ADAPTER = SRC_ROOT / "geometry" / "symbols.py"

# spec D6: inside `engines`, only the `read/` package may import `fransys_model.derive` or
# `fransys_model.vocab` (the `drawing_text` formatters excepted), and only the `read/` and
# `write/` packages may import `fransys_model.layout`, except FC4's three enums, which any
# engine module may import by name from `fransys_model.layout`.
MODEL_DERIVE = "fransys_model.derive"
MODEL_VOCAB = "fransys_model.vocab"
MODEL_LAYOUT = "fransys_model.layout"
LAYOUT_ENUMS = frozenset({"Orientation", "MarkerSide", "LabelKind"})
READER_PACKAGE = "fransys_layout.engines.schematic.read"
WRITER_PACKAGE = "fransys_layout.engines.schematic.write"

# The engine modules that still break that rule, each with the exact names it imports, keyed by
# the path under `src/fransys_layout`. The list is empty and stays as the refusal: a new
# entry is a rule breach, and a stale entry fails the test.
ENGINE_ALLOWED_OFFENDERS: dict[str, frozenset[str]] = {}


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


def _under(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def _violates(imported: set[str], forbidden: tuple[str, ...]) -> set[str]:
    """The subset of `imported` that names a forbidden module or one of its submodules."""
    return {module for module in imported for banned in forbidden if _under(module, banned)}


def _beyond_kernel(imported: set[str]) -> set[str]:
    """Imports of `fransys_model` that are not `fransys_model.kernel` or `drawing_text`.

    `from fransys_model import vocab` resolves to the bare package name, so the bare
    name counts as a violation too. `fransys_model.derive.drawing_text` is allowed here
    at the module level (decision layout-0037); `_drawing_text_readers` separately checks
    that only its two pure formatters are the names actually imported from it.
    """
    return {
        m
        for m in imported
        if _under(m, MODEL) and not _under(m, MODEL_KERNEL) and not _under(m, DRAWING_TEXT_MODULE)
    }


def _layout_names(source: str) -> set[str]:
    """The names `source` imports from `fransys_model.layout`."""
    return {
        target.rpartition(".")[2]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import | ast.ImportFrom)
        for target in _model_targets(node)
        if _under(target, MODEL_LAYOUT)
    }


def _beyond_kernel_in(path: Path, source: str) -> set[str]:
    """`_beyond_kernel` of a file; the symbol adapter may also import the model's `Orientation`."""
    found = _beyond_kernel(_imports_of(path))
    if path == SYMBOL_ADAPTER and _layout_names(source) <= {"Orientation"}:
        found.discard(MODEL_LAYOUT)
    return found


def _drawing_text_names(module_name: str, source: str, *, is_init: bool) -> set[str]:
    """Every name imported directly from `fransys_model.derive.drawing_text` in `source`."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and _resolve_import(
            module_name, is_init=is_init, node=node
        ) == [DRAWING_TEXT_MODULE]:
            names.update(alias.name for alias in node.names)
    return names


def _drawing_text_readers(path: Path) -> set[str]:
    """Names imported from `drawing_text` in `path` that are not one of its two formatters."""
    module_name, is_init = _module_name(path)
    names = _drawing_text_names(module_name, path.read_text(encoding="utf-8"), is_init=is_init)
    return names - DRAWING_TEXT_FORMATTERS


def _symbol_library_imports(imported: set[str]) -> set[str]:
    return _violates(imported, SYMBOL_LIBRARIES)


def _imports_of(path: Path) -> set[str]:
    module_name, is_init = _module_name(path)
    return _imported_modules(module_name, path.read_text(encoding="utf-8"), is_init=is_init)


def _layer_files(layer: str) -> list[Path]:
    return sorted((SRC_ROOT / layer).rglob("*.py"))


def _in_package(module_name: str, package: str, *, is_init: bool) -> bool:
    """Whether a module is inside the directory package `package`.

    Today's files `read.py` and `write.py` are modules, not packages, and are not inside.
    """
    if module_name == package:
        return is_init
    return module_name.startswith(package + ".")


def _model_targets(node: ast.Import | ast.ImportFrom) -> set[str]:
    """The `fransys_model` names an import statement reaches, submodule or imported name.

    `from fransys_model import derive`, `from ...derive.drawing_text import name` and
    `from fransys_model.layout import name` reach the name itself, so each imported name is
    appended to those three modules. Relative imports cannot reach `fransys_model` and give
    nothing.
    """
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    if node.level or not node.module:
        return set()
    if node.module in (MODEL, DRAWING_TEXT_MODULE, MODEL_LAYOUT):
        return {f"{node.module}.{alias.name}" for alias in node.names}
    return {node.module}


def _is_layout_target(target: str) -> bool:
    """Whether `target` is a `fransys_model.layout` name other than FC4's three enums."""
    is_enum = target.rpartition(".")[0] == MODEL_LAYOUT and (
        target.rpartition(".")[2] in LAYOUT_ENUMS
    )
    return _under(target, MODEL_LAYOUT) and not is_enum


def _is_derive_or_vocab_target(target: str) -> bool:
    """Whether `target` is a `derive` or `vocab` name outside the `drawing_text` formatters."""
    if not (_under(target, MODEL_DERIVE) or _under(target, MODEL_VOCAB)):
        return False
    is_formatter = target.rpartition(".")[0] == DRAWING_TEXT_MODULE and (
        target.rpartition(".")[2] in DRAWING_TEXT_FORMATTERS
    )
    return not is_formatter


def _forbidden_engine_imports(module_name: str, source: str, *, is_init: bool) -> set[str]:
    """The `derive`/`vocab`/`layout` names `source` imports that its package may not (D6).

    `read/` is exempt from all three; `write/` is exempt from `layout` only.
    """
    if _in_package(module_name, READER_PACKAGE, is_init=is_init):
        return set()
    layout_allowed = _in_package(module_name, WRITER_PACKAGE, is_init=is_init)
    return {
        target
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import | ast.ImportFrom)
        for target in _model_targets(node)
        if _is_derive_or_vocab_target(target) or (not layout_allowed and _is_layout_target(target))
    }


def _engine_imports_found() -> dict[str, set[str]]:
    """Each engine file's forbidden imports, keyed by its path under `src/fransys_layout`."""
    found: dict[str, set[str]] = {}
    for path in _layer_files("engines"):
        module_name, is_init = _module_name(path)
        source = path.read_text(encoding="utf-8")
        found[path.relative_to(SRC_ROOT).as_posix()] = _forbidden_engine_imports(
            module_name, source, is_init=is_init
        )
    return found


def _engine_problems(found: dict[str, set[str]], allowed: dict[str, frozenset[str]]) -> list[str]:
    """Imports outside the allow-list, and allow-list entries that no longer import the name."""
    problems = [
        f"{file}: imports {bad}, not in ENGINE_ALLOWED_OFFENDERS"
        for file, names in sorted(found.items())
        for bad in sorted(names - allowed.get(file, frozenset()))
    ]
    problems += [
        f"{file}: stale ENGINE_ALLOWED_OFFENDERS entry {gone}, no longer imported"
        for file, names in sorted(allowed.items())
        for gone in sorted(names - found.get(file, set()))
    ]
    return problems


def test_no_layer_imports_a_layer_to_its_left() -> None:
    """No layer imports a layer to its left (engines, lint, stages, conventions, geometry)."""
    problems = [
        f"{path}: imports {bad}"
        for layer, banned in FORBIDDEN.items()
        for path in _layer_files(layer)
        for bad in sorted(_violates(_imports_of(path), banned))
    ]
    assert problems == []


def test_only_engines_import_beyond_the_model_kernel() -> None:
    """`geometry`, `stages` and `lint` import nothing of the model but its kernel."""
    problems = [
        f"{path}: imports {bad}"
        for layer in KERNEL_ONLY_LAYERS
        for path in _layer_files(layer)
        for bad in sorted(_beyond_kernel_in(path, path.read_text(encoding="utf-8")))
    ]
    assert problems == []


def test_only_engines_import_the_drawing_text_readers() -> None:
    """Outside `engines`, only `DRAWING_TEXT_FORMATTERS` may come from `drawing_text`."""
    problems = [
        f"{path}: imports {bad}"
        for layer in KERNEL_ONLY_LAYERS
        for path in _layer_files(layer)
        for bad in sorted(_drawing_text_readers(path))
    ]
    assert problems == []


def test_only_the_symbol_adapter_imports_the_symbol_libraries() -> None:
    """No module but `geometry/symbols.py` imports `graphical_symbols`/`electrical_symbols`."""
    problems = [
        f"{path}: imports {bad}"
        for path in sorted(SRC_ROOT.rglob("*.py"))
        if path != SYMBOL_ADAPTER
        for bad in sorted(_symbol_library_imports(_imports_of(path)))
    ]
    assert problems == []


def test_only_the_reader_imports_derive_vocab_or_layout_in_engines() -> None:
    """In `engines`, `derive`, `vocab` and `layout` are imported only by their packages."""
    assert _engine_problems(_engine_imports_found(), ENGINE_ALLOWED_OFFENDERS) == []


def _engine_source_problems(source: str, allowed: dict[str, frozenset[str]]) -> list[str]:
    """`_engine_problems` for one engine module fed as a source string."""
    module_name = "fransys_layout.engines.schematic.bad"
    found = {"bad.py": _forbidden_engine_imports(module_name, source, is_init=False)}
    return _engine_problems(found, allowed)


def test_checker_fails_when_an_engine_imports_a_derive_module() -> None:
    """An engine module outside `read/` importing `derive.designation` is reported."""
    source = "from fransys_model.derive.designation import reference_designation\n"
    assert _engine_source_problems(source, {}) == [
        "bad.py: imports fransys_model.derive.designation, not in ENGINE_ALLOWED_OFFENDERS"
    ]


def test_checker_fails_when_an_engine_imports_derive_by_its_bare_name() -> None:
    """`from fransys_model import derive` resolves to the imported name, and is reported."""
    source = "from fransys_model import derive, kernel\n"
    assert _engine_source_problems(source, {}) == [
        "bad.py: imports fransys_model.derive, not in ENGINE_ALLOWED_OFFENDERS"
    ]


def test_checker_fails_when_an_engine_imports_a_vocab_table() -> None:
    """`from fransys_model.vocab.tables import ports` is reported, under `TYPE_CHECKING` too."""
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from fransys_model.vocab.tables import ports\n"
    )
    assert _engine_source_problems(source, {}) == [
        "bad.py: imports fransys_model.vocab.tables, not in ENGINE_ALLOWED_OFFENDERS"
    ]


def test_checker_allows_the_drawing_text_formatters_and_kernel_in_an_engine() -> None:
    """The three `drawing_text` formatters and `kernel` are not reported, but a reader is."""
    source = (
        "from fransys_model.derive.drawing_text import frame_column, position_text\n"
        "from fransys_model.derive.drawing_text import location_prefix, marker_text\n"
        "from fransys_model.kernel import Id\n"
    )
    assert _engine_source_problems(source, {}) == [
        (
            "bad.py: imports fransys_model.derive.drawing_text.marker_text, "
            "not in ENGINE_ALLOWED_OFFENDERS"
        )
    ]


def test_checker_reports_a_stale_allow_list_entry() -> None:
    """A listed offender that no longer imports the name is reported, so the list only shrinks."""
    source = "from fransys_model.kernel import Id\n"
    allowed = {"bad.py": frozenset({"fransys_model.vocab.enums"})}
    assert _engine_source_problems(source, allowed) == [
        (
            "bad.py: stale ENGINE_ALLOWED_OFFENDERS entry fransys_model.vocab.enums, "
            "no longer imported"
        )
    ]


def test_checker_exempts_the_reader_package_but_not_the_reader_file() -> None:
    """A module under `read/` may import `derive`; today's `read.py` file is not exempt."""
    source = "from fransys_model.derive.designation import port_designation\n"
    inside = _forbidden_engine_imports(
        "fransys_layout.engines.schematic.read.items", source, is_init=False
    )
    init = _forbidden_engine_imports(READER_PACKAGE, source, is_init=True)
    file = _forbidden_engine_imports(READER_PACKAGE, source, is_init=False)
    assert (inside, init, file) == (set(), set(), {"fransys_model.derive.designation"})


def test_checker_fails_when_an_engine_imports_a_layout_name() -> None:
    """A `fransys_model.layout` name outside `read/` and `write/` is reported."""
    source = "from fransys_model.layout import derived_layout_ids\n"
    assert _engine_source_problems(source, {}) == [
        ("bad.py: imports fransys_model.layout.derived_layout_ids, not in ENGINE_ALLOWED_OFFENDERS")
    ]


def test_checker_allows_the_three_layout_enums_in_an_engine() -> None:
    """Orientation, MarkerSide and LabelKind from `fransys_model.layout` are not reported."""
    source = "from fransys_model.layout import Orientation, MarkerSide, LabelKind\n"
    assert _engine_source_problems(source, {}) == []


def test_checker_fails_when_an_engine_imports_layout_by_its_bare_name() -> None:
    """`from fransys_model import layout` resolves to the imported name, and is reported."""
    source = "from fransys_model import layout\n"
    assert _engine_source_problems(source, {}) == [
        "bad.py: imports fransys_model.layout, not in ENGINE_ALLOWED_OFFENDERS"
    ]


def test_checker_allows_off_stub_line_from_drawing_text_in_an_engine() -> None:
    """`off_stub_line` is a pure formatter of `drawing_text`, so it is not reported."""
    source = "from fransys_model.derive.drawing_text import off_stub_line\n"
    assert _engine_source_problems(source, {}) == []


def test_checker_exempts_the_writer_package_for_layout_only() -> None:
    """A module under `write/` may import `layout` but not `derive`; today's `write.py` may not."""
    source = (
        "from fransys_model.layout import derived_layout_ids\n"
        "from fransys_model.derive.designation import port_designation\n"
    )
    inside = _forbidden_engine_imports(
        "fransys_layout.engines.schematic.write.records", source, is_init=False
    )
    init = _forbidden_engine_imports(WRITER_PACKAGE, source, is_init=True)
    file = _forbidden_engine_imports(WRITER_PACKAGE, source, is_init=False)
    assert (inside, init, file) == (
        {"fransys_model.derive.designation"},
        {"fransys_model.derive.designation"},
        {"fransys_model.derive.designation", "fransys_model.layout.derived_layout_ids"},
    )


def test_checker_exempts_the_reader_package_for_layout_too() -> None:
    """A module under `read/` may import `derive`, `vocab` and `layout` alike."""
    source = (
        "from fransys_model.layout import derived_layout_ids\n"
        "from fransys_model.derive.designation import port_designation\n"
        "from fransys_model.vocab.tables import ports\n"
    )
    inside = _forbidden_engine_imports(
        "fransys_layout.engines.schematic.read.items", source, is_init=False
    )
    assert inside == set()


def test_checker_fails_when_a_stage_imports_an_engine() -> None:
    """The layer check catches a `stages` module importing `engines`, fed as a source string."""
    source = "from fransys_layout.engines.schematic import engine\n"
    imported = _imported_modules("fransys_layout.stages.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["stages"]) == {"fransys_layout.engines.schematic"}


def test_checker_fails_when_conventions_import_a_stage() -> None:
    """The conventions layer imports `geometry` and the kernel only: a stage import is caught."""
    source = "from fransys_layout.stages import place\n"
    imported = _imported_modules("fransys_layout.conventions.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["conventions"]) == {"fransys_layout.stages"}


def test_checker_fails_when_geometry_imports_conventions() -> None:
    """`geometry` sits to the right of `conventions`, so it may not import it."""
    source = "from fransys_layout.conventions import fact\n"
    imported = _imported_modules("fransys_layout.geometry.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["geometry"]) == {"fransys_layout.conventions"}


def test_checker_fails_when_conventions_import_the_model_vocabulary() -> None:
    """Conventions are kernel-only: `vocab` is caught, so an enum reaches a row as its value."""
    source = "from fransys_model.vocab.enums import FunctionKind\n"
    imported = _imported_modules("fransys_layout.conventions.bad", source, is_init=False)
    assert "conventions" in KERNEL_ONLY_LAYERS
    assert _beyond_kernel(imported) == {"fransys_model.vocab.enums"}


def test_checker_fails_on_a_relative_import_to_the_left() -> None:
    """The layer check resolves `from ..lint import codes` inside `geometry`."""
    source = "from ..lint import codes\n"
    imported = _imported_modules("fransys_layout.geometry.bad", source, is_init=False)
    assert _violates(imported, FORBIDDEN["geometry"]) == {"fransys_layout.lint"}


def test_checker_fails_when_a_stage_imports_the_model_vocabulary() -> None:
    """The kernel-only check catches `vocab`, and the bare package, but not `kernel`."""
    source = (
        "from fransys_model.kernel import Id\n"
        "from fransys_model.vocab.enums import FunctionKind\n"
        "from fransys_model import derive\n"
    )
    imported = _imported_modules("fransys_layout.stages.bad", source, is_init=False)
    assert _beyond_kernel(imported) == {"fransys_model.vocab.enums", "fransys_model"}


def test_checker_still_fails_when_a_stage_imports_another_derive_module() -> None:
    """The `drawing_text` exception is narrow: any other `derive` name still fails."""
    source = "from fransys_model.derive.designation import reference_designation\n"
    imported = _imported_modules("fransys_layout.stages.bad", source, is_init=False)
    assert _beyond_kernel(imported) == {"fransys_model.derive.designation"}


def test_checker_allows_the_drawing_text_formatters_from_a_stage() -> None:
    """`fransys_model.derive.drawing_text` itself is not a kernel-only violation."""
    source = (
        "from fransys_model.derive.drawing_text import "
        "frame_column, location_prefix, position_text\n"
    )
    imported = _imported_modules("fransys_layout.stages.bad", source, is_init=False)
    assert _beyond_kernel(imported) == set()


def test_symbol_adapter_may_import_only_the_model_orientation_from_layout() -> None:
    """LC7: `Orientation` is the model's; the adapter may import it, and no other layout name."""
    ok = "from fransys_model.layout import Orientation\n"
    bad = "from fransys_model.layout import Orientation, SymbolPlacement\n"
    assert _layout_names(ok) == {"Orientation"}
    assert _beyond_kernel_in(SYMBOL_ADAPTER, ok) == set()
    assert _beyond_kernel_in(SYMBOL_ADAPTER, bad) == {MODEL_LAYOUT}


def test_checker_fails_when_a_stage_imports_a_drawing_text_reader() -> None:
    """A name from `drawing_text` other than the three pure formatters still fails."""
    source = "from fransys_model.derive.drawing_text import frame_column, marker_text\n"
    names = _drawing_text_names("fransys_layout.stages.bad", source, is_init=False)
    assert names - DRAWING_TEXT_FORMATTERS == {"marker_text"}


def test_checker_fails_when_a_stage_imports_a_symbol_library() -> None:
    """The symbol-library check catches both libraries, in either import form."""
    source = "import graphical_symbols\nfrom electrical_symbols import LIBRARY\n"
    imported = _imported_modules("fransys_layout.stages.bad", source, is_init=False)
    assert _symbol_library_imports(imported) == {"graphical_symbols", "electrical_symbols"}
