"""Field case: a text the placer really loses is reported by the build, never dropped silently.

The engineering shape: a contactor with a lamp, a supply and one net, drawn at a house text
height that fits and again at a text height too large for the page's free room, so one marking
has no free candidate and is left unplaced.

The worry: a build runs the engine once per profile in use and splices the pages, so the
first run's findings could be thrown away with its drawing, leaving an overprint with no
warning. The measured answer: texts are placed after the last plan of a run, and a run whose
page is spliced out is replaced by the run that owns it; a lost text on a page that stays
reaches the build as `LABEL_UNPLACED`.

The rule (TEXT-CENSUS): a build that lost a text carries its finding; a build that lost none
carries none.
"""

import tempfile
from decimal import Decimal
from pathlib import Path

import fransys as fr
from fransys.colours import BU


def _build(text_height_mm: str | None) -> list[str]:
    d = fr.design("demo_parts", place="CAB")
    if text_height_mm is None:
        d.layout.profile(hide_unused_pins=True)
    else:
        d.layout.profile(hide_unused_pins=True, text_height_mm=Decimal(text_height_mm))
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamp = d.device("P1", "DEMO-LAMP-24")
        q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.wire(q.aux["14"], lamp["1"], wire=blue)
    d.wire(psu.output["-"], lamp["2"], wire=blue)
    d.net("SIG", q.aux_nc["21"], lamp["2"])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    return [f.code for f in fr.check(result)]


def test_a_lost_text_reaches_the_builds_findings() -> None:
    assert "LABEL_UNPLACED" in _build("3.0")


def test_a_build_that_loses_no_text_carries_no_finding() -> None:
    assert "LABEL_UNPLACED" not in _build(None)
