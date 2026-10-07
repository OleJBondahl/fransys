"""The HARNESS-ASSEMBLIES worked example builds end to end (acceptance 11, model-0171, model-0172).

A contactor on flying leads wears a housing, a relay module is mated to a harness plug, and the
harness `W1` carries two wires between its plugs.
"""

import fransys as fr
from fransys.colours import BK, RD

from fransys_model.derive import TOP_LEVEL, bom_lines, harness_wires, item_designation
from fransys_model.kernel import Severity
from fransys_model.vocab.tables import items


def _build() -> fr.BuildResult:
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
    return fr.build(d)


def test_the_worked_example_builds_names_the_fitted_housing_and_counts_the_contacts() -> None:
    """Can-fail: each fact below is one of the lanes' rules, so dropping any one changes it."""
    result = _build()
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    assert [f.code for f in result.findings if f.severity is Severity.WARNING] == []
    named = {
        "/".join(i.key): item_designation(result.model, i.id) for i in items(result.model).values()
    }
    assert named["K/J1"] == "K1-J1"
    assert named["K/P1"] == "W1-P1"
    assert named["K/P2"] == "W1-P2"
    (harness,) = [i.id for i in items(result.model).values() if i.tag == "W1"]
    assert len(harness_wires(result.model, harness)) == 2
    counts = {line.mpn: line.count for line in bom_lines(result.model, TOP_LEVEL)}
    assert counts["DEMO-CRIMP-F"] == 6
    assert counts["DEMO-CRIMP-M"] == 2
