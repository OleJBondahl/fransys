"""A demo lamp stands in a `d.series`: its ports state their sides (DEMO-LAMP-SIDE, A1)."""

import fransys_parts
import pytest
from fransys_author.surface import design

from fransys_model.vocab import Conductor

WIRE = ("BK", 0.75)


@pytest.fixture(scope="module")
def demo():
    return fransys_parts.load("demo_parts")


def _series(demo):
    d = design(demo, place="C1")
    psu = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", psu.output)
    s1 = d.device("S1", "DEMO-SWITCH-2P")
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.series(dc.plus, s1.sw, h1.lamp, dc.minus, wire=WIRE)
    return d, psu, s1, h1


def test_a_demo_lamp_builds_in_a_series_and_is_wired_line_to_load(demo):
    d, psu, s1, h1 = _series(demo)
    ends = {frozenset((r.a, r.b)) for r in d.draft().records() if isinstance(r, Conductor)}
    want = {
        frozenset((psu.output["+"].id, s1.sw["A"].id)),
        frozenset((s1.sw["B"].id, h1.lamp["1"].id)),
        frozenset((h1.lamp["2"].id, psu.output["-"].id)),
    }
    assert ends == want
