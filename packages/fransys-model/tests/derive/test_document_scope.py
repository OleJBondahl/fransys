"""`document_scope`: one document's selections, against the pdf sites' former choices (RO-1).

EXPECTED is the base probe's output (`claude-tools/ro1_scope_probe.py`, run before the swap) for
the harness shapes of `test_cable_drawing_wires.py` plus a terminal strip: names are authoring
keys. `cable_list` disagrees with `cables` for a location or item document (model-0268). A
location document's `connector_items` leave out the plugs of the harnesses it does not draw
(pdf-0043); the base probe listed them.
"""

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import bom_lines, document_scope
from fransys_model.derive.bom import TOP_LEVEL
from fransys_model.kernel import make_id
from fransys_model.vocab import Document, DocumentPreset
from fransys_model.vocab.tables import aspect_nodes, items, units

_PLUG4 = "DEMO-CONN-4P"
_PLUG2 = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"

EXPECTED = {
    "harness_wires": {
        "system": {
            "unit": None,
            "cables": ("BARE/cbare", "MIX/cmix"),
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
        "location:group/BARE": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "group/BARE",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "location:group/LINK": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "group/LINK",
            "strips": (),
            "connector_items": [],
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
        "item:BARE/cbare": {
            "unit": None,
            "cables": (),
            "harnesses": (),
            "bom_scope": "BARE/cbare",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:LINK/LINK": {
            "unit": None,
            "cables": (),
            "harnesses": ("LINK/LINK",),
            "bom_scope": "LINK/LINK",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:MIX/MIX": {
            "unit": None,
            "cables": ("MIX/cmix",),
            "harnesses": (),
            "bom_scope": "MIX/MIX",
            "strips": (),
            "connector_items": [],
            "boards": (),
        },
        "item:ONLY/ONLY": {
            "unit": None,
            "cables": (),
            "harnesses": ("ONLY/ONLY",),
            "bom_scope": "ONLY/ONLY",
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

BUILT = {"harness_wires"}


def _mixed(d):
    with d.function("MIX", "Mixed loom"):
        loom = d.harness("MIX", place="L0")
        near = d.device("J1", _PLUG4, parent=loom, place="L0")
        far = d.device("J2", _PLUG4, parent=loom, place="L0")
        d.cable("MIX", _CABLE, parent=loom, name="cmix", place="L0").core(1, near[1], far[1])
        d.detail.wire(near[2], far[2], wire=(BU, 0.5), label="SIG")
        d.detail.wire(near[3], far[3], wire=(BU, 1.5))


def _only(d):
    with d.function("ONLY", "Wire-only loom"):
        loom = d.harness("ONLY", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.detail.wire(near[1], far[1], wire=(BU, 0.5))
    with d.function("LINK", "Link loom"):
        loom = d.harness("LINK", place="L0")
        plug = d.device("J1", _PLUG2, parent=loom, place="L0")
        d.detail.wire(plug[1], plug[2], wire=(BU, 0.5))


def _bare(d):
    with d.function("BARE", "Bare loom"):
        loom = d.harness("BARE", place="L0")
        near = d.device("J1", _PLUG2, parent=loom, place="L0")
        far = d.device("J2", _PLUG2, parent=loom, place="L0")
        d.cable("BARE", _CABLE, parent=loom, name="cbare", place="L0").core(1, near[1], far[1])
    with d.function("LOOSE", "Loose"):
        a = d.device("LA1", _PLUG2, place="L0")
        b = d.device("LA2", _PLUG2, place="L0")
    d.detail.wire(a[1], b[1], wire=(BU, 0.5))


@pytest.fixture(scope="module")
def models():
    """One design: every harness shape, a loose plug pair and a terminal strip at L0."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _mixed(d)
    _only(d)
    _bare(d)
    with d.function("STRIP", "Strip"):
        d.terminal_strip("X1", "DEMO-TB-2.5", 2, place="L0")
    return {"harness_wires": fr.build(d).model}


def _name(model, id_):
    """The authoring key of an item, unit or aspect node id, joined by `/`."""
    if id_ is None:
        return None
    table = {"item": items, "unit": units, "aspect_node": aspect_nodes}[id_.kind]
    return "/".join(str(k) for k in table(model)[id_].key)


def _names(model, ids):
    return tuple(_name(model, i) for i in ids)


def _document(label, preset, *, location=None, item=None, unit=None):
    key = ("probe", label)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=preset,
        location=location,
        item=item,
        add=(),
        remove=(),
        cover="",
        notes=None,
        unit=unit,
    )


def _subject(model, label):
    """The probe's `Document` for `label`: `system`, or `unit:`, `location:`, `item:` + key."""
    kind, _, key = label.partition(":")
    if kind == "system":
        return _document(label, DocumentPreset.SYSTEM)
    table = {"unit": units, "location": aspect_nodes, "item": items}[kind]
    found = next(i for i, r in table(model).items() if "/".join(str(k) for k in r.key) == key)
    preset = DocumentPreset.PCB_SCHEMATIC if kind == "item" else DocumentPreset.CABINET_SCHEMATIC
    return _document(
        label,
        preset,
        location=found if kind == "location" else None,
        item=found if kind == "item" else None,
        unit=found if kind == "unit" else None,
    )


def _field(model, scope, field):
    value = getattr(scope, field)
    if field == "unit":
        return _name(model, value)
    if field == "bom_scope":
        return "TOP_LEVEL" if value is TOP_LEVEL else _name(model, value)
    if field == "cables":
        return _names(model, [c.cable for c in value])
    return (
        tuple(sorted(_names(model, value))) if field == "connector_items" else _names(model, value)
    )


def _cases(field, built):
    return [
        (m, d, sel[field]) for m, docs in EXPECTED.items() for d, sel in docs.items() if m in built
    ]


def _check(models, model_name, label, field, want):
    model = models[model_name]
    got = _field(model, document_scope(model, _subject(model, label)), field)
    want = tuple(want) if isinstance(want, list) else want
    assert got == want, (model_name, label, field)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("unit", BUILT))
def test_unit_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.unit` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "unit", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("cables", BUILT))
def test_cables_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.cables` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "cables", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("harnesses", BUILT))
def test_harnesses_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.harnesses` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "harnesses", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("bom_scope", BUILT))
def test_bom_scope_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.bom_scope` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "bom_scope", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("strips", BUILT))
def test_strips_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.strips` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "strips", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("connector_items", BUILT))
def test_connector_items_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.connector_items` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "connector_items", want)


@pytest.mark.parametrize(("model_name", "label", "want"), _cases("boards", BUILT))
def test_boards_matches_the_old_pdf_selection(models, model_name, label, want):
    """`DocumentScope.boards` equals the pdf sites' former selection (RO-1 part A)."""
    _check(models, model_name, label, "boards", want)


def test_a_system_document_has_no_unit_and_the_top_level_scope(models):
    model = models["harness_wires"]
    scope = document_scope(model, _document("s", DocumentPreset.SYSTEM))
    assert scope.unit is None
    assert scope.bom_scope is TOP_LEVEL


def test_a_location_document_leaves_out_every_harness_item_it_does_not_draw(models):
    """`bom_without` holds each loom and its plugs and cables; the loose connectors stay."""
    model = models["harness_wires"]
    scope = document_scope(model, _subject(model, "location:location/L0"))
    left_out = set(_names(model, scope.bom_without))
    assert {
        "MIX/MIX",
        "MIX/J1",
        "MIX/cmix",
        "ONLY/ONLY",
        "ONLY/J2",
        "LINK/LINK",
        "BARE/BARE",
        "BARE/cbare",
    } <= left_out
    assert not {"LOOSE/LA1", "LOOSE/LA2"} & left_out


def test_a_system_document_leaves_nothing_out(models):
    model = models["harness_wires"]
    assert document_scope(model, _document("s", DocumentPreset.SYSTEM)).bom_without == ()


@pytest.mark.parametrize("whole_model", [False, True])
def test_bom_lines_leave_out_the_items_it_is_told_to(models, whole_model):
    """`without=` removes exactly the named items' counts, for a location scope and for `None`."""
    model = models["harness_wires"]
    scope = document_scope(model, _subject(model, "location:location/L0"))
    node = None if whole_model else scope.bom_scope

    def counted(**kw):
        return sum(line.count for line in bom_lines(model, node, **kw))

    named = [i for i in scope.bom_without if items(model)[i].part is not None]
    assert named
    assert counted() - counted(without=scope.bom_without) >= len(named)
    assert counted(without=()) == counted()
