"""OVERLAP and OUT_OF_PAGE over finished drawings (DRAWING-INVARIANTS, R323).

Each code has a clean drawing that raises nothing and a drawing with one planted defect.
"""

from contextlib import nullcontext
from dataclasses import replace
from typing import Any
from unittest.mock import patch

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_drawn
from fransys_el.drawing_invariants import drawing_invariant_findings, page_overlaps
from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import Netlist, _part
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, Size
from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnText, DrawnWire
from fransys_model.kernel import Id, Severity, id_namespace

PAGE = Id(kind="page", value="page-1")


def _portless_part(drawing: Drawing):
    """A page part of planted symbols ("k-a" is no library key): they have no ports. A real build never runs under this."""
    with patch("fransys_el.drawn_netlist.port_points", return_value=()):
        return _part(drawing, {}, LIBRARY)


def _symbol(sid: str, box: Box) -> DrawnSymbol:
    return DrawnSymbol(sid, "k-" + sid, box.x, box.y, "R0", outline=box)


def _drawing(*symbols: DrawnSymbol, texts: tuple[DrawnText, ...] = ()) -> dict[Id[Any], Drawing]:
    return {PAGE: Drawing(Size(100, 100), symbols, (), texts, (), "v")}


def _findings(drawings) -> tuple[Any, ...]:
    """The page invariants over drawings with no ports: a Netlist built from their geometry."""
    return drawing_invariant_findings(Netlist({page: _portless_part(drawing) for page, drawing in drawings.items()}, Union(), {}, {}, {}, {}))


def _codes(drawings) -> list[str]:
    return [f.code for f in _findings(drawings)]


def test_a_clean_page_raises_nothing():
    clean = _drawing(_symbol("a", Box(1, 1, 10, 10)), _symbol("b", Box(11, 1, 10, 10)))
    assert _codes(clean) == []


def test_two_bodies_with_shared_area_raise_overlap_naming_both_keys():
    planted = _drawing(_symbol("a", Box(1, 1, 10, 10)), _symbol("b", Box(5, 5, 10, 10)))
    (found,) = _findings(planted)
    assert found.code == "OVERLAP"
    assert found.severity is Severity.WARNING
    assert "k-a / k-b" in found.message


def test_a_text_on_a_body_raises_overlap():
    text = DrawnText("T1", Box(2, 2, 4, 2), "designation", "NW")
    planted = _drawing(_symbol("a", Box(1, 1, 10, 10)), texts=(text,))
    assert _codes(planted) == ["OVERLAP"]


def test_a_slot_text_on_a_neighbours_body_or_beyond_the_page_is_seen():
    """TEXT-BOX-MEASURED: the box symdef measured around a slot string is ink the page checks read."""
    owner = replace(_symbol("a", Box(1, 1, 10, 10)), slot_ink=(("marking.x", Box(20, 20, 6, 2)),))
    clear = _drawing(owner, _symbol("b", Box(40, 40, 10, 10)))
    assert _codes(clear) == []
    over = _drawing(owner, _symbol("b", Box(22, 19, 10, 10)))
    assert _codes(over) == ["OVERLAP"]
    out = _drawing(replace(_symbol("a", Box(1, 1, 10, 10)), slot_ink=(("marking.x", Box(97, 20, 6, 2)),)))
    assert _codes(out) == ["OUT_OF_PAGE"]


def test_two_slot_texts_of_one_symbol_that_share_area_raise_overlap():
    """TEXT-BOX-MEASURED: two pin names of one box that overprint are reported; names that only touch are not."""
    names = (("marking.a", Box(20, 20, 40, 8)), ("marking.b", Box(36, 20, 40, 8)))
    apart = (("marking.a", Box(20, 20, 16, 8)), ("marking.b", Box(36, 20, 40, 8)))
    assert [_codes(_drawing(replace(_symbol("a", Box(1, 1, 10, 10)), slot_ink=ink))) for ink in (names, apart)] == [["OVERLAP"], []]


def test_a_body_beyond_the_content_box_raises_out_of_page():
    planted = _drawing(_symbol("a", Box(95, 0, 10, 10)))
    (found,) = _findings(planted)
    assert found.code == "OUT_OF_PAGE"
    assert "k-a" in found.message


@pytest.mark.parametrize("box", [Box(-3, 0, 4, 2), Box(10, 0, 4, 2), Box(10, 98, 4, 2), Box(0, 10, 4, 2), Box(96, 10, 4, 2)])
def test_a_text_beyond_or_touching_the_content_box_edge_raises_out_of_page(box):
    """KI-195 (R746): a box that touches the edge, not only one that crosses it, is out."""
    assert _codes(_drawing(texts=(DrawnText("T1", box, "designation", "NW"),))) == ["OUT_OF_PAGE"]


@pytest.fixture(scope="module")
def laid():
    model = bank_model(8)
    conventions, kit = house(), box_kit(model)
    problem, _ = build(model, kit, conventions, LIBRARY)
    _, found, drawn = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    return found, drawn


