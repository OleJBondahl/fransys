"""Field case: three changeover contacts of one relay switch a motor between two supplies.
The bug: three one-pole contacts could not be one series element, so the throws could not face the line and drew as three poles.
Fixed by author-0046 (`d.poles`, API-CLARITY C6.4) and layout-0227, which draws the group."""

import re
from functools import cache
from typing import Any

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

_SEL = "-Q1's part already states a selector: pass q1.co"
_TOP = 4  # the three poles, as (pole, QA/QB load pin, motor pin)
_POLES = tuple(zip(range(1, _TOP), ("2", "4", "6"), ("U", "V", "W"), strict=True))


def selector_design():
    """Page g's relay as a selector, and the cabinet location its document draws."""
    d = fr.design("demo_parts", place="CAB")
    cabinet = d.location("CAB", "Cabinet")  # the document subject
    xa, xb = d.terminal_strip("XA", "DEMO-TB-2.5"), d.terminal_strip("XB", "DEMO-TB-2.5")
    a = d.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
    b = d.ac_supply("B", "230", xb[1], xb[2], xb[3], names=("B_L1", "B_L2", "B_L3"))
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    qa, qb = d.device("QA", "DEMO-MCB-3P"), d.device("QB", "DEMO-MCB-3P")
    k1, m1 = d.device("K1", "DEMO-RLY-4CO-24"), d.device("M1", "DEMO-MOTOR-4KW")
    d.series(dc.plus, k1.coil, dc.minus, wire=0.75)
    q = d.poles(k1.co_1, k1.co_2, k1.co_3, selector=True)
    d.series(a, qa.element, q.no, m1, wire=2.5)
    d.series(b, qb.element, q.nc, wire=2.5)
    return d, cabinet


@cache
def _built() -> fr.BuildResult:
    d, cabinet = selector_design()
    doc = unit_document(cabinet)
    return fr.build(d, doc)


def _model():
    return _built().model


def test_supply_a_reaches_the_make_throws_b_the_breaks_and_the_commons_feed_m1() -> None:
    rows = fr.derive.wire_rows(fr.build(selector_design()[0]).model)
    ends = {frozenset((r.from_, r.to)) for r in rows}
    for pole, line, motor in _POLES:
        assert frozenset((f"+CAB-QA:{line}", f"+CAB-K1:{pole}4")) in ends
        assert frozenset((f"+CAB-QB:{line}", f"+CAB-K1:{pole}2")) in ends
        assert frozenset((f"+CAB-K1:{pole}1", f"+CAB-M1:{motor}")) in ends
    assert sum(f"-K1:{_TOP}" in r.from_ + r.to for r in rows) == 0, "co_4 stays apart"


def _symbols(model) -> list[Any]:
    return [s for drawing in drawn_pages(model).values() for s in drawing.symbols]


def test_every_pin_of_the_group_prints_its_marking() -> None:
    model = _model()
    marked = {text for s in _symbols(model) for slot, text in s.slots if slot.startswith("marking.")}
    assert {f"{pole}{end}" for pole in range(1, _TOP) for end in "124"} <= marked


def test_the_three_pole_build_shows_no_wire_meets_net() -> None:
    assert "WIRE_MEETS_NET" not in {f.code for f in _built().findings}


def test_selector_on_a_part_that_states_its_sides_raises() -> None:
    d = fr.design("demo_parts")
    q1 = d.device("Q1", "DEMO-SEL-3P-24")
    with pytest.raises(fr.AuthorError, match=f"^{re.escape(_SEL)}$"):
        d.poles(q1.co, selector=True)
