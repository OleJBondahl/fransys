"""Field case: a cable page and the cable list name the connector, not just the device.

The engineering shape: two devices with two connectors each, joined by two cables, one per
connector pair (`-A1-X1` to `-A2-X1`, `-A1-X2` to `-A2-X2`).

The bug: each cable's page labelled its end boxes with the device only (`+C1-A1`), and the cable
list's From and To said the same, so the two cables read alike and the connectors could not be
told apart.

The rule (decision model-0206): an end whose cores land on one connector of a device that prints
its connectors as sub-parts prints that connector's segment behind the device
(`+C1-A1-X1`), through `connector_segment`, in the end label and in the cable list.
"""

import re

import fransys as fr
import pytest
from _model_build_cover import layout_trigger_document
from fransys_render import cable_blocks

from fransys_model.derive import cable_list_rows


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    a1, a2 = d.device("A1", "DEMO-IO-2X"), d.device("A2", "DEMO-IO-2X")
    for n in (1, 2):
        cable = d.cable(f"W{n}", "DEMO-CBL-4G1.5")
        cable.core(1, getattr(a1, f"x{n}")["1"], getattr(a2, f"x{n}")["1"])
    return fr.build(d, layout_trigger_document())


def test_the_cable_list_names_each_connector(built: fr.BuildResult) -> None:
    rows = {row.designation: (row.from_label, row.to_label) for row in cable_list_rows(built.model)}
    assert rows == {"-W1": ("+C1-A1-X1", "+C1-A2-X1"), "-W2": ("+C1-A1-X2", "+C1-A2-X2")}


def test_the_cable_page_end_label_names_the_connector(built: fr.BuildResult) -> None:
    labels = [
        {t for t in re.findall(r">([^<]*)</text>", svg) if "A" in t and "W" not in t}
        for svg in dict(cable_blocks(built.model)).values()
    ]
    assert sorted(map(sorted, labels)) == [
        ["+C1-A1-X1", "+C1-A2-X1"],
        ["+C1-A1-X2", "+C1-A2-X2"],
    ]
