import xml.etree.ElementTree as ET

import pytest
from fransys_wago import modules_xml

from fransys_model.vocab.enums import SignalType

pytestmark = pytest.mark.wp("wago")


def test_channel_type_comes_from_the_channel_template(new_rack):
    """A device whose request disagrees with the channel it is bound to does not change its type."""
    rack = new_rack()
    part = rack.part("p", "750-X", (SignalType.DI, SignalType.AI_CURRENT))
    module = rack.module(part, "m", "A1", 1)
    rack.device("d0", "B1", "Door", module.channels[0], signal=SignalType.AI_CURRENT)
    rack.device("d1", "B2", "Level", module.channels[1], signal=SignalType.DI)
    (module_element,) = ET.fromstring(modules_xml(rack.freeze(), rack.rack))  # noqa: S314 -- parsing this test's own `modules_xml` output, not untrusted input
    assert [(c.get("Input"), c.get("Type")) for c in module_element] == [
        ("0", "bool"),
        ("0", "short"),
    ]


def test_the_demo_rack_is_one_module_element_per_module_with_channels(demo_rack):
    root = ET.fromstring(modules_xml(demo_rack.freeze(), demo_rack.rack))  # noqa: S314 -- same: parsing the demo rack's own generated XML, not untrusted input
    assert root.tag == "Modules"
    assert len(root) == 4
