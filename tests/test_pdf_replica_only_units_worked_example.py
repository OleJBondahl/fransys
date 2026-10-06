"""`fransys_pdf`'s replica-only drawing-set skip rule (STEP 4 addition,
`.fransys/WORK-ORDER-UNIT-DOCUMENTS.md`'s "STEP 2b RULING AND A STEP 4 ADDITION"), proven
against the units worked example's own real, facade-built geometry -- not a hand-built layout
fixture. `packages/fransys-pdf/tests/test_replica_only.py` proves the predicate's logic
directly against hand-built `layout.*` records (the package's own unit of testing); this file
proves the real worked example actually has the shape that predicate assumes, and that a real
author-level rewiring flips it, both on `fr.build`'s own output.
"""

import sys
from decimal import Decimal
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by
# name: `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fransys_pdf import check, source
from fransys_pdf._drawings import replica_only_sets, schematic_pages
from fransys_pdf._lists import _boards_for, _terminal_strips_for, bom_page
from fransys_render import pages as render_pages
from test_units_worked_example import _PROJECT, io_board

from fransys_model.derive import unit_release, units
from fransys_model.kernel import Origin, Severity, evolve, make_id
from fransys_model.layout import SymbolPlacement
from fransys_model.layout import layout_of as layout_of_model
from fransys_model.vocab import Document, DocumentPreset, Item, PageKind, PartCategory, documents
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import items as items_table
from fransys_model.vocab.tables import units as units_table
from fransys_model.vocab.templates import Part

_REPLICA_ONLY_SET_COUNT = 2
_IO_BOARD_COUNT = 1  # a `demo-io-board` unit's own single board
_CABINET_OWN_STRIP_COUNT = 1  # a `demo-pump-cabinet` unit's own single strip, X2
_UNWIRED_FIELD_TERMINALS = 2  # the first two field terminals; a third is wired to a neighbour
_ORIGIN = Origin(
    file="tests/test_pdf_replica_only_units_worked_example.py", line=1, note="STEP 4 addition"
)


def pump_cabinet(s, *, name, extra_unitless_neighbor=False):
    """Adapted from `test_units_worked_example.pump_cabinet`: same shape, plus an optional
    third field terminal wired to a brand-new unitless item at the cabinet's own location --
    can-fail 1's own fixture ("add one conductor from a replica to unitless content").
    """
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    count = 3 if extra_unitless_neighbor else 2
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(count)]
    board_x1, _ = io_board(u.scope("io", at=c))
    w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
    p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
    cable.core(1, field[0].outer, p1["1"])
    cable.core(2, field[1].outer, p1["2"])
    u.mate(p1, board_x1)
    for index, t in enumerate(field):
        u.boundary(t)
        if index < _UNWIRED_FIELD_TERMINALS:
            u.unused(t)  # nothing crosses it: declared, so no BOUNDARY_UNCONNECTED
    if extra_unitless_neighbor:
        neighbor = s.item("DEMO-CONN-2P", tag="P9", at=c, group=grp)
        wire = s.wiring(colour="BU", gauge="0.5")
        wire(field[2].outer, neighbor["1"])
    return c, field


def _build(*, name1="C1", name2="C2", extra_unitless_neighbor=False):
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    c1, _field1 = pump_cabinet(
        d.scope("pump1", at=er), name=name1, extra_unitless_neighbor=extra_unitless_neighbor
    )
    c2, _field2 = pump_cabinet(d.scope("pump2", at=er), name=name2)
    result = fr.build(parts, d.draft(), system_document())
    # An `ERROR` stops `build` before layout (decision 0028): no `layout.*` record to measure.
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    return result.model, c1.id, c2.id


def _with_documents(model, *location_ids):
    docs = [
        Document(
            id=make_id(Document, ("probe-doc", str(index))),
            key=("probe-doc", str(index)),
            preset=DocumentPreset.CABINET_SCHEMATIC,
            location=location_id,
            item=None,
            add=(),
            remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
            cover="# Cover",
            notes=None,
        )
        for index, location_id in enumerate(location_ids)
    ]
    return evolve(model, put=docs, origin=_ORIGIN), docs


