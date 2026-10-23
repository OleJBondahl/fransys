"""FLIP-NOW F3 DEL-3, closed by FAN-2 (R338): the overview imports nothing of the old engine.

The old schematic engine and its stages are deleted; a module of those names coming back into
the overview's imports fails here.
"""

import ast
from pathlib import Path

import fransys_layout

_OVERVIEW = Path(fransys_layout.__file__).parent / "engines" / "overview"
_OLD = ("fransys_layout.engines.schematic", "fransys_layout.stages")


def _old_imports(source: str) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(_OLD):
            found |= {(node.module or "", a.name) for a in node.names}
        if isinstance(node, ast.Import):
            found |= {(a.name, "") for a in node.names if a.name.startswith(_OLD)}
    return found


def test_overview_imports_nothing_of_the_old_engine() -> None:
    """A new import of `engines/schematic` or `stages` from the overview fails here."""
    seen = sorted(
        (str(p.relative_to(_OVERVIEW)), imp)
        for p in sorted(_OVERVIEW.rglob("*.py"))
        for imp in _old_imports(p.read_text())
    )
    assert not seen, f"overview imports of the old engine: {seen}"


def test_the_check_sees_an_old_engine_import() -> None:
    """The scan finds `from ...stages.space import X`, so the test above can fail."""
    src = "from fransys_layout.stages.space import Other\nimport fransys_layout.stages.x\n"
    assert _old_imports(src) == {
        ("fransys_layout.stages.space", "Other"),
        ("fransys_layout.stages.x", ""),
    }
