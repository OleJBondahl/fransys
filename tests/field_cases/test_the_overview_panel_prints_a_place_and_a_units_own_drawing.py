"""Field case: two places, ER and FLD, each holding a lamp, and two rack units each holding a board unit, with a cable to a lamp.
The bugs (legacy findings D1, D2): the place box's panel read +ER alone, and a unit's panel named no drawing set, so search found no -A2.
Fixed by overview-0007, a place box holds its title and page data holds own_drawings, one line per unit, with the place's label."""

import json
import re
from typing import Any

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import BU
from fransys_overview._js_panels import JS_PANELS
from test_a_unit_box_takes_its_place_colour_on_the_overview import _cab, _Io

_LOCATION = 3  # the index of the location split in a box's `cls`; `_js_core.SPLIT_AT`


@fr.unit("demo-rack", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _rack(u: fr.Design) -> _Io:
    return _Io(u.add(_cab, "A2").out)


@pytest.fixture(scope="module")
def data(tmp_path_factory) -> dict[str, Any]:
    d = fr.design("demo_parts")
    d.project(title="FC", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("ER", "Engine room")
    d.location("FLD", "Field")
    first, second = d.add(_rack, "R1"), d.add(_rack, "R2")
    with d.function("OUT", "Outside"):
        near = d.device("H7", "DEMO-LAMP-24", place="ER")
        far = d.device("H8", "DEMO-LAMP-24", place="FLD")
        for lamp, place in ((far, "FLD"), (near, "ER")):
            neutral = d.terminal_strip(f"X{place}", "DEMO-TB-2.5", place=place)
            d.series(neutral[1].inner, lamp["2"], wire=(BU, 0.5))
        d.cable("W1", "DEMO-CBL-4G1.5", length_m=10).core(1, far["1"], first.out[1])
        d.cable("W2", "DEMO-CBL-4G1.5", length_m=10).core(1, near["1"], second.out[1])
    written = fr.write(fr.build(d, system_document()), tmp_path_factory.mktemp("out"))
    page = next(p for p in written if p.name.endswith("overview.html")).read_text()
    block = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert block is not None
    return json.loads(block.group(1))


def _boxes(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [box for view in data["views"] for box in view["boxes"]]


def _place(data: dict[str, Any], first_line: str) -> dict[str, Any]:
    return next(b for b in _boxes(data) if b["ref"][0] == "place" and b["lines"][0] == first_line)


def test_the_place_box_keeps_its_designation_with_the_text_under_it(data) -> None:
    assert _place(data, "+ER")["lines"] == ["+ER", "Engine room"]


def test_the_panel_title_of_a_place_is_its_designation_and_text(data) -> None:
    assert _place(data, "+ER")["title"] == "+ER Engine room"


def test_the_place_box_takes_the_class_its_items_have(data) -> None:
    lamp = next(b for b in _boxes(data) if b["lines"][0].endswith("-H7"))
    assert _place(data, "+ER")["cls"][_LOCATION] == lamp["cls"][_LOCATION]


def test_the_nested_units_panel_names_its_own_drawing(data) -> None:
    assert "Own drawing: -A2 in demo-cab rev 1.1" in data["own_drawings"]
    assert data["own_drawings"][data["units"].index("-A2")] == "Own drawing: -A2 in demo-cab rev 1.1"


def test_the_legend_prints_a_place_as_the_boxes_do(data) -> None:
    assert data["location_texts"]["ER"] == "+ER"
    assert _place(data, "+ER")["lines"][0] == data["location_texts"]["ER"]


def test_the_legend_reads_the_location_texts() -> None:
    assert "data.location_texts[cls]" in JS_PANELS


def test_the_find_box_shows_a_nested_units_system_designation(data) -> None:
    nested = [i for i, label in enumerate(data["units"]) if label == "-A2"]
    assert [data["unit_systems"][i] for i in nested] == ["-R1-A2", "-R2-A2"]
    assert data["unit_systems"][data["units"].index("-R1")] is None


def test_the_find_box_prints_the_system_designation_beside_the_label() -> None:
    assert "' (' + data.unit_systems[i] + ')'" in JS_PANELS
