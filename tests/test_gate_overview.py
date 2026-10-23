"""Overview and home gates E14 to E16 (spec SURFACE-COHERENCE R1): ids, page script, two homes.

E14: no rendered id in the overview page. E15: no random, clock or network in the page script.
E16: the wago signal table has one home (README-wago-2); the version string's home is HOMES.
"""

import ast
import sys
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys_overview import html
from gate_scan import PACKAGES_ROOT, src_modules

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.kernel import render_id

OVERVIEW_SRC = PACKAGES_ROOT / "fransys-overview" / "src" / "fransys_overview"
FORBIDDEN_JS = ("Math.random", "Date", "fetch(", "XMLHttpRequest", "innerHTML")
SIGNAL_HOME = "fransys_wago.signals"


def rendered_ids_in(page: str, ids: list[str]) -> list[str]:
    """E14: the rendered ids that appear in `page`."""
    return [text for text in ids if text in page]


def forbidden_in(source: str) -> list[str]:
    """E15: the forbidden substrings held by a string constant of `source`."""
    texts = [
        n.value
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    return sorted({word for word in FORBIDDEN_JS for text in texts if word in text})


def signal_format_sites(sources: dict[str, str]) -> list[str]:
    """E16 (ii): `module:line` of each `SignalFormat(` call outside the wago signal table."""
    return [
        f"{module}:{n.lineno}"
        for module, source in sources.items()
        if module != SIGNAL_HOME
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call)
        and (n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", ""))
        == "SignalFormat"
    ]


def _sources() -> dict[str, str]:
    return {m: p.read_text(encoding="utf-8") for m, p in src_modules()}


@pytest.fixture(scope="module")
def demo_overview():
    """The units worked example's overview: its model and page, built once."""
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), system_document()).model
    out = lay_out_overview(model)[0]
    return out, html(out)


def test_the_overview_page_prints_no_id(demo_overview):
    out, page = demo_overview
    ids = [render_id(i) for table in out.tables.values() for i in table]
    assert len(ids) > 50, "the model holds few ids"
    assert "C1" in page, "the page holds no designation"
    assert len(page) > 10_000, "the page is empty"
    assert rendered_ids_in(page, ids) == []


def test_the_id_gate_can_fail():
    assert rendered_ids_in("<b>function:abc</b>", ["function:abc", "port:x"]) == ["function:abc"]


def _js_files() -> list[Path]:
    files = [*sorted(OVERVIEW_SRC.glob("_js_*.py")), OVERVIEW_SRC / "_app.py"]
    return [f for f in files if f.name != "_vendor_cytoscape.py"]


def test_the_page_script_has_no_random_clock_or_network():
    files = _js_files()
    assert "_js_draw.py" in [f.name for f in files], "the script walk missed _js_draw.py"
    hits = {f.name: forbidden_in(f.read_text(encoding="utf-8")) for f in files}
    assert {name: words for name, words in hits.items() if words} == {}


def test_the_script_gate_can_fail():
    for word in FORBIDDEN_JS:
        assert forbidden_in(f'JS = r"""const x = {word} + 1;"""') == [word]
    assert forbidden_in('JS = "const x = 1;"') == []


def test_the_signal_table_has_one_home():
    sources = _sources()
    assert "SignalFormat(" in sources[SIGNAL_HOME], "the home lost the table"
    assert signal_format_sites(sources) == []


def test_the_home_gate_can_fail():
    assert signal_format_sites({"fransys_wago.x": "SignalFormat(abbr='DI')"}) == [
        "fransys_wago.x:1"
    ]
    assert signal_format_sites({"fransys_wago.x": "m.SignalFormat(1)"}) == ["fransys_wago.x:1"]
