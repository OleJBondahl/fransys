"""OVERLAP and OUT_OF_PAGE over finished drawings (DRAWING-INVARIANTS, R323).

Each code has a clean drawing that raises nothing and a drawing with one planted defect.
"""

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_drawn
from fransys_el.drawing_invariants import drawing_invariant_findings, page_overlaps
from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import Netlist, _part
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, Size
from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnText
from fransys_model.kernel import Id, Severity

PAGE = Id(kind="page", value="page-1")


def _symbol(sid: str, box: Box) -> DrawnSymbol:
    return DrawnSymbol(sid, "k-" + sid, box.x, box.y, "R0", outline=box)


def _drawing(*symbols: DrawnSymbol, texts: tuple[DrawnText, ...] = ()) -> dict:
    return {PAGE: Drawing(Size(100, 100), symbols, (), (), texts, (), "v")}


def _findings(drawings) -> tuple:
    """The page invariants over drawings with no ports: a Netlist built from their geometry."""
    pages = {page: _part(drawing, {}, LIBRARY) for page, drawing in drawings.items()}
    return drawing_invariant_findings(Netlist(pages, Union(), {}, {}, {}, {}))


def _codes(drawings) -> list[str]:
    return [f.code for f in _findings(drawings)]


def test_a_clean_page_raises_nothing():
    clean = _drawing(_symbol("a", Box(0, 0, 10, 10)), _symbol("b", Box(10, 0, 10, 10)))
    assert _codes(clean) == []


def test_two_bodies_with_shared_area_raise_overlap_naming_both_keys():
    planted = _drawing(_symbol("a", Box(0, 0, 10, 10)), _symbol("b", Box(5, 5, 10, 10)))
    (found,) = _findings(planted)
    assert found.code == "OVERLAP"
    assert found.severity is Severity.WARNING
    assert "k-a / k-b" in found.message


def test_a_text_on_a_body_raises_overlap():
    text = DrawnText("T1", Box(2, 2, 4, 2), "designation", "NW")
    planted = _drawing(_symbol("a", Box(0, 0, 10, 10)), texts=(text,))
    assert _codes(planted) == ["OVERLAP"]


def test_a_body_beyond_the_content_box_raises_out_of_page():
    planted = _drawing(_symbol("a", Box(95, 0, 10, 10)))
    (found,) = _findings(planted)
    assert found.code == "OUT_OF_PAGE"
    assert "k-a" in found.message


def test_a_text_beyond_the_content_box_raises_out_of_page():
    text = DrawnText("T1", Box(-3, 0, 4, 2), "designation", "NW")
    assert _codes(_drawing(texts=(text,))) == ["OUT_OF_PAGE"]


@pytest.fixture(scope="module")
def laid():
    model = bank_model(8)
    conventions, kit = house(), box_kit(model)
    problem, _ = build(model, kit, conventions, LIBRARY)
    _, found, drawn, _ = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
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
    body = _symbol("a", Box(0, 0, 10, 10))
    on_body = DrawnText("-K1", Box(2, 2, 4, 2), "TAG", "NW")
    off_page = DrawnText("-K1", Box(98, 0, 6, 2), "TAG", "NW")
    assert _codes(_drawing(body, texts=(on_body,))) == ["OVERLAP"]
    assert _codes(_drawing(texts=(off_page,))) == ["OUT_OF_PAGE"]


def test_a_laid_out_model_draws_its_annexes_as_tag_texts_the_checks_read(laid):
    """The annex boxes of the core layout stand in each page's Drawing as TAG texts."""
    _, drawn = laid
    assert any(t.kind == "TAG" for d in drawn.values() for t in d.texts)


def test_a_real_build_passes_its_cut_ends_so_a_page_cut_net_is_not_lost():
    """R358 in the real build: a bank cut over pages joins its nets by markers at el's cut ends."""
    model = bank_model(40)
    conventions, kit = house(), box_kit(model)
    problem, _ = build(model, kit, conventions, LIBRARY)
    _, found, drawn, _ = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    assert len(drawn) > 1
    assert [f for f in found if f.code == "CONNECTION_NOT_DRAWN"] == []


def test_a_symbol_drawn_at_a_pin_end_over_a_body_raises_overlap_not_anchor_overlap():
    power = DrawnSymbol("pw", "power-24v", 4, 4, "R0", outline=Box(4, 4, 6, 6))
    planted = _drawing(_symbol("a", Box(0, 0, 10, 10)), power)
    (found,) = _findings(planted)
    assert (found.code, "power-24v" in found.message) == ("OVERLAP", True)
