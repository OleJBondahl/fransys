"""Field case: a block diagram's cable tags stay apart at a larger profile text height.

The engineering shape: a cabinet unit hands back a two-terminal interface strip. Inside it a
loom cable runs from the two terminals to a connector; outside, each terminal has its own cable
to a field device (a motor, a switch). The system overview draws the unit's box with
four cable tags on one edge. The profile sets `text_height_mm` 2.5, the A3 proof setting.

The bug: a column box was one text line high whatever the text room, and its cable tags were
spaced at least one wiring grid apart, so with a text taller than one grid unit two tags on
that edge printed over each other: DIAGRAM_TEXT_OVERLAP (a core wire against the cable tags).
The fix (a measurement, no decision record): ends never sit closer than a text, and a column box is
at least tall enough for its ends at that spacing.
"""

import tempfile
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest
from fransys.pipeline import BuildErrors

_TB = "DEMO-TB-2.5"
_CABLE = "DEMO-CBL-4G1.5"


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit("pump-box", revision=1, interface_version=1, date="2026-10-13", text="1", by="AB")
def _box(d: fr.Design) -> _Io:
    x1 = d.terminal_strip("X1", _TB, 2, interface=True)
    plug = d.device("P1", "DEMO-CONN-2P")
    loom = d.harness("WH1")
    core = d.cable("W1", _CABLE, parent=loom, name="w1c")
    core.core(1, x1[1], plug[1])
    core.core(2, x1[2], plug[2])
    return _Io(x1)


def _built(mm: str) -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# System\n", encoding="utf-8")
        d = fr.design("demo_parts", place="C1")
        d.layout.profile(text_height_mm=Decimal(mm))
        s = d.add(_box, "U1")
        d.cable("W2", _CABLE).core(1, s.x1[1], d.device("M1", "DEMO-MOTOR-4KW")["U"])
        d.cable("W3", _CABLE).core(1, s.x1[2], d.device("K1", "DEMO-SWITCH-2P").x1[1])
        return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


@cache
def _error_codes(mm: str) -> list[str]:
    result = _built(mm)
    try:
        fr.write(result, Path(tempfile.mkdtemp()))
    except BuildErrors as raised:
        return [f.code for f in raised.findings]
    return []


@pytest.mark.parametrize("mm", ["1.8", "2.0", "2.5", "3.5"])
def test_cable_tags_on_one_box_edge_never_overlap(mm: str) -> None:
    assert "DIAGRAM_TEXT_OVERLAP" not in _error_codes(mm)
