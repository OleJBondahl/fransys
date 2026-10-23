"""Signature gate over `derive/texts` (EL-8, design 7.7): a text function takes a `PrintContext`.

Every public function defined in a `derive/texts` module has a parameter annotated
`PrintContext`, except the value formatters named below. The flat text modules that still live in
`derive/` are listed so the list can only shrink: EL-9 and later orders empty it.
"""

import ast
from pathlib import Path

DERIVE = Path(__file__).resolve().parent.parent / "src" / "fransys_model" / "derive"
TEXTS = DERIVE / "texts"

# Flat legacy text modules (EL-8 Q2): a rewrite moves one into `texts/` and deletes its entry.
LEGACY_FLAT = (
    "frame_position",
    "line_text",
    "marker_text",
    "overview_text",
    "page_destination",
    "plc_channel_text",
    "port_marking",
    "sheet_forms",
    "stub_text",
)
LEGACY_FLAT_CEILING = 9

# Value formatters and slot-table helpers that read no print context (the table builds the context).
VALUE_FORMATTERS = frozenset(
    {
        "core_text.core_text",
        "core_text.cross_section_text",
        "core_text.join_words",
    }
)
VALUE_FORMATTERS_CEILING = 3


def _annotation_names(function: ast.FunctionDef) -> set[str]:
    """The names of the parameters' annotations, `PrintContext` or a string of it."""
    args = function.args
    found: set[str] = set()
    for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
        note = arg.annotation
        if isinstance(note, ast.Name):
            found.add(note.id)
        elif isinstance(note, ast.Constant) and isinstance(note.value, str):
            found.add(note.value)
    return found


def _missing_context(module: str, source: str) -> list[str]:
    """`"<module>.<function>"` for each public function of `source` with no `PrintContext`."""
    tree = ast.parse(source)
    return [
        f"{module}.{node.name}"
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and "PrintContext" not in _annotation_names(node)
        and f"{module}.{node.name}" not in VALUE_FORMATTERS
    ]


def test_every_public_text_function_takes_a_print_context() -> None:
    """No public function of a `derive/texts` module lacks a `PrintContext` parameter."""
    missing: list[str] = []
    for path in sorted(TEXTS.glob("*.py")):
        if path.stem not in {"__init__", "context"}:
            missing += _missing_context(path.stem, path.read_text(encoding="utf-8"))
    assert missing == []


def test_the_gate_fails_on_a_text_without_a_context() -> None:
    """A synthetic module whose public function drops the parameter is reported."""
    bad = "def end_text(model, end):\n    return ''\n"
    good = "def end_text(model, end, ctx: PrintContext):\n    return ''\n"
    assert _missing_context("synthetic", bad) == ["synthetic.end_text"]
    assert _missing_context("synthetic", good) == []


def test_the_allowlists_name_real_modules_and_only_shrink() -> None:
    """Each flat legacy module is still a flat file; each formatter is still defined."""
    assert len(LEGACY_FLAT) <= LEGACY_FLAT_CEILING
    assert len(VALUE_FORMATTERS) <= VALUE_FORMATTERS_CEILING
    stale = [name for name in LEGACY_FLAT if not (DERIVE / f"{name}.py").is_file()]
    assert stale == [], f"a rewrite moved these into texts/: delete the entries {stale}"
    for qualified in VALUE_FORMATTERS:
        module, function = qualified.split(".")
        source = (TEXTS / f"{module}.py").read_text(encoding="utf-8")
        defined = {n.name for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        assert function in defined, qualified
