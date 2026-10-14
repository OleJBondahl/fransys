"""`core_list_rows` reads the ends off `cable_rows` and `open_core_rows` (CO3, CO4, model-0214)."""

from functools import cache

import fransys as fr


@cache
def _model() -> fr.Model:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w1.core(1, x1[1], h1[1])
    w1.spare(3, at=x1[7])
    w1.core(5, x1[8])
    w1.spare()
    return fr.build(d).model


def test_rows_are_by_core_number_with_the_ends_of_the_cable_and_open_core_rows() -> None:
    model = _model()
    rows = fr.derive.core_list_rows(model)
    assert [row.core for row in rows] == [1, 2, 3, 4, 5, 6]
    (cable,) = [row.cable for row in fr.derive.cable_list_rows(model)]
    (wired,) = fr.derive.cable_rows(model, cable)
    assert (rows[0].end_a, rows[0].end_b) == (wired.end_a_designation, wired.end_b_designation)
    opened = {row.index: row for row in fr.derive.open_core_rows(model, cable)}
    assert [row.end_a for row in rows[1:]] == [opened[i].at_designation for i in (2, 3, 4, 5, 6)]
    assert [row.note for row in rows] == ["", "spare", "spare", "spare", "", ""]
    assert [row.pair for row in rows] == ["P1", "P1", "P2", "P2", "screen P1", "screen P2"]
