"""The two root fixtures' `Design`s, not yet built (spec F9).

A module of its own, not part of `conftest.py`: every `packages/*/tests/` directory in this
workspace has its own `conftest.py`, none of them a Python package (no `__init__.py`), so
the bare name `conftest` is ambiguous workspace-wide -- whichever one Python happens to
import first wins the module cache, and `from conftest import ...` elsewhere silently
resolves to the wrong file. `test_facade_swap.py` (spec F9) needs to build each fixture's
`Design` twice in one test run (by hand and through `fr.build`), so these live under a name
that is not ambiguous.
"""

from typing import TYPE_CHECKING

from fransys_author import Design

if TYPE_CHECKING:
    from fransys_model.kernel import Draft


def cabinet_design(parts: Draft) -> Design:
    """The demo cabinet's `Design`."""
    d = Design(parts)
    d.project(
        title="Demo cabinet",
        number="DEMO-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    x1 = d.strip("X1", at=c1)
    t1 = x1.terminal("DEMO-TB-2.5", group=sup)
    t2 = x1.terminal("DEMO-TB-2.5", group=sup)
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=sup)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=sup)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, q1.fn("element")["1"])
    wire(q1.fn("element")["2"], k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], t2.inner)
    d.chain(t1, q1.fn("element"), k1.fn("coil"), t2)
    w1 = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=5000, at=c1)
    w1.core(1, t1.outer, t2.outer)
    return d


def harness_with_board_design(parts: Draft) -> Design:
    """The demo harness-and-board's `Design`."""
    d = Design(parts)
    d.project(
        title="Demo harness and board",
        number="DEMO-2",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    board = d.item(None, tag="A1", at=c1, group=sup)
    relay = d.item("DEMO-RLY-2CO-24", tag="K1", parent=board, at=c1, group=sup)
    conn1 = d.item("DEMO-CONN-2P", tag="X1", parent=board, at=c1, group=sup)
    conn2 = d.item("DEMO-CONN-2P", tag="X2", parent=board, at=c1, group=sup)

    harness = d.harness(tag="WH1", at=c1, group=sup)
    housing = d.item("DEMO-CONN-2P", tag="X3", parent=harness, at=c1, group=sup)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1", parent=harness, at=c1)
    cable.core(1, housing.fn("x1")["2"], conn2.fn("x1")["2"])

    d.mate(housing, conn1)
    d.wiring(colour="BU", gauge="0.75")(conn2.fn("x1")["1"], relay.fn("coil")["A1"])
    return d
