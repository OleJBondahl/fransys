"""Invented models for the diagram engine's tests, each built once (`functools.cache`).

Every builder returns a frozen, numbered `Model` (no facade, no layout engine run). `station` is
the block-diagram spec's worked example 1; `chain(n)` is a path of boxes; `one_box`, `fanout`
and `loose` are the three hand models of the diagram findings.
"""

from functools import cache
from itertools import pairwise
from typing import Any

import fransys_author
import fransys_parts

from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import Model, freeze, merge

_PROJECT: dict[str, Any] = {
    "title": "Block diagram",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_CABLE, _MOTOR, _SWITCH = "DEMO-CBL-4G1.5", "DEMO-MOTOR-4KW", "DEMO-SWITCH-2P"
_TB, _CONN = "DEMO-TB-2.5", "DEMO-CONN-2P"


def _design():
    """The demo parts and an empty design with its project and first revision."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


def _numbered(parts, d) -> Model:
    """Merge, freeze and number: the model a layout engine reads."""
    return number_pass(freeze(merge(parts, d.draft())))[0]


@cache
def station() -> Model:
    """Cabinet `-U1` (strips X1, X3, connector C1), motors M1 and M2, switch K1, strip X0.

    Four cables: W1 X1:1 to X0, W11 X3 to M1, W21 X3 to M2, W3 K1 to plug P3 mated to C1.
    The system reading has 4 lines over 5 boxes; K1 and X0 are by others.
    """
    parts, d = _design()
    u = d.scope("cab").unit("demo-pump-cabinet", revision=2, interface="1", tag="U1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    grp = u.group("FLD", "Field wiring")
    x1, x3 = u.strip("X1"), u.strip("X3")
    t1 = x1.terminal(_TB, group=grp)
    t11, t21 = (x3.terminal(_TB, group=grp) for _ in range(2))
    c1 = u.item(_CONN, tag="C1", group=grp)
    for handle in (t1, t11, t21, c1):
        u.boundary(handle)
    field = d.group("EXT", "Field")
    t0 = d.strip("X0", external=True).terminal(_TB, group=field)
    m1 = d.item(_MOTOR, tag="M1", group=field)
    m2 = d.item(_MOTOR, tag="M2", group=field)
    k1 = d.item(_SWITCH, tag="K1", group=field, external=True)
    d.cable(_CABLE, tag="W1").core(1, t1.outer, t0.outer)
    d.cable(_CABLE, tag="W11").core(1, t11.outer, m1["U"])
    d.cable(_CABLE, tag="W21").core(1, t21.outer, m2["U"])
    w3 = d.cable(_CABLE, tag="W3")
    p3 = d.item(_CONN, tag="P3", parent=w3, group=field)
    w3.core(1, k1.fn("x1")["1"], p3["1"])
    d.mate(p3, c1)
    return _numbered(parts, d)


@cache
def chain(n: int) -> Model:
    """`n` top-level motors M1..Mn in a row, each joined to the next by one cable: `n - 1` lines."""
    parts, d = _design()
    group = d.group("FLD", "Field")
    motors = [d.item(_MOTOR, tag=f"M{i}", group=group) for i in range(1, n + 1)]
    for i, (a, b) in enumerate(pairwise(motors), start=1):
        d.cable(_CABLE, tag=f"W{i}").core(1, a["U"], b["U"])
    return _numbered(parts, d)


@cache
def one_box() -> Model:
    """Motor M1 and cable W1 whose one core joins two ports of M1: one box, no line."""
    parts, d = _design()
    m1 = d.item(_MOTOR, tag="M1", group=d.group("FLD", "Field"))
    d.cable(_CABLE, tag="W1").core(1, m1["U"], m1["V"])
    return _numbered(parts, d)


@cache
def fanout() -> Model:
    """Cable W1 with two cores reaching motors M1, M2 and switch K1 from M1: three boxes."""
    parts, d = _design()
    group = d.group("FLD", "Field")
    m1, m2 = (d.item(_MOTOR, tag=f"M{i}", group=group) for i in (1, 2))
    k1 = d.item(_SWITCH, tag="K1", group=group)
    w1 = d.cable(_CABLE, tag="W1")
    w1.core(1, m1["U"], m2["U"])
    w1.core(2, m1["V"], k1.fn("x1")["1"])
    return _numbered(parts, d)


@cache
def loose() -> Model:
    """Motors M1 and M2 joined by a wire with no cable."""
    parts, d = _design()
    group = d.group("FLD", "Field")
    m1, m2 = (d.item(_MOTOR, tag=f"M{i}", group=group) for i in (1, 2))
    d.wiring(colour="BU", gauge="0.75")(m1["U"], m2["U"])
    return _numbered(parts, d)
