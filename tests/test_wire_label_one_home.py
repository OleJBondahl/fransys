"""V8: the text printed at both ends of a wire is joined in one place, `wire_label_text`.

Scans every `packages/*/src` module except `fransys_model/derive/drawing_text.py` for an
f-string, a `+` or a `join` that combines a wire's two end texts (an `end_a...` name with an
`end_b...` name, `from_` with `to`, or two designation calls). The scan is proved able to fail
on a synthetic module.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "packages/fransys-model/src/fransys_model/derive/drawing_text.py"


def _names(node: ast.AST) -> set[str]:
    found = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            found.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            found.add(sub.attr)
    return found


def _is_join(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
    )


def _called(call: ast.Call) -> str | None:
    """The name a call goes to: `f(...)` or `x.f(...)` give `f`."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def _designation_calls(node: ast.AST) -> int:
    """How many designation or end-text calls `node` holds: two in one join are a wire's ends."""
    return sum(
        1
        for sub in ast.walk(node)
        if isinstance(sub, ast.Call)
        and _called(sub) is not None
        and ("designation" in str(_called(sub)) or _called(sub) == "_end_text")
    )


def _joins_two_ends(node: ast.AST) -> bool:
    if not (isinstance(node, ast.JoinedStr) or _is_join(node) or isinstance(node, ast.BinOp)):
        return False
    names = _names(node)
    first = any("end_a" in n or n == "from_" for n in names)
    second = any("end_b" in n or n == "to" for n in names)
    return (first and second) or _designation_calls(node) >= 2


def joins_in(source: str) -> list[int]:
    """The line of each expression in `source` that joins a wire's two end texts."""
    nodes = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.expr)]
    return [node.lineno for node in nodes if _joins_two_ends(node)]


def test_the_scan_finds_a_second_home() -> None:
    """The check can fail: a module that joins `end_a` and `end_b` is caught."""
    assert joins_in('label = f"{row.end_a_designation} {row.end_b_designation}"') == [1]
    assert joins_in('label = " ".join((from_, to))') == [1]
    assert joins_in('label = f"{port_designation(m, a)} {port_designation(m, b)}"') == [1]
    assert joins_in('label = f"{item.designation} {other}"') == []


def test_no_module_but_drawing_text_joins_a_wires_two_ends() -> None:
    """The one-home test: `wire_label_text` is the only place the two ends are joined."""
    homes = {
        str(path.relative_to(ROOT)): joins_in(path.read_text(encoding="utf-8"))
        for path in sorted(ROOT.glob("packages/*/src/**/*.py"))
        if path != HOME
    }
    assert {path: lines for path, lines in homes.items() if lines} == {}
