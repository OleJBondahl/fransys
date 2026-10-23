"""Field case: the boxes of one device's two interface connectors print pins, not a code name.

The engineering shape: an I/O unit with one two-connector device whose interface holds its
connectors in two fields (`X1_L1`, `X2_L2`), each landed by a cable core from outside.

The bug: the box printed a name line, the interface field name (`X1_L1`), which reads as code and
told nothing the designation did not. Under a device that prints no connector label the two
boxes then looked identical.

The rule (decision model-0206, amending layout-0155 item 3): a unit interface box prints its
designation, its part line, then the port designations its cores land on, through
`port_designation`. No line is a field name.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document


class _Io(NamedTuple):
    X1_L1: Any
    X2_L2: Any


@fr.unit("demo-io", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _io(d: fr.Design) -> _Io:
    a1 = d.device("A1", "DEMO-IO-2X", interface=True)
    return _Io(a1.x1, a1.x2)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    unit = d.add(_io, "IO")
    p1, p2 = d.device("P1", "DEMO-CONN-2P"), d.device("P2", "DEMO-CONN-2P")
    cable = d.cable("W1", "DEMO-CBL-4G1.5")
    cable.core(1, p1["1"], unit.X1_L1["1"])
    cable.core(2, p2["1"], unit.X2_L2["1"])
    return fr.build(d, layout_trigger_document())


def _boundary_lines(built: fr.BuildResult) -> list[tuple[str, ...]]:
    """The printed lines of each generic box of the unit's interface, from the core's drawings."""
    boxes = [s for d in drawn_pages(built.model).values() for s in d.symbols]
    lines = [tuple(c for row in s.texts for c in row) for s in boxes if s.key == "generic-box"]
    return [box for box in lines if any(c.startswith("-IO-A1-X") for c in box)]


def test_a_boundary_box_prints_no_field_name(built: fr.BuildResult) -> None:
    lines = _boundary_lines(built)
    assert len(lines) == 2
    for box_lines in lines:
        assert not {"X1_L1", "X2_L2"} & set(box_lines)


def test_a_boundary_box_prints_the_pins_its_core_lands_on(built: fr.BuildResult) -> None:
    lines = sorted(_boundary_lines(built))
    assert [box[0] for box in lines] == ["-IO-A1-X1", "-IO-A1-X2"]
    assert [box[-1] for box in lines] == ["-IO-A1-X1:1", "-IO-A1-X2:1"]
