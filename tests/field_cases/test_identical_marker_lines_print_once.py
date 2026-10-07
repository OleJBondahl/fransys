"""Field case: a marker prints one line for each place its net continues, not one per end.

The engineering shape: the three line-side poles of a three-pole contactor paralleled on one net
that also reaches the coil of each of two relays, so the net is a fan-out with five ends and the
three poles stand in one cell.

The bug: a marker listed one line for every other end, so a relay's marker printed the contactor's
cell three times ("#1-2A", "#1-2A", "#1-2A").
The rule (decisions model-0137 / model-0139): identical targets count once, in `target_lines`.
"""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.designation import port_designation
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, layout_of


def _texts() -> dict[str, list[str]]:
    """Each marker's printed lines by its port's designation."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Marker", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        k2, k3 = (d.device(tag, "DEMO-RLY-2CO-24") for tag in ("K2", "K3"))
    ends = [k1.main[pin] for pin in "135"] + [k2.coil["A2"], k3.coil["A2"]]
    for end in ends[1:]:
        d.wire(ends[0], end, wire=(BU, 0.5))
    model = fr.build(d, cabinet_document(_cabinet)).model
    return {
        port_designation(model, m.port): marker_text(model, m).split("\n")
        for m in layout_of(model, LinkMarker).values()
    }


def test_three_ends_in_one_cell_give_one_marker_line() -> None:
    texts = _texts()
    assert texts["-K3:A2"] == ["#1-2A +1"]  # C2: the first place and one more distinct one
    assert all(len(lines) == len(set(lines)) for lines in texts.values())
