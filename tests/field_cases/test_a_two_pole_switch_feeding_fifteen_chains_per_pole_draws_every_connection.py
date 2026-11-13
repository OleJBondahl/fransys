"""Field case (KI-755, SWITCH-PORT-FAN): a two-pole switch feeding chains on each pole draws every connection, no short or dangling end.
v0.22.8: CND 28, DWE 4 at 15+15 and CND 9, DWE 1 at 20+10; the cut tied a bundle's lanes across nets and named a lane under an arrow it never reached.
Rules BUNDLE-ARROW and BUNDLE-LANE-END, designer R1890, R1902, R1904."""

from collections import Counter
from contextlib import nullcontext
from functools import cache
from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import RD

from fransys_model.kernel import id_namespace

# KI-763: OUT_OF_PAGE (a row-end tag past the content box) shows at 13+13, 14+14 and others; it is not in _CODES.
_CODES = ("CONNECTION_NOT_DRAWN", "DRAWING_SHORTS_NETS", "DANGLING_WIRE_END", "MARKER_UNPLACED", "REFERENCE_NOT_READABLE")
_SHAPES = [
    (15, 15), (13, 13), (14, 14), (16, 16), (17, 17), (10, 20), (12, 18), (18, 12), (19, 11), (20, 10),
    (21, 9), (22, 8), (24, 6), (25, 5), (30, 2), (2, 30), (15, 1), (1, 15), (24, 24), (2, 40), (12, 40),
]  # fmt: skip


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@cache
def _counts(first: int, second: int, salt: str) -> Counter[str]:
    @fr.unit("fan", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def fan(u: fr.Design) -> _Io:
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", first + second)
        x2 = u.terminal_strip("X2", "DEMO-TB-2.5", first + second)
        s1 = u.device("S1", "DEMO-SWITCH-DC-2P")
        for n in range(1, first + second + 1):
            u.series(x1[n], s1.main.pole(1 if n <= first else 2), x2[n], wire=(RD, 100))
        return _Io(x1)

    with id_namespace(salt) if salt != "-" else nullcontext():
        d = fr.design("demo_parts")
        d.add(fan, "U1", place=None)
        return Counter(f.code for f in fr.build(d, unit_document("fan")).findings if f.code in _CODES)


@pytest.mark.parametrize("salt", ["-", "a"])
@pytest.mark.parametrize(("first", "second"), _SHAPES)
def test_a_switch_pole_fan_draws_every_connection_with_no_short_and_no_dangling_end(first: int, second: int, salt: str) -> None:
    assert dict(_counts(first, second, salt)) == {}
