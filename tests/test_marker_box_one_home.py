"""layout-0406, el-0073: a marker's drawn box has one home on all builds (R554, R555 B4, R557).

Layout's `marker_drawn_box` (from `Options.link_fit`) holds the outline el draws by
`marker_rule` (equal for a stub, a tag's own-text box inside it); `link_fit` equals the rule at its own size; the PDF link area is that outline
"""

import importlib.util

import pytest
from _marker_box_checks import marker_box_facts
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS


@pytest.fixture(scope="module", params=CASE_PARAMS)
def facts(request: pytest.FixtureRequest):
    return marker_box_facts(BUILDS[request.param])


def test_layouts_drawn_box_is_the_outline_el_draws(facts) -> None:
    assert facts
    assert all(f.matched for f in facts)


def test_link_fit_is_the_marker_rules_box(facts) -> None:
    assert all(f.fit_ok for f in facts if f.fit_ok is not None)


def test_the_pdf_link_area_is_the_outline_one_gap_out(facts) -> None:
    assert all(f.pdf_ok for f in facts if f.pdf_ok is not None)
    assert any(f.pdf_ok for f in facts)


def test_the_model_derive_has_no_marker_box() -> None:
    from fransys_model import derive

    assert not hasattr(derive, "marker_box")
    assert importlib.util.find_spec("fransys_model.derive.marker_box") is None
