"""Field case: two supplies over a narrow redundancy module stand apart, each over its own group.

The engineering shape: two 24 V supplies feed one redundancy module with an input group per
supply (1+ 1- and 2+ 2-, about 22 px apart); its output is wired to strip terminals.

The bug: the box widened its pin pitch for the contacts under its pins but never for its feeders,
so the two supplies stood on top of each other (SYMBOL_OVERLAP), 32 units apart at 48 wide.
Long supply tags widen a feeder past its slot; the long-tags case holds that.
The rule (decision layout-0124, amending layout-0107): a feeder's keep-out under its attach pin
counts in the box's pin pitch, so the box is as long as its pins and feeders need.
"""

import itertools
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import item_box
from _drawn_pages import drawn_pages
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
        d.detail.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.detail.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.detail.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.detail.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _pin_x(box, name: str) -> int:
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
