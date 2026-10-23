"""The drawn page carries every annotation the core placed (el-0017, CORE-TEXTS).

Both fixtures are built once; each check reads the same written model.
"""

import sys
from dataclasses import replace
from pathlib import Path

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys import colours
from fransys_el import (
    build,
    lay_out_drawn,
    options,
    symbol_kit,
)
from fransys_el.kit_keys import tag_of
from fransys_el.placement_ids import symbol_key
from fransys_el.placement_markers import ARROW, KINDS, LONE, facing_views, marker_fit
from fransys_el.placement_widest import link_fit
from ring_cases import bank_model, box_kit, channels_model
from symdef import repeat

from electrical_symbols import LIBRARY
from fransys_layout.core import PinRef, solve
from fransys_model.derive import function_item
from fransys_model.derive.drawing_text import port_marking
from fransys_model.vocab.tables import items

sys.path.append(str(Path(__file__).parents[3] / "tests"))
from _card_case import card_case_drafts
from _model_build_cover import cabinet_document


def _built(model, *, generic: bool):
    conventions = house()
    kit = box_kit(model) if generic else symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, conventions, LIBRARY)
    pins = [PinRef(s.id, p.id) for s in problem.symbols for p in s.pins]
    fit = marker_fit(model, kit, None, LIBRARY, pins)  # the fitted boxes, as `lay_out` passes them
    wide = link_fit(model, kit, LIBRARY, None)
    turned, above, below = facing_views()
    chosen = replace(
        options(conventions, LIBRARY),
        marker_fit=fit,
        link_fit=wide,
        marker_vertical=turned,
        marker_above=above,
        marker_below=below,
    )
    core = solve(problem, chosen)
    written, _, drawn, _ = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    return model, kit, core, written, drawn, chosen


@pytest.fixture(scope="module", params=["card16", "bank8"])
def fixture(request):
    if request.param == "card16":
        return _built(fr.build(*card_case_drafts(16)).model, generic=False)
    return _built(bank_model(8), generic=True)


def _texts(fixture, kind):
    drawn = fixture[4]
    return [t for d in drawn.values() for t in d.texts if t.kind == kind]


def test_every_placed_symbol_has_one_designation_text(fixture) -> None:
    core = fixture[2]
    placed = [p for page in core.placement.pages for p in page.placed]
    assert len(placed) > 0
    assert len(_texts(fixture, "TAG")) == len(placed)


def test_the_designation_texts_are_the_tag_text_of_the_placed_functions(fixture) -> None:
    model, kit, core, *_ = fixture
    placed = {p.sym for page in core.placement.pages for p in page.placed}
    want = sorted(
        tag_of(model, f, unit=items(model)[function_item(model, f)].unit)  # its own set's unit
        for f in kit
        if symbol_key(model, f) in placed
    )
    assert sorted(t.text for t in _texts(fixture, "TAG")) == want


def test_no_text_overlaps_and_every_text_box_is_inside_the_content_box(fixture) -> None:
    _, _, core, _, drawn, _ = fixture
    assert [f for f in core.findings if f.code == "ANNEX_UNPLACED"] == []
    for drawing in drawn.values():
        for t in drawing.texts:
            assert t.box.x >= 0
            assert t.box.y >= 0
            assert t.box.x + t.box.w <= drawing.area.w
            assert t.box.y + t.box.h <= drawing.area.h


def _crosses(a, b, box) -> bool:
    (x1, y1), (x2, y2) = a, b
    lo_x, hi_x = sorted((x1, x2))
    lo_y, hi_y = sorted((y1, y2))
    return lo_x < box.x + box.w and hi_x > box.x and lo_y < box.y + box.h and hi_y > box.y


def test_no_wire_crosses_a_designation_text(fixture) -> None:
    for drawing in fixture[4].values():
        for t in drawing.texts:
            for wire in drawing.wires:
                for a, b in zip(wire.points, wire.points[1:], strict=False):
                    assert not _crosses(a, b, t.box), (t.text, wire.id)


def _marking_slots(fixture):
    """The `marking.*` slots of the drawn symbols that are no generic box, as (symbol key, slot)."""
    return sorted(
        (s.key, slot, text)
        for d in fixture[4].values()
        for s in d.symbols
        if s.key != "generic-box"
        for slot, text in s.slots
        if slot.startswith("marking.")
    )


