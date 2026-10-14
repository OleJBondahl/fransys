"""Field case: a star marker that names many other ends puts a terminal of the net first.

The engineering shape: the three line-side poles of a contactor, the coils of two relays, a lamp
and one terminal of a strip on one net, so the net is a star with seven ends. The poles stand in
cell 1A, the terminal in a later column, which reads after them.

The bug: a marker past two targets prints its first target in reading order and `+k`. That
end was a pole or a sibling branch, so the terminal the net is fed from was named nowhere.
The rule (model-0139, amended by model-0235): the first target is a terminal of the net when it
has one, else the first other end in reading order; one derive function chooses it.
"""

from typing import TYPE_CHECKING

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.designation import port_designation
from fransys_model.derive.drawing_text import marker_text, place_text
from fransys_model.layout import LinkMarker, Page, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _built() -> Model:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Star", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        k2, k3 = (d.device(tag, "DEMO-RLY-2CO-24") for tag in ("K2", "K3"))
    with d.function("T", "Feed"):
        lamp = d.device("H1", "DEMO-LAMP-24")
    d.wire(lamp.lamp[1], x1[1], wire=(BU, 0.5))
    ends = [k1.main[pin] for pin in "135"] + [k2.coil["A2"], k3.coil["A2"], x1[1]]
    for end in ends[1:]:
        d.wire(ends[0], end, wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cabinet)).model


def _by_port(model: Model) -> dict[str, LinkMarker]:
    return {port_designation(model, m.port): m for m in layout_of(model, LinkMarker).values()}


def _terminal_cell(model: Model) -> str:
    """The frame cell of the strip terminal's own marker, as its page reads it."""
    marker = _by_port(model)["-X1:1"]
    page = layout_of(model, Page)[marker.page]
    return place_text(model, page, page, marker.x, marker.y)


def test_a_relays_marker_names_the_terminal_first() -> None:
    model = _built()
    cell = _terminal_cell(model)
    assert cell == "5A"  # the poles stand in 1A and the terminal reads after them
    for name in ("-K2:A2", "-K3:A2"):
        text = marker_text(model, _by_port(model)[name])
        assert text.startswith(f"#1-{cell} +")


def test_the_terminals_own_marker_names_the_first_end_in_reading_order() -> None:
    """The terminal names no other terminal: its first target is first in reading order."""
    model = _built()
    assert marker_text(model, _by_port(model)["-X1:1"]).startswith("#1-1A +")
