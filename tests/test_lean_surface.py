"""`scripts/lean_surface.py`: `surface_modules`, `surface_names`, `resolve_surface_names`.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. The module-list and `__all__` tests read
the real workspace (this module's whole point is to be the one home other checks trust), so a
change here is a real change in review; the AST-vs-`__doc__` trap test needs no real file at
all, since `literal_docstring` only ever looks at an in-memory `ast` tree.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_surface", ROOT / "scripts" / "lean_surface.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_surface.py"
    raise ImportError(msg)
lean_surface = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_surface
_spec.loader.exec_module(lean_surface)

#: The workspace's own ~21-entry surface (MS1, MS2, MS6, MS8; MS1 amended 2026-09-27 to seven
#: model modules; CT1 dropped `fransys_wireviz`), spelled out so a change to it is visible
#: in review rather than hidden behind a recomputed assertion.
_EXPECTED_SURFACE_MODULES = (
    "electrical_symbols",
    "fransys",
    "fransys.colours",
    "fransys_author",
    "fransys_author.surface",
    "fransys_author.surface.colours",
    "fransys_kicad",
    "fransys_layout",
    "fransys_model.derive",
    "fransys_model.derive.baseline",
    "fransys_model.derive.drawing_text",
    "fransys_model.derive.numbering_pins",
    "fransys_model.kernel",
    "fransys_model.layout",
    "fransys_model.vocab",
    "fransys_overview",
    "fransys_parts",
    "fransys_pdf",
    "fransys_render",
    "fransys_reports",
    "fransys_wago",
)


def test_surface_modules_is_the_expected_21_entries():
    """Every `packages/*` top-level module (`fransys_model` excepted), its seven named
    modules (MS1), `fransys.colours` and the author package's two surface modules (MS8):
    no more, no fewer.
    """
    assert lean_surface.surface_modules() == _EXPECTED_SURFACE_MODULES


def test_surface_names_matches___all___for_drawing_text_baseline_and_numbering_pins():
    """`derive.drawing_text`/`.baseline`/`.numbering_pins` each carry a real `__all__` now
    (main's SURFACE Part 1) -- `surface_names` reports exactly that tuple, non-empty, for each.
    """
    from fransys_model.derive import baseline, drawing_text, numbering_pins

    names = lean_surface.surface_names()
    for dotted, module in (
        ("fransys_model.derive.drawing_text", drawing_text),
        ("fransys_model.derive.baseline", baseline),
        ("fransys_model.derive.numbering_pins", numbering_pins),
    ):
        assert names[dotted] == tuple(module.__all__)
        assert names[dotted] != ()


def test_surface_names_empty_when_a_real_module_has_no___all__():
    """`fransys_model` itself has no `__all__` (excluded from the surface entirely, MS1) --
    `surface_names` reports `()` for it when asked, never raises.
    """
    import fransys_model

    assert not hasattr(fransys_model, "__all__")
    names = lean_surface.surface_names(modules=["fransys_model"])
    assert names["fransys_model"] == ()


def test_surface_names_real_for_fransys():
    """`fransys.__all__`'s real names come through unchanged."""
    names = lean_surface.surface_names()
    assert "Design" in names["fransys"]
    assert "author" not in names["fransys"]
    assert "build" in names["fransys"]
    assert "derive" in names["fransys"]


def test_resolve_surface_names_skips_module_references_without_erroring():
    """`fransys.__all__` lists `"derive"`, a submodule -- `resolve_
    surface_names` never raises on it and never returns an entry for it.
    """
    resolved = lean_surface.resolve_surface_names(("fransys",))
    names = {entry.name for entry in resolved}
    assert "derive" not in names
    assert "build" in names


def test_resolve_surface_names_skips_plain_data_without_erroring():
    """`fransys_model.derive.__all__` lists plain constants (`TOP_LEVEL`, `BOM_COLUMNS`,
    ...) alongside real defs -- `resolve_surface_names` skips the constants, never raises, and
    still resolves the real defs.
    """
    resolved = lean_surface.resolve_surface_names(("fransys_model.derive",))
    names = {entry.name for entry in resolved}
    assert "TOP_LEVEL" not in names
    assert "BOM_COLUMNS" not in names
    assert "bom_lines" in names


def test_dataclass_auto_doc_is_not_a_literal_docstring():
    """The trap: a plain `dataclasses.dataclass` with no written docstring still gets a
    runtime `__doc__` (`"Foo(x: int)"`, auto-generated) -- but `literal_docstring` looks at the
    source `ast`, not the runtime object, and correctly reports it has none.
    """

    @dataclasses.dataclass(frozen=True)
    class Foo:
        x: int

    assert Foo.__doc__ is not None
    assert Foo.__doc__.startswith("Foo(x:")

    tree = ast.parse(
        "import dataclasses\n\n\n@dataclasses.dataclass(frozen=True)\nclass Foo:\n    x: int\n"
    )
    node = lean_surface.find_def(tree, "Foo")
    assert node is not None
    assert lean_surface.literal_docstring(node) is None


def test_literal_docstring_finds_a_real_one():
    """A written docstring is a real `ast.Constant`, not skipped."""
    tree = ast.parse('def f():\n    """A real docstring."""\n    return 1\n')
    node = lean_surface.find_def(tree, "f")
    assert node is not None
    docstring = lean_surface.literal_docstring(node)
    assert docstring is not None
    assert docstring.value == "A real docstring."


def test_docstring_line_count_counts_source_lines_inclusive():
    """Lines from the opening triple-quote line to the closing one, inclusive (LC3's own rule)."""
    tree = ast.parse('def f():\n    """One.\n\n    Two.\n    """\n')
    node = lean_surface.find_def(tree, "f")
    docstring = lean_surface.literal_docstring(node)
    assert lean_surface.docstring_line_count(docstring) == 4
