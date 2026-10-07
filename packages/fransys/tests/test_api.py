"""F1: the public surface (the engineer surface, no `author`), and the first-party import scan."""

import ast
import re
from pathlib import Path

import fransys
import fransys.colours as fransys_colours
import fransys_author.surface as surface_module
import fransys_author.surface.colours as surface_colours

from fransys_model import derive as model_derive

_REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "examples").is_dir())

_EXPECTED_ALL = [
    "AI",
    "AO",
    "CONTROL",
    "DI",
    "DO",
    "EARTHED",
    "GENERIC",
    "IT",
    "AuthorError",
    "BuildErrors",
    "BuildResult",
    "Design",
    "Device",
    "DocumentPreset",
    "Draft",
    "Finding",
    "Fn",
    "FreezeError",
    "Layout",
    "MergeConflict",
    "Model",
    "PageKind",
    "PartLibraryError",
    "Pin",
    "Release",
    "ReleasePin",
    "SIGNAL",
    "Run",
    "Severity",
    "Terminal",
    "TerminalStrip",
    "TypedDevice",
    "TypedFn",
    "build",
    "check",
    "derive",
    "design",
    "diff",
    "document",
    "export_names",
    "lint",
    "parts",
    "parts_module",
    "release",
    "releases",
    "unit",
    "verify",
    "write",
]

# Every first-party import name besides `fransys` itself (spec F1: a consumer script
# imports nothing else).
_FIRST_PARTY_NOT_FRANSYS = frozenset(
    {
        "fransys_model",
        "graphical_symbols",
        "electrical_symbols",
        "fransys_parts",
        "fransys_author",
        "fransys_layout",
        "fransys_render",
        "fransys_reports",
        "fransys_pdf",
        "fransys_kicad",
        "fransys_wago",
        "fransys_overview",
    }
)

_FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _names_match(expected: list[str], actual: list[str]) -> bool:
    return sorted(expected) == sorted(actual)


def first_party_violations(source: str) -> set[str]:
    """First-party top-level packages `source` imports besides `fransys` itself."""
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    return imported & _FIRST_PARTY_NOT_FRANSYS


def _python_blocks(markdown: str) -> list[str]:
    """Every ```python fenced code block of `markdown`, its own text."""
    return _FENCE.findall(markdown)


def test_public_names():
    assert _names_match(_EXPECTED_ALL, list(fransys.__all__))


def test_public_names_can_fail():
    assert not _names_match(_EXPECTED_ALL, [*fransys.__all__, "extra_name"])


def test_author_is_not_public():
    assert "author" not in fransys.__all__
    assert not hasattr(fransys, "author")


def test_every_surface_name_is_public():
    """The facade's own `design` function stands for the surface's `design` (EA1)."""
    surface = set(surface_module.__all__) - {"design"}
    assert surface <= set(fransys.__all__)
    assert fransys.design is not surface_module.design


def test_surface_names_are_the_surface_objects():
    for name in surface_module.__all__:
        if name != "design":
            assert getattr(fransys, name) is getattr(surface_module, name)


def test_surface_check_can_fail():
    assert not {*surface_module.__all__, "NotAName"} - {"design"} <= set(fransys.__all__)


def test_colours_import_from_the_facade():
    from fransys.colours import BK, BU

    assert (BK, BU) == ("BK", "BU")
    assert fransys_colours.__all__ == surface_colours.__all__


def test_derive_is_the_models_derive_module():
    assert fransys.derive is model_derive
    assert fransys.derive.top_level_cables is model_derive.top_level_cables


def test_derive_top_level_cables_runs_on_a_built_model(demo_cabinet):
    rows = fransys.derive.top_level_cables(demo_cabinet)
    assert rows == model_derive.top_level_cables(demo_cabinet)
    assert rows, "the demo cabinet's field cable is a top-level cable"


# Named, commented exclusions from the docs/ scan below (default-deny at the root, so a doc
# added anywhere else under docs/ is covered with no further action):
# - docs/plans/: historical planning notes showing package-internal signatures
#   (docs/archive/plans/2026-09-20-scaffold.md), not a script a consumer would copy and run.
# - docs/decisions/: decision records quote or reference internal signatures for context,
#   not consumer-facing worked examples either.
# - docs/archive/: history (LC4); the moved plans and specs show internal signatures too.
_DOCS_SCAN_EXCLUDED = ("plans", "decisions", "archive")


def _docs_markdown_files(root=_REPO_ROOT):
    for path in (root / "docs").rglob("*.md"):
        relative = path.relative_to(root / "docs")
        if relative.parts and relative.parts[0] in _DOCS_SCAN_EXCLUDED:
            continue
        yield path


def test_examples_and_docs_worked_examples_import_only_fransys():
    violations: dict[str, set[str]] = {}
    for path in (_REPO_ROOT / "examples").rglob("*.py"):
        found = first_party_violations(path.read_text(encoding="utf-8"))
        if found:
            violations[str(path)] = found
    for path in _docs_markdown_files():
        text = path.read_text(encoding="utf-8")
        for index, block in enumerate(_python_blocks(text)):
            try:
                found = first_party_violations(block)
            except SyntaxError:
                # A signature listing (root DESIGN section 6), not a runnable worked
                # example: nothing to scan for imports.
                continue
            if found:
                violations[f"{path}#{index}"] = found
    assert violations == {}


def test_the_docs_scan_excludes_only_the_named_directories(tmp_path):
    """Can-fail twin: a doc under an unlisted docs/ subdirectory is still scanned.

    Built on its own tmp_path tree, so it holds in the public export, which has no docs/specs.
    """
    for sub in (*_DOCS_SCAN_EXCLUDED, "specs"):
        (tmp_path / "docs" / sub).mkdir(parents=True)
        (tmp_path / "docs" / sub / "a.md").write_text("x\n", encoding="utf-8")
    scanned = {p.relative_to(tmp_path / "docs").parts[0] for p in _docs_markdown_files(tmp_path)}
    assert scanned == {"specs"}


def test_the_import_scan_can_fail():
    assert first_party_violations("import fransys_model") == {"fransys_model"}
    assert first_party_violations("import fransys\nfrom pathlib import Path") == set()
