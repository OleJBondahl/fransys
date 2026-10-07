"""CUT-END (case (b)): a conductor a page break severs is cut inside the unit that draws it.

One unit `u1` holds connectors `panel<i>`, each wired pin for pin to a connector `peer<i>`;
some panels are marked `boundary`. A boundary function has a replica page in the unit-less
drawing set of its location, so its "earliest page" was that replica page, `links` classified the
cut CROSS_UNIT (no marker) and coherence expected a marker pair: `CONNECTION_NOT_DRAWN`. The cut
belongs to the unit whose drawing draws the wire: both markers stand on the unit's own pages.

Each variant names a row of the evidence table for case (b): v1 (one location, six wires), v2
(peer at no location), v2b (panel at no location), v3 (two locations), v10 (three pairs of two
pins, all boundary), v12 (the third panel only), v13 (both ends at no location). v3 and the
`_first_only` v13 are guards that pass on the base; the others fail there.

Built through the `fransys` facade from `examples/demo-parts` (`DEMO-CONN-2P`, two pins, so six
wires are six single-wire pairs or three pairs of two pins); read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.derive import unit_release
from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Cut end",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(
    *,
    pairs: int,
    pins: int,
    boundary: tuple[int, ...] | None,
    panel_at: str | None = "LOC1",
    peer_at: str | None = "LOC1",
):
    """Unit `u1` with `pairs` panels of `pins` pins wired pin for pin to their peers, the panels
    in `boundary` marked (`boundary=None`: no unit at all, the same design at the top level); a
    location name of `None` leaves that end at no location."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    if boundary is None:
        s = d.scope("s")
    else:
        s = d.scope("s").unit("u1", revision=1, interface="1")
        s.revision(1, date="2026-01-01", text="First release", created="XX")
    boundary = boundary or ()
    named = sorted({name for name in (panel_at, peer_at) if name is not None})
    at = {name: s.location(name, name) for name in named}
    wire = d.wiring(colour="BU", gauge="0.5")
    for i in range(pairs):
        panel = s.item("DEMO-CONN-2P", name=f"panel{i}", at=at.get(panel_at))
        if i in boundary:
            s.boundary(panel)
        peer = s.item("DEMO-CONN-2P", name=f"peer{i}", at=at.get(peer_at))
        for pin in range(1, pins + 1):
            wire(panel.fn("x1")[str(pin)], peer.fn("x1")[str(pin)])
    return fr.build(parts, d.draft(), layout_trigger_document())


def _pages_of(model, name: str) -> dict:
    """The pages the function `x1` of the item `name` stands on, page id -> its drawing set."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return {
        placement.page: sets[pages[placement.page].drawing_set]
        for placement in layout_of(model, SymbolPlacement).values()
        if functions(model)[placement.function].key[1] == name
    }


def _severed(model, pairs: int) -> list[int]:
    """The indices of the pairs whose two ends share no page: a wire that needs a cut."""
    return [
        i
        for i in range(pairs)
        if not set(_pages_of(model, f"panel{i}")) & set(_pages_of(model, f"peer{i}"))
    ]


def _has_replica(model, i: int) -> bool:
    """Whether panel `i` also stands in a drawing set that belongs to no unit."""
    return any(d.unit is None for d in _pages_of(model, f"panel{i}").values())


def _ends(model, name: str) -> list[LinkMarker]:
    """The markers standing on ports of the function `x1` of the item `name`."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if functions(model)[ports(model)[m.port].function].key[1] == name
    ]


def _errors(result) -> list[str]:
    """The codes of the ERROR findings, in order."""
    return [f.code for f in result.findings if f.severity is Severity.ERROR]


def _assert_cut_in_the_unit(result, severed: list[int]) -> None:
    """0 ERROR, and both functions of every severed pair carry markers, each on a page of a
    drawing set of the unit `u1` itself (never the unit-less set's replica page). A marker pair
    names each other across two pages."""
    model = result.model
    assert _errors(result) == []
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    markers = layout_of(model, LinkMarker)
    for i in severed:
        panel_ends, peer_ends = _ends(model, f"panel{i}"), _ends(model, f"peer{i}")
        assert panel_ends
        assert peer_ends
        for marker in (*panel_ends, *peer_ends):
            owner = sets[pages[marker.page].drawing_set].unit
            assert owner is not None
            assert unit_release(model, owner).name == "u1"
            assert markers[marker.partner].partner == marker.id
            assert marker.partner != marker.id
            assert markers[marker.partner].page != marker.page


def test_v1_one_location_six_boundary_wires_are_cut_in_the_unit() -> None:
    """Six single-wire pairs at one location, all panels boundary: the page breaks after the
    fourth pair, so the last two pairs are cut."""
    # UNDO: fransys_layout/stages/references/cuts.py `_cuts` and
    #     lint/_cuts.py `conductor_cut`: `min(pages_a)` for a boundary end ->
    #     its replica page (the unit-less set's page 1)
    result = _build(pairs=6, pins=1, boundary=(0, 1, 2, 3, 4, 5))
    severed = _severed(result.model, 6)
    assert severed
    assert all(_has_replica(result.model, i) for i in severed)
    _assert_cut_in_the_unit(result, severed)


def test_v2_boundary_panel_and_peer_at_no_location_are_cut_in_the_unit() -> None:
    """The peer at no location, the panel boundary. Layout-0081: a unit is one drawing set
    whatever locations its items stand at, so the peer's end is no longer in a set of its own: the
    pair shares a page of the unit's one set, is not cut, and warns no `LINK_PARTNER_UNLOCATED`
    (before, the two ends stood in two sets of the unit and the wire was cut between them)."""
    # UNDO: stages/types.py, `Column.drawing_set_key`: the unit branch returns
    #     `(self.unit, self.location)` again (two sets, the pair is cut between them)
    result = _build(pairs=1, pins=1, boundary=(0,), peer_at=None)
    assert _errors(result) == []
    assert _severed(result.model, 1) == []
    assert _has_replica(result.model, 0)
    assert "LINK_PARTNER_UNLOCATED" not in {f.code for f in result.findings}


