"""Field case: two 24 V supplies feed one redundancy module with an input group per supply, about 22 px apart.
The bug: the box widened its pitch for contacts under its pins but not its feeders, so the two supplies overlapped (SYMBOL_OVERLAP).
Fixed by layout-0124 (amending layout-0107), a feeder's keep-out under its attach pin counts in the box's pin pitch."""

import itertools
from typing import Any

import fransys as fr
import pytest
from _drawn_facts import item_box
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BN, BU

from fransys_layout.geometry import GENERIC_BOX_KEY, generic_box_geometry, overlaps, translate
from fransys_layout.geometry.symbols import symbol_geometry
from fransys_model.layout import Orientation

_LONG = "SUPPLY-PUMP-STATION-NUMBER-ONE-FEEDER-"
_TAGS = pytest.mark.parametrize("name", ["T", _LONG], ids=["short", "long-tags"])


def _built(name: str = "T") -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 1).run("L", 1)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 1).run("L", 1)
    with d.function("G", "Group"):
        psus = [d.device(f"{name}{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.series(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.series(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.series(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.series(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _pin_x(box, name: str) -> Any:
    return box.x + dict(box.offsets)[name]


def _keepout(one):
    """The keep-out of a drawn symbol on its page."""
    if one.key == GENERIC_BOX_KEY:
        offsets, sides = dict(one.offsets), dict(one.sides)
        names = tuple(offsets)
        sides = tuple(sides.get(n, "s") for n in names)
        offsets = tuple(v / 8 for v in offsets.values())
        geometry = generic_box_geometry(names, sides, offsets=offsets)
    else:
        geometry = symbol_geometry(one.key, poles=one.poles, orientation=Orientation[one.orient])
    return translate(geometry.keepout, dx=one.x, dy=one.y)


@_TAGS
def test_the_build_reports_no_symbol_overlap(name: str) -> None:
    """The lint finds no two keep-outs sharing interior."""
    result = _built(name)
    assert "SYMBOL_OVERLAP" not in {f.code for f in result.findings}


@_TAGS
def test_no_two_symbols_of_a_page_overlap(name: str) -> None:
    """No two placed keep-out rectangles of one page intersect."""
    for drawing in drawn_pages(_built(name).model).values():
        for one, other in itertools.combinations(drawing.symbols, 2):
            if "junction-dot" not in (one.key, other.key):
                assert not overlaps(_keepout(one), _keepout(other))


@_TAGS
def test_each_feeder_stands_over_its_own_group(name: str) -> None:
    """Each supply's output pins stand over its group's pins, the supplies apart."""
    model = _built(name).model
    module = item_box(model, "M1")
    for n in (1, 2):
        psu = item_box(model, f"{name}{n}")
        for out in ("+", "-"):
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"in_{n}.{n}{out}")
