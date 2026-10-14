"""The findings guide tables are generated from the codes registry (BUILD-MESSAGES M8, A2).

`scripts/findings_guide.py` is the one generator. Loaded by path, as `test_boundaries.py` loads
`lean_surface.py`, so the script is not a package module.
"""

import dataclasses
import importlib.util
import sys
from importlib.resources import files
from pathlib import Path

from fransys import _codes

ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIR = Path(str(files("fransys").joinpath("guide")))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"could not load {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


findings_guide = _load("fransys_findings_guide", ROOT / "scripts" / "findings_guide.py")
guide_examples = _load("fransys_guide_examples_list", ROOT / "tests" / "test_guide_examples.py")


def test_every_findings_page_is_the_generated_table() -> None:
    """Every findings page equals its generated text; a failure names the stale pages."""
    stale = [
        path.name
        for path, text in findings_guide.expected_pages(GUIDE_DIR).items()
        if path.read_text(encoding="utf-8") != text
    ]
    assert stale == []


def test_a_changed_fix_makes_the_page_stale() -> None:
    """Can-fail: one changed `fix` renders a table that differs from the page on disk."""
    path = GUIDE_DIR / "findings-validators.md"
    text = path.read_text(encoding="utf-8")
    infos = [info for info in _codes.BY_CODE.values() if info.page == "findings-validators"]
    changed = [dataclasses.replace(infos[0], fix=infos[0].fix + " x"), *infos[1:]]
    assert findings_guide.render_page(text, changed) != text


def test_generated_pages_are_the_listed_findings_pages() -> None:
    """The generator's pages are the findings pages `test_guide_examples.py` lists."""
    listed = sorted(page for page in guide_examples.GUIDE_PAGES if page.startswith("findings-"))
    assert list(findings_guide.page_names()) == listed
