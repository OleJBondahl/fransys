"""Field case: a contactor coil with a suppressor wired across its terminals, where the suppressor's designation sorts first.
The bug: the carrier was the lower designation, so the suppressor stood in the terminals' column and the coil was pushed aside.
Fixed by model-0137 and layout-0115, the coil carries and the suppressor is the side element whatever the designations are."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU


def _columns() -> dict[str, list[int]]:
    """The x of the coil K1, the suppressor D1 and the two terminals, by their drawn symbol."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Coil", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    feed, back = d.terminal_strip("X1", "DEMO-TB-2.5", 1), d.terminal_strip("X2", "DEMO-TB-2.5", 1)
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        d1 = d.device("D1", "DEMO-FUSE-ABAT")
    wire = (BU, 0.5)
    d.series(feed[1].outer, k1.coil["A1"], wire=wire)
    d.series(k1.coil["A2"], back[1].outer, wire=wire)
    d.series(k1.coil["A1"], d1["1"], wire=wire)
    d.series(k1.coil["A2"], d1["2"], wire=wire)
    model = fr.build(d, cabinet_document(_cabinet)).model
    columns: dict[str, list[int]] = {}
    for drawing in drawn_pages(model).values():
        for symbol in drawing.symbols:
            columns.setdefault(symbol.key, []).append(symbol.x)
    return columns


def test_the_coil_stands_in_the_terminals_column_and_the_suppressor_beside_it() -> None:
    at = _columns()
    (coil,) = at["operating-device"]
    assert at["terminal"] == [coil, coil]
    assert at["fuse"] != [coil]
