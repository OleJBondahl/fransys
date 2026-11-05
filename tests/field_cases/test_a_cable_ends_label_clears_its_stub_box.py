"""Field case: a multi-core cable leaves a row of relays for one arrow box, with a label per branch.
The bug: a branch label could stand under the arrow box's text (seen at a 2.6 mm smallest text height, no longer a setting).
Fixed by layout-0206, a line label keeps clear of the boxes of the stubs its own line ends in, as of every other box."""

from functools import cache

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    fld = d.location("FLD", "Field")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    for n in range(1, 5):
        relay = d.device(f"K{n}", "DEMO-RLY-2CO-24")
        lamp = d.device(f"M{n}", "DEMO-LAMP-24", place="FLD")
        cable.core(n, relay.coil["A1"], lamp["1"])
        d.series(relay.coil["A2"], lamp["2"], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab), unit_document(fld))


def test_no_text_overlaps_the_cables_label_or_its_arrow_box() -> None:
    bad = [(f.code, f.message) for f in _built().findings if f.code == "WIRE_OVER_LABEL" and "-W1" in f.message]
    assert bad == []
