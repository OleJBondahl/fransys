"""`interface_reads` feeds `edges` (HL13, model-0176): GND counts in the supply share.

Built through `import fransys as fr` from `examples/demo-parts` only. J2 has two pins on GND
and two signal pins; J1 has two signal pins and the lower designation.
"""

from dataclasses import replace
from fractions import Fraction
from typing import NamedTuple

import fransys as fr
from fransys.colours import BK, RD

from fransys_layout.engines.schematic.read.interfaces import interface_reads
from fransys_layout.stages.edges import BOTTOM, TOP, edges
from fransys_model.vocab.tables import functions, units


class _Io(NamedTuple):
    J1: fr.Device
    J2: fr.Device


@fr.unit("demo-edges", revision=1, interface_version=1, date="2026-10-07", text="t", by="XX")
def _board(d: fr.Design) -> _Io:
    j1 = d.device("J1", "DEMO-CONN-4P", interface=True)
    j2 = d.device("J2", "DEMO-CONN-4P", interface=True)
    inner_1, inner_2 = d.device("R1", "DEMO-CONN-4P"), d.device("R2", "DEMO-CONN-4P")
    for pin in (1, 2):
        d.wire(j1[pin], inner_1[pin], wire=(RD, 0.5))
    for pin in (1, 2, 3, 4):
        d.wire(j2[pin], inner_2[pin], wire=(RD, 0.5))
    return _Io(j1, j2)


def _reads() -> tuple:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    io = d.add(_board, "U1")
    strip = d.terminal_strip("X0", "DEMO-TB-2.5", 2, place="C1")
    d.dc_supply("24VDC", plus=strip[1], minus=strip[2], voltage=24)
    loom = d.harness("W1", place="C1")
    for name, interface in (("1", io.J1), ("2", io.J2)):
        near = d.device(f"P{name}", "DEMO-HSG-4F", parent=loom, place="C1")
        far = d.device(f"Q{name}", "DEMO-HSG-4M", parent=loom, place="C1")
        d.mate(near, interface)
        cable = d.cable(f"C{name}", "DEMO-CBL-4G1.5", parent=loom, place="C1")
        for pin in (1, 2, 3, 4):
            cable.core(pin, near[pin], far[pin])
        if name == "2":
            d.wire(far[1], strip[2], wire=(BK, 0.5))
            d.wire(far[2], strip[2], wire=(BK, 0.5))
    model = fr.build(d).model
    (unit,) = units(model)
    return model, interface_reads(model, unit)


def test_each_boundary_function_is_read_with_its_line_and_share() -> None:
    model, reads = _reads()
    by_name = {r.designation: r for r in reads}
    assert set(by_name) == {"-U1-J1", "-U1-J2"}
    assert all(r.line and r.hint is None for r in reads)
    assert by_name["-U1-J2"].share == Fraction(1, 2)
    assert by_name["-U1-J1"].share == Fraction(0)
    assert {functions(model)[r.function].name for r in reads} == {"x1"}


def test_the_supply_interface_goes_on_top_though_the_other_has_the_lower_designation() -> None:
    """With GND out of the share both read 0, J1 wins the tie and J2 falls below."""
    _, reads = _reads()
    one = [replace(r, width=Fraction(1)) for r in reads]
    got = {r.designation: edges(one)[r.function] for r in one}
    assert got == {"-U1-J2": TOP, "-U1-J1": BOTTOM}
