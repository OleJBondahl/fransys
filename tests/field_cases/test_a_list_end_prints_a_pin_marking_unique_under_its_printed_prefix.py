"""Field case: a board with several connector functions whose pins are all marked P01, P02.
The bug: a list end fell back to the pin name, as the marking repeats across the connectors of one item.
Fixed by MARK-DOOR (R1799(3)): a marking is unique among the ports under one printed prefix (`-U2-J3`)."""

import fransys as fr
import pytest


@pytest.fixture(scope="module")
def built() -> tuple[fr.BuildResult, object]:
    d = fr.design("demo_parts", place="C1")
    u2 = d.device("U2", "DEMO-BOARD-4J")
    return fr.build(d), u2


def test_a_marking_repeated_across_connectors_prints_behind_each_connectors_prefix(built) -> None:
    result, u2 = built
    assert fr.derive.port_designation(result.model, u2.j3["2"].id) == "-U2-J3:P02"
    assert fr.derive.port_designation(result.model, u2.j1["1"].id) == "-U2-J1:P01"


def test_a_marking_repeated_within_one_connector_falls_back_to_the_name(built) -> None:
    result, u2 = built
    assert fr.derive.port_designation(result.model, u2.j4["2"].id) == "-U2-J4:2"
