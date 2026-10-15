"""Field case: a series through a cable whose part has a core table needs no `wire=`.

The engineering shape: a field motor on a four-core cable, wired from a terminal strip. The cores
are the cable part's own: colour, number and PE core are stated by its core table.

The ask (legacy batch A12, C11): `d.series(x4[1:4], w2, m1.motor)` once raised "this series reaches
no supply: give wire=(colour, size)", though every wire of the series is a core with its colour.

Decision author-0055 (API-FRICTION-2 C11): the cores take their colours from the core table, and
`wire=` is not asked for. This base already did it: the wire-row resolver of author-0052 reports
`WIRE_ROW_UNRESOLVED` for a plain hop only, and a core is no plain hop. The case holds that.
"""

import fransys as fr
from fransys.colours import BU


def _design(**series) -> fr.Design:
    d = fr.design("demo_parts")
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5", 4)
    w2 = d.cable("W2", "DEMO-CBL-4G1.5")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(x4[1:4], w2, m1.motor, **series)
    return d


def _cores(d: fr.Design) -> list[tuple[int, str, str]]:
    return [(r.core, r.colour, r.end_b) for r in fr.derive.core_list_rows(fr.build(d).model)]


def test_the_cores_list_the_core_tables_colours_with_no_wire() -> None:
    assert _cores(_design()) == [
        (1, "BN", "-X4:1"),
        (2, "BK", "-X4:2"),
        (3, "GY", "-X4:3"),
        (4, "GNYE", ""),
    ]


def test_no_wire_row_finding_is_raised_for_the_cores() -> None:
    codes = {f.code for f in fr.build(_design()).findings}
    assert "WIRE_ROW_UNRESOLVED" not in codes


def test_a_stated_wire_leaves_the_core_colours_to_the_table() -> None:
    assert _cores(_design(wire=(BU, 1.5))) == _cores(_design())
