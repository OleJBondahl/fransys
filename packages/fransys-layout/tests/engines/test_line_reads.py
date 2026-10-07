"""HL1, HL6: which conductors a line carries and which connector functions get a box.

Built through the facade from `examples/demo-parts`; nothing names a real plant.
"""

import fransys as fr
from fransys.colours import BK, BN, RD

from fransys_layout.engines.schematic.read.harness_lines import (
    boxed_functions,
    line_reads,
    plug_functions,
)
from fransys_model.derive import harness_wires
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import conductors, functions, items


def _build():
    """A harness `W1` of two wires and a one-core cable between plugs mated to `J1` and `M1`;
    a two-core cable `W2` and a one-core cable `W3` between plain housings; `U1` mated to none."""
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    with d.function("K", "Contactor control"):
        k1 = d.device("K1", "DEMO-CTR-LEADS", place="C1")
        j1 = d.device(
            "J1",
            "DEMO-HSG-4F",
            parent=k1,
            place="C1",
            contacts="DEMO-CRIMP-F",
            joins={"1": k1.coil["A1"], "2": k1.coil["A2"], "3": k1.aux["13"], "4": k1.aux["14"]},
        )
        m1 = d.device("M1", "DEMO-RELAY-MOD-2", place="C1")
        w1 = d.harness("W1", place="C1")
        p1 = d.device("P1", "DEMO-HSG-4M", parent=w1, place="C1", contacts="DEMO-CRIMP-M")
        p2 = d.device("P2", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
        d.mate(p1, j1)
        d.mate(p2, m1.j1)
        d.wire(p1[1], p2[1], wire=(RD, 0.5))
        d.wire(p1[2], p2[2], wire=(BK, 0.5))
        d.cable("W1C", "DEMO-CBL-4G1.5", length_m=1, parent=w1).core(BN, p1[3], p2[3])
        _cable(d, "W2", 2)
        _cable(d, "W3", 1)
        d.device("U1", "DEMO-HSG-4F", place="C1", contacts="DEMO-CRIMP-F")
    return fr.build(d).model


def _cable(d, tag, cores):
    a = d.device(f"{tag}A", "DEMO-HSG-4M", place="C1", contacts="DEMO-CRIMP-M")
    b = d.device(f"{tag}B", "DEMO-HSG-4M", place="C1", contacts="DEMO-CRIMP-M")
    cable = d.cable(tag, "DEMO-CBL-4G1.5", length_m=1)
    for core, colour in zip(range(1, cores + 1), (BN, BK), strict=False):
        cable.core(colour, a[core], b[core])


def _tag(model, tag):
    (item,) = [i.id for i in items(model).values() if i.tag == tag]
    return item


def test_the_harness_is_one_line_with_its_two_wires_carried() -> None:
    model = _build()
    reads = line_reads(model)
    line = next(one for one in reads.lines if one.owner == _tag(model, "W1"))
    assert len(line.conductors) == 3  # two wires and the one core of its cable
    assert {row.conductor for row in harness_wires(model, line.owner)} <= set(line.conductors)
    assert list(line.conductors) == sorted(line.conductors)
    assert len(line.ends) == 2
    assert set(line.conductors) <= reads.carried


def test_a_two_core_cable_is_a_line_and_a_one_core_cable_is_none() -> None:
    model = _build()
    reads = line_reads(model)
    owners = [one.owner for one in reads.lines]
    assert _tag(model, "W2") in owners
    assert _tag(model, "W3") not in owners
    assert owners == sorted(owners)
    one_core = [c.id for c in conductors(model).values() if c.carrier == _tag(model, "W3")]
    assert len(one_core) == 1
    assert not set(one_core) & reads.carried


def _function(model, item_tag):
    (found,) = [f.id for f in functions(model).values() if f.item == _tag(model, item_tag)]
    return found


def test_boxed_functions_hold_the_plugs_and_the_mated_connectors_only() -> None:
    model = _build()
    boxed = boxed_functions(model)
    plugs = plug_functions(line_reads(model))
    assert {_function(model, "P1"), _function(model, "P2")} <= plugs
    assert plugs <= boxed
    assert _function(model, "J1") in boxed
    assert any(
        f.kind is FunctionKind.CONNECTOR and f.id in boxed for f in functions(model).values()
    )
    assert all(functions(model)[f].kind is FunctionKind.CONNECTOR for f in boxed)
    assert _function(model, "U1") not in boxed