def _symdef_marking_slots(model, kit, placed):
    """The expected `marking.*` slots, read from symdef's repeated symbol, not the code's filter.

    Each slot symdef declares on the symbol repeated `poles` times is matched back to its port.
    """
    want = []
    for function, pick in kit.items():
        if pick.key == "generic-box" or symbol_key(model, function) not in placed:
            continue
        by_slot = {f"marking.{name}": port for port, name in pick.ports.items()}
        base = LIBRARY.get(pick.key)
        symbol = base if pick.poles == 1 else repeat(base, pick.poles)
        declared = [s.id for s in symbol.slots]
        want += [
            (pick.key, slot, port_marking(model, by_slot[slot]))
            for slot in declared
            if slot in by_slot and port_marking(model, by_slot[slot])
        ]
    return sorted(want)


def test_every_port_whose_symbol_declares_a_marking_slot_has_its_marking(fixture) -> None:
    model, kit, core, *_ = fixture
    placed = {p.sym for page in core.placement.pages for p in page.placed}
    want = _symdef_marking_slots(model, kit, placed)
    assert _marking_slots(fixture) == want
    assert any(text in {"A1", "A2"} for _, _, text in want)


def _changeovers():
    """Three one-pole changeovers of one relay, wired as a three-phase make path."""
    d = fr.design("demo_parts")
    xa = d.terminal_strip("XA", "DEMO-TB-2.5")
    supply = d.ac_supply("A", "230", xa[1], xa[2], xa[3])
    qa, m1 = d.device("QA", "DEMO-MCB-3P"), d.device("M1", "DEMO-MOTOR-4KW")
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    group = d.poles(k1.co_1, k1.co_2, k1.co_3, selector=False)
    d.series(supply, qa.element, group.no, m1, wire=2.5)
    return fr.build(d).model


def test_a_pole_gang_has_the_markings_of_every_pole_of_its_repeated_symbol() -> None:
    """Three change-overs drawn as one gang: symdef repeats the symbol."""
    gang = _built(_changeovers(), generic=False)
    want = _symdef_marking_slots(
        gang[0], gang[1], {p.sym for pg in gang[2].placement.pages for p in pg.placed}
    )
    assert {slot for key, slot, _ in want if key == "change-over-contact"} >= {
        "marking.3.com",
        "marking.2.no",
    }
    assert _marking_slots(gang) == want


def test_a_core_page_title_carries_its_group_blocks_text(fixture) -> None:
    """E0: a core page has a page group, so its title is that block's text, not designations.

    The old engine's pages had no group and wrote `layout.label` records, which is why they
    printed "by others, -A1, ..." from the designations; the core path writes no label record.
    """
    from fransys_model.derive import ordered_pages, page_title
    from fransys_model.vocab import aspect_nodes

    written = fixture[3]
    drawn = fixture[4]
    for page in (p for p in ordered_pages(written) if p.id in drawn):
        assert page.groups
        assert aspect_nodes(written)[page.groups[0].group].description in page_title(written, page)


def _drawn_markers(fixture):
    return [
        s
        for d in fixture[4].values()
        for s in d.symbols
        if s.key in ("reference-marker", "marker-arrow-turned")
    ]


def test_every_core_marker_is_drawn_with_its_far_cell_in_its_text(fixture) -> None:
    """The text is `derive.marker_text` of the written LinkMarker; it ends in the core's cell."""
    core = fixture[2]
    drawn = {(s.x, s.y): dict(s.slots)["ref"] for s in _drawn_markers(fixture)}
    markers = core.annotations.markers
    assert len(drawn) == len(markers)
    for m in markers:
        text = drawn[m.x, m.y]
        assert text.startswith("#")
        assert text.endswith(f"-{m.cell}"), (text, m)


def test_the_channels_23_page_draws_its_four_marker_boxes() -> None:
    """Measured: bank8 draws none since BOX-SIDES A; channels 23 is the smallest with 2+ markers.

    Eight when every pair kind took the widest box; four on frames 1c46c629 (R350, R362). On the
    text-stage core (annex footprints) 21 and 22 fit one page and cut nothing; 23 cuts first."""
    page = _built(channels_model(23), generic=True)
    assert len(page[2].annotations.markers) == 4
    assert len(_drawn_markers(page)) == 4


