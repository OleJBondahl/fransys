"""Every OUT_OF_CONTENT_BOX message names the page and frame cell it stands on (LEGACY-CHAINS 5b).

The messages built the page and cell nowhere, so a consumer could not find the symbol. The cell
text is `derive.drawing_text.position_text`'s, the one form every printed position has.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

_COLUMNS = 9
_AT = re.compile(r" at p(?:\d+\.)?(?P<page>\d+):(?P<column>\d+)(?P<row>[A-Z])$", re.MULTILINE)


class _Strips(NamedTuple):
    X4: Any


@fr.unit(
    "demo-control",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Control",
    number="N-1",
)
def _control(d: Any) -> _Strips:
    d.layout.profile(hide_unused_pins=True, column_gap=16)  # the unit's own profile (model-0192)
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5")
    plus, minus = x4.run("24V", bridged=True), x5.run("0V", bridged=True)
    with d.function("DRV", "Drives"):
        for n in range(1, _COLUMNS + 1):
            coil = d.device(f"K{n}", "DEMO-CTR-3P-24").coil
            first, second = (d.device(f"B{n}{m}", "DEMO-PB-NC").sw for m in (1, 2))
            d.wire(plus, first["A"], wire=("RD", 0.75))
            d.wire(first["B"], second["A"], wire=("RD", 0.75))
            d.wire(second["B"], coil["A1"], wire=("RD", 0.75))
            d.wire(coil["A2"], minus, wire=("BK", 0.75))
            d.layout.chain(first, second, coil)
    return _Strips(x4)


def _findings() -> list[fr.Finding]:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    built = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-control", cover=cover)
    )
    return [f for f in fr.check(built) if f.code == "OUT_OF_CONTENT_BOX"]


def test_each_out_of_content_box_message_names_its_page_and_cell() -> None:
    findings = _findings()
    assert len(findings) == 3
    for finding in findings:
        found = _AT.search(finding.message)
        assert found is not None, finding.message
        assert found["column"] == "8"  # the last frame column: the box stands against the frame
