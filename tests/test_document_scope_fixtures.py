"""`document_scope` on the fixture documents: the pdf sites' former selections (RO-1 part A).

EXPECTED is the base probe's output (`claude-tools/ro1_scope_probe.py`, run on the commit before
the swap): the demo cabinet, the units worked example and the demo skid.
"""

import importlib.util
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import cabinet_document, system_document
from demo_designs import cabinet_design
from document_scope_probe import cases, check, document_scope, names, subject
from fransys_author.design import Design
from test_units_worked_example import _system_design

from fransys_model.derive import bom_lines
from fransys_model.derive.bom import TOP_LEVEL
from fransys_model.vocab.tables import aspect_nodes, units

SKID = Path(__file__).resolve().parent.parent / "examples" / "demo-skid" / "skid.py"

EXPECTED = {
    "cabinet": {
        "system": {
            "unit": None,
            "cables": ("W1",),
            "harnesses": (),
            "bom_scope": "TOP_LEVEL",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:group/SUP": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "group/SUP",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:location/C1": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "location/C1",
            "strips": ("X1",),
            "connector_items": [],
            "boards": (),
        },
        "item:W1": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "W1",
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
    },
    "worked": {
        "system": {
            "unit": None,
            "cables": ("WM1", "WM1S", "WM2", "WM2S"),
            "harnesses": (),
            "bom_scope": "TOP_LEVEL",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "unit:pump1/io/unit": {
            "unit": "pump1/io/unit",
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump1/io/unit",
            "strips": (),
            "connector_items": ["pump1/io/X1"],
            "boards": (),
        },
        "unit:pump1/unit": {
            "unit": "pump1/unit",
            "cables": ("pump1/w1c",),
            "harnesses": (),
            "bom_scope": "pump1/unit",
            "strips": ("pump1/X2",),
            "connector_items": [],
            "boards": (),
        },
        "unit:pump2/unit": {
            "unit": "pump2/unit",
            "cables": ("pump2/w1c",),
            "harnesses": (),
            "bom_scope": "pump2/unit",
            "strips": ("pump2/X2",),
            "connector_items": [],
            "boards": (),
        },
        "unit:pump2/io/unit": {
            "unit": "pump2/io/unit",
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump2/io/unit",
            "strips": (),
            "connector_items": ["pump2/io/X1"],
            "boards": (),
        },
        "location:pump2/location/C2": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump2/location/C2",
            "strips": ("pump2/X2",),
            "connector_items": ["pump2/io/X1"],
            "boards": (),
        },
        "location:pump2/io/group/BRD": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump2/io/group/BRD",
            "strips": (),
            "connector_items": ["pump2/io/X1"],
            "boards": (),
        },
        "location:location/ER": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "location/ER",
            "strips": ("pump1/X2", "pump2/X2"),
            "connector_items": ["pump1/io/X1", "pump2/io/X1"],
            "boards": (),
        },
        "location:group/FLD": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "group/FLD",
            "strips": (),
            "connector_items": ["K1"],
            "boards": (),
        },
        "item:WM1": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "WM1",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:WM1S": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "WM1S",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:WM2": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "WM2",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:WM2S": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "WM2S",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:pump1/X2": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump1/X2",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:pump1/io/board": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump1/io/board",
            "strips": (),
            "connector_items": [],
            "boards": ("pump1/io/board",),
        },
        "item:pump1/w1c": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump1/w1c",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:pump2/io/board": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump2/io/board",
            "strips": (),
            "connector_items": [],
            "boards": ("pump2/io/board",),
        },
        "item:pump2/w1c": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "pump2/w1c",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
    },
    "skid": {
        "system": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "TOP_LEVEL",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:location/CAB": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "location/CAB",
            "strips": ("U1/X3", "U1/X10", "U1/X11"),
            "connector_items": [],
            "boards": (),
        },
        "location:U1/group/G1": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "U1/group/G1",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:U1/group/G5": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "U1/group/G5",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:U1/group/G0": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "U1/group/G0",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:U1/X3": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "U1/X3",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
    },
}

BUILT = {"cabinet", "worked", "skid"}


@pytest.fixture(scope="module")
def models():
    """The three fixture models, built once for the module."""
    parts = fransys_parts.load("demo_parts")
    built = {}
    for name, design in (("cabinet", cabinet_design(parts)),):
        document = cabinet_document(Design(parts).location("C1", "Demo cabinet"))
        built[name] = fr.build(parts, design.draft(), document).model
    design, _field1, _field2 = _system_design(parts)
    built["worked"] = fr.build(parts, design.draft(), system_document()).model
    spec = importlib.util.spec_from_file_location("demo_skid_design", SKID)
    assert spec is not None
    assert spec.loader is not None
    skid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skid)
    skid_design, skid_document = skid.design()
    built["skid"] = fr.build(fr.parts("demo_parts"), skid_design.draft(), skid_document).model
    return built


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "unit", BUILT))
def test_unit_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.unit` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "unit", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "cables", BUILT))
def test_cables_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.cables` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "cables", want)


@pytest.mark.parametrize(("model_name", "label", "want"), cases(EXPECTED, "harnesses", BUILT))
def test_harnesses_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.harnesses` equals the pdf sites' former selection (RO-1 part A)."""
    check(models, model_name, label, "harnesses", want)


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


def test_a_unit_document_reads_its_unit_cables_and_a_system_document_the_top_level_ones(models):
    model = models["worked"]
    unit = document_scope(model, subject(model, "unit:pump1/unit"))
    system = document_scope(model, subject(model, "system"))
    assert unit.unit is not None
    assert names(model, [c.cable for c in unit.cables]) == ("pump1/w1c",)
    assert system.unit is None
    assert names(model, [c.cable for c in system.cables]) == ("WM1", "WM1S", "WM2", "WM2S")
    assert system.bom_scope is TOP_LEVEL


def _bought_elsewhere(model):
    """The parts the system's top-level BOM and every unit's own BOM list."""
    scopes = [TOP_LEVEL, *units(model)]
    return {line.part for scope in scopes for line in bom_lines(model, scope) if line.part}


@pytest.mark.parametrize("model_name", ["worked", "skid"])
def test_every_bom_line_a_location_document_drops_is_in_another_bom(models, model_name):
    """Pdf-0043 guard: a part a location BOM leaves out is still bought by the system or a unit."""
    model = models[model_name]
    elsewhere = _bought_elsewhere(model)
    dropped = set()
    for node, record in aspect_nodes(model).items():
        scope = document_scope(model, subject(model, "location:" + "/".join(map(str, record.key))))
        full = {line.part: line.count for line in bom_lines(model, node)}
        kept = {line.part: line.count for line in bom_lines(model, node, without=scope.bom_without)}
        dropped |= {part for part, count in full.items() if part and kept.get(part, 0) < count}
    assert dropped <= elsewhere
