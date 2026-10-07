"""`diagram_sheets` on the block-diagram worked examples and a cut chain (BD-3 R1, render-0009)."""

import sys
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

_ROOT = Path(__file__).resolve().parent.parent
for _dir in (_ROOT / "tests", _ROOT / "packages" / "fransys-layout" / "tests"):
    if str(_dir) not in sys.path:
        sys.path.append(str(_dir))

import fransys_render  # noqa: E402 -- ditto
from diagram_models import chain  # noqa: E402 -- after the sys.path setup
from fransys_render import _constants  # noqa: E402 -- ditto
from test_block_diagram_worked_examples import _station  # noqa: E402 -- ditto
from test_units_worked_example import _build_cabinet_own  # noqa: E402 -- ditto

from fransys_layout import lay_out_diagrams  # noqa: E402 -- ditto
from fransys_layout.engines.diagram import sizes  # noqa: E402 -- pins render's own constants
from fransys_model.kernel import Origin, evolve  # noqa: E402 -- ditto
from fransys_model.layout import DiagramBox, layout_of  # noqa: E402 -- ditto

_ORIGIN = Origin(file="test_block_diagram_render.py", line=1, note="fixture")
SVG = "{http://www.w3.org/2000/svg}"


def _laid(model):
    return lay_out_diagrams(model)[0]


def _station_model():
    return _laid(_station())


def _cabinet_model():
    return _laid(_build_cabinet_own(prefix="p", name="C1")[0].model)


def _texts(svg: str) -> list[str]:
    return [t.text or "" for t in ET.fromstring(svg).iter(SVG + "text")]  # noqa: S314 -- own output


def _dashed(svg: str) -> int:
    return sum(1 for e in ET.fromstring(svg).iter(SVG + "line") if e.get("stroke-dasharray"))  # noqa: S314 -- own output


def _only(model) -> str:
    (svg,) = fransys_render.diagram_sheets(model).values()
    return svg


def test_the_station_sheet_is_a2_with_its_box_line_and_tab_texts():
    svg = _only(_station_model())
    root = ET.fromstring(svg)  # noqa: S314 -- own output
    assert (root.get("width"), root.get("height")) == ("594mm", "420mm")
    assert root.get("viewBox") == "0 0 594 420"
    texts = _texts(svg)
    for want in ("-U1", "-M1", "-W1", "-W3", "-W11", "-W21", "-X1", "-X3", "-C1"):
        assert want in texts
    assert texts.count("-X3") == 2


def test_by_others_boxes_are_dashed_and_the_others_are_not():
    assert _dashed(_only(_station_model())) == 8  # -K1 and -X0, four edges each
    assert _dashed(_only(_cabinet_model())) == 0


def test_the_cabinet_sheet_prints_its_boxes_and_tab():
    texts = _texts(_only(_cabinet_model()))
    for want in ("-X2", "demo-io-board rev 1.3", "-WH1", "-U1-X1"):
        assert want in texts


def test_the_diagram_sits_at_the_content_box_offset():
    assert 'transform="translate(5 5)"' in _only(_station_model())


def test_the_output_is_deterministic():
    model = _station_model()
    assert fransys_render.diagram_sheets(model) == fransys_render.diagram_sheets(model)


def test_a_box_is_drawn_from_its_record():
    model = _station_model()
    box = next(b for b in layout_of(model, DiagramBox).values() if not b.dashed)
    edited = evolve(model, remove=[box.id], put=[replace(box, dashed=True)], origin=_ORIGIN)
    assert _dashed(_only(edited)) == _dashed(_only(model)) + 4


def test_a_cut_chain_marks_both_sheets_naming_the_other():
    sheets = list(fransys_render.diagram_sheets(_laid(chain(20))).values())
    assert len(sheets) == 2
    first = [t for t in _texts(sheets[0]) if t.startswith("p")]
    second = [t for t in _texts(sheets[1]) if t.startswith("p")]
    assert first
    assert second
    assert all(t.startswith("p2:") for t in first)
    assert all(t.startswith("p1:") for t in second)


@pytest.mark.parametrize(
    ("ours", "theirs"),
    [
        (_constants.DIAGRAM_TEXT_PAD_G, sizes.TEXT_PAD),
        (_constants.DIAGRAM_TEXT_LEAD_G, sizes.TEXT_LEAD),
        (_constants.DIAGRAM_TAB_PAD_G, sizes.TAB_PAD),
    ],
)
def test_render_pads_equal_the_layout_engines(ours, theirs):
    assert ours == theirs
