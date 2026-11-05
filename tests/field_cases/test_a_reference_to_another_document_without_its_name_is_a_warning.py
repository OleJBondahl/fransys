"""Field case: a cabinet contact's coil table cites a field-location block by prefix only, without naming its other document.
The bug: an unnamed reference to a page of no document in this set sends a reader nowhere, and nothing counted or warned it.
Fixed by model-0258, references_off_document counts them and REFERENCE_OFF_DOCUMENT (WARNING) names the reference and its fix."""

import dataclasses
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_model.kernel import Origin, evolve
from fransys_model.layout import DrawingSet, layout_of

_WIRE = (BU, 0.5)
_CODE = "REFERENCE_OFF_DOCUMENT"


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Docs", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    fld = d.location("FLD", "Field")
    psu = d.device("T1", "DEMO-PSU-24")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="blk", parent=q, place="FLD")
    lamp = d.device("P1", "DEMO-LAMP-24", place="FLD")
    d.series(psu.output["+"], q.coil["A1"], wire=_WIRE)
    d.series(psu.output["-"], q.coil["A2"], wire=_WIRE)
    d.series(psu.output["+"], q.aux["13"], wire=_WIRE)
    d.series(q.aux["14"], lamp["1"], wire=_WIRE)
    d.series(psu.output["-"], lamp["2"], wire=_WIRE)
    d.series(lamp["1"], block.no["53"], wire=_WIRE)
    d.series(block.no["54"], lamp["2"], wire=_WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Docs\n", encoding="utf-8")
    cabinet = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(cabinet, cab, cover=cover), fr.document(cabinet, fld, cover=cover))


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


def test_a_reference_that_names_its_location_is_not_counted() -> None:
    assert _off(_built()) == []


def test_the_same_reference_with_no_name_is_counted_and_warned() -> None:
    found = _off(_unnamed(_built()))
    assert found, "the unnamed reference into the field set is warned"
    assert all(f.severity is fr.Severity.WARNING and "page" in f.message for f in found)
