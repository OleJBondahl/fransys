"""Field case: a harness plug at the top level is mated to a unit's interface connector, and a board
inside that unit mates two of its own connectors.

The bug (v0.9.x): the mates of a model had no public reader. `connector_rows` covers board
connectors only, so a plug mated to a unit's interface connector was reachable only through
the table. Fixing decision: model-0147 (`fr.derive.mates`, one row per mate at every level,
texts as the connector list prints them at system level).
"""

from typing import NamedTuple

import fransys as fr

_CONN = "DEMO-CONN-2P"


class _Io(NamedTuple):
    X1: fr.Fn


@fr.unit(
    "demo-mated-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
def _board(u: fr.Design) -> _Io:
    io = u.device("X1", _CONN, interface=True)
    u.mate(u.device("J1", _CONN), u.device("J2", _CONN))
    return _Io(io.x1)


def test_the_reader_lists_the_top_level_mate_and_the_one_inside_the_unit() -> None:
    d = fr.design("demo_parts")
    io = d.add(_board, "U1")
    plug = d.device("P1", _CONN)
    d.mate(plug, io.X1)
    model = fr.build(d).model
    rows = fr.derive.mates(model)
    assert len(rows) == 2
    assert [(r.a_designation, r.b_designation) for r in rows] == sorted(
        (r.a_designation, r.b_designation) for r in rows
    )
    texts = {(r.a_designation, r.b_designation) for r in rows}
    assert ("-P1", "-U1-X1") in texts
    assert any({a, b} == {"-U1-J1", "-U1-J2"} for a, b in texts)
    listed = {
        c.connector: c.designation
        for item in fr.derive.items(model)
        for c in fr.derive.connector_rows(model, item)
    }
    texts_by_function = {r.a: r.a_designation for r in rows} | {r.b: r.b_designation for r in rows}
    covered = listed.keys() & texts_by_function.keys()
    assert covered
    assert all(listed[f] == texts_by_function[f] for f in covered)
