"""The block diagram through the facade (BD-3 F1, decision 0119).

The diagram lays out only for a kept BLOCK_DIAGRAM page; the SYSTEM preset keeps it; a kept page
over a diagram that cannot be drawn is `DOCUMENT_NO_DRAWINGS`, a reading with no line is silent.
"""
# CONNECTION_NOT_DRAWN 2 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

import functools

import fransys as fr
import fransys_parts
from _model_build_cover import _COVER
from fransys_author.design import Design
from test_units_worked_example import _PROJECT, pump_cabinet

from fransys_model.vocab import DocumentPreset


def _design(leaves: int):
    """A cabinet-less system: motor `M0` joined by one cable to each of `leaves` motors."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc, grp = d.location("C1", "Cabinet"), d.group("EXT", "Field")
    hub = d.item("DEMO-MOTOR-4KW", tag="M0", at=loc, group=grp)
    for n in range(1, leaves + 1):
        leaf = d.item("DEMO-MOTOR-4KW", tag=f"M{n}", at=loc, group=grp)
        d.cable("DEMO-CBL-4G1.5", tag=f"W{n}").core(1, hub["U"], leaf["U"])
    return parts, d.draft(), loc


def _built(leaves: int, document):
    parts, draft, loc = _design(leaves)
    return fr.build(parts, draft, document(loc))


def _system():
    return lambda _loc: fr.document(DocumentPreset.SYSTEM, None, cover=_COVER)


@functools.cache
def _system_build():
    return _built(3, _system())


def _codes(result) -> set[str]:
    return {f.code for f in fr.check(result)}


def test_a_system_document_lays_out_and_writes_its_diagram(tmp_path):
    result = _system_build()
    assert result.diagrams.sheet_places()
    assert "DOCUMENT_NO_DRAWINGS" not in _codes(result)
    inter = tmp_path / "inter"
    fr.write(result, tmp_path / "out", intermediates=inter)
    (source,) = [p.read_text(encoding="utf-8") for p in sorted(inter.glob("*.typ"))]
    assert "#page(width: 594mm, height: 420mm" in source


def test_a_diagram_column_taller_than_a_sheet_is_drawn_on_two_sheets():
    """25 leaves make a column taller than a sheet: it continues on the next sheet, no ERROR."""
    result = _built(25, _system())
    assert result.diagrams.sheet_places() == ((None, 1), (None, 2))
    assert "DOCUMENT_NO_DRAWINGS" not in _codes(result)


def test_a_reading_with_no_line_gives_no_page_and_no_finding():
    result = _built(0, _system())
    assert not result.diagrams.sheet_places()
    assert "DOCUMENT_NO_DRAWINGS" not in _codes(result)


def test_the_cabinets_own_document_writes_no_diagram_record_and_no_page(tmp_path):
    """A unit document keeps no BLOCK_DIAGRAM page by default: nothing is laid out."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    pump_cabinet(d.scope("p"), name="C1")
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, "demo-pump-cabinet", cover=_COVER)
    result = fr.build(parts, d.draft(), document)
    assert not result.diagrams.sheet_places()
    inter = tmp_path / "inter"
    fr.write(result, tmp_path / "out", intermediates=inter)
    assert all("height: 420mm" not in p.read_text(encoding="utf-8") for p in inter.glob("*.typ"))
