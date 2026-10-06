"""The replica-only drawing set skip rule (STEP 4 addition, `.fransys/WORK-ORDER-UNIT-
DOCUMENTS.md`'s "STEP 2b RULING AND A STEP 4 ADDITION"): a document draws no page for a
drawing set that holds only black-box replicas and no real conductor, and reports it with an
INFO finding (`DRAWING_SET_REPLICA_ONLY`) instead of a silent omission.
"""

from dataclasses import replace

from _build import (
    conductor,
    document,
    drawing_set,
    layout_page,
    link_marker_pair,
    location,
    model,
    pin,
    route,
    symbol_placement,
    unit,
)
from fransys_pdf import check
from fransys_pdf._drawings import replica_only_sets, schematic_pages

from fransys_model.kernel import Severity
from fransys_model.kernel.ids import render_id
from fransys_model.vocab import DocumentPreset, PageKind, documents

K = PageKind
_REMOVE_LISTS = (K.PLC_LIST, K.TERMINAL_LIST, K.BOM)

# Two top-level locations, each with a boundary replica and no conductor: named per the work
# order's own hand-back on the units worked example ("there are two in the system build ...
# one per cabinet location").
_REPLICA_ONLY_SET_COUNT = 2


def _cabinet_document(key_part: str, loc):
    return document(
        f"d_{key_part}",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=loc,
        cover="# Cover",
        notes=None,
        remove=_REMOVE_LISTS,
    )


def _replica_only_document(key_part: str, loc, u, *, with_conductor_to_unitless: bool = False):
    """One `cabinet_schematic` document at `loc`, whose top-level set holds only `u`'s
    boundary replica (`item.unit=u.id`) and no conductor -- unless `with_conductor_to_
    unitless` is set, in which case a second, unitless pin is placed on the same page and
    joined to the replica by a real `Conductor`/`Route` (can-fail 1's own fixture: "add one
    conductor from a replica to unitless content").
    """
    ds = drawing_set(f"ds_{key_part}", location=loc, number=1)
    page = layout_page(f"p_{key_part}", drawing_set=ds, number=1)
    replica_item, replica_fn, replica_port = pin(f"replica_{key_part}", "R1", unit=u.id)
    placement = symbol_placement(f"sp_{key_part}", function=replica_fn.id, page=page.id)
    records = [ds, page, replica_item, replica_fn, replica_port, placement]
    if with_conductor_to_unitless:
        other_item, other_fn, other_port = pin(f"other_{key_part}", "U1")
        other_placement = symbol_placement(
            f"sp_other_{key_part}", function=other_fn.id, page=page.id
        )
        cond = conductor(f"w_{key_part}", a=replica_port.id, b=other_port.id)
        wire = route(
            f"route_{key_part}", page=page.id, a=replica_port.id, b=other_port.id, conductor=cond.id
        )
        records.extend([other_item, other_fn, other_port, other_placement, cond, wire])
    doc = _cabinet_document(key_part, loc)
    records.append(doc)
    return records, doc, ds, page


def _two_replica_only_records():
    """The work order's own worked-example shape: two top-level locations, each with one
    replica-only set and its own `cabinet_schematic` document. Returns raw records (not yet
    frozen), so a caller can add more records to the same model before calling `model(...)`.
    """
    c1 = location("C1", "First cabinet")
    c2 = location("C2", "Second cabinet")
    u = unit("u1", name="relay-interface-board")
    records1, doc1, ds1, _page1 = _replica_only_document("a", c1, u)
    records2, doc2, ds2, _page2 = _replica_only_document("b", c2, u)
    records = [c1, c2, u, *records1, *records2]
    return records, doc1, doc2, ds1, ds2


def _two_replica_only_documents():
    records, doc1, doc2, ds1, ds2 = _two_replica_only_records()
    m = model(*records)
    return m, doc1, doc2, ds1, ds2


