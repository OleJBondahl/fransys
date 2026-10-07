"""Regression: a chain between two rails draws its supply end on top (C20, layout-0115 D5).

A 24 V power supply feeds breaker Q2, lamp H1 and breaker Q1 in series, back to its 0 V output.
Q2 is wired to `+` and Q1 to `-`, so the designations run against the current. The potential rank
of the two end pins decides, so the breaker at `+` is drawn above the one at `-`, whatever the
designation text says. This guards C20; it never failed, so it carries no xfail.
"""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items


def _rows() -> dict[str | None, int]:
    """Each breaker's drawn y: Q2 next to `+`, Q1 next to `-`, the lamp H1 between their pins 2."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Chain", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        q1, q2 = (d.device(tag, "DEMO-MCB-C6") for tag in ("Q1", "Q2"))
        h1 = d.device("H1", "DEMO-LAMP-24")
    wire = (BU, 0.5)
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("CONTROL", psu)
    d.wire(psu.output["+"], q2["1"], wire=wire)
    d.wire(q2["2"], h1["1"], wire=wire)
    d.wire(h1["2"], q1["2"], wire=wire)
    d.wire(q1["1"], psu.output["-"], wire=wire)
    model = fr.build(d, cabinet_document(_cabinet)).model
    return {
        items(model)[functions(model)[p.function].item].tag: p.y
        for p in layout_of(model, SymbolPlacement).values()
    }


def test_the_breaker_at_the_plus_rail_stays_above_the_one_at_the_minus_rail() -> None:
    rows = _rows()
    assert rows["Q2"] < rows["Q1"]
