"""Field case: two placed units each hand back a 4-pin connector, and a top design lands a
4-core cable between them, core n on pin n at both ends.

The bug (v0.7.0): the container holds the connectors only as handles from `d.add`, and no handle
listed its pins, so it could not loop over them; the only pin lists were private. Fixing
decision: author-0020 (`fn.pins`, in the order the connector list prints).
"""

from typing import NamedTuple

import fransys as fr

_CONN = "DEMO-CONN-4P"


class _Io(NamedTuple):
    X1: fr.Fn


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: fr.Design) -> _Io:
    return _Io(d.device("X1", _CONN, interface=True).x1)


def test_a_loop_over_pins_lands_core_n_on_pin_n_at_both_ends() -> None:
    d = fr.design("demo_parts", place="C1")
    a, b = d.add(_board, "U1"), d.add(_board, "U2")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
    for core, (pin_a, pin_b) in enumerate(zip(a.X1.pins, b.X1.pins, strict=True), start=1):
        w1.core(core, pin_a, pin_b)
    model = fr.build(d).model
    (cable,) = (i for i, item in fr.derive.items(model).items() if item.tag == "W1")
    rows = fr.derive.cable_rows(model, cable)
    assert [(r.index, r.end_a_designation, r.end_b_designation) for r in rows] == [
        (n, f"-U1-X1:{n}", f"-U2-X1:{n}") for n in (1, 2, 3, 4)
    ]
