"""S20 M4: the first rows keep room above them for their texts, inside the content box.

The cabinet on the default sheet is the measuring stick. A constant, two lanes of headroom
(decision layout-0031), was once the smallest that kept a north-facing port's route and wire
label inside the content box. The top reference band every page keeps (M4, `place`'s
`reference_band`, with C14's text room) now does that work, so with no lanes at all the cabinet
still has no finding. The cabinet has no route over row 0 to show what the room is for (D1 turns
the `-K8` contact that had one, so its route runs straight), so one relay wired to itself stands
in for it.
"""

import importlib
from typing import TYPE_CHECKING

from dd_chain_fixtures import build, design
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic import engine, run_stages
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint.codes import OUT_OF_CONTENT_BOX
from fransys_layout.stages.place import PAGE_OVERFULL
from fransys_model.kernel import freeze

if TYPE_CHECKING:
    import pytest

    from fransys_layout.stages import Layout


def _set_room(monkeypatch: pytest.MonkeyPatch, *, lanes: int, text_room: bool) -> None:
    """`lanes` lanes of headroom; `text_room=False` also turns the room off: `place` then gets
    a text lift and sink of zero and a band of zero (M4). (`fransys_layout.stages.place`
    names the re-exported function, so the module comes from `importlib`.)
    """
    monkeypatch.setattr(engine, "TOP_HEADROOM_LANES", lanes)
    if not text_room:
        module = importlib.import_module("fransys_layout.stages.place")
        monkeypatch.setattr(module, "_text_room", lambda *_: (0, 0))
        monkeypatch.setattr(module, "_reference_band", lambda *_: 0)


def _run(
    monkeypatch: pytest.MonkeyPatch, *, lanes: int, text_room: bool
) -> tuple[Layout, list[str]]:
    """The cabinet's layout and finding codes with `lanes` lanes of headroom."""
    _set_room(monkeypatch, lanes=lanes, text_room=text_room)
    model = freeze(build_cabinet())
    layout, _, findings = run_stages(model, read_inputs(model))
    return layout, [finding.code for finding in findings]


def _run_relay(monkeypatch: pytest.MonkeyPatch, *, text_room: bool) -> tuple[Layout, list[str]]:
    """The layout and finding codes of one relay `K1`, no headroom lane.

    Its coil's A1 is wired to pin 12 of its first contact: the wire leaves a north-facing port of
    row 0 and passes over it.
    """
    _set_room(monkeypatch, lanes=0, text_room=text_room)
    parts, d = design()
    k1 = d.item(
        "DEMO-RLY-2CO-24", tag="K1", at=d.location("C1", "Cabinet"), group=d.group("G1", "G")
    )
    d.wiring(colour="BU", gauge="0.5")(k1.fn("coil")["A1"], k1.fn("co_1")["12"])
    result = build(parts, d)
    layout = stage_results(result.model, read_inputs(result.model))[0].layout
    return layout, [finding.code for finding in result.findings]


def _highest_route(layout: Layout) -> int:
    """The smallest y of any route vertex of the layout."""
    return min(point.at.y for route in layout.routes for point in route.points)


def _highest_top(layout: Layout) -> int:
    """The smallest y of any keep-out, label or marker box or route vertex of the layout."""
    return min(
        (
            *(one.at.y + one.geometry.keepout.y for one in layout.placed),
            *(label.box.y for label in layout.labels),
            *(marker.box.y for marker in layout.markers),
            *(point.at.y for route in layout.routes for point in route.points),
        )
    )


def test_the_cabinet_has_no_content_box_finding_with_the_engine_constant() -> None:
    """Row 0 starts below the headroom, so no route or label leaves the content box."""
    model = freeze(build_cabinet())
    _, _, findings = run_stages(model, read_inputs(model))
    codes = [finding.code for finding in findings]
    assert OUT_OF_CONTENT_BOX not in codes
    assert PAGE_OVERFULL not in codes


def test_the_first_rows_keep_room_for_their_texts_with_no_headroom_lanes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M4: with no headroom lane, every text, keep-out box and route vertex is still inside, and
    row 0 stands below the band (a positive reading: its keep-out top is below the box top)."""
    layout, codes = _run(monkeypatch, lanes=0, text_room=True)
    assert OUT_OF_CONTENT_BOX not in codes
    assert _highest_top(layout) >= 0
    layout, codes = _run_relay(monkeypatch, text_room=True)
    assert OUT_OF_CONTENT_BOX not in codes
    assert _highest_route(layout) >= 0
    assert min(one.at.y + one.geometry.keepout.y for one in layout.placed) > 0


def test_without_the_text_room_and_without_headroom_a_route_leaves_the_content_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Can fail, and shows M4's band and C14's room are what keep them in: turn them and the
    lanes off, and a route leaving a north-facing port of row 0 turns above the content-box top
    (y < 0), which the lint reports. The frame gap (layout-0104) is off too: it moves the page
    right and down by a grid, which lifts this one route to y 0."""
    monkeypatch.setattr(importlib.import_module("fransys_layout.stages.tidy"), "TEXT_GAP", 0)
    layout, codes = _run_relay(monkeypatch, text_room=False)
    assert _highest_route(layout) < 0
    assert OUT_OF_CONTENT_BOX in codes


def test_no_cabinet_text_stands_closer_than_the_text_gap_to_the_left_frame() -> None:
    """layout-0104: every label, an outline title among them, is 8 G (the house text gap, written
    out) from the content box's left edge on every page; the measured minimum is also not 0."""
    model = freeze(build_cabinet())
    layout, _, _ = run_stages(model, read_inputs(model))
    lefts = [label.box.x for label in layout.labels]
    assert lefts
    assert min(lefts) >= 8
