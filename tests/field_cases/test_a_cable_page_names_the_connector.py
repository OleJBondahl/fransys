"""Field case: two devices with two connectors each, joined by two cables, one per connector pair.
The bug: each cable's end labels and the cable list named the device only, so the two cables read alike.
Fixed by model-0206, an end on one connector prints the connector segment (`+C1-A1-X1`) via connector_segment."""

import re

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys_render import cable_blocks

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_cables
from fransys_model.derive import cable_list_rows


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    a1, a2 = d.device("A1", "DEMO-IO-2X"), d.device("A2", "DEMO-IO-2X")
    for n in (1, 2):
        cable = d.cable(f"W{n}", "DEMO-CBL-4G1.5")
        cable.core(1, getattr(a1, f"x{n}")["1"], getattr(a2, f"x{n}")["1"])
    return fr.build(d, unit_document(cabinet))


def test_the_cable_list_names_each_connector(built: fr.BuildResult) -> None:
    rows = {row.designation: (row.from_label, row.to_label) for row in cable_list_rows(built.model)}
    assert rows == {"-W1": ("+C1-A1-X1", "+C1-A2-X1"), "-W2": ("+C1-A1-X2", "+C1-A2-X2")}


def test_the_cable_page_end_label_names_the_connector(built: fr.BuildResult) -> None:
    labels = [
        {t for t in re.findall(r">([^<]*)</text>", svg) if "A" in t and "W" not in t}
        for svg in dict(cable_blocks(built.model, lay_out_cables(built.model, LIBRARY), LIBRARY)).values()
    ]
    assert sorted(map(sorted, labels)) == [
        ["+C1-A1-X1", "+C1-A2-X1"],
        ["+C1-A1-X2", "+C1-A2-X2"],
    ]
