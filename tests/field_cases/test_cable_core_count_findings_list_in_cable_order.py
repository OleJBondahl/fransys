"""Field case: four cables of one product, each with fewer cores than the product has, so each draws a finding.
The bug: the order key read the product facet, which prints no designation, so findings fell back to Id order and renames reordered them.
Fixed by 0135, the key reads the first subject that prints a designation."""

import fransys as fr
import pytest

_SALTS = ("a", "m", "z", "q", "k")
_NATURAL = ["W1", "W2", "W10", "W11"]


def _core_count_order(salt: str) -> list[str]:
    d = fr.design("demo_parts", place="C1")
    d.project(title="T", number="N", customer="C", revision=1, author="d")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    for n in (10, 1, 11, 2):
        j1 = d.device(f"J{n}", "DEMO-CONN-2P", name=f"{salt}a{n}")
        j2 = d.device(f"K{n}", "DEMO-CONN-2P", name=f"{salt}b{n}")
        cable = d.cable(f"W{n}", "DEMO-CBL-4G1.5", name=f"{salt}w{n}")
        cable.core(1, j1[1], j2[1])
    model = fr.build(d)
    return [
        fr.derive.item_designation(model.model, one)
        for f in model.findings
        if f.code in ("CABLE_CORES_FEWER", "CABLE_CORES_MORE")
        for one in f.subjects
        if one.kind == "item"
    ]


@pytest.mark.parametrize("salt", _SALTS)
def test_the_findings_list_the_cables_in_natural_order(salt: str) -> None:
    assert _core_count_order(salt) == _NATURAL
