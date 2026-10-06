"""A unit document draws its unit's own cables (units spec U3, decision pdf-0015).

`harness_cables_for` reads `Document.unit` (not only `Document.item`): a unit document asking for
`CONTENTS` or `HARNESS_DRAWING` gets `derive.unit_cables`, so `check` reports `DOCUMENT_NO_DRAWINGS`
only when a cable's drawing is really missing, and `source` prints the pages.
"""

from _build import (
    cable_facet,
    cable_product_facet,
    conductor,
    core_facet,
    document,
    item,
    model,
    part,
    pin,
    project,
    revision_entry,
    unit,
)
from fransys_pdf import check, source
from fransys_pdf._contents import contents_page
from fransys_pdf._drawings import harness_cables_for

from fransys_model.derive import unit_cables
from fransys_model.vocab import ConductorKind, DocumentPreset, PageKind, documents

K = PageKind
_NO_DRAWINGS = "DOCUMENT_NO_DRAWINGS"


def _unit_with_cables():
    """A container unit with one loose cable of its own.

    The container `u1` owns the loose cable `w1` and holds a nested unit `u2` owning `w2`; `w3` is
    a top-level cable (no unit). The document is `u1`'s own, with the harness pages only.
    """
    p = project()
    u1 = unit("u1", name="cabinet")
    u2 = unit("u2", name="board", parent=u1.id)
    w1_part = part("w1", description="Cable of the container part")
    w1_product = cable_product_facet("w1", subject=w1_part.id, core_count=0)
    w2_part = part("w2", description="Cable of the nested unit part")
    w2_product = cable_product_facet("w2", subject=w2_part.id, core_count=0)
    w3_part = part("w3", description="Top-level cable part")
    w3_product = cable_product_facet("w3", subject=w3_part.id, core_count=0)
    w1 = item("w1", description="Cable of the container", part=w1_part.id, unit=u1.id)
    w2 = item("w2", description="Cable of the nested unit", part=w2_part.id, unit=u2.id)
    w3 = item("w3", description="Top-level cable", part=w3_part.id)
    facets = tuple(
        cable_facet(key, subject=cable.id, length_mm=None)
        for key, cable in (("w1", w1), ("w2", w2), ("w3", w3))
    )
    entries = tuple(
        revision_entry(key, unit=u, revision=1, date="2026-09-01")
        for key, u in (("r1", u1), ("r2", u2))
    )
    doc = document(
        "d-unit",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=u1,
        cover="# Cover",
        remove=(K.BOM,),
    )
    m = model(
        p,
        u1,
        u2,
        w1_part,
        w1_product,
        w2_part,
        w2_product,
        w3_part,
        w3_product,
        w1,
        w2,
        w3,
        *facets,
        *entries,
        doc,
    )
    return m, doc, w1, w2, w3


def test_harness_cables_for_a_unit_subject_is_the_units_own_cables():
    """Both harness page kinds give the unit's own cable: not `()`, not a nested unit's, not a
    top-level one. Can-fail: the pre-fix `harness_cables_for` returned `()` for a unit subject."""
    m, doc, w1, w2, w3 = _unit_with_cables()
    record = documents(m)[doc.id]
    for kind in (K.HARNESS_DRAWING, K.CONTENTS):
        found = harness_cables_for(m, record, (kind,))
        assert [cable.cable for cable in found] == [w1.id]
    assert w2.id not in {c.cable for c in harness_cables_for(m, record, (K.HARNESS_DRAWING,))}
    assert w3.id not in {c.cable for c in harness_cables_for(m, record, (K.HARNESS_DRAWING,))}


def test_harness_cables_for_a_unit_subject_is_empty_when_no_harness_page_kind_is_requested():
    """The guard before the unit branch still holds: `COVER` alone asks for no cable."""
    m, doc, _w1, _w2, _w3 = _unit_with_cables()
    record = documents(m)[doc.id]
    assert harness_cables_for(m, record, (K.COVER,)) == ()


def test_check_gives_no_drawings_finding_for_a_unit_document_with_a_cable():
    """Positive: the unit's own cable always gets its table page (CT2), so no
    `DOCUMENT_NO_DRAWINGS` -- a table needs no rendered drawing to be "missing" against. Only
    the unit's own cable is asked for: the nested unit's and the top-level cable's are not this
    document's, and are not missed."""
    m, _doc, _w1, _w2, _w3 = _unit_with_cables()
    findings = check(m, {})
    assert [f for f in findings if f.code == _NO_DRAWINGS] == []


