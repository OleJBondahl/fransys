"""`lay_out_drawn` returns the page `Drawing` values beside `lay_out`'s model (el-0039, R228)."""

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out, lay_out_drawn
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY, library_version
from fransys_layout.core import Size
from fransys_model.derive import ordered_pages

AREA = Size(1312, 854)  # the default sheet's content box in G


@pytest.fixture(scope="module")
def laid():
    model = bank_model(8)
    conventions, kit = house(), box_kit(model)
    problem, _ = build(model, kit, conventions, LIBRARY)
    args = (model, kit, problem, conventions, LIBRARY)
    return model, lay_out(*args), lay_out_drawn(*args)


def test_the_model_and_findings_equal_lay_outs(laid):
    _, (plain, found), (model, more, _, _) = laid
    assert model == plain
    assert more[: len(found)] == found  # the drawing invariants append their own findings


def test_the_pages_come_in_print_order_with_the_content_box_and_library(laid):
    _, _, (model, _, drawn, _) = laid
    assert drawn
    assert list(drawn) == [p.id for p in ordered_pages(model) if p.id in drawn]
    for page in ordered_pages(model):
        if page.id in drawn:
            assert drawn[page.id].area == AREA
            assert drawn[page.id].library_version == library_version()


def test_the_symbol_ids_are_unique_render_ids(laid):
    _, _, (_, _, drawn, _) = laid
    ids = [s.id for d in drawn.values() for s in d.symbols]
    assert ids
    assert len(set(ids)) == len(ids)
    assert all(isinstance(i, str) and i for i in ids)


def test_two_runs_over_the_same_model_draw_the_same_pages():
    model = bank_model(8)
    conventions = house()

    def run():
        kit = box_kit(model)
        problem, _ = build(model, kit, conventions, LIBRARY)
        return lay_out_drawn(model, kit, problem, conventions, LIBRARY)[2]

    assert run() == run()
