"""Severity has one home (decision 0410, FINDINGS-SEVERITY-ONE-HOME): the code's `CodeInfo`.

Outside `fransys_kernel` and the codes modules, no `Severity.X` is handed to a call, as a
keyword value, a positional argument or an if-expression branch of either. An emit site names
"""

import ast

from gate_scan import src_modules

EXEMPT_PACKAGE = "fransys_kernel"


def _is_severity(node: ast.expr) -> bool:
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Severity"


def _values(node: ast.expr) -> list[ast.expr]:
    if isinstance(node, ast.IfExp):
        return [*_values(node.body), *_values(node.orelse)]
    return [node]


def severity_arguments(source: str) -> list[int]:
    """Lines where a call takes a `Severity.X`, directly or as an if-expression arm."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            given = [*node.args, *(k.value for k in node.keywords)]
            lines += [v.lineno for arg in given for v in _values(arg) if _is_severity(v)]
    return sorted(lines)


def _exempt(module: str) -> bool:
    last = module.rsplit(".", maxsplit=1)[-1]
    return module.split(".", maxsplit=1)[0] == EXEMPT_PACKAGE or last.startswith(("codes", "_codes"))


def test_no_emit_site_names_a_severity():
    seen = 0
    hits = []
    for module, path in src_modules():
        if _exempt(module):
            continue
        seen += 1
        hits += [f"{module}:{n}" for n in severity_arguments(path.read_text(encoding="utf-8"))]
    assert seen > 100, "the walk saw too few modules"
    assert hits == []


def test_the_severity_gate_can_fail():
    forms = [
        "Finding(code='X', severity=Severity.ERROR)",
        "finding(Severity.WARNING, 'X')",
        "Finding(severity=Severity.ERROR if a else Severity.INFO)",
    ]
    for source in forms:
        assert severity_arguments(source), source
    assert severity_arguments("ok = f.severity is Severity.ERROR\nd = {Severity.INFO: 1}") == []
