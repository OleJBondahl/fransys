"""Field case: a location document's lists and BOM omit the harness its drawings omit.

The engineering shape: a cabinet with two relay modules and one harness whose two female plugs
(crimped housings) are mated to the modules' headers, one plain wire between the plugs. The
cabinet's schematic document adds the connector list and keeps the BOM. A system document of the
same design sits beside it.

The bug: a location document draws no harness (ruling W-CABINET), yet its connector list headed
a table for each plug of the harness and its BOM bought the plugs' housings and contacts. The
document's lists and its drawings disagreed about what the document covers.

The rule (decision pdf-0043, owner 2026-10-16): a document's lists cover exactly what its
drawings draw. The cabinet's connector list and BOM leave the harness out; the system document's
BOM still holds its parts, so no part drops out of every BOM.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_pdf
import fransys_render
from fransys.colours import RD

from fransys_model.derive import document_sheets_of
from fransys_model.vocab.tables import documents

_PLUG_PARTS = {"DEMO-HSG-4F", "DEMO-CRIMP-F"}


@cache
def _built() -> tuple[fr.BuildResult, dict[str, str], Any]:
    d = fr.design("demo_parts")
    d.project(title="Looms", number="LM-1", customer="Demo Co", revision=1, author="d")
    cabinet = d.location("C1", "Cabinet")
    m1 = d.device("M1", "DEMO-RELAY-MOD-2", place="C1")
    m2 = d.device("M2", "DEMO-RELAY-MOD-2", place="C1")
    w1 = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    p2 = d.device("P2", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, m1.j1)
    d.mate(p2, m2.j1)
    d.detail.wire(p1[1], p2[1], wire=(RD, 0.5))
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cover\n", encoding="utf-8")
        add = (fr.PageKind.CONNECTOR_LIST, fr.PageKind.BOM)
        built = fr.build(
            d,
            fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover, add=add),
            fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover),
        )
    texts = {
        str(record.preset): fransys_pdf.source(
            built.model, doc_id, {}, fransys_render.sheets(document_sheets_of(built.model))
        )
        for doc_id, record in documents(built.model).items()
    }
    return built, texts, cabinet.id


def _cabinet_text() -> str:
    return _built()[1]["DocumentPreset.CABINET_SCHEMATIC"]


def test_the_cabinet_connector_list_keeps_the_modules_headers() -> None:
    """The modules sit in the cabinet and are drawn: their header tables stay."""
    assert 'text("-M1-J1 (cont.)")' in _cabinet_text()
    assert 'text("-M2-J1 (cont.)")' in _cabinet_text()


def test_the_cabinet_connector_list_has_no_table_for_the_harness_plugs() -> None:
    """The harness is not drawn by the cabinet document, so its plugs head no table."""
    assert 'text("-W1-P1 (cont.)")' not in _cabinet_text()
    assert 'text("-W1-P2 (cont.)")' not in _cabinet_text()


def test_the_cabinet_bom_does_not_buy_the_harness_plugs() -> None:
    """The plugs' housings and contacts are the harness's parts, not the cabinet drawings'."""
    text = _cabinet_text()
    assert "DEMO-RELAY-MOD-2" in text
    assert not any(f'text("{mpn}")' in text for mpn in _PLUG_PARTS)


def test_every_bom_line_the_cabinet_document_drops_is_in_the_system_bom() -> None:
    """No part is lost: what the cabinet BOM leaves out, the system BOM still lists."""
    built, _, node = _built()
    model, text = built.model, _cabinet_text()
    unfiltered = fr.derive.bom_lines(model, scope=node)
    dropped = {line.mpn for line in unfiltered if f'text("{line.mpn}")' not in text}
    assert dropped == _PLUG_PARTS
    system = {line.mpn for line in fr.derive.bom_lines(model, scope=fr.derive.TOP_LEVEL)}
    assert dropped <= system
