"""The core path warns once per authored hint call it does not read (SW9, model-0336)."""

from typing import NamedTuple

import fransys as fr
from fransys._layout_core import lay_out_on_core

from electrical_symbols import LIBRARY
from fransys_model.layout import SideHint, layout_of

_CODE = "HINT_NOT_READ"


class _Io(NamedTuple):
    X1: fr.TerminalStrip
    X2: fr.TerminalStrip


@fr.unit("demo-unread-core", revision=1, interface_version=1, date="2026-10-18", text="t", by="XX")
def _board(d: fr.Design) -> _Io:
    return _Io(
        d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True),
        d.terminal_strip("X2", "DEMO-TB-2.5", 2, interface=True),
    )


def _laid(*, hints: int):
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    io = d.add(_board, "U1")
    with d.function("FIELD", "Unit feed"):
        d.series(io.X1[1], k1.coil, io.X1[2], wire=("BU", 0.75))
    for strip in (io.X1, io.X2)[:hints]:
        d.layout.side(strip, fr.ABOVE)
    model = fr.build(d).model
    return model, lay_out_on_core(model, LIBRARY)[1]


def test_one_authored_call_gives_one_warning_on_the_core_path() -> None:
    model, findings = _laid(hints=1)
    records = layout_of(model, SideHint).values()
    assert len(records) == 2  # one record per terminal of the hinted strip
    warned = [f for f in findings if f.code == _CODE]
    (one,) = warned
    assert set(one.subjects) == {h.function for h in records}
    assert not [f for f in findings if f.code == "PLACEMENT_PROBLEM"]


def test_two_authored_calls_give_two_warnings_on_the_core_path() -> None:
    model, findings = _laid(hints=2)
    assert len(layout_of(model, SideHint)) == 4
    assert len([f for f in findings if f.code == _CODE]) == 2


def test_no_hint_gives_none_on_the_core_path() -> None:
    _, findings = _laid(hints=0)
    assert not [f for f in findings if f.code in (_CODE, "PLACEMENT_PROBLEM")]
