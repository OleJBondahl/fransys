"""Invented models for the cable engine's golden and link tests (CT5-LINK), built from demo-parts.

Each builder returns a `SimpleNamespace` with `model` (the frozen model after `lay_out_cables`),
`frozen` (before it) and the ids a test names. `MODELS` lists them by name for the golden. Nothing
here names a real plant.
"""

from functools import cache
from types import SimpleNamespace
from typing import Any

import fransys_author
import fransys_parts
from demo_designs import cabinet_design, harness_with_board_design

from fransys_layout import lay_out_cables
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, merge

_PROJECT: dict[str, Any] = {
    "title": "Cable blocks",
    "number": "P-1012",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_CABLE, _MOTOR, _TB = "DEMO-CBL-4G1.5", "DEMO-MOTOR-4KW", "DEMO-TB-2.5"


def design():
    """The parts and a fresh `Design` with a project and one revision."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


def lay(parts, draft_of) -> tuple[Any, Any]:
    """`(frozen, laid out)` of `draft_of`'s design, numbered, with the cable pass run."""
    frozen, _ = number_pass(freeze(merge(parts, draft_of.draft())))
    return frozen, lay_out_cables(frozen)[0]


def _built(parts, d, **ids: Any) -> SimpleNamespace:
    frozen, model = lay(parts, d)
    return SimpleNamespace(frozen=frozen, model=model, **ids)


@cache
def demo_cabinet() -> SimpleNamespace:
    """The root demo cabinet: its -W1 joins the two -X1 terminals (a jumper)."""
    parts = fransys_parts.load("demo_parts")
    return _built(parts, cabinet_design(parts))


@cache
def demo_harness() -> SimpleNamespace:
    """The root demo harness and board: harness WH1 with one cable."""
    parts = fransys_parts.load("demo_parts")
    return _built(parts, harness_with_board_design(parts))


@cache
def flat() -> SimpleNamespace:
    """Strips -X1 (6) and -X2 (3), motors -M1 and -M2: W1 straight, W2 a jumper, W3 out of order."""
    parts, d = design()
    er, fld = d.location("ER", "Engine room"), d.location("FLD", "Field")
    g, gf = d.group("ER", "Cabinet"), d.group("FLD", "Field")
    x1, x2 = d.strip("X1", at=er), d.strip("X2", at=er)
    t1 = [x1.terminal(_TB, group=g) for _ in range(6)]
    t2 = [x2.terminal(_TB, group=g) for _ in range(3)]
    m1 = d.item(_MOTOR, tag="M1", at=fld, group=gf)
    m2 = d.item(_MOTOR, tag="M2", at=fld, group=gf)
    w1 = d.cable(_CABLE, tag="W1", at=er, group=g)
    for n, port in enumerate(("U", "V", "W", "PE"), start=1):
        w1.core(n, t1[n - 1].outer, m1[port])
    d.cable(_CABLE, tag="W2", at=er, group=g).core(1, t1[4].outer, t1[5].outer)
    w3 = d.cable(_CABLE, tag="W3", at=er, group=g)
    for n, (near, far) in enumerate(((2, "U"), (0, "V"), (1, "W")), start=1):
        w3.core(n, t2[near].outer, m2[far])
    return _built(parts, d)


@cache
def unit() -> SimpleNamespace:
    """A unit with strip -X5 and its own cable to an external top-level motor."""
    parts, d = design()
    fld, gf = d.location("FLD", "Field"), d.group("FLD", "Field")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    terminal = cab.strip("X5", at=c1).terminal(_TB, group=grp)
    motor = d.item(_MOTOR, tag="M9", at=fld, group=gf, external=True)
    cab.cable(_CABLE, name="w", at=c1).core(1, terminal.outer, motor["U"])
    return _built(parts, d)


@cache
def nested() -> SimpleNamespace:
    """Unit `outer` holds plug -P9 and unit `inner`; `inner`'s cable runs -X5:2 to -P9:2."""
    parts, d = design()
    outer = d.scope("pump1", at=d.location("ER", "Engine room")).unit(
        "outer", revision=1, interface="1"
    )
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = outer.location("C1", "Cabinet")
    p9 = outer.item("DEMO-CONN-2P", tag="P9", at=cab, group=outer.group("OUT", "Outer"))
    inner = outer.scope("io", at=cab).unit("inner", revision=1, interface="1")
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    strip = inner.strip("X5", at=cab)
    terminals = [strip.terminal(_TB, group=inner.group("IN", "Inner")) for _ in range(2)]
    inner.cable(_CABLE, name="w", at=cab).core(1, terminals[1].inner, p9["2"])
    return _built(parts, d)


@cache
def fan_out() -> SimpleNamespace:
    """Strip -X1 with three terminals, cores 1 to 3 to the U port of motors -M1, -M2, -M3."""
    parts, d = design()
    er, fld = d.location("ER", "Engine room"), d.location("FLD", "Field")
    g, gf = d.group("ER", "Cabinet"), d.group("FLD", "Field")
    strip = d.strip("X1", at=er)
    terminals = [strip.terminal(_TB, group=g) for _ in range(3)]
    motors = [d.item(_MOTOR, tag=f"M{n}", at=fld, group=gf) for n in (1, 2, 3)]
    cable = d.cable(_CABLE, tag="W1", at=er, group=g)
    for n, (terminal, motor) in enumerate(zip(terminals, motors, strict=True), start=1):
        cable.core(n, terminal.outer, motor["U"])
    return _built(parts, d, cable=cable.id)


@cache
def swap() -> SimpleNamespace:
    """A unit's two strips and two external motors; cores 2 and 3 swap columns (a 2:2 jog)."""
    parts, d = design()
    fld, gf = d.location("FLD", "Field"), d.group("FLD", "Field")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    x5, x6 = cab.strip("X5", at=c1), cab.strip("X6", at=c1)
    t = [x5.terminal(_TB, group=grp) for _ in range(2)] + [
        x6.terminal(_TB, group=grp) for _ in range(2)
    ]
    m1 = d.item(_MOTOR, tag="M1", at=fld, group=gf, external=True)
    m2 = d.item(_MOTOR, tag="M2", at=fld, group=gf, external=True)
    cable = cab.cable(_CABLE, name="w", at=c1)
    for n, terminal, far in ((1, t[0], m1["U"]), (2, t[1], m2["U"]), (3, t[2], m1["V"])):
        cable.core(n, terminal.outer, far)
    cable.core(4, t[3].outer, m2["V"])
    return _built(parts, d, cable=cable.id)


@cache
def harness_fan() -> SimpleNamespace:
    """Harness WH1: W1 (M1:U, V to M2:U, V, 5000 mm) and W2 (M1:W to M3:U) share end -M1."""
    parts, d = design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH1", at=c1, group=g)
    m1, m2, m3 = (d.item(_MOTOR, tag=f"M{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    w1 = d.cable(_CABLE, tag="W1", parent=harness, at=c1, length_mm=5000)
    w1.core(1, m1["U"], m2["U"])
    w1.core(2, m1["V"], m2["V"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, m1["W"], m3["U"])
    return _built(parts, d, harness=harness.id)


@cache
def chain() -> SimpleNamespace:
    """Harness WH2, a daisy chain: W1 joins -X1 to -X2, W2 joins -X2 to -X3."""
    parts, d = design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH2", at=c1, group=g)
    x1, x2, x3 = (d.item(_MOTOR, tag=f"X{n}", parent=harness, at=c1, group=g) for n in (1, 2, 3))
    d.cable(_CABLE, tag="W1", parent=harness, at=c1).core(1, x1["U"], x2["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, x2["V"], x3["U"])
    return _built(parts, d, harness=harness.id)


@cache
def pair() -> SimpleNamespace:
    """Harness WH3: two independent cables, W1 from -A1 to -B1 and W2 from -A2 to -B2."""
    parts, d = design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH3", at=c1, group=g)
    ends = {
        t: d.item(_MOTOR, tag=t, parent=harness, at=c1, group=g) for t in ("A1", "B1", "A2", "B2")
    }
    d.cable(_CABLE, tag="W1", parent=harness, at=c1).core(1, ends["A1"]["U"], ends["B1"]["U"])
    d.cable(_CABLE, tag="W2", parent=harness, at=c1).core(1, ends["A2"]["U"], ends["B2"]["U"])
    return _built(parts, d, harness=harness.id)


@cache
def ring() -> SimpleNamespace:
    """Harness WH7, an odd ring: W1 joins -A to -B, W2 -B to -C, W3 -C to -A (one core each)."""
    parts, d = design()
    c1, g = d.location("C1", "Cabinet"), d.group("G", "Group")
    harness = d.harness(tag="WH7", at=c1, group=g)
    a, b, c = (d.item(_MOTOR, tag=t, parent=harness, at=c1, group=g) for t in "ABC")
    cables = [d.cable(_CABLE, tag=f"W{n}", parent=harness, at=c1) for n in (1, 2, 3)]
    cables[0].core(1, a["U"], b["U"])
    cables[1].core(1, b["V"], c["V"])
    cables[2].core(1, c["W"], a["W"])
    return _built(parts, d, harness=harness.id, w3=cables[2].id, c=c.id)


@cache
def l1_picture() -> SimpleNamespace:
    """The owner's L1 picture: -X1 down to -H2; core 3 joins -H2:W and -H2:PE (a looped core)."""
    parts, d = design()
    er, fld = d.location("ER", "Engine room"), d.location("FLD", "Field")
    g, gf = d.group("ER", "Cabinet"), d.group("FLD", "Field")
    strip = d.strip("X1", at=er)
    terminals = [strip.terminal(_TB, group=g) for _ in range(2)]
    h2 = d.item(_MOTOR, tag="H2", at=fld, group=gf)
    cable = d.cable(_CABLE, tag="W1", at=er, group=g)
    cable.core(1, terminals[0].outer, h2["U"])
    cable.core(2, terminals[1].outer, h2["V"])
    cable.core(3, h2["W"], h2["PE"])
    return _built(parts, d, cable=cable.id, h2=h2.id)


MODELS = {
    "demo_cabinet": demo_cabinet,
    "demo_harness": demo_harness,
    "flat": flat,
    "unit": unit,
    "nested": nested,
    "fan_out": fan_out,
    "swap": swap,
    "harness_fan": harness_fan,
    "chain": chain,
    "pair": pair,
    "ring": ring,
    "l1_picture": l1_picture,
}
