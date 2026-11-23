"""Field case: a star marker that names many other ends puts a terminal of the net first.
The bug: the marker named its first target in reading order, a pole, so the net's feeding terminal was named nowhere.
Fixed by model-0139 (amended by model-0235), the first target is a terminal of the net when it has one, else the first other end."""

from typing import TYPE_CHECKING

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive import position_at, reference_targets
from fransys_model.derive.designation import port_designation
from fransys_model.derive.drawing_text import marker_text
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
    ends = [lamp.lamp[1], *(k1.main[pin] for pin in "135"), k2.coil["A2"], k3.coil["A2"], x1[1].inner]
    for end in ends[1:]:
        d.series(ends[0], end, wire=(BU, 0.5))
    d.series(lamp.lamp[2], x1[2].inner, wire=(BU, 0.5))
    d.series(k2.coil["A1"], k3.coil["A1"], wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cabinet)).model


def _marker(model: Model, name: str) -> LinkMarker:
    markers = {port_designation(model, m.port): m for m in layout_of(model, LinkMarker).values()}
    assert name in markers, f"no layout.link_marker record for {name}: the net is drawn whole, so no reference end is placed (have {sorted(markers)})"
    return markers[name]


def _terminal_cell(model: Model) -> str:
    """The frame cell of the strip terminal's own marker, as its page reads it."""
    marker = _marker(model, "-X1:1")
    page = layout_of(model, Page)[marker.page]
    cell = next(cell for (_, cell), ends in reference_targets(model).items() if any(end[0] == marker.id for end in ends))
    return position_at(model, page, page, *cell)


def test_a_relays_marker_names_the_terminal_first() -> None:
    model = _built()
    cell = _terminal_cell(model)
    assert cell == "4A"  # the poles stand in 1A and the terminal reads after them
    for name in ("-K2:A2", "-K3:A2"):
        text = marker_text(model, _marker(model, name))
        assert text.startswith(f"#1-{cell} +")


def test_the_terminals_own_marker_names_the_first_end_in_reading_order() -> None:
    """The terminal names no other terminal: its first target is first in reading order."""
    model = _built()
    assert marker_text(model, _marker(model, "-X1:1")).startswith("#1-1A +")
