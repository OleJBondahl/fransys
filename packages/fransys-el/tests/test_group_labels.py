"""Two aspect nodes with one label (a unit's group and the design's) are two core groups."""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BU
from fransys_el.placement_groups import label_of
from fransys_el.write_ids import group_ids

from fransys_model.vocab import aspect_nodes


class _Feed(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("label-feed", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _feed(d: fr.Design) -> _Feed:
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    with d.function("FEED", "Unit's own feed"):
        d.series(dc.plus, x1[1], dc.minus, wire=(BU, 0.75))
    return _Feed(x1)


def _model():
    d = fr.design("demo_parts")
    io = d.add(_feed, "U1")
    g2 = d.device("G2", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC2", g2.output)
    with d.function("FEED", "The design's feed"):
        d.series(dc.plus, io.X1[2], dc.minus, wire=(BU, 0.75))
    return fr.build(d).model


def test_same_label_in_a_unit_and_the_design_gives_two_group_texts() -> None:
    """Each of the two `FEED` function nodes has its own text, and `group_ids` maps both back."""
    model = _model()
    nodes = [n for n, r in aspect_nodes(model).items() if r.label == "FEED"]
    assert len(nodes) == 2
    texts = {label_of(model, n) for n in nodes}
    assert len(texts) == 2
    found = group_ids(model)
    assert {found[t] for t in texts} == set(nodes)
