"""No core sort on raw id text (layout-0336, Ruling 70): a tie among ids falls to natural_key."""

import ast
from pathlib import Path

import pytest

CORE = Path(__file__).parent.parent / "packages/fransys-layout/src/fransys_layout/core"
# (module, function, the sorted() call's first argument as written): sorts of id text
SITES = [
    ("blocks", "assign_blocks", "by_box.items()"),
    ("blocks_hints", "keep_together", "members"),
    ("place_levels", "_groups", "spans"),
]


def unkeyed(source: str, function: str, subject: str) -> list[int]:
    """Lines of `sorted(<subject>, ...)` in `function` whose key does not name natural_key."""
    tree = ast.parse(source)
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function]
    assert fns, f"{function} not found: the site moved, update SITES"
    found = []
    for call in (c for fn in fns for c in ast.walk(fn) if isinstance(c, ast.Call)):
        named = isinstance(call.func, ast.Name) and call.func.id == "sorted"
        if named and call.args and ast.unparse(call.args[0]) == subject:
            key = next((k.value for k in call.keywords if k.arg == "key"), None)
            if key is None or "natural_key" not in ast.unparse(key):
                found.append(call.lineno)
    return found


@pytest.mark.parametrize(("module", "function", "subject"), SITES)
def test_the_id_sort_keys_by_natural_key(module, function, subject):
    source = (CORE / f"{module}.py").read_text(encoding="utf-8")
    assert f"sorted({subject}" in source, f"no sorted({subject}) in {module}: update SITES"
    assert unkeyed(source, function, subject) == []


def test_the_scan_can_fail():
    plain = "def f(members):\n    return sorted(members)\n"
    assert unkeyed(plain, "f", "members") == [2]
    keyed = "def f(members):\n    return sorted(members, key=natural_key)\n"
    assert unkeyed(keyed, "f", "members") == []
    wrong = "def f(members):\n    return sorted(members, key=len)\n"
    assert unkeyed(wrong, "f", "members") == [2]
