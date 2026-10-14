"""Field case: a cable's line label clears the arrow box at its end.

The engineering shape: a 4-core cable `-W1` leaves a cabinet row of four relays, one core on each
coil's A1, and ends at four lamps in the field. At the cabinet its line is one leaving line: a
bar over the four coils, a trunk to an arrow box that names `-W1 <- +FLD-M1`, and a label per
branch (`-W1.1` to `-W1.5`).

The bug: the labels were placed before the arrow box existed, so a branch label could stand under
the box's text: TEXT_OVERLAP on `-W1`. It shows from a text height of 2.6 mm; the house 1.8 mm is
clear (the consumer's repro ran at module 3.9).

Rule (decision layout-0206): a line label keeps clear of the boxes of the stubs its own line ends
in, as of every other box on the page.
"""

import tempfile
from decimal import Decimal
from functools import cache
from pathlib import Path

import fransys as fr
import pytest


@cache
def _built(text_mm: str) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.layout.profile(text_height_mm=Decimal(text_mm))
    cab = d.location("C1", "Cabinet")
    d.location("FLD", "Field")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    for n in range(1, 5):
        relay = d.device(f"K{n}", "DEMO-RLY-2CO-24")
        cable.core(n, relay.coil["A1"], d.device(f"M{n}", "DEMO-LAMP-24", place="FLD")["1"])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


@pytest.mark.parametrize("text_mm", ["1.8", "3.0"])
def test_no_text_overlaps_the_cables_label_or_its_arrow_box(text_mm: str) -> None:
    bad = [
        (f.code, f.message)
        for f in _built(text_mm).findings
        if f.code in {"TEXT_OVERLAP", "WIRE_OVER_LABEL"} and "-W1" in f.message
    ]
    assert bad == []
