"""R481: a cut pin alone on its net gets a lead wire; its stub marker stands at the lead end."""

from __future__ import annotations

from dataclasses import replace

from options_fixtures import core_options

from fransys_layout.core import Facts, PinRef, PlacementProblem
from fransys_layout.core.geometry import marker_box
from fransys_layout.core.route import route_pages
from fransys_layout.core.text_markers import mark_pages
from fransys_layout.core.values import CutEnd

from .conftest import MARKER
from .cut_fixtures import AREA, elem, net
from .pipeline_fixtures import cut_of, placed_from


def _drawn(*, cut: bool):
    lone = replace(net("m", "x.s"), cut=(CutEnd(PinRef("x", "s")),) if cut else ())
    prob = PlacementProblem(AREA, (elem("x"),), (lone,), facts=Facts())
    opts = core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    result = cut_of(prob, opts)
    placement = placed_from(result, prob, opts)
    routes = route_pages(placement, result, prob, opts)
    wires = [w for p in routes.pages for w in p.wires if w.net == "m"]
    return opts, wires, mark_pages(result, placement, prob, opts)


def test_a_lone_cut_pin_has_a_lead_one_wiring_step_long() -> None:
    opts, wires, _ = _drawn(cut=True)
    (lead,) = wires
    (x0, y0), (x1, y1) = lead.points
    assert abs(x1 - x0) + abs(y1 - y0) == opts.wiring_grid


def test_the_stub_marker_stands_at_the_end_of_the_lead() -> None:
    opts, wires, markers = _drawn(cut=True)
    (marker,) = markers
    tip = wires[0].points[-1]
    box = marker_box(marker, opts)
    assert box.x <= tip[0] <= box.x + box.w
    assert box.y <= tip[1] <= box.y + box.h
    assert wires[0].points[0] != tip


def test_a_net_that_is_not_cut_has_no_lead_and_no_stub() -> None:
    _, wires, markers = _drawn(cut=False)
    assert (wires, markers) == ([], ())
