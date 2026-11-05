"""Field case: every diagram line of a fan-out cable prints the cable's own designation.
The bug: layout-0199 gave the three lines `-W1.1`, `-W1.2` and `-W1.3`, so the harness-line suffix read as three cables.
Fixed by layout-0259, each line prints `-W1`; harness lines on cabinet pages keep `.n`."""

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


def test_every_line_of_a_fan_out_prints_the_plain_designation(built: fr.BuildResult) -> None:
    printed = sorted(line.designation for line in diagram_lines(built.model, None))
    assert printed == ["-W1", "-W1", "-W1", "-W2"]
