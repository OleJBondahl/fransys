"""Every OUT_OF_CONTENT_BOX message names the page and frame cell it stands on (LEGACY-CHAINS 5b).

The messages built the page and cell nowhere, so a consumer could not find the symbol. The cell
text is `derive.drawing_text.position_text`'s, the one form every printed position has. The
overflow is vertical (layout-0175 moves a column that is too wide, not one that is too tall).
"""

import re
import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

_CHAIN = 20  # one column of twenty switches stands taller than the content box
_AT = re.compile(r" at (?P<column>\d+)(?P<row>[A-Z]) \((?:\+\w+)*p(?:\d+\.)?\d+", re.MULTILINE)


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
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5")
    plus = x4.run("24V", bridged=True)
    with d.function("DRV", "Drives"):
        switches = [d.device(f"B{n}", "DEMO-PB-NC").sw for n in range(_CHAIN)]
        d.wire(plus, switches[0]["A"], wire=("RD", 0.75))
        for above, below in pairwise(switches):
            d.wire(above["B"], below["A"], wire=("RD", 0.75))
        d.layout.chain(*switches)
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
    assert findings  # a column taller than the box cannot move to another page (layout-0175)
    for finding in findings:
        found = _AT.search(finding.message)
        assert found is not None, finding.message
        assert found["column"] == "1"
        assert found["row"] == "F"  # the last frame row: the chain runs out of the box below
