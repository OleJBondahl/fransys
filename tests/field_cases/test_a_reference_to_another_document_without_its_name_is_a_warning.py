"""Field case: a reference to a page of another document, not naming it, is counted and warned.

The engineering shape: a contactor in a cabinet document whose add-on contact block stands in a
field location, wired there to a lamp. The coil's contact table names the block's contacts with
the location prefix, `+FLD`, so a reader knows which drawing to open although the cabinet document
does not print the field pages.

The need: a printed reference whose target page is in no page of this document, and whose text
does not name the other document, sends a reader nowhere. `references_off_document` on the page and
unit rows counts them, and `REFERENCE_OFF_DOCUMENT` (WARNING) names the reference, its page and the
fix. A reference that names its other document is correct and is not counted. Decision model-0258.

Layout always names the location, so the unnamed case is planted: the field drawing set loses its
location in the built model, which leaves the same references with no location prefix.
"""

import dataclasses
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_model.kernel import Origin, evolve
from fransys_model.layout import DrawingSet, Label, LabelKind, Page, layout_of

_WIRE = (BU, 0.5)
_CODE = "REFERENCE_OFF_DOCUMENT"


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Docs", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    d.location("FLD", "Field")
    psu = d.device("T1", "DEMO-PSU-24")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="blk", parent=q, place="FLD")
    lamp = d.device("P1", "DEMO-LAMP-24", place="FLD")
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=_WIRE)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=_WIRE)
    d.detail.wire(q.aux["14"], lamp["1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], lamp["2"], wire=_WIRE)
    d.detail.wire(lamp["1"], block.no["53"], wire=_WIRE)
    d.detail.wire(block.no["54"], lamp["2"], wire=_WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Docs\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _unnamed(result: fr.BuildResult) -> fr.BuildResult:
    """`result` with the field drawing set stripped of its location, so no text can name it."""
    sets = layout_of(result.model, DrawingSet).values()
    field = next(s for s in sets if s.location is not None and s.number != 1)
    origin = Origin(file="<field case>", line=1, note="plant")
    plain = dataclasses.replace(field, location=None)
    model = evolve(result.model, remove=[field.id], put=[plain], origin=origin)
    return dataclasses.replace(result, model=model)


def _off(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == _CODE]


def _expected(result: fr.BuildResult) -> int:
    """The labels of the first set that list a partner on a page of another set."""
    model = result.model
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return sum(
        any(pages[p.page].drawing_set != pages[label.page].drawing_set for p in label.partners)
        and sets[pages[label.page].drawing_set].number == 1
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE
    )


def test_a_reference_that_names_its_location_is_not_counted() -> None:
    result = _built()
    assert _expected(result) > 0, "the case needs a reference into the field set"
    report = fr.readability(result)
    assert [row.references_off_document for row in report.pages] == [0] * len(report.pages)
    assert [row.references_off_document for row in report.units] == [0] * len(report.units)
    assert _off(result) == []


def test_the_same_reference_with_no_name_is_counted_and_warned() -> None:
    planted = _unnamed(_built())
    expected = _expected(planted)
    report = fr.readability(planted)
    assert sum(row.references_off_document for row in report.pages) == expected > 0
    assert sum(row.references_off_document for row in report.units) == expected
    found = _off(planted)
    assert len(found) == expected
    assert all(f.severity is fr.Severity.WARNING and "page" in f.message for f in found)
