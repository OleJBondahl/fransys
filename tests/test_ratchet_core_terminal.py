"""Ratchet E core_terminal_kind: terminal and strip special cases in the layout core.

A general technique takes its rules as options, so a core branch on the "terminal" or "strip" kind
is a convention to lower. Only code counts: docstrings and comments never do.
"""

import ast

import pytest
from gate_scan import ROOT, check_stock, stock

CORE = ROOT / "packages" / "fransys-layout" / "src" / "fransys_layout" / "core"
WORDS = {"terminal", "strip"}
NAMES = {"TERMINAL", "STRIP", "terminal", "strip"}
COMPARES = (ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.Is, ast.IsNot)


def _is_kind(node: ast.expr) -> bool:
    """True for a string equal to a kind word, or a name or attribute that names one."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and node.value.casefold() in WORDS
    if isinstance(node, ast.Name):
        return node.id in NAMES
    return isinstance(node, ast.Attribute) and node.attr in NAMES


def _tests(tree: ast.AST) -> list[ast.expr]:
    """The test expressions that branch: If, While, IfExp and comprehension ifs."""
    found: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            found.append(node.test)
        elif isinstance(node, ast.comprehension):
            found.extend(node.ifs)
    return found


def terminal_cases(source: str) -> list[int]:
    """The line of each kind comparison in a branch test, and each kind pattern in a match."""
    tree = ast.parse(source)
    sites: dict[ast.AST, int] = {}
    for test in _tests(tree):
        for node in ast.walk(test):
            if (
                isinstance(node, ast.Compare)
                and any(isinstance(op, COMPARES) for op in node.ops)
                and any(_is_kind(side) for side in (node.left, *node.comparators))
            ):
                sites[node] = node.lineno
    for case in ast.walk(tree):
        if isinstance(case, ast.match_case):
            for pat in ast.walk(case.pattern):
                if isinstance(pat, ast.MatchValue) and _is_kind(pat.value):
                    sites[pat] = pat.lineno
    return list(sites.values())


@pytest.mark.private_input  # a private-gate count (R462)
def test_core_terminal_kind_stock():
    found = sum(
        len(terminal_cases(path.read_text(encoding="utf-8"))) for path in CORE.rglob("*.py")
    )
    check_stock("core_terminal_kind", found, stock("core_terminal_kind"))


def test_synthetic_equality_on_terminal_string_counts_one():
    assert terminal_cases('def f(kind):\n    if kind == "terminal":\n        pass\n') == [2]


def test_synthetic_identity_with_terminal_attribute_counts_one():
    assert terminal_cases("if kind is ItemKind.TERMINAL:\n    pass\n") == [1]


def test_synthetic_docstring_mentioning_terminal_counts_zero():
    assert (
        terminal_cases('def f(kind):\n    """A terminal, or a strip."""\n    return kind\n') == []
    )


def test_synthetic_other_kind_string_counts_zero():
    assert terminal_cases('if kind == "box":\n    pass\n') == []


def test_synthetic_match_case_strip_counts_one():
    assert terminal_cases('match kind:\n    case "strip":\n        pass\n') == [2]


def test_synthetic_compare_inside_an_if_test_counts_one():
    assert terminal_cases("if any(c == STRIP for c in xs):\n    pass\n") == [1]
