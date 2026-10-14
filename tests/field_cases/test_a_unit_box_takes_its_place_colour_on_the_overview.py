"""Field case: a unit instance added at a place, seen on the overview under 'Colour by location'.

Engineering shape: two places, ER and FLD. A unit instance PC is added with `place="ER"`; one
lamp stands in FLD and hangs on a cable from the unit. The page colours every box by its class
in the chosen split, and the location split's class is the place's label.

The bug: the unit's own box (+ER-PC) had no location class, so it drew grey, while the items
inside it (-H1, -X1) drew in ER's colour.

Fix: overview-0006. The box takes the class of `derive.unit_location`, the one fact the unit
documents print their ends against.
"""

import json
import re
from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import BU

_LOCATION = 3  # the index of the location split in a box's `cls`; `_js_core.SPLIT_AT`


class _Io(NamedTuple):
    out: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cab(u: fr.Design) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        out = x1.run("L1", 1)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.wire(out[1], lamp["1"], wire=(BU, 0.5))
    return _Io(out)


@pytest.fixture(scope="module")
def boxes(tmp_path_factory) -> list[dict]:
    d = fr.design("demo_parts", place="ER")
    d.project(title="FC", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("ER", "Electrical room")
    d.location("FLD", "Field")
    unit = d.add(_cab, "PC", place="ER")
    with d.function("OUT", "Outside"):
        lamp = d.device("H8", "DEMO-LAMP-24", place="FLD")
        d.cable("W1", "DEMO-CBL-4G1.5", length_m=10).core(1, lamp["1"], unit.out[1])
    written = fr.write(fr.build(d, system_document()), tmp_path_factory.mktemp("out"))
    page = next(p for p in written if p.name.endswith("overview.html")).read_text()
    block = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert block is not None
    return [box for view in json.loads(block.group(1))["views"] for box in view["boxes"]]


def _location_class(boxes: list[dict], first_line: str) -> str | None:
    return next(b for b in boxes if b["lines"][0] == first_line)["cls"][_LOCATION]


def test_the_unit_box_takes_the_colour_of_its_place(boxes) -> None:
    assert _location_class(boxes, "+ER-PC") is not None
    assert _location_class(boxes, "+ER-PC") == _location_class(boxes, "-H1")


def test_the_lamp_in_the_other_place_has_another_class(boxes) -> None:
    assert _location_class(boxes, "+FLD-H8") != _location_class(boxes, "-H1")