def test_replica_only_sets_give_no_page_and_one_info_each():
    m, doc1, doc2, ds1, ds2 = _two_replica_only_documents()
    record1 = documents(m)[doc1.id]
    record2 = documents(m)[doc2.id]
    assert schematic_pages(m, record1, (K.SCHEMATIC,)) == ()
    assert schematic_pages(m, record2, (K.SCHEMATIC,)) == ()
    findings = check(m, {})
    replica_findings = [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"]
    assert len(replica_findings) == _REPLICA_ONLY_SET_COUNT
    for finding in replica_findings:
        assert finding.severity is Severity.INFO
        assert "holds only black-box replicas: not drawn" in finding.message
    assert {f.subjects for f in replica_findings} == {(doc1.id, ds1.id), (doc2.id, ds2.id)}
    no_drawings = [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert no_drawings == []


def test_replica_only_message_names_the_locations_path():
    m, doc1, _doc2, ds1, _ds2 = _two_replica_only_documents()
    findings = check(m, {})
    (finding,) = [
        f
        for f in findings
        if f.code == "DRAWING_SET_REPLICA_ONLY" and f.subjects == (doc1.id, ds1.id)
    ]
    assert finding.message == "drawing set +C1 holds only black-box replicas: not drawn"


def test_replica_only_message_prints_a_nested_location_path_root_first():
    outer = location("C1", "First cabinet")
    inner = replace(location("SUB", "Sub-cabinet"), parent=outer.id)
    u = unit("u1", name="relay-interface-board")
    records, _doc, ds, _page = _replica_only_document("n", inner, u)
    findings = check(model(outer, inner, u, *records), {})
    (finding,) = [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"]
    assert finding.subjects[1] == ds.id
    assert finding.message == "drawing set +C1+SUB holds only black-box replicas: not drawn"


def test_a_conductor_from_a_replica_to_unitless_content_draws_the_set_and_drops_the_info():
    """Can-fail 1 (a real behavioural difference, not a flag flip): a real conductor from the
    boundary replica to unitless content at the same location is drawn like any same-set
    connection (units spec U2's own ruling) -- the page now exists and the INFO for that set
    is gone. This is this package's own unit-of-testing proof, against hand-built `layout.*`
    records (a real `Page` with a real `Route`, not a mocked flag); the same behaviour is
    proven again on the units worked example's own facade-built geometry in root
    `tests/test_pdf_replica_only_units_worked_example.py::
    test_a_real_rewired_replica_boundary_draws_its_set_and_drops_the_info`.
    """
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="relay-interface-board")
    records, doc, _ds, page = _replica_only_document("a", c1, u, with_conductor_to_unitless=True)
    m = model(c1, u, *records)
    record = documents(m)[doc.id]
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert len(pages) == 1
    assert pages[0].id == page.id
    assert replica_only_sets(m, record, (K.SCHEMATIC,)) == ()
    svgs = {render_id(page.id): "<svg>drawn</svg>"}
    findings = check(m, svgs)
    assert [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"] == []
    assert [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []


def test_two_black_box_replicas_joined_by_their_own_conductor_are_still_drawn():
    """Isolates the "no conductor" clause from `drawing_set_is_replica_only` itself: both
    placements are black-box replicas of the same unit (so `drawing_set_is_replica_only` alone
    would call this set replica-only), but a real conductor joins them. The set must still be
    drawn -- this is the fixture a can-fail on the conductor check alone (not the replica-only
    check) can flip, isolated from can-fail 1 above, which flips `drawing_set_is_replica_only`
    too by using a non-black-box far end.
    """
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="relay-interface-board")
    ds = drawing_set("ds_joined", location=c1, number=1)
    page = layout_page("p_joined", drawing_set=ds, number=1)
    a_item, a_fn, a_port = pin("replica_a", "R1", unit=u.id)
    b_item, b_fn, b_port = pin("replica_b", "R2", unit=u.id)
    sp_a = symbol_placement("sp_a", function=a_fn.id, page=page.id)
    sp_b = symbol_placement("sp_b", function=b_fn.id, page=page.id)
    cond = conductor("w_joined", a=a_port.id, b=b_port.id)
    wire = route("route_joined", page=page.id, a=a_port.id, b=b_port.id, conductor=cond.id)
    doc = _cabinet_document("joined", c1)
    m = model(
        c1, u, ds, page, a_item, a_fn, a_port, b_item, b_fn, b_port, sp_a, sp_b, cond, wire, doc
    )
    record = documents(m)[doc.id]
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert len(pages) == 1
    assert replica_only_sets(m, record, (K.SCHEMATIC,)) == ()


def test_document_no_drawings_does_not_fire_alongside_the_info_with_other_content_elsewhere():
    """The two replica-only documents give INFO only, no ERROR, alongside a third, unrelated
    document with real, non-replica-only content that draws fine -- both directions in one
    model, not just the happy path."""
    records, doc1, doc2, _ds1, _ds2 = _two_replica_only_records()
    c3 = location("C3", "Third cabinet")
    ds3 = drawing_set("ds_c3", location=c3, number=3)
    page3 = layout_page("p_c3", drawing_set=ds3, number=1)
    real_item, real_fn, real_port = pin("real3", "K1")  # unit=None: not a black-box replica
    placement3 = symbol_placement("sp3", function=real_fn.id, page=page3.id)
    doc3 = _cabinet_document("c3", c3)
    m2 = model(*records, c3, ds3, page3, real_item, real_fn, real_port, placement3, doc3)
    record3 = documents(m2)[doc3.id]
    svgs = {render_id(page3.id): "<svg>real</svg>"}
    assert len(schematic_pages(m2, record3, (K.SCHEMATIC,))) == 1
    findings = check(m2, svgs)
    replica_findings = [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"]
    assert len(replica_findings) == _REPLICA_ONLY_SET_COUNT
    assert {f.subjects[0] for f in replica_findings} == {doc1.id, doc2.id}
    no_drawings = [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert no_drawings == []


def test_document_no_drawings_still_fires_for_a_genuinely_empty_match():
    """The other direction: a document whose location names no drawing set at all is still a
    real `DOCUMENT_NO_DRAWINGS` ERROR, never mistaken for the replica-only case."""
    c1 = location("C1", "Empty cabinet")
    doc = _cabinet_document("empty", c1)
    m = model(c1, doc)
    findings = check(m, {})
    (finding,) = [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert finding.severity is Severity.ERROR
    assert "no drawing set found" in finding.message
    assert [f for f in findings if f.code == "DRAWING_SET_REPLICA_ONLY"] == []


def test_replica_only_sets_are_not_skipped_for_a_unit_subject_document():
    """The guard's `record.unit is None` clause must gate the *absence* of a unit subject, not
    its presence (survivor id 4, confirmed with `mutant_diff.py`: flipped to `record.unit is
    not None`). A genuine unit document (`record.unit` set, `location` and `unit_name` both
    `None`) must still reach `undrawn_replica_only_sets` and report its own real replica-only
    set.

    A document with `location=unit=unit_name=None` (the guard's own early-return case, a
    `SYSTEM` preset with no subject) does *not* discriminate this mutant: with no location and
    no resolvable unit, `_geometry._matched_drawing_sets` returns `()` regardless of whether
    the guard's own early return fires, so both the real code and the mutant agree on `()` for
    that fixture, by coincidence, not because the guard did anything. This fixture instead
    gives the document a real unit subject and one real replica-only drawing set of that unit,
    so the two paths disagree: real code falls through to `undrawn_replica_only_sets` and
    finds it; the mutant's guard (`unit is not None` now true) short-circuits to `()` and loses
    it.
    """
    u1 = unit("u1", name="cabinet")
    u2 = unit("u2", name="board")
    ds = drawing_set("ds_unit", unit=u1, number=1)
    page = layout_page("p_unit", drawing_set=ds, number=1)
    replica_item, replica_fn, replica_port = pin("replica_unit", "R1", unit=u2.id)
    placement = symbol_placement("sp_unit", function=replica_fn.id, page=page.id)
    doc = document(
        "d_unit_only",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u1,
        cover="# Cover",
        notes=None,
        remove=_REMOVE_LISTS,
    )
    m = model(u1, u2, ds, page, replica_item, replica_fn, replica_port, placement, doc)
    record = documents(m)[doc.id]
    assert record.location is None
    assert record.unit == u1.id
    assert record.unit_name is None
    assert replica_only_sets(m, record, (K.SCHEMATIC,)) == (ds,)


def test_a_link_marker_on_the_set_also_counts_as_a_real_conductor():
    """Layout-0045's U2 amendment: a same-unit connection split across two pages of one set
    is drawn with a `LinkMarker` pair, not a `Route` (a `Route` only ever lives on one page).
    A marker on this set's own page is never a cross-unit cut (those get no marker at all, by
    construction), so it is a real, same-unit connection this set genuinely draws -- the
    replica-only rule must not hide it. Two black-box replicas, no `Route`, but one page
    carries a `LinkMarker`.
    """
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="relay-interface-board")
    ds = drawing_set("ds_marked", location=c1, number=1)
    page = layout_page("p_marked", drawing_set=ds, number=1)
    other_page = layout_page("p_other", drawing_set=ds, number=2)
    a_item, a_fn, a_port = pin("replica_a", "R1", unit=u.id)
    b_item, b_fn, b_port = pin("replica_b", "R2", unit=u.id)
    sp_a = symbol_placement("sp_a", function=a_fn.id, page=page.id)
    sp_b = symbol_placement("sp_b", function=b_fn.id, page=other_page.id)
    marker_a, marker_b = link_marker_pair(
        "m1", page_a=page.id, port_a=a_port.id, page_b=other_page.id, port_b=b_port.id
    )
    doc = _cabinet_document("marked", c1)
    m = model(
        c1,
        u,
        ds,
        page,
        other_page,
        a_item,
        a_fn,
        a_port,
        b_item,
        b_fn,
        b_port,
        sp_a,
        sp_b,
        marker_a,
        marker_b,
        doc,
    )
    record = documents(m)[doc.id]
    assert len(schematic_pages(m, record, (K.SCHEMATIC,))) == 2
    assert replica_only_sets(m, record, (K.SCHEMATIC,)) == ()
