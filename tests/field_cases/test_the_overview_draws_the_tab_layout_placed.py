"""Field case: the overview page draws each cable tab at the size layout placed it.

Engineering shape: a unit with a supply terminal strip and a lamp, and a cable from the unit to a
second lamp in the field. The overview draws a box for each, and a tab outside a box edge where
the cable's line ends.

The bug: the page script drew every tab `text_width + text_height` wide and twice the text height
high, while layout had placed the line to touch a tab of `text_width` plus its own padding twice,
and the text height plus the padding twice high. The drawn tab and the laid-out tab disagreed.

Fix: overview-0012. `OverviewTab` records `width` and `height`; the page data holds them and the
script computes no tab size.
"""

import json
import re
from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.layout import OverviewBox, layout_of

_X, _Y, _WIDTH, _HEIGHT = 0, 1, 4, 5  # the page tab row: x, y, text_width, text, width, height


class _Io(NamedTuple):
    out: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cab(u: fr.Design) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        out = x1.run("L1", 1)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.detail.wire(out[1], lamp["1"], wire=(BU, 0.5))
    return _Io(out)


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
        d.cable("W1", "DEMO-CBL-4G1.5", length_m=10).core(1, lamp["1"], unit.out[1])
    built = fr.build(d, system_document())
    written = fr.write(built, tmp_path_factory.mktemp("out"))
    page = next(p for p in written if p.name.endswith("overview.html")).read_text()
    block = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert block is not None
    return built.model, json.loads(block.group(1))


def test_every_drawn_tab_has_the_size_layout_recorded(built) -> None:
    model, data = built
    recorded = sorted(
        (t.x, t.y, t.width, t.height)
        for b in layout_of(lay_out_overview(model)[0], OverviewBox).values()
        for t in b.tabs
    )
    drawn = sorted(
        (t[_X], t[_Y], t[_WIDTH], t[_HEIGHT])
        for view in data["views"]
        for box in view["boxes"]
        for t in box["tabs"]
    )
    assert recorded
    assert drawn == recorded
