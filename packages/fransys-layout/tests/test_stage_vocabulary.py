"""No stage names a function kind or reads an authoring-key prefix (design/foundations.md 2.8, F3).

Stdlib `ast`, as in `test_layering.py`. A stage reads what the engine stamped into
`KindRoles`; it never compares a kind string, and it never slices or indexes `.key`.
A line that carries `vocab-ok` is exempt: it must say why. The key check is a heuristic: it
sees a subscript whose base is an attribute named `key`, not one on a local bound from it.
"""

import ast
from pathlib import Path

from fransys_model.vocab.enums import FunctionKind

SRC = Path(__file__).resolve().parent.parent / "src" / "fransys_layout"
STAGES = SRC / "stages"
# the conventions' code modules (facts, rows, evaluate); its tables are data and name kinds
CONVENTIONS_CODE = ("__init__", "facts", "rows", "evaluate")
KINDS = frozenset(kind.value for kind in FunctionKind)
EXEMPT = "vocab-ok"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """The `id`s of the string nodes that are docstrings."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def violations(source: str) -> list[str]:
    """Every kind string constant and every `<x>.key[...]` access in `source`, one line each."""
    tree = ast.parse(source)
    lines = source.splitlines()
    docstrings = _docstring_nodes(tree)
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and node.value in KINDS
        ):
            message = f"line {node.lineno}: function kind string {node.value!r}"
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "key"
        ):
            message = f"line {node.lineno}: authoring key element or prefix access"
        else:
            continue
        if EXEMPT not in lines[node.lineno - 1]:
            found.append(message)
    return sorted(found)


def test_no_stage_names_a_kind_or_reads_a_key_prefix() -> None:
    """The real `stages/*.py` and the conventions' code modules have no violation."""
    paths = [*STAGES.glob("*.py"), *(SRC / "conventions" / f"{n}.py" for n in CONVENTIONS_CODE)]
    problems = [
        f"{path.name}: {message}"
        for path in sorted(paths)
        for message in violations(path.read_text(encoding="utf-8"))
    ]
    assert problems == []


def test_checker_fails_on_a_kind_comparison() -> None:
    """`x.kind == "terminal"` is a violation, at its line."""
    source = "def f(x):\n    return x.kind == 'terminal'\n"
    assert violations(source) == ["line 2: function kind string 'terminal'"]


def test_checker_fails_on_a_key_prefix() -> None:
    """`spec.key[:2]` is a violation, at its line."""
    source = "def f(spec):\n    return spec.key[:2]\n"
    assert violations(source) == ["line 2: authoring key element or prefix access"]


def test_checker_ignores_a_docstring_and_honours_an_exemption() -> None:
    """A docstring may say `terminal`; a `vocab-ok` line is exempt."""
    source = (
        'def f():\n    """A terminal, "terminal"."""\n    return "coil"  # vocab-ok: a key part\n'
    )
    assert violations(source) == []