def test_a_marker_carries_the_tint_of_its_reference_number(fixture) -> None:
    """`#n` takes tint `(n - 1) % 8` of `REF_TINTS`: both ends of a net share it (REF-COLOURS)."""
    from fransys_el import REF_TINTS

    drawn = _drawn_markers(fixture)
    for s in drawn:
        number = int(dict(s.slots)["ref"].partition("-")[0].removeprefix("#"))
        assert s.tint == REF_TINTS[(number - 1) % len(REF_TINTS)]


def test_the_nets_of_the_channels_23_page_that_draw_markers_have_one_tint_each() -> None:
    """Two nets draw markers since the fitted stub boxes (R350) moved the cut; three before."""
    assert len({s.tint for s in _drawn_markers(_built(channels_model(23), generic=True))}) == 2


def test_a_stub_text_wider_than_the_plain_flag_gets_a_fitted_box_for_the_core_to_reserve() -> None:
    """Without `marker_fit` a long text keeps the plain box and its flag leaves its page (R318)."""
    model = channels_model(21)
    kit = box_kit(model)
    problem, _ = build(model, kit, house(), LIBRARY)
    pins = [PinRef(s.id, p.id) for s in problem.symbols for p in s.pins]
    plain = options(house(), LIBRARY).marker
    fit = marker_fit(model, kit, None, LIBRARY, pins)
    assert fit
    assert any(boxes != plain for (_, kind), boxes in fit.items() if kind in LONE)


def test_the_built_options_hold_a_fitted_box_for_every_marker_kind(monkeypatch) -> None:
    """R378, R384: the options the real build solves hold a box for each kind: fit or link_fit."""
    from fransys_el import lay_out_core

    from fransys_layout.core.values import RefKind

    assert set(KINDS) == {k.value for k in RefKind}
    seen = []

    def spy(part, opts):
        seen.append(opts)
        return solve(part, opts)

    monkeypatch.setattr(lay_out_core, "solve", spy)
    _built(_fan_out().model, generic=False)
    assert seen
    for opts in seen:
        pins = {pin for pin, _ in opts.marker_fit}
        assert pins
        for pin in pins:
            assert {k for p, k in opts.marker_fit if p == pin} == set(KINDS) - {ARROW}, pin
        assert opts.link_fit  # the arrow's box: the widest line, R350


def _fan_out():
    """One coil net fanning out to thirty-eight coils: arrows and a long stub text."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Marker", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        coils = [d.device(f"K{n}", "DEMO-RLY-2CO-24").coil["A2"] for n in range(1, 40)]
    for end in coils[1:]:
        d.detail.wire(coils[0], end, wire=(colours.BU, 0.5))
    return fr.build(d, cabinet_document(cabinet))


def _row_band(page, sym):
    """The solved band (top, bottom) of the row whose footprints hold `sym` on `page`."""
    at = next(p.footprint.y for p in page.placed if p.sym == sym)
    return next(b for b in page.bands if b[0] <= at < b[1])


@pytest.mark.parametrize(
    ("kind", "generic", "size"), [("arrow", False, 0), ("tag", True, 23), ("tag", True, 32)]
)
def test_every_flag_box_lies_inside_its_rows_solved_band(kind, generic, size) -> None:
    """R377: the stagger and the clearing step a flag only inside the room its row was given."""
    model = _fan_out().model if kind == "arrow" else channels_model(size)
    _, _, core, _, _, chosen = _built(model, generic=generic)
    pages = {pg.page: pg for pg in core.placement.pages}
    flags = core.annotations.markers
    assert {str(m.kind) for m in flags} >= {kind}
    for m in flags:
        top, bottom = _row_band(pages[m.page], m.end.sym)
        boxes = chosen.marker_fit.get((m.end, str(m.kind))) or chosen.link_fit
        box = boxes[m.orient]
        assert top <= m.y + box.y
        assert m.y + box.y + box.h <= bottom, (m.end, box)
