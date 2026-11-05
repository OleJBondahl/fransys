"""Field case: a contactor whose NC contact 21 has no conductor reaching it on the page (the declared-net case left with d.detail.net, RETURN-NET).
The bug: layout kept the contact, but the coil's contact table listed it as a spare, asking a second, conductor-only question.
Fixed by model-0120, `derive.function_is_unused` is the one answer that layout and the table both read."""

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU


def _built(*, wired: bool = False, hide: bool = True):
    """The contactor Q1 with its NC contact 21 unwired; `wired` runs a wire to it."""
    d = fr.design("demo_parts", place="CAB")
    d.layout.profile(hide_unused_pins=hide)
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamp = d.device("P1", "DEMO-LAMP-24")
        q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.series(psu.output["+"], q.coil["A1"], wire=blue)
    d.series(psu.output["-"], q.coil["A2"], wire=blue)
    d.series(psu.output["+"], q.aux["13"], wire=blue)
    d.series(q.aux["14"], lamp["1"], wire=blue)
    d.series(psu.output["-"], lamp["2"], wire=blue)
    p2 = d.device("P2", "DEMO-LAMP-24")
    d.series(q.aux_nc["22"], p2["1"], wire=blue)
    d.series(psu.output["-"], p2["2"], wire=blue)
    if wired:
        d.series(q.aux_nc["21"], lamp["2"], wire=blue)
    doc = unit_document(cab)
    return fr.build(d, doc)


def _built_net_contact():
    """The model of `_built()` without hiding, which the cross-link study reads (study_cases.py) as a core measure."""
    return _built(hide=False).model
