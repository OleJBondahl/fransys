"""`fr.write` draws the schematic pages from the core's `Drawing` (SW5)."""

import tempfile
from pathlib import Path

import fransys as fr
from _card_case import card_case_drafts
from _tables_on import TABLES_ON
from fransys import pipeline
from fransys.colours import BU

from fransys_model.kernel import Severity


def _lamps() -> tuple:
    """Two relay coils and one wire: symbols the library holds, no generic box."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    d.detail.wire(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)


def test_a_core_path_build_writes_a_pdf_and_no_error(tmp_path: Path) -> None:
    result = fr.build(*_lamps(), settings=TABLES_ON)
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert [p for p in written if p.suffix == ".pdf"]
    assert not [f for f in fr.check(result) if f.severity is Severity.ERROR]


def test_the_core_path_page_svg_is_the_drawing_of_the_records() -> None:
    result = fr.build(*_lamps(), settings=TABLES_ON)
    (svg,) = pipeline._result_svgs(result).values()
    assert svg.startswith("<svg")
    # the content-box group, two coils and the two contact tables under them (render-0027)
    assert svg.count("<g transform") == 5


def test_a_core_path_card_writes_a_pdf(tmp_path: Path) -> None:
    result = fr.build(*card_case_drafts(16), settings=TABLES_ON)
    assert [p for p in fr.write(result, tmp_path / "out") if p.suffix == ".pdf"]
