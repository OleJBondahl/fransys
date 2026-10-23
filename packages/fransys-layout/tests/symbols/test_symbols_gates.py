"""The three gates of the symdef layer (SB11, layout-0316): imports, words, arithmetic.

Each gate has a real-tree test and a synthetic one that proves the gate can fail.
"""

import ast
import re
from pathlib import Path

import pytest

import fransys_layout

SRC = Path(fransys_layout.__file__).parent
LAYER = SRC / "symbols"
#: The old engine's adapter, the one other importer; it dies at SCHEMATIC-FLIP (SB9). Shrink-only.
LEGACY = {"geometry/symbols.py"}

WORDS = (
    "coil",
    "contact",
    "relay",
    "terminal",
    "breaker",
    "motor",
    "plc",
    "fuse",
    "lamp",
    "diode",
    "transformer",
    "designation",
    "electrical",
)
BANNED_CALLS = {"min", "max", "sum", "round", "abs", "divmod", "pow"}


def imports_symdef(source: str) -> bool:
    """Whether the source imports symdef or one of its submodules."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import) and any(
            a.name.split(".")[0] == "symdef" for a in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "symdef":
            return True
    return False


def electrical_words(source: str) -> list[str]:
    """The banned words in the source, comments and strings included."""
    text = source.lower()
    return [w for w in WORDS if re.search(rf"\b{w}", text)]


def arithmetic(source: str) -> list[int]:
    """Lines with an operator, a unary minus or a rounding call: arithmetic on a value."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if (isinstance(node, ast.BinOp) and not isinstance(node.op, ast.BitOr))  # `A | B` is a type
        or isinstance(node, ast.AugAssign)
        or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd))
        or (isinstance(node, ast.Call) and getattr(node.func, "id", "") in BANNED_CALLS)
    ]


def layer_files() -> list[Path]:
    return sorted(LAYER.glob("*.py"))


def test_only_the_layer_and_the_legacy_adapter_import_symdef() -> None:
    found = {
        p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py") if imports_symdef(p.read_text())
    }
    outside = {f for f in found if not f.startswith("symbols/")}
    assert outside == LEGACY, (
        "a module other than the layer imports symdef; the legacy set only falls"
    )
    assert any(f.startswith("symbols/") for f in found)


def test_the_import_gate_can_fail() -> None:
    assert imports_symdef("import symdef\n")
    assert imports_symdef("from symdef import measure\n")
    assert imports_symdef("import symdef.authoring\n")
    assert not imports_symdef("import electrical_symbols\n")


def test_the_layer_holds_no_electrical_word() -> None:
    assert layer_files()
    assert {p.name: electrical_words(p.read_text()) for p in layer_files()} == {
        p.name: [] for p in layer_files()
    }


@pytest.mark.parametrize("word", WORDS)
def test_the_word_gate_can_fail(word: str) -> None:
    assert electrical_words(f"def f():\n    return '{word}s'\n") == [word]


def test_the_layer_does_no_arithmetic() -> None:
    assert {p.name: arithmetic(p.read_text()) for p in layer_files()} == {
        p.name: [] for p in layer_files()
    }


@pytest.mark.parametrize(
    "stmt",
    [
        "return box.w + 1",
        "x += 1",
        "return -x",
        "return max(a, b)",
        "return round(x)",
        "return a // 2",
    ],
)
def test_the_arithmetic_gate_can_fail(stmt: str) -> None:
    assert arithmetic(f"def f(box, x, a, b):\n    {stmt}\n") == [2]


def test_a_type_union_is_not_arithmetic() -> None:
    assert arithmetic("def f(x: int | None) -> int | None:\n    return x\n") == []


def test_copies_and_the_union_call_are_not_arithmetic() -> None:
    assert (
        arithmetic("def f(g):\n    return Box(g.min.x, g.min.y, g.width, GridBox.union(g, g))\n")
        == []
    )
