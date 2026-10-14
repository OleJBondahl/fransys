"""Field case: a unit's terminal strip fanning out to many breakers builds and writes.

The engineering shape: one `@fr.unit` holding a terminal strip X1 and N two-pole breakers, with one
wire from terminal 1 to the input pin of each breaker. The same fan-out outside a unit was clean.

The bug (v0.15.0): from N=4 the check gave N-1 `DIAGRAM_LINE_OFF_BOX` errors on the unit's overview
(a line end off its box outline), and `fr.write` refused the build. It was fixed on main by
layout-0191 (a box edge keeps a tab text height between its ends, `end_floor` in
`diagram/arrange.py`). This case is a regression lock, not an xfail.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BN


class _Io(NamedTuple):
    X1: fr.TerminalStrip


def _fanout(n: int) -> Any:
    @fr.unit(
        "fanout", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
        title="Fan-out", number="F-1",
    )  # fmt: skip
    def fanout(d: fr.Design) -> _Io:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
        for i in range(n):
            f = d.device(f"F{i + 1}", "DEMO-MCB-2P")
            d.wire(x1[1], f.pole_1["1"], wire=(BN, 2.5))
        return _Io(x1)

    return fanout


@pytest.mark.parametrize("n", [3, 4, 6])
def test_a_unit_fan_out_to_n_breakers_has_no_line_off_box_and_writes(
    n: int, tmp_path: Path
) -> None:
    d = fr.design("demo_parts")
    d.add(_fanout(n), "U1")
    result = fr.build(d)
    assert [f for f in fr.check(result) if f.code == "DIAGRAM_LINE_OFF_BOX"] == []
    assert fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")
