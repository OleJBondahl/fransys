"""The facade lays out and draws every schematic on the core alone (FLIP-NOW F2, Acceptance)."""

from pathlib import Path

import fransys as fr

SRC = Path(fr.__file__).parent


def test_no_facade_module_names_the_old_schematic_layout() -> None:
    named = [p.name for p in SRC.glob("*.py") if "lay_out_schematic" in p.read_text("utf-8")]
    assert named == []


def test_no_facade_module_names_the_old_page_drawer() -> None:
    named = [p.name for p in SRC.glob("*.py") if "fransys_render.pages" in p.read_text("utf-8")]
    assert named == []
