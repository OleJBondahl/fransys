"""`document_scope`: one document's selections, against the pdf sites' former choices (RO-1).

EXPECTED is the base probe's output (`claude-tools/ro1_scope_probe.py`, run before the swap) for
a loose plug pair, a cable and a terminal strip: names are authoring
"""

import fransys as fr
import pytest
from document_scope_probe import cases, check, document, document_scope
from fransys.colours import BU

from fransys_model.derive.bom import TOP_LEVEL
from fransys_model.vocab import DocumentPreset

EXPECTED = {
    "loose_design": {
        "system": {
            "unit": None,
            "cables": ("LOOSE/cc",),
            "harnesses": (),
            "bom_scope": "TOP_LEVEL",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:location/L0": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "location/L0",
            "strips": ("X1",),
            "connector_items": ["LOOSE/LA1", "LOOSE/LA2"],
            "boards": (),
        },
        "location:group/LOOSE": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "group/LOOSE",
            "strips": (),
            "connector_items": ["LOOSE/LA1", "LOOSE/LA2"],
            "boards": (),
        },
        "item:LOOSE/cc": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "LOOSE/cc",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:X1": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "X1",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
    }
}

BUILT = {"loose_design"}


@pytest.fixture(scope="module")
def models():
    """One design: a loose plug pair with a cable and a wire, and a terminal strip at L0."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("LOOSE", "Loose"):
        a = d.device("LA1", "DEMO-CONN-2P", place="L0")
        b = d.device("LA2", "DEMO-CONN-2P", place="L0")
        d.cable("CBL", "DEMO-CBL-4G1.5", name="cc", place="L0").core(1, a[1], b[1])
    d.series(a[2], b[2], wire=(BU, 0.5))
    with d.function("STRIP", "Strip"):
        d.terminal_strip("X1", "DEMO-TB-2.5", 2, place="L0")
    return {"loose_design": fr.build(d).model}


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "unit", BUILT))
def test_unit_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.unit` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "unit", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "cables", BUILT))
def test_cables_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.cables` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "cables", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "bom_scope", BUILT))
def test_bom_scope_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.bom_scope` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "bom_scope", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "strips", BUILT))
def test_strips_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.strips` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "strips", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "connector_items", BUILT))
def test_connector_items_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.connector_items` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "connector_items", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "boards", BUILT))
def test_boards_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.boards` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "boards", want)


def test_a_system_document_has_no_unit_and_the_top_level_scope(models):
    model = models["loose_design"]
    scope = document_scope(model, document("s", DocumentPreset.SYSTEM))
    assert scope.unit is None
    assert scope.bom_scope is TOP_LEVEL


def test_a_system_document_leaves_nothing_out(models):
    model = models["loose_design"]
    assert document_scope(model, document("s", DocumentPreset.SYSTEM)).bom_without == ()