def test_the_worked_examples_two_top_level_sets_are_replica_only_with_one_info_each():
    """The real geometry `_is_replica_only_undrawn` assumes: both cabinets' top-level (unit=
    None) drawing sets hold only their own two field-terminal boundary replicas, no other
    placement, no route, no marker -- confirmed here by count, not assumed by a hand-built
    fixture (`_REPLICA_ONLY_SET_COUNT` is the work order's own "two in the system build, one
    per cabinet location")."""
    model, c1_id, c2_id = _build()
    model, docs = _with_documents(model, c1_id, c2_id)
    records = documents(model)
    for doc in docs:
        record = records[doc.id]
        assert schematic_pages(model, record, (PageKind.SCHEMATIC,)) == ()
        assert len(replica_only_sets(model, record, (PageKind.SCHEMATIC,))) == 1
    findings = check(model, {})
    replica_findings = [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"]
    assert len(replica_findings) == _REPLICA_ONLY_SET_COUNT
    expected_messages = {
        "drawing set +ER+C1 holds only black-box replicas: not drawn",
        "drawing set +ER+C2 holds only black-box replicas: not drawn",
    }
    for finding in replica_findings:
        assert finding.severity is Severity.INFO
        assert finding.message in expected_messages
    assert [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []


def test_a_real_rewired_replica_boundary_draws_its_set_and_drops_the_info():
    """Can-fail 1, on real geometry: rebuilding with a third field terminal on pump1's own
    cabinet, wired to a brand-new unitless item at the same location (units spec U2's "an
    ordinary same-set connection"), makes pump1's top-level set a real page -- pump2's own,
    untouched, stays replica-only, so this is a genuine behavioural difference for one
    cabinet, not a global flag flip.
    """
    model, c1_id, c2_id = _build(extra_unitless_neighbor=True)
    model, docs = _with_documents(model, c1_id, c2_id)
    records = documents(model)
    doc_c1, doc_c2 = docs
    record_c1 = records[doc_c1.id]
    record_c2 = records[doc_c2.id]

    pages_c1 = schematic_pages(model, record_c1, (PageKind.SCHEMATIC,))
    assert len(pages_c1) >= 1
    assert replica_only_sets(model, record_c1, (PageKind.SCHEMATIC,)) == ()

    assert schematic_pages(model, record_c2, (PageKind.SCHEMATIC,)) == ()
    assert len(replica_only_sets(model, record_c2, (PageKind.SCHEMATIC,))) == 1

    findings = check(model, {})
    replica_findings = [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"]
    assert len(replica_findings) == 1
    assert replica_findings[0].subjects[0] == doc_c2.id


def _unit_by_name_and_prefix(model, *, name, prefix):
    """The one unit of `model` named `name` whose own key starts with `prefix` (units spec U6).

    `_build()` instantiates `demo-pump-cabinet` and, nested in it, `demo-io-board` once per
    cabinet (`pump1`, `pump2`); both units of one name are real content, so this also proves
    the fix picks exactly the intended unit, not "the first one found".
    """
    all_units = units_table(model)
    return next(
        unit_id
        for unit_id in sorted(units(model))
        if unit_release(model, unit_id).name == name and all_units[unit_id].key[0] == prefix
    )


def test_a_units_own_documents_scope_their_lists_to_that_unit_directly():
    """`fransys_pdf._lists._boards_for`/`_terminal_strips_for` (units spec U6, decision
    pdf-0006), proven on the worked example's real, facade-built geometry: a unit document's
    TERMINAL_LIST/CONNECTOR_LIST cover only items whose own `Item.unit` is that unit,
    directly -- never the recursive subtree.

    This is also the crash the fix closes: before it, `_boards_for` asserted the document's
    `location` was not `None`, which a unit-subject `pcb_schematic` document -- exactly
    `io_board`'s own worked-example shape -- violates, so `source()` raised `AssertionError`
    for `io_doc` below. `PageKind.SCHEMATIC` is removed from both documents so the unrelated
    missing-SVG concern of a real drawing page never masks that.
    """
    model, _c1_id, _c2_id = _build()
    io_unit_id = _unit_by_name_and_prefix(model, name="demo-io-board", prefix="pump1")
    cabinet_unit_id = _unit_by_name_and_prefix(model, name="demo-pump-cabinet", prefix="pump1")

    io_doc = Document(
        id=make_id(Document, ("probe-doc", "io")),
        key=("probe-doc", "io"),
        preset=DocumentPreset.PCB_SCHEMATIC,
        location=None,
        item=None,
        unit=io_unit_id,
        add=(),
        remove=(PageKind.SCHEMATIC,),
        cover="# Cover",
        notes=None,
    )
    cabinet_doc = Document(
        id=make_id(Document, ("probe-doc", "cabinet")),
        key=("probe-doc", "cabinet"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        unit=cabinet_unit_id,
        add=(PageKind.CONNECTOR_LIST,),
        remove=(PageKind.SCHEMATIC,),
        cover="# Cover",
        notes=None,
    )
    # A second root in the io-board unit: a unit's sole root prints no heading (UNIT-ID I4),
    # which is not what this test is about. It is no board, so the board count stays one.
    io_second_root = Item(
        id=make_id(Item, ("probe-doc", "io-second-root")),
        key=("probe-doc", "io-second-root"),
        part=None,
        parent=None,
        position=None,
        tag="K9",
        description="",
        installed=True,
        unit=io_unit_id,
    )
    model = evolve(model, put=[io_doc, cabinet_doc, io_second_root], origin=_ORIGIN)
    records = documents(model)

    # The real end-to-end proof: building the unit-subject PCB_SCHEMATIC document's source
    # does not raise (the actual pre-fix crash), and its CONNECTOR_LIST holds exactly the
    # io-board unit's own board, nothing recursed in from anywhere else.
    io_text = source(model, io_doc.id, {})
    assert io_text.count("#heading(level: 2,") == _IO_BOARD_COUNT
    assert len(_boards_for(model, records[io_doc.id])) == _IO_BOARD_COUNT

    # The cabinet unit's own document: its TERMINAL_LIST covers its own strip (X2), but its
    # CONNECTOR_LIST is empty -- the board belongs to the nested `demo-io-board` unit, and
    # direct membership never recurses into a nested unit's own items.
    cabinet_text = source(model, cabinet_doc.id, {})
    # Exactly one level-2 heading (TERMINAL_LIST's own X2 section): CONNECTOR_LIST renders
    # `None.`, no heading. A regression to the recursive subtree would pull in pump1's own
    # nested io-board's strip too (there is none) or, worse, both cabinets' strips.
    assert cabinet_text.count("#heading(level: 2,") == _CABINET_OWN_STRIP_COUNT
    assert "X2" in cabinet_text
    cabinet_record = records[cabinet_doc.id]
    assert len(_terminal_strips_for(model, cabinet_record)) == _CABINET_OWN_STRIP_COUNT
    assert _boards_for(model, cabinet_record) == ()


def test_a_units_document_title_block_shows_its_current_revision_and_date_end_to_end():
    """`document_facts`'s unit branch (units spec U3, decision pdf-0006), proven end to end
    through `source()` on the worked example's real, facade-built geometry -- not only
    `packages/fransys-pdf/tests/test_source.py`'s own hand-built-fixture proof
    (`test_unit_document_source_wires_title_block_scope_and_per_set_counter`). The worked
    example authors the cabinet's `Revision` entry itself (`pump_cabinet`, revision `2`, a
    missing one is an ERROR); the `Document` is hand-built here, the same way this file's own
    `_with_documents` hand-builds `Document` records.
    """
    model, _c1_id, _c2_id = _build()
    cabinet_unit_id = _unit_by_name_and_prefix(model, name="demo-pump-cabinet", prefix="pump1")
    doc = Document(
        id=make_id(Document, ("probe-doc", "title-block")),
        key=("probe-doc", "title-block"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        unit=cabinet_unit_id,
        add=(),
        remove=(PageKind.SCHEMATIC, PageKind.PLC_LIST, PageKind.TERMINAL_LIST),
        cover="# Cover",
        notes=None,
    )
    model_with_doc = evolve(model, put=[doc], origin=_ORIGIN)
    text = source(model_with_doc, doc.id, {})
    assert 'text(size: 8pt, "Scope"), text(size: 10pt, text("demo-pump-cabinet"))' in text
    assert 'text(size: 8pt, "Revision"), text(size: 10pt, text("1.2"))' in text
    assert 'text(size: 8pt, "Revision date"), text(size: 10pt, text("2026-01-01"))' in text


def _system_document(id_suffix: str) -> Document:
    return Document(
        id=make_id(Document, ("probe-doc", id_suffix)),
        key=("probe-doc", id_suffix),
        preset=DocumentPreset.SYSTEM,
        location=None,
        item=None,
        add=(),
        remove=(),
        cover="# Cover",
        notes=None,
    )


def test_the_worked_examples_system_document_has_no_top_level_cable_and_gives_the_info():
    """Units spec U3's amended "cable drawings" bullet (STEP 4b addition, decision pdf-0006),
    proven on the worked example's real, facade-built geometry: every cable the worked
    example authors is a unit's own (`pump_cabinet`'s `w1c`, built inside `u.unit(...)`), so
    the model has no top-level cable at all -- confirmed here by finding, not assumed
    (`.fransys/review/step4-system-harness-drawing-no-drawings.png`'s own prior review, now
    superseded by this ruling).
    """
    model, _c1_id, _c2_id = _build()
    doc = _system_document("system")
    model = evolve(model, put=[doc], origin=_ORIGIN)

    findings = check(model, {})
    own_findings = [f for f in findings if doc.id in f.subjects]
    assert [f for f in own_findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []
    (info,) = [f for f in own_findings if f.code == "DOCUMENT_NO_TOP_LEVEL_CABLES"]
    assert info.severity is Severity.INFO

    text = source(model, doc.id, {})
    assert '#par(text("No drawings."))' not in text


def test_adding_one_top_level_cable_draws_the_section_and_clears_the_info():
    """Can-fail 1's own positive proof, on the same real geometry: a hand-built top-level
    cable item (`unit=None`, the same shape `top_level_cables`'s own model-side tests use)
    gives the section its one real page and clears the INFO -- a genuine behavioural
    difference on the worked example's own model, not a flag flip.
    """
    model, _c1_id, _c2_id = _build()
    extra_cable_part = Part(
        id=make_id(Part, ("probe-doc", "extra-cable", "part")),
        key=("probe-doc", "extra-cable", "part"),
        mpn="PROBE-CABLE",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    extra_cable_product = CableProductFacet(
        id=make_id(CableProductFacet, ("probe-doc", "extra-cable", "product")),
        key=("probe-doc", "extra-cable", "product"),
        subject=extra_cable_part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    extra_cable = Item(
        id=make_id(Item, ("probe-doc", "extra-cable")),
        key=("probe-doc", "extra-cable"),
        part=extra_cable_part.id,
        parent=None,
        position=None,
        tag="W99",
        description="",
        installed=True,
        unit=None,
    )
    extra_facet = CableFacet(
        id=make_id(CableFacet, ("probe-doc", "extra-cable", "cable")),
        key=("probe-doc", "extra-cable", "cable"),
        subject=extra_cable.id,
        length_mm=None,
    )
    doc = _system_document("system-with-cable")
    model = evolve(
        model,
        put=[extra_cable_part, extra_cable_product, extra_cable, extra_facet, doc],
        origin=_ORIGIN,
    )

    findings = check(model, {})
    own_findings = [f for f in findings if doc.id in f.subjects]
    assert [f for f in own_findings if f.code == "DOCUMENT_NO_TOP_LEVEL_CABLES"] == []

    text = source(model, doc.id, {})
    # CT2: the cable's own table page needs no svgs entry, unlike the WireViz image it replaces.
    assert "<svg>" not in text
    assert text.count("#table(columns: 4,") == 1
    assert '#par(text("No drawings."))' not in text


def test_the_cabinet_units_own_bom_holds_the_board_line_and_no_relay():
    """BOM acceptance (STEP 4 work order): "The cabinet PDF's title block reads
    `pump-cabinet` `02` `2026-09-23`. Its BOM holds the board line and no relay" (mapped
    fixture names `demo-pump-cabinet`/`demo-io-board`). Scoped to the cabinet unit's own id
    (`_bom_scope`'s unit branch, units spec U5/U6), the BOM holds the nested `demo-io-board`
    unit as one line (`derive.bom_lines`'s own "mpn the instance's name" convention for a
    nested unit line) and none of that board's own components -- the relay `DEMO-RLY-2CO-24`
    is a `demo-io-board` member, not a direct `demo-pump-cabinet` one.
    """
    model, _c1_id, _c2_id = _build()
    cabinet_unit_id = _unit_by_name_and_prefix(model, name="demo-pump-cabinet", prefix="pump1")
    doc = Document(
        id=make_id(Document, ("probe-doc", "cabinet-bom")),
        key=("probe-doc", "cabinet-bom"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        unit=cabinet_unit_id,
        add=(),
        remove=(),
        cover="# Cover",
        notes=None,
    )
    model = evolve(model, put=[doc], origin=_ORIGIN)
    record = documents(model)[doc.id]
    text = bom_page(model, record)
    assert "demo-io-board" in text
    assert "DEMO-RLY-2CO-24" not in text


# -- STEP 4b(b): the board unit's own SCHEMATIC section now draws (units spec U1's board-unit
# ruling, model-0041) -----------------------------------------------------------------------


def test_a_board_unit_documents_schematic_section_now_draws_its_own_content():
    """STEP 4b(b) (units spec U1's board-unit ruling, model-0041): `DEMO-PCB-IO` is the sole
    root item of its own nested unit `demo-io-board`, so its unit document's SCHEMATIC
    section is no longer `NO_DRAWINGS` (that was STEP 4's own finding, captured as
    `step4-board-schematic-no-drawings.png` in the STEP 4 review) -- it now has a real page,
    with `K1`'s own coil function on it, and no `ERROR` finding.
    """
    model, _c1_id, _c2_id = _build()
    io_unit_id = _unit_by_name_and_prefix(model, name="demo-io-board", prefix="pump1")
    io_doc = Document(
        id=make_id(Document, ("probe-doc", "board-schematic")),
        key=("probe-doc", "board-schematic"),
        preset=DocumentPreset.PCB_SCHEMATIC,
        location=None,
        item=None,
        unit=io_unit_id,
        add=(),
        remove=(PageKind.CONNECTOR_LIST, PageKind.BOM),
        cover="# Cover",
        notes=None,
    )
    model = evolve(model, put=[io_doc], origin=_ORIGIN)
    record = documents(model)[io_doc.id]

    pages_found = schematic_pages(model, record, (PageKind.SCHEMATIC,))
    assert len(pages_found) >= 1

    svgs = dict(render_pages(model))
    findings = check(model, svgs)
    own_errors = [f for f in findings if io_doc.id in f.subjects and f.severity == Severity.ERROR]
    assert own_errors == []

    by_key = {item.key: item.id for item in items_table(model).values()}
    k1_item = by_key[("pump1", "io", "k1")]
    coil_fn = next(
        f for f in functions_table(model).values() if f.item == k1_item and f.key[-1] == "coil"
    )
    page_ids = {page.id for page in pages_found}
    placed_functions = {
        placement.function
        for placement in layout_of_model(model, SymbolPlacement).values()
        if placement.page in page_ids
    }
    assert coil_fn.id in placed_functions, "K1's coil is actually on the board's own page"

    text = source(model, io_doc.id, svgs)
    assert '#par(text("No drawings."))' not in text
