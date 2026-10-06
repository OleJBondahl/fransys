"""Field case: a board holding several four-pin headers and two two-pin headers draws.

The engineering shape: a board unit built into a PCB schematic document, with n four-pin headers
and two two-pin headers, one net joining a pin of the first four-pin header to a pin of the last
two-pin header. One header or two build; three or more raised "two LinkMarker records share one
key".

The bug (LINKMARKER-KEY, layout-0127): with three or more headers the page set splits and the
net's headers draw once per drawing set. A cut's two markers were keyed by their port, side and
partner port alone, so the two sets' markers of that one cut shared a key.
The fix: such markers also carry their port's placement discriminator, and the coherence lint no
longer expects markers for a cut between two units' sets (layout-0127).
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest

COVER = Path(tempfile.mkdtemp()) / "cover.md"
COVER.write_text("# Demo board\n", encoding="utf-8")


class Interface(NamedTuple):
    first: fr.Device


def _build(four_pin: int):
    tags = [(f"J{i + 1}", "DEMO-CONN-4P") for i in range(four_pin)]
    tags += [(f"J{four_pin + i + 1}", "DEMO-CONN-2P") for i in range(2)]

    @fr.unit(
        "demo-board",
        revision=1,
        interface_version=1,
        date="2026-10-06",
        text="First",
        by="XX",
        title="Demo",
        number="D-1",
    )
    def board_unit(d):
        board = d.device(None, "DEMO-PCB-IO", name="board")
        dev = {tag: d.device(tag, part, parent=board, interface=True) for tag, part in tags}
        d.net("SIG", dev[tags[0][0]].x1[2], dev[tags[-1][0]].x1[1])
        return Interface(dev[tags[0][0]])

    design = fr.design("demo_parts")
    design.add(board_unit, "U1")
    document = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=COVER)
    return fr.build(design, document)


@pytest.mark.parametrize(
    "four_pin",
    [
        1,
        2,
        3,
        4,
        5,
    ],
)
def test_many_headers_on_one_board_draw(four_pin):
    result = _build(four_pin)
    assert not [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
