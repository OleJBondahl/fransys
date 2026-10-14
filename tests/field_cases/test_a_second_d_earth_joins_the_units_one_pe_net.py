"""Field case: a second `d.earth` in one unit joins that unit's one PE net.

The engineering shape: a cabinet unit places a child unit that holds a 20-screw PE bar exposed in
its interface. The parent earths two motors, each in its own `d.earth` call, and lands a third
pin on the child's bar.

The bug (0.18.3): the second `d.earth` raised AuthorError "'U1/net/PE' already names a different
net record in this scope; use a different name= or tag=", though `d.earth` takes neither.
The rule: a unit has one PE net (pe-bar B0), and each further `d.earth` adds its pins to it
(model-0236).
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.vocab.tables import nets, ports


class _Bar(NamedTuple):
    pe: Any


class _Top(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("earth-child", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _child(u: Any) -> _Bar:
    return _Bar(pe=u.device("PE1", "DEMO-PEBAR-20", interface=True))


@fr.unit("earth-top", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _top(u: Any) -> _Top:
    bar = u.add(_child, "B1")
    m1 = u.device("M1", "DEMO-MOTOR-4KW")
    m2 = u.device("M2", "DEMO-MOTOR-4KW")
    m3 = u.device("M3", "DEMO-MOTOR-4KW")
    u.earth(m1.motor["PE"])
    u.earth(m2.motor["PE"], m3.motor["PE"])
    u.earth(bar.pe.pe["2"])
    return _Top()


def test_every_d_earth_call_in_a_unit_joins_one_pe_net() -> None:
    """The build succeeds, and the unit's one `PE` net holds all four pins."""
    d = fr.design("demo_parts")
    d.add(_top, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "earth", cover=cover))
    top = [n for n in nets(result.model).values() if n.key[:3] == ("U1", "net", "PE")]
    assert len(top) == 1
    assert len(top[0].ports) == 4
    assert {ports(result.model)[p].name for p in top[0].ports} >= {"PE", "2"}