@pytest.mark.rule("KEEP-OUT")
def test_keep_out_bank8_overlaps_do_not_rise(laid):
    """Whole class, ratcheted: members of OVERLAP on bank8 may only fall (pinned at 10)."""
    members = sum(len(page_overlaps(d)) for d in laid[1].values())
    assert members <= 10


@pytest.mark.rule("PAGE-FRAME")
def test_page_frame_bank8_has_nothing_outside_the_content_box(laid):
    """Whole class: every body and text of every page lies inside its content box."""
    assert [f for f in laid[0] if f.code == "OUT_OF_PAGE"] == []


def test_an_annex_tag_on_a_body_raises_overlap_and_beyond_the_page_out_of_page():
    """Annex boxes reach the Drawing as TAG texts (R345), so the text checks read them."""
    body = _symbol("a", Box(1, 1, 10, 10))
    on_body = DrawnText("-K1", Box(2, 2, 4, 2), "TAG", "NW")
    off_page = DrawnText("-K1", Box(98, 0, 6, 2), "TAG", "NW")
    assert _codes(_drawing(body, texts=(on_body,))) == ["OVERLAP"]
    assert _codes(_drawing(texts=(off_page,))) == ["OUT_OF_PAGE"]


def test_a_laid_out_model_draws_its_annexes_as_tag_texts_the_checks_read(laid):
    """The annex boxes of the core layout stand in each page's Drawing as TAG texts."""
    _, drawn = laid
    assert any(t.kind == "TAG" for d in drawn.values() for t in d.texts)


@pytest.mark.parametrize("salt", ["-", "a", "e"])
def test_a_real_build_passes_its_cut_ends_so_a_page_cut_net_is_not_lost(salt):
    """R358 in the real build: a bank cut over pages joins its nets by markers at el's cut ends, at every salt (R1407: lead keeps)."""

    def drawn_findings():
        model = bank_model(40)
        conventions, kit = house(), box_kit(model)
        problem, _ = build(model, kit, conventions, LIBRARY)
        return lay_out_drawn(model, kit, problem, conventions, LIBRARY)

    with id_namespace(salt) if salt != "-" else nullcontext():
        _, found, drawn = drawn_findings()
    assert len(drawn) > 1
    assert [f for f in found if f.code in {"CONNECTION_NOT_DRAWN", "MARKER_UNPLACED"}] == []  # R1506: widen hands every pass's losses to the cut


def test_a_symbol_drawn_at_a_pin_end_over_a_body_raises_overlap_not_anchor_overlap():
    power = DrawnSymbol("pw", "power-24v", 4, 4, "R0", outline=Box(4, 4, 6, 6))
    planted = _drawing(_symbol("a", Box(1, 1, 10, 10)), power)
    (found,) = _findings(planted)
    assert (found.code, "power-24v" in found.message) == ("OVERLAP", True)


MARKER = DrawnSymbol("m", "reference-marker", 10, 12, "R0", outline=Box(10, 10, 6, 4), ports=("P",), net="N")


def _marker_codes(*wires: tuple[Any, ...], dots: tuple[Any, ...] = (), body: bool = False) -> list[str]:
    """The finding codes of a page with the marker above (its port at its origin) and `wires`."""
    symbols = [
        MARKER,
        *(DrawnSymbol("d", "junction-dot", x, y, "R0", outline=Box(x - 1, y - 1, 2, 2)) for x, y in dots),
    ]
    symbols += [_symbol("a", Box(1, 30, 10, 10))] if body else []
    wired = tuple(DrawnWire(f"w{i}", pts, "signal") for i, pts in enumerate(wires))
    drawing = Drawing(Size(100, 100), tuple(symbols), wired, (), (), "v")
    part = replace(_portless_part(drawing), ports={"P": (10, 12)})
    net = Netlist({PAGE: part}, Union(), {}, {}, {}, {})
    return [f.code for f in drawing_invariant_findings(net)]


def test_a_wire_ending_inside_a_marker_box_raises_wire_over_marker_alone():
    assert _marker_codes(((0, 11), (12, 11))) == ["WIRE_OVER_MARKER"]


@pytest.mark.rule("MARKER-FREE-SIDE")
def test_a_wire_ending_exactly_on_a_marker_box_edge_raises_wire_over_marker():
    assert _marker_codes(((30, 11), (16, 11))) == ["WIRE_OVER_MARKER"]


def test_a_wire_crossing_a_marker_box_or_a_dot_in_it_raises_wire_over_marker():
    assert _marker_codes(((12, 0), (12, 30))) == ["WIRE_OVER_MARKER"]
    assert _marker_codes(dots=((13, 11),)) == ["WIRE_OVER_MARKER"]


def test_the_wire_that_ends_at_the_markers_own_port_and_a_far_wire_raise_nothing():
    assert _marker_codes(((0, 12), (10, 12)), ((40, 0), (40, 50)), dots=((60, 60),)) == []


