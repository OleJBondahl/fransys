"""Field case: a cable whose cores run J1-J2 and J2-J3 draws two block-diagram lines, none from J1 to J3.
The bug: a cable reaching three boxes drew one line from its first box to each other, so J1-J3 joined boxes no core joins.
Fixed by BLOCK-LINES-REAL (KI-1461): one line for each pair of boxes a core joins."""

import fransys as fr
import pytest

from fransys_model.derive.block_diagram import box_lines, diagram_lines


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Cable W1 with core 1 from J1 to J2 and core 2 from J2 to J3."""
    d = fr.design("demo_parts")
    j = {tag: d.device(tag, "DEMO-CONN-4P") for tag in ("J1", "J2", "J3")}
    cable = d.cable("W1", "DEMO-CBL-4G1.5")
    cable.core(1, j["J1"][1], j["J2"][1])
    cable.core(2, j["J2"][2], j["J3"][2])
    return fr.build(d)


def test_a_chain_cable_draws_only_the_pairs_its_cores_join(built: fr.BuildResult) -> None:
    """KI-1461: a line joins two boxes only when a core of its cable joins them."""
    pairs = sorted(tuple(sorted(box_lines(built.model, box, None)[0] for box in (line.a, line.b))) for line in diagram_lines(built.model, None))
    assert pairs == [("-J1", "-J2"), ("-J2", "-J3")]