def test_v2b_boundary_panel_at_no_location_and_peer_at_a_location_are_cut_in_the_unit() -> None:
    """The panel at no location and boundary, the peer at a location: as v2, ends swapped (one
    unit set, layout-0081: no cut, no `LINK_PARTNER_UNLOCATED`)."""
    # UNDO: as test_v2
    result = _build(pairs=1, pins=1, boundary=(0,), panel_at=None)
    assert _errors(result) == []
    assert _severed(result.model, 1) == []
    assert _has_replica(result.model, 0)
    assert "LINK_PARTNER_UNLOCATED" not in {f.code for f in result.findings}


def test_v3_boundary_panels_at_another_location_stay_clean() -> None:
    """Guard: panels at their own location PNL, peers at LOC1, all boundary. Layout-0081: the two
    locations are one drawing set of the unit, so only the pair the page break severs (the third)
    is cut, where before all three were (two sets of the unit). Its cut is still a pair of off
    stubs (two top-level locations, C21) inside the unit."""
    # UNDO: stages/types.py, `Column.drawing_set_key`: the unit branch returns
    #     `(self.unit, self.location)` again (all three pairs are cut)
    result = _build(pairs=3, pins=2, boundary=(0, 1, 2), panel_at="PNL")
    severed = _severed(result.model, 3)
    assert severed == [2]
    assert all(_has_replica(result.model, i) for i in severed)
    _assert_cut_in_the_unit(result, severed)
    assert not any(m.star is StarKind.OFF for m in layout_of(result.model, LinkMarker).values())


def test_v3_two_top_level_locations_of_one_unit_draw_no_off_stubs() -> None:
    """LD7: a stub only where a wire leaves its DRAWING. Panels at PNL and peers at LOC1 are two
    top-level locations of ONE unit, so one drawing set: the pairs that share a page are plain
    wires (no marker at all) and the cut pair is a marker pair, never an off stub."""
    # UNDO: stages/offstubs.py `crosses_location`: drop `and a.drawing_set_key !=
    #     b.drawing_set_key` (two top-level locations cross again: off stubs on every pair)
    result = _build(pairs=3, pins=2, boundary=(), panel_at="PNL")
    assert _errors(result) == []
    markers = layout_of(result.model, LinkMarker).values()
    assert markers
    assert not any(m.star is StarKind.OFF for m in markers)
    for i in (0, 1):
        assert not _ends(result.model, f"panel{i}")
        assert not _ends(result.model, f"peer{i}")


def test_v3_top_level_control_two_locations_still_draw_off_stubs() -> None:
    """The same design with no unit: the two locations are two drawing sets, so every wire
    between them still ends in an off stub at both ends."""
    result = _build(pairs=3, pins=2, boundary=None, panel_at="PNL")
    assert _errors(result) == []
    markers = list(layout_of(result.model, LinkMarker).values())
    assert markers
    assert all(m.star is StarKind.OFF for m in markers)


def test_v10_three_boundary_pairs_of_two_pins_are_cut_in_the_unit() -> None:
    """Three pairs of two pins, all panels boundary: the third pair falls on the unit's second
    page, away from its panel."""
    # UNDO: as test_v1 (`min(pages_a)` for a boundary end -> its replica page)
    result = _build(pairs=3, pins=2, boundary=(0, 1, 2))
    severed = _severed(result.model, 3)
    assert severed
    assert all(_has_replica(result.model, i) for i in severed)
    _assert_cut_in_the_unit(result, severed)


def test_v12_boundary_on_the_third_panel_only_is_cut_in_the_unit() -> None:
    """Three pairs of two pins, only the third panel boundary: the third pair is the one the page
    break severs, and its panel is the one with a replica."""
    # UNDO: as test_v1 (`min(pages_a)` for a boundary end -> its replica page)
    result = _build(pairs=3, pins=2, boundary=(2,))
    severed = _severed(result.model, 3)
    assert severed == [2]
    assert _has_replica(result.model, 2)
    _assert_cut_in_the_unit(result, severed)


def test_v13_both_ends_at_no_location_all_panels_boundary_are_cut_in_the_unit() -> None:
    """Both ends at no location, three pairs of two pins, all panels boundary. The evidence table
    has one boundary panel here and reads it as failing; on the base that shape is clean (see
    the guard below) and this one, with every panel boundary, fails."""
    # UNDO: as test_v1 (`min(pages_a)` for a boundary end -> its replica page); and
    #     `_cuts` rule 1 applies with no location too
    result = _build(pairs=3, pins=2, boundary=(0, 1, 2), panel_at=None, peer_at=None)
    severed = _severed(result.model, 3)
    assert severed
    assert all(_has_replica(result.model, i) for i in severed)
    _assert_cut_in_the_unit(result, severed)


def test_v13_first_only_both_ends_at_no_location_stays_clean() -> None:
    """Guard (passes on the base): as v13, the first panel only boundary. The page break severs
    a pair whose panel has no replica, and the boundary pair shares a page."""
    # No UNDO: a guard that passes on the base.
    result = _build(pairs=3, pins=2, boundary=(0,), panel_at=None, peer_at=None)
    severed = _severed(result.model, 3)
    assert severed == [2]
    assert not _has_replica(result.model, 2)
    _assert_cut_in_the_unit(result, severed)
