"""A document whose subject is a unit release name resolves exactly like the equivalent
document naming that unit's own id (spec unit-subject-by-name UN1-UN4): `schematic_pages`/
`replica_only_sets`'s subject-family guard, and `harness_cables_for`'s resolution (which used
to read `record.unit` through the now-deleted `_unit_subject`), both go through
`derive.document_unit`, not `Document.unit` alone.

Named `..._harness_drawings` (not the bare `test_unit_name_subject.py` a sibling part's own
test file already claims in this shared worktree) to keep the two files from colliding.
"""

from _build import (
    cable_facet,
    cable_product_facet,
    document,
    item,
    model,
    part,
    project,
    revision_entry,
    unit,
)
from fransys_pdf import _drawings
from fransys_pdf._contents import contents_page
from fransys_pdf._drawings import harness_cables_for, replica_only_sets, schematic_pages

from fransys_model.kernel import make_id
from fransys_model.vocab import Document, DocumentPreset, PageKind, documents

K = PageKind


def _unit_name_document(key_part: str, *, unit_name: str) -> Document:
    """A `Document` like `_build.document()`'s own harness-drawing shape, but with `unit_name`
    (not yet one of that shared helper's keywords) in place of `unit`."""
    key = ("document", key_part)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=DocumentPreset.HARNESS_DRAWING,
        location=None,
        item=None,
        add=(),
        remove=(K.BOM,),
        cover="# Cover",
        notes=None,
        unit=None,
        unit_name=unit_name,
    )


def _two_equivalent_documents():
    """One unit (`u1`, release name `"board"`) with one loose cable (`w1`), and two documents
    about it: `by_id` names `u1` directly, `by_name` names its release `"board"` instead --
    the two must resolve to the same unit through `derive.document_unit`.
    """
    p = project()
    u1 = unit("u1", name="board")
    w1_part = part("w1", description="Cable of the board part")
    w1_product = cable_product_facet("w1", subject=w1_part.id, core_count=0)
    w1 = item("w1", description="Cable of the board", part=w1_part.id, unit=u1.id)
    facet = cable_facet("w1", subject=w1.id, length_mm=None)
    entry = revision_entry("r1", unit=u1, revision=1, date="2026-09-01")
    by_id = document(
        "d-by-id",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=u1,
        cover="# Cover",
        remove=(K.BOM,),
    )
    by_name = _unit_name_document("d-by-name", unit_name="board")
    m = model(p, u1, w1_part, w1_product, w1, facet, entry, by_id, by_name)
    return m, w1, by_id, by_name


def test_harness_cables_for_a_unit_name_subject_matches_the_units_own_id():
    """Can-fail (probe): reverting `harness_cables_for`'s `document_unit(model, record)` call
    to a hardcoded `record.unit` read makes `found_by_name` go back to `()` -- a `unit_name`-
    only document has no `.unit` at all.
    """
    m, w1, by_id, by_name = _two_equivalent_documents()
    record_by_id = documents(m)[by_id.id]
    record_by_name = documents(m)[by_name.id]
    found_by_id = harness_cables_for(m, record_by_id, (K.HARNESS_DRAWING,))
    found_by_name = harness_cables_for(m, record_by_name, (K.HARNESS_DRAWING,))
    assert [c.cable for c in found_by_id] == [w1.id]
    assert found_by_name == found_by_id


def test_contents_page_for_a_unit_name_subject_matches_the_units_own_id():
    """`_contents.py` itself has no `Document.unit`/`unit_name` read (it only calls
    `harness_cables_for`), so this is the end-to-end proof that its output does not depend on
    which of the two fields carries the subject.
    """
    m, _w1, by_id, by_name = _two_equivalent_documents()
    text_by_id = contents_page(m, documents(m)[by_id.id], (K.CONTENTS,))
    text_by_name = contents_page(m, documents(m)[by_name.id], (K.CONTENTS,))
    assert text_by_name == text_by_id
    assert '#par(text("None."))' not in text_by_name


def test_schematic_guard_no_longer_shortcuts_a_unit_name_subject(monkeypatch):
    """Fix (1): `schematic_pages`/`replica_only_sets` used to read `record.unit is None` alone
    in their subject-family guard, so a `unit_name`-only document (whose `.unit` is `None` by
    construction, units spec, `Document.__post_init__`) was always turned away before its
    drawing sets could ever be matched, even though it does have a subject. `_geometry`'s own
    matcher is stubbed here so the assertion is about the guard in this file alone, not about
    `_geometry.py`'s own unit-name resolution (a sibling part's file).
    """
    m, _w1, _by_id, by_name = _two_equivalent_documents()
    record_by_name = documents(m)[by_name.id]
    calls = []
    monkeypatch.setattr(
        _drawings,
        "_drawing_set_pages",
        lambda model, record, pages: calls.append((model, record, pages)) or ("sentinel-page",),
    )
    monkeypatch.setattr(
        _drawings,
        "undrawn_replica_only_sets",
        lambda model, record, pages: calls.append((model, record, pages)) or ("sentinel-set",),
    )
    assert schematic_pages(m, record_by_name, (K.SCHEMATIC,)) == ("sentinel-page",)
    assert replica_only_sets(m, record_by_name, (K.SCHEMATIC,)) == ("sentinel-set",)
    assert len(calls) == 2


def test_schematic_guard_still_shortcuts_with_no_subject_at_all(monkeypatch):
    """The other direction: the `SYSTEM` preset (no subject at all) still returns `()` without
    ever calling `_geometry`'s matcher -- the guard fix widens which documents pass through, it
    does not remove the guard itself.
    """
    system_doc = document("d-system", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(project(), system_doc)
    record = documents(m)[system_doc.id]
    calls = []
    monkeypatch.setattr(
        _drawings, "_drawing_set_pages", lambda *args: calls.append(args) or ("sentinel-page",)
    )
    assert schematic_pages(m, record, (K.SCHEMATIC,)) == ()
    assert calls == []
