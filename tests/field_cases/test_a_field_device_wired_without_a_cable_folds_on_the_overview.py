"""Field case: a unit with two outside lamps, one on a cable and one on loose wires.
The bug: the field-device fold read member boxes from the system level, which holds only cable ends, so fr.check raised KeyError.
Fixed by the O9 fact (no new decision), a fold member's box text is level_box_lines, not a system-level box lookup."""

import re
from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import BU


class _Io(NamedTuple):
    cabled: fr.Run
    loose: fr.Run
    neutral: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cab(u: fr.Design) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        cabled, loose, neutral = x1.run("L1", 1), x1.run("L2", 1), x1.run("N", 2)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.series(cabled[1].inner, lamp["1"], wire=(BU, 0.5))
        back = u.terminal_strip("X2", "DEMO-TB-2.5").run("N", 1)
        u.series(back[1].inner, lamp["2"], wire=(BU, 0.5))
    return _Io(cabled, loose, neutral)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="FC", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    unit = d.add(_cab, "U1", place=None)
    with d.function("OUT", "Outside"):
        on_cable = d.device("H8", "DEMO-LAMP-24")
        cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
        cable.core(1, on_cable["1"], unit.cabled[1])
        cable.core(2, on_cable["2"], unit.neutral[1])
        on_wire = d.device("H9", "DEMO-LAMP-24")
        d.series(unit.loose[1].outer, on_wire["1"], wire=(BU, 0.5))
        d.series(unit.neutral[2].outer, on_wire["2"], wire=(BU, 0.5))
    return fr.build(d, system_document())


def test_the_check_completes(built) -> None:
    result = built
    fr.check(result)


def test_the_overview_lists_both_lamps_as_members_of_the_field_box(built, tmp_path) -> None:
    written = fr.write(built, tmp_path)
    html = next(p for p in written if p.name.endswith("overview.html")).read_text()
    assert re.search(r'Field devices \(2\)"\],"members":\[.*?\+CAB-H8.*?\+CAB-H9', html)
