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
from fransys.colours import BN, BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import overlaps
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.vocab.tables import items

_LONG = "SUPPLY-PUMP-STATION-NUMBER-ONE-FEEDER-"
_TAGS = pytest.mark.parametrize("name", ["T", _LONG], ids=["short", "long-tags"])


def _built(name: str = "T") -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 1).run("L", 1)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 1).run("L", 1)
    with d.function("G", "Group"):
        psus = [d.device(f"{name}{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    result = fr.build(d, doc)
    return result, stage_results(result.model, read_inputs(result.model))[0].layout


def _box(model, layout, tag: str):
    (item,) = (one.id for one in items(model).values() if one.key[-1] in (f"G/{tag}", tag))
    return next(one for one in layout.placed if one.function == item)


def _pin_x(box, name: str) -> int:
    (pin,) = (g for g in box.geometry.ports if g.name == name)
    return box.at.x + pin.at.x


@_TAGS
def test_the_build_reports_no_symbol_overlap(name: str) -> None:
    """The lint finds no two keep-outs sharing interior."""
    result, _ = _built(name)
    assert "SYMBOL_OVERLAP" not in {f.code for f in result.findings}


@_TAGS
def test_no_two_symbols_of_a_page_overlap(name: str) -> None:
    """No two placed keep-out rectangles of one page intersect."""
    _, layout = _built(name)
    for one, other in itertools.combinations(layout.placed, 2):
        if (one.drawing_set, one.page) == (other.drawing_set, other.page):
            assert not overlaps(placed_keepout(one), placed_keepout(other))


@_TAGS
def test_each_feeder_stands_over_its_own_group(name: str) -> None:
    """Each supply's output pins stand over its group's pins, the supplies apart."""
    result, layout = _built(name)
    module = _box(result.model, layout, "M1")
    for n in (1, 2):
        psu = _box(result.model, layout, f"{name}{n}")
        for out in ("+", "-"):
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"in_{n}.{n}{out}")
