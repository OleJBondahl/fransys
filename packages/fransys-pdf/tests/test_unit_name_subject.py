"""Spec unit-subject-by-name UN1-UN4: a `unit_name` subject reads exactly like the matching
`unit=<id>` subject, everywhere `_geometry.py`/`_lists.py`/`checks.py` read the document's
subject unit through `derive.document_unit`.
"""

from dataclasses import replace

from _build import document, item, model, project, unit
from fransys_pdf import check
from fransys_pdf._geometry import document_facts, document_release, subject_label
from fransys_pdf._lists import designation_list_page

from fransys_model.kernel import make_id
from fransys_model.vocab import Document, DocumentPreset, PageKind, documents

K = PageKind
_CODE = "TITLE_BLOCK_UNIT_IDENTITY_MISSING"
_UNIT_DOCUMENT_REMOVE = (K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)


def _name_subject_model():
    """One empty-identity unit `relay-board` with a root item and a child (so `designation_list`
    has a real row: UNIT-ID I4 drops the sole root's own row), and two documents about the
    unit: one subject `unit=<id>`, one `unit_name="relay-board"` -- everything else identical."""
    u = unit("u1", name="relay-board", revision=1)
    root = item("k1", description="Root item", unit=u.id)
    child = item("k2", description="Child item", parent=root.id, unit=u.id)
    unit_doc = document(
        "d-unit",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        remove=_UNIT_DOCUMENT_REMOVE,
    )
    name_key = ("document", "d-name")
    name_doc = replace(
        unit_doc,
        id=make_id(Document, name_key),
        key=name_key,
        unit=None,
        unit_name="relay-board",
    )
    m = model(project(), u, root, child, unit_doc, name_doc)
    return m, unit_doc, name_doc


def test_unit_name_subject_resolves_the_same_unit_as_an_equivalent_unit_subject():
    """UN1-UN2 equivalence: `subject_label`, `document_facts`, `document_release` and a list
    page (`designation_list_page`) all read the same values for a `unit_name` subject as for
    the matching `unit=<id>` subject. Can-fail (probe): reverting one of these sites to bare
    `record.unit` makes the `unit_name` side see no subject at all.
    """
    m, unit_doc, name_doc = _name_subject_model()
    unit_record = documents(m)[unit_doc.id]
    name_record = documents(m)[name_doc.id]

    assert subject_label(m, name_record) == subject_label(m, unit_record)
    assert subject_label(m, name_record) == "relay-board"

    assert document_facts(m, name_record) == document_facts(m, unit_record)

    assert document_release(m, name_record) == document_release(m, unit_record)
    assert document_release(m, name_record) is not None

    assert designation_list_page(m, name_record) == designation_list_page(m, unit_record)
    assert designation_list_page(m, name_record) != ""


def test_unit_identity_warning_fires_the_same_for_a_unit_name_subject():
    """UNIT-ID I3 equivalence: the empty-title/-number release warns on both documents alike."""
    m, unit_doc, name_doc = _name_subject_model()
    findings = {found.subjects: found for found in check(m, {}) if found.code == _CODE}
    assert set(findings) == {(unit_doc.id,), (name_doc.id,)}
    assert findings[(unit_doc.id,)].message == findings[(name_doc.id,)].message
