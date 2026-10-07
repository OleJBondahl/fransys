"""Field case: a coil carries its column; a suppressor wired across it is a side element.

The engineering shape: a contactor coil fed from a terminal at A1 and returning to a terminal at
A2, with a suppressor (a two-port element) wired across A1 and A2. The suppressor has no item
relation to the coil in the model and its designation, D1, sorts before the coil's K1. The demo
parts have no diode, so a fuse stands in: any two-port part with a through link is the same shape.

The bug: the carrier was the lower designation, so D1 stood in the terminals' column and the coil
was pushed aside as its side element.
The rule (decisions model-0137 / layout-0115): the coil carries and the suppressor is the side
element whatever the designations are, as it already is for a suppressor that is a child item.
"""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions


def _columns() -> dict[str, int]:
    """The x of the coil K1, the suppressor D1 and the two terminals, by their tags."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Coil", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    feed, back = d.terminal_strip("X1", "DEMO-TB-2.5", 1), d.terminal_strip("X2", "DEMO-TB-2.5", 1)
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        d1 = d.device("D1", "DEMO-FUSE-ABAT")
    wire = (BU, 0.5)
    d.wire(feed[1].outer, k1.coil["A1"], wire=wire)
    d.wire(k1.coil["A2"], back[1].outer, wire=wire)
    d.wire(k1.coil["A1"], d1["1"], wire=wire)
    d.wire(k1.coil["A2"], d1["2"], wire=wire)
    model = fr.build(d, cabinet_document(_cabinet)).model
    return {
        "/".join(functions(model)[p.function].key[:-2]): p.x
        for p in layout_of(model, SymbolPlacement).values()
    }


def test_the_coil_stands_in_the_terminals_column_and_the_suppressor_beside_it() -> None:
    at = _columns()
    assert at["G/K1"] == at["X1/terminal/1"] == at["X2/terminal/1"]
    assert at["G/D1"] != at["G/K1"]
