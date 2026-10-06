"""The spec's worked example, completed with the demo parts (spec acceptance, WP order C2).

`fr.parts`/`fr.author`/`fr.build` do not exist yet (the facade is a later work package):
this test uses `fransys_parts`/`fransys_author` and the model's own passes plus
the layout engine directly, the same pipeline `fr.build` will run.
"""

import fransys_parts
from fransys_author import Design

from fransys_layout.engines.schematic import lay_out_schematic
from fransys_model.derive import allocate_plc, number
from fransys_model.kernel import Severity, freeze, merge
from fransys_model.vocab import ALL_VALIDATORS


def test_the_worked_example_runs_freezes_numbers_allocates_and_lays_out():
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)

    d.project(
        title="Pump station",
        number="P-1001",
        customer="Example Co",
        revision=1,
        author="OJB",
    )
    d.revision(1, date="2026-09-21", text="First issue", created="XX")

    c1 = d.location("C1", "Pump cabinet")
    sup = d.group("SUP", "24 V supply")
    p1 = d.group("P1", "Pump 1")

    # Not in the spec text: a PLC module for k1.fn("coil").plc("do", ...) below to bind to.
    # The worked example shows the authoring syntax for a channel request; it does not show
    # the rack that serves it, so this test adds the smallest one that does.
    d.item("DEMO-PLC-DO-2", tag="A1", at=c1, group=p1)

    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=p1)
    k1 = d.item("DEMO-RLY-2CO-24", name="run", at=c1, group=p1)
    h1 = d.item("DEMO-LAMP-24", name="lamp", at=c1, group=p1, installed=False)
    m1 = d.item("DEMO-MOTOR-4KW", tag="M1", at=d.location("F1", "Field"), group=p1)

    x1 = d.strip("X1", at=c1)
    t1 = x1.terminal("DEMO-TB-2.5", group=sup)
    t2 = x1.terminal("DEMO-TB-2.5", group=p1)
    l1 = x1.terminal("DEMO-TB-2.5", "L", group=p1)

    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, q1["1"])
    wire(q1["2"], k1["A1"], label="W101")
    wire.run(k1["A2"], h1["2"], t2.inner)

    d.net("P24", t1.outer, cls="power", potential="+24V")
    d.net("M24", t2.outer, cls="power", potential="0V")

    w1 = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=12000)
    w1.core(1, l1.outer, m1["U"])

    k1.fn("coil").plc("do", "PUMP1_RUN")

    # t1 (=SUP) is reached by its wire and drawn again in =P1 by the layout engine; it is
    # not itself in the chain (spec A8, worked example, corrected 2026-09-22).
    d.chain(q1, k1.fn("coil"), t2)

    draft = d.draft()
    model = freeze(merge(parts, draft))

    # "freezes without an error finding" (spec acceptance): freeze() itself only raises
    # on a structural problem (it did not, above); engineering findings are the model's
    # validators, run here the way `fr.build` will run them.
    frozen_findings = [f for validator in ALL_VALIDATORS for f in validator(model)]
    assert [f for f in frozen_findings if f.severity is Severity.ERROR] == []

    model, number_findings = number(model)
    model, allocation_findings = allocate_plc(model)
    model, layout_findings = lay_out_schematic(model)

    all_findings = (*number_findings, *allocation_findings, *layout_findings)
    assert [f for f in all_findings if f.severity is Severity.ERROR] == []

    assert model.digests["core"]
    assert model.digests["facet"]
    assert model.digests["layout"]
