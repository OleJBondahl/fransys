"""Field case: a unit whose only harness has no cable still gets its harness drawing.

The engineering shape: a unit with two relay modules and one harness W1. W1 has two female
plugs mated to the modules' headers, and two plain single wires between the plugs. There is
no cable, only wires.

The bug: a HARNESS_DRAWING document of that unit stopped with DOCUMENT_NO_DRAWINGS "the unit
has no cable", although the cable engine draws a wire-only harness (its end boxes, their pins
and one line per wire). Fixed by v0.13.1 item W: decisions model-0182 (the drawn blocks have one
home) and pdf-0024 (the PDF reads it).
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, RD

from fransys_layout import lay_out_cables
from fransys_model.derive.cable_drawing import block_wires, drawn_pins, end_rows
from fransys_model.kernel import Severity
from fransys_model.layout import CableBlock, layout_of


class _Open(NamedTuple):
    """The unit exposes nothing."""


@fr.unit("demo-looms", revision=1, interface_version=1, date="2026-10-08", text="First", by="XX")
def _looms(u: fr.Design) -> _Open:
    u.location("C1", "Cabinet")
    m1 = u.device("M1", "DEMO-RELAY-MOD-2", place="C1")
    m2 = u.device("M2", "DEMO-RELAY-MOD-2", place="C1")
    w1 = u.harness("W1", place="C1")
    p1 = u.device("P1", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    p2 = u.device("P2", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    u.mate(p1, m1.j1)
    u.mate(p2, m2.j1)
    u.wire(p1[1], p2[1], wire=(RD, 0.5))
    u.wire(p1[2], p2[2], wire=(BK, 0.5))
    return _Open()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Looms\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_looms, "U1", place=None)
    doc = fr.document(fr.DocumentPreset.HARNESS_DRAWING, "demo-looms", cover=cover)
    return fr.build(d, doc)


def test_the_harness_drawing_builds_without_an_error(built: fr.BuildResult) -> None:
    """No ERROR finding, in particular no DOCUMENT_NO_DRAWINGS."""
    errors = [f"{f.code}: {f.message}" for f in fr.check(built) if f.severity is Severity.ERROR]
    assert errors == []


def test_the_drawing_has_end_boxes_with_pins_and_one_line_per_wire(built: fr.BuildResult) -> None:
    """The engine already lays out the block: two end boxes of 4 pins (2 landed), 2 wires."""
    laid: Any = lay_out_cables(built.model)[0]
    (block,) = [b for b in layout_of(laid, CableBlock).values() if b.unit is not None]
    top, bottom = end_rows(laid, block.subject, block.unit)
    ends = (*top, *bottom)
    assert len(ends) == 2
    pins = [drawn_pins(laid, block.subject, end, block.unit) for end in ends]
    assert [(len(p), sum(x.landed for x in p)) for p in pins] == [(4, 2), (4, 2)]
    assert len(block_wires(laid, block.subject, block.unit)) == 2
