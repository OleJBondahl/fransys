"""Field case (KI-1491, closed): the widen loop's measured re-cut of a 17+17 switch-pole fan puts all 34 terminals on one page in five rows.
32 connections are then not drawn. The in-tree shape never re-cuts, so the case forces the first re-cut; origin/main gives the same cut and miss."""

from collections import Counter
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import RD

from fransys_layout.core import widen

if TYPE_CHECKING:
    import pytest


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("fan", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _fan(u: fr.Design) -> _Io:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 34)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5", 34)
    s1 = u.device("S1", "DEMO-SWITCH-DC-2P")
    for n in range(1, 35):
        u.series(x1[n], s1.main.pole(1 if n <= 17 else 2), x2[n], wire=(RD, 100))
    return _Io(x1)


def test_a_forced_recut_of_a_switch_fan_draws_every_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    true, calls = widen.overflows, []

    def once(*args):
        calls.append(1)
        return (object(),) if len(calls) == 1 else true(*args)

    monkeypatch.setattr(widen, "overflows", once)
    d = fr.design("demo_parts")
    d.add(_fan, "U1", place=None)
    found = Counter(f.code for f in fr.build(d, unit_document("fan")).findings)
    assert found["CONNECTION_NOT_DRAWN"] == 0
