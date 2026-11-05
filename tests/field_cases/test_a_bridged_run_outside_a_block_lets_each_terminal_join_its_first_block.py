"""Field case: a sized run of 4 terminals, bridged, made outside every function block.
The bug: the bridge took every terminal with no block open, so each printed with no block (`-U1-X1:24V:2`).
Fixed by author-0037: a run's bridge takes terminals only inside an open block, else each joins its first block."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU


class _Cab(NamedTuple):
    """A unit with no boundary device to hand back."""


def _designations(*, bridged: bool | tuple[int, int]) -> dict[int, str]:
    """The reference designation of run terminals 2 and 3 after the build."""

    @fr.unit(
        "cab",
        revision=1,
        interface_version=1,
        date="2026-10-14",
        text="First issue",
        by="XX",
        title="Cabinet",
        number="C-1",
    )
    def cab(c):
        psu = c.device("G1", "DEMO-PSU-24")
        run = c.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 4, bridged=bridged)
        c.series(psu.output["+"], run[1].inner, wire=(BU, 0.75))
        for i in (1, 2):
            with c.function(f"F{i}", f"Lamp {i}"):
                lamp = c.device(f"H{i}", "DEMO-LAMP-24")
                c.series(run[i + 1].inner, lamp.lamp["1"], wire=(BU, 0.75))
            c.series(lamp.lamp["2"], psu.output["-"], wire=(BU, 0.75))
        ids[2], ids[3] = run[2].id, run[3].id
        return _Cab()

    ids: dict[int, Any] = {}
    d = fr.design("demo_parts")
    d.add(cab, "U1")
    model = fr.build(d).model
    return {n: fr.derive.reference_designation(model, i) for n, i in ids.items()}


@pytest.mark.parametrize("bridged", [True, (1, 4)])
def test_each_bridged_terminal_joins_the_block_that_first_wires_it(bridged) -> None:
    names = _designations(bridged=bridged)
    assert names[2].startswith("=F1")
    assert names[3].startswith("=F2")