@pytest.mark.rule("MARKER-FREE-SIDE")
def test_a_wire_that_runs_through_its_own_markers_box_before_its_port_raises_wire_over_marker():
    assert _marker_codes(((12, 0), (12, 12), (10, 12))) == ["WIRE_OVER_MARKER"]
    assert _marker_codes(((12, 0), (12, 30), (0, 30), (0, 12), (10, 12))) == ["WIRE_OVER_MARKER"]
    assert _marker_codes(((0, 12), (10, 12))) == []


@pytest.mark.rule("MARKER-FREE-SIDE")
def test_an_entry_segment_along_the_marker_box_edge_is_exempt_but_one_through_the_interior_is_not():
    assert _marker_codes(((10, 10), (10, 12))) == []  # R2101: ends at the port, runs along the west edge
    assert _marker_codes(((12, 8), (12, 12), (10, 12))) == ["WIRE_OVER_MARKER"]


def test_a_wire_through_a_body_that_is_no_marker_is_still_overlap():
    assert _marker_codes(((5, 25), (5, 45)), body=True) == ["OVERLAP"]


def _head_codes(*wires: tuple[Any, ...], key: str = "contact-head") -> list[str]:
    """The finding codes of a page with a box at (20, 20, 20, 10) of `key` and `wires`."""
    box = Box(20, 20, 20, 10)
    wired = tuple(DrawnWire(f"w{i}", pts, "signal") for i, pts in enumerate(wires))
    drawing = Drawing(Size(100, 100), (DrawnSymbol("h", key, 20, 20, "R0", outline=box),), wired, (), (), "v")
    return _codes({PAGE: drawing})


@pytest.mark.rule("TAG-CORNERS")
def test_a_wire_sharing_interior_with_a_table_head_raises_overlap_ending_inside_or_across():
    assert _head_codes(((0, 25), (30, 25))) == ["OVERLAP"]
    assert _head_codes(((0, 25), (60, 25))) == ["OVERLAP"]


@pytest.mark.rule("TAG-CORNERS")
def test_a_wire_running_along_a_table_heads_edge_raises_overlap_one_per_wire_and_a_corner_touch_is_clear():
    """R1828, layout-0556: an edge run counts as `core.through` says (R1135, R1164); a zero-length corner touch stays clear (R976, R977)."""
    assert _head_codes(((0, 20), (60, 20))) == ["OVERLAP"]
    assert _head_codes(((0, 20), (60, 20)), ((40, 0), (40, 60))) == ["OVERLAP", "OVERLAP"]
    assert _head_codes(((0, 30), (20, 30)), ((40, 30), (60, 30))) == []


@pytest.mark.rule("TAG-CORNERS")
def test_a_diagonal_wire_through_a_body_a_marker_or_a_text_raises_its_finding():
    """R1828: a diagonal segment is the true segment, not a horizontal at its first y."""
    assert _head_codes(((0, 0), (60, 60))) == ["OVERLAP", "WIRE_NOT_ORTHOGONAL"]
    assert _head_codes(((0, 40), (20, 30))) == ["WIRE_NOT_ORTHOGONAL"]  # ends at the corner, no length inside
    assert _marker_codes(((0, 0), (30, 30))) == ["WIRE_OVER_MARKER", "WIRE_NOT_ORTHOGONAL"]
    text = DrawnText("T1", Box(20, 20, 20, 10), "designation", "NW")
    drawing = Drawing(Size(100, 100), (), (DrawnWire("w", ((0, 0), (60, 60)), "signal"),), (text,), (), "v")
    assert _codes({PAGE: drawing}) == ["OVERLAP", "WIRE_NOT_ORTHOGONAL"]


def test_a_wire_ending_inside_an_ordinary_body_not_at_its_pin_raises_overlap():
    assert _head_codes(((0, 25), (30, 25)), key="k-a") == ["OVERLAP"]


def _dot_page(dot_at: tuple[int, int], pin_at: tuple[int, int]) -> list[str]:
    """OVERLAP members of a terminal body whose pin is at `pin_at` and a dot at `dot_at`."""
    body = DrawnSymbol("t", "terminal", 0, 0, "R0", outline=Box(0, 0, 10, 10), ports=("P",))
    dot = DrawnSymbol("d", "junction-dot", *dot_at, "R0", outline=Box(dot_at[0] - 1, dot_at[1] - 1, 2, 2))
    return page_overlaps(_drawing(body, dot)[PAGE], {"P": pin_at})


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_dot_on_its_symbols_own_pin_point_is_no_overlap():
    assert _dot_page((5, 0), (5, 0)) == []


def test_a_dot_off_the_pin_point_or_on_another_symbols_pin_still_overlaps():
    assert _dot_page((5, 5), (5, 0)) == ["terminal / junction-dot"]
    assert _dot_page((5, 5), (7, 7)) == ["terminal / junction-dot"]
