"""Field case: a fan-out cable's lines on the block diagram carry the `.n` branch suffix.

The engineering shape: a 1:3 fan-out cable W1. Core 1 runs from a header J1 to J2, core 2 to J3
and core 3 to J4, so the block diagram draws three lines from the cable's first box. A second
cable W2 joins two boxes.

The bug: the three lines all printed the plain `-W1`, so a reader could not tell the branches
apart, while a harness line of three or more ends prints `-W13.n` on each branch (owner F3,
2026-10-07). Fixed by decision layout-0199 (LEGACY-B3 L17): the lines of a fan-out print `-W1.1`,
`-W1.2`, `-W1.3`; a cable with one line prints plain.
"""

import fransys as fr
import pytest

from fransys_model.derive.block_diagram import diagram_lines

_PLUG = "DEMO-CONN-4P"
_CABLE = "DEMO-CBL-4G1.5"


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Cable W1 from J1 to J2, J3 and J4; cable W2 from J1 to J5."""
    d = fr.design("demo_parts")
    j = {tag: d.device(tag, _PLUG) for tag in ("J1", "J2", "J3", "J4", "J5")}
    fan = d.cable("W1", _CABLE)
    for core, far in enumerate(("J2", "J3", "J4"), start=1):
        fan.core(core, j["J1"][core], j[far][core])
    d.cable("W2", _CABLE).core(1, j["J1"][4], j["J5"][1])
    return fr.build(d)


def test_the_lines_of_a_fan_out_print_a_branch_number(built: fr.BuildResult) -> None:
    printed = sorted(line.designation for line in diagram_lines(built.model, None))
    assert printed == ["-W1.1", "-W1.2", "-W1.3", "-W2"]
