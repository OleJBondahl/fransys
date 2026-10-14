"""Field case: findings about cores missing on cables of one product list in cable order.

Engineering shape: four harnesses WH1, WH2, WH10 and WH11 each hold a cable of one cable
product. Each cable carries one core where the product has four, so each draws a
`CABLE_CORE_COUNT` finding.

The bug: a finding stores its subjects in Id order, and the product's facet sorts before the
cable. The reader-order key read the facet, which prints no designation and is shared by all four,
so the findings fell back to Id order and a rename of the cables reordered them.

Fixing decision: 0135 (the key reads the first subject that prints a designation).
"""

import fransys as fr
import pytest

_SALTS = ("a", "m", "z", "q", "k")
_NATURAL = ["WH1", "WH2", "WH10", "WH11"]


def _core_count_order(salt: str) -> list[str]:
    d = fr.design("demo_parts", place="C1")
    d.project(title="T", number="N", customer="C", revision=1, author="d")
    for n in (10, 1, 11, 2):
        harness = d.harness(f"WH{n}", name=f"{salt}wh{n}")
        j1 = d.device("J1", "DEMO-CONN-2P", parent=harness, name=f"{salt}a{n}")
        j2 = d.device("J2", "DEMO-CONN-2P", parent=harness, name=f"{salt}b{n}")
        cable = d.cable(f"W{n}", "DEMO-CBL-4G1.5", parent=harness, name=f"{salt}w{n}")
        cable.core(1, j1[1], j2[1])
    model = fr.build(d)
    return [
        fr.derive.item_designation(model.model, one)
        for f in model.findings
        if f.code == "CABLE_CORE_COUNT"
        for one in f.subjects
        if one.kind == "item"
    ]


@pytest.mark.parametrize("salt", _SALTS)
def test_the_findings_list_the_cables_in_natural_order(salt: str) -> None:
    assert _core_count_order(salt) == _NATURAL
