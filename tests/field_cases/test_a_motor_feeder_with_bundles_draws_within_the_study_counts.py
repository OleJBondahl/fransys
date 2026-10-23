"""Field case: three fan starters under one breaker, each a bundle of three poles, on the core path.

The engineering shape: breaker, contactor, overload and motor in series, three phases each, with
the contactor's coil and lamp on a 24 V supply.

The bug: a bundle's poles are drawn as three separate wires that cross each other, and a source
two pages from its loads costs references. P7.2 builds the family on the private core path
(SWITCHES SW4, decision el-0007); the counts are SW8 row P7.2: 13 references or fewer, crossings
under 9. The renderer draws a bundle trunk as its lanes (BUNDLE-DRAW, render-0023).
"""

import dataclasses

import fransys as fr
import fransys_el
from _motor_feeder_case import feeder_counts, motor_feeder_case_drafts
from _page_drawings import page_drawings
from fransys_render import svg

from electrical_symbols import LIBRARY

MAX_REFERENCES = 13
CROSSINGS_BELOW = 9


def test_a_motor_feeder_with_bundles_draws_within_the_study_counts() -> None:
    result = fr.build(*motor_feeder_case_drafts())
    refs, crossings = feeder_counts(result)
    assert refs <= MAX_REFERENCES, (refs, crossings)
    assert crossings < CROSSINGS_BELOW, (refs, crossings)
    style = fransys_el.style(LIBRARY)
    trunks = [
        (drawing, wire)
        for drawing in page_drawings(result).values()
        for wire in drawing.wires
        if wire.lanes > 1
    ]
    assert trunks, "the feeder has bundle trunks"
    for drawing, wire in trunks:
        one = dataclasses.replace(drawing, symbols=(), wires=(wire,))
        assert svg(one, LIBRARY, style).count("<polyline") == wire.lanes


def test_the_feeder_pages_render_whole() -> None:
    result = fr.build(*motor_feeder_case_drafts())
    style = fransys_el.style(LIBRARY)
    for drawing in page_drawings(result).values():
        assert svg(drawing, LIBRARY, style)
