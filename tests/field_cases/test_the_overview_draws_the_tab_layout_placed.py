"""Field case: a unit with a supply terminal strip and a lamp, and a cable to a second lamp in the field, on the overview page.
The bug: the page script drew each cable tab at its own size, while layout had placed the line to touch a tab of another size.
Fixed by overview-0012, `OverviewTab` records `width` and `height`, and the page data holds them so the script computes no tab size."""

import json
import re

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import BU
from test_a_unit_box_takes_its_place_colour_on_the_overview import _cab

from electrical_symbols import LIBRARY
from fransys_layout.engines.overview import lay_out_overview
from fransys_model.layout import OverviewBox, layout_of

_X, _Y, _WIDTH, _HEIGHT = 0, 1, 4, 5  # the page tab row: x, y, text_width, text, width, height


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = fr.design("demo_parts", place="ER")
    d.project(title="FC", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("ER", "Electrical room")
    d.location("FLD", "Field")
    unit = d.add(_cab, "PC", place="ER")
    with d.function("OUT", "Outside"):
        lamp = d.device("H8", "DEMO-LAMP-24", place="FLD")
        neutral = d.terminal_strip("X9", "DEMO-TB-2.5", place="FLD")
        d.series(neutral[1].inner, lamp["2"], wire=(BU, 0.5))
        d.cable("W1", "DEMO-CBL-4G1.5", length_m=10).core(1, lamp["1"], unit.out[1])
    built = fr.build(d, system_document())
    written = fr.write(built, tmp_path_factory.mktemp("out"))
    page = next(p for p in written if p.name.endswith("overview.html")).read_text()
    block = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert block is not None
    return built.model, json.loads(block.group(1))


def test_every_drawn_tab_has_the_size_layout_recorded(built) -> None:
    model, data = built
    recorded = sorted((t.x, t.y, t.width, t.height) for b in layout_of(lay_out_overview(model, LIBRARY)[0], OverviewBox).values() for t in b.tabs)
    drawn = sorted((t[_X], t[_Y], t[_WIDTH], t[_HEIGHT]) for view in data["views"] for box in view["boxes"] for t in box["tabs"])
    assert recorded
    assert drawn == recorded
