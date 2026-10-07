"""HA8 end to end: a housing's crimp contacts are counted once per wired pin in the BOM.

The engineering shape: a 4-way connector housing with a crimp contact part, wired on some pins.
The contact part has no function, so only the BOM knows it (decision model-0170).
"""

import fransys as fr
from fransys.colours import BU


def _contact_line(wired: int) -> fr.derive.BomLine:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Demo cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    p1 = d.device("P1", "DEMO-HSG-4M", contacts="DEMO-CRIMP-M")
    for number in range(1, wired + 1):
        d.wire(strip[number], p1[str(number)], wire=(BU, 0.5))
    model = fr.build(d).model
    (line,) = (b for b in fr.derive.bom_lines(model) if b.mpn == "DEMO-CRIMP-M")
    return line


def test_a_contact_counts_once_per_wired_pin() -> None:
    line = _contact_line(2)
    assert line.count == 2
    assert line.designations == ("-P1",)


def test_a_third_wire_adds_a_third_contact() -> None:
    assert _contact_line(3).count == 3