def _no_cable_message(*records):
    """The one `DOCUMENT_NO_DRAWINGS` message of a model built from `records` (no svgs)."""
    (finding,) = [f for f in check(model(*records), {}) if f.code == _NO_DRAWINGS]
    return finding.message


def test_no_cable_message_says_unit_for_a_unit_document_and_harness_for_an_item_document():
    """The finding names the subject the reader asked about: a unit document whose unit has no
    cable says "the unit has no cable", an item (harness) document keeps "the harness has no
    cable". Can-fail: one shared text makes one of the two assertions fail."""
    u = unit("u1", name="cabinet")
    unit_doc = document("d-unit", preset=DocumentPreset.HARNESS_DRAWING, subject=u, cover="# Cover")
    harness = item("wh1", description="Demo harness")
    item_doc = document(
        "d-item", preset=DocumentPreset.HARNESS_DRAWING, subject=harness, cover="# Cover"
    )
    assert _no_cable_message(project(), u, unit_doc) == "HARNESS_DRAWING: the unit has no cable"
    assert _no_cable_message(project(), harness, item_doc) == (
        "HARNESS_DRAWING: the harness has no cable"
    )


def test_source_prints_a_table_page_per_unit_cable_and_the_contents_table():
    """`source` for a unit document: the table page carries the cable's own (unit-relative)
    designation and the contents page lists it, instead of `No drawings.` and `None.` (CT2: a
    table needs no rendered SVG, so `source` is called with no `svgs` entry for it at all)."""
    m, doc, w1, w2, _w3 = _unit_with_cables()
    text = source(m, doc.id, {})
    (cable,) = harness_cables_for(m, documents(m)[doc.id], (K.HARNESS_DRAWING,))
    assert cable.cable == w1.id
    assert "<svg>" not in text
    assert '#par(text("No drawings."))' not in text
    assert '#par(text("None."))' not in text
    assert f'"{cable.designation}"' in text
    (nested_cable,) = unit_cables(m, w2.unit)
    assert nested_cable.designation != cable.designation
    assert f'"{nested_cable.designation}"' not in text


def _nested_unit_contents(*, outside_ends: int) -> str:
    """The CONTENTS page of the nested unit `u2` (inside `u1`) owning cable `w1`, one core.

    Its two ends are devices `E0`, `E1`: the first `outside_ends` of them in no unit, so they
    read `""` in `u2`'s unit-relative document (decision model-0090), the rest in `u2` itself.
    """
    u1 = unit("u1", name="cabinet")
    u2 = unit("u2", name="board", parent=u1.id)
    ends = [
        pin(f"e{index}", f"E{index}", unit=None if index < outside_ends else u2.id)
        for index in range(2)
    ]
    cable_part = part("cab1", description="Invented 1-core cable")
    cable = item("w1", description="Cable of the board", part=cable_part.id, unit=u2.id)
    core = conductor(
        "core-1", a=ends[0][2].id, b=ends[1][2].id, kind=ConductorKind.CORE, carrier=cable.id
    )
    doc = document(
        "d-unit",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=u2,
        cover="# Cover",
        remove=(K.BOM, K.HARNESS_DRAWING),
    )
    m = model(
        project(),
        u1,
        u2,
        *(record for end in ends for record in end),
        cable_part,
        cable_product_facet("cab1", subject=cable_part.id, core_count=1),
        cable,
        cable_facet("w1", subject=cable.id, length_mm=1500),
        core,
        core_facet("core-1", subject=core.id, index=1),
        doc,
    )
    return contents_page(m, documents(m)[doc.id], (K.CONTENTS,))


def test_the_ends_cell_drops_a_blank_end_and_its_dash():
    """One end outside the nested unit (`""`) and one inside (`-E1`): the cell is `-E1` alone, no
    dangling en dash on either side. Can-fail: the plain join printed `" \N{EN DASH} -E1"`."""
    contents = _nested_unit_contents(outside_ends=1)
    assert contents.endswith('text("1500"), text("-E1"))')
    assert "\N{EN DASH}" not in contents


def test_the_ends_cell_is_empty_when_both_ends_are_blank():
    """Both ends outside the nested unit: an empty cell, not a lone en dash."""
    contents = _nested_unit_contents(outside_ends=2)
    assert contents.endswith('text("1500"), text(""))')
    assert "\N{EN DASH}" not in contents
