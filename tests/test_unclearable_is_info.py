"""A drawing defect no consumer action clears is INFO, with Fransys's own text (layout-0252).

The twelve codes of `UNCLEARABLE` are the render-stage WARNINGs whose `who` is Fransys. Each is INFO
in its `CodeInfo`, carries the text as its fix, and no emitting site writes `Severity.WARNING`
beside it. Every other layout WARNING keeps a consumer fix and stays a WARNING.
"""

import ast
from pathlib import Path

from fransys_layout.lint.codes import FINDING_CODES, UNCLEARABLE, severity_of
from fransys_layout.lint.codes_defects import COULD_NOT_DRAW
from fransys_model.kernel import Severity

LAYOUT_SRC = Path(__file__).resolve().parent.parent / "packages" / "fransys-layout" / "src"
TEXT = "Fransys could not draw this cleanly; please report it with the smallest model"


def test_every_unclearable_code_is_info_with_the_text() -> None:
    infos = {info.code: info for info in FINDING_CODES}
    assert COULD_NOT_DRAW == TEXT
    assert len(UNCLEARABLE) == 12
    for code in UNCLEARABLE:
        assert infos[code].severities == (Severity.INFO,), code
        assert infos[code].fix == TEXT, code
        assert severity_of(code) is Severity.INFO, code


def test_no_warning_a_consumer_can_clear_is_touched() -> None:
    """Every layout WARNING outside the list names a consumer or author action."""
    for info in FINDING_CODES:
        if info.code in UNCLEARABLE:
            continue
        assert info.fix != TEXT, info.code
        if Severity.WARNING in info.severities:
            assert info.who != "Fransys", info.code
            assert severity_of(info.code) is Severity.WARNING, info.code


def test_no_site_writes_warning_for_an_unclearable_code() -> None:
    """Probe target: a `Finding(code=<unclearable>, severity=Severity.WARNING)` anywhere fails."""
    bad: list[str] = []
    for path in LAYOUT_SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                kw = {k.arg: ast.unparse(k.value) for k in node.keywords if k.arg}
                if kw.get("code") in UNCLEARABLE and kw.get("severity") == "Severity.WARNING":
                    bad.append(f"{path.name}:{node.lineno}")
    assert bad == []
